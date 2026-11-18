"""Testes: historico com mudanca de status, recarga da matriz e encodings .npz. Sem camera."""
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import acesso
import config
import main
import reconhecimento

T0 = datetime(2026, 6, 1, 8, 0)
T1 = datetime(2026, 6, 1, 8, 2)   # 2 min depois (dentro dos 5 min)


# ---------- 1) Historico: mudou o status -> registra mesmo dentro do intervalo ----------
def test_mudou_o_status_registra_dentro_do_intervalo(tmp_path):
    arq = str(tmp_path / "hist.csv")
    acesso.registrar_acesso("1", "Joao", "Prensa_B", acesso.NEGADO, "x", 0.9, T0, arq)
    assert acesso.registrar_acesso("1", "Joao", "Prensa_B", acesso.LIBERADO, "", 0.9, T1, arq)
    assert pd.read_csv(arq)["Status"].tolist() == ["NEGADO", "LIBERADO"]


def test_mesmo_status_continua_sendo_ignorado(tmp_path):
    arq = str(tmp_path / "hist.csv")
    acesso.registrar_acesso("1", "Joao", "Prensa_B", acesso.NEGADO, "x", 0.9, T0, arq)
    assert not acesso.registrar_acesso("1", "Joao", "Prensa_B", acesso.NEGADO, "x", 0.9, T1, arq)
    assert len(pd.read_csv(arq)) == 1


def test_voltou_ao_status_anterior_tambem_registra(tmp_path):
    arq = str(tmp_path / "hist.csv")
    acesso.registrar_acesso("1", "Joao", "Prensa_B", acesso.NEGADO, "x", 0.9, T0, arq)
    acesso.registrar_acesso("1", "Joao", "Prensa_B", acesso.LIBERADO, "", 0.9, T1, arq)
    assert acesso.registrar_acesso("1", "Joao", "Prensa_B", acesso.NEGADO, "x", 0.9, datetime(2026, 6, 1, 8, 3), arq)
    assert len(pd.read_csv(arq)) == 3


# ---------- 2) Matriz recarregada quando o CSV muda ----------
def escrever_matriz(caminho, nivel, mtime):
    caminho.write_text(f"Matricula,Celula,Nivel,Validade\n1,Prensa_B,{nivel},2099-12-31\n", encoding="utf-8")
    os.utime(caminho, (mtime, mtime))     # mtime controlado, sem depender do relogio


def test_matriz_sem_mudanca_retorna_none(tmp_path):
    csv = tmp_path / "matriz.csv"
    escrever_matriz(csv, "L", 1000)
    nova, mtime = acesso.matriz_mudou(None, str(csv))      # primeira leitura
    assert nova is not None and mtime == 1000
    assert acesso.matriz_mudou(mtime, str(csv)) == (None, 1000)


def test_matriz_modificada_e_recarregada(tmp_path):
    csv = tmp_path / "matriz.csv"
    escrever_matriz(csv, "L", 1000)
    _, mtime = acesso.matriz_mudou(None, str(csv))
    escrever_matriz(csv, "U", 2000)
    nova, mtime = acesso.matriz_mudou(mtime, str(csv))
    assert mtime == 2000 and nova.iloc[0]["Nivel"] == "U"


def test_matriz_ilegivel_mantem_a_antiga(tmp_path):
    assert acesso.matriz_mudou(1000, str(tmp_path / "nao_existe.csv")) == (None, 1000)
    vazio = tmp_path / "vazio.csv"
    vazio.write_text("", encoding="utf-8")                 # arquivo no meio de um salvamento
    assert acesso.matriz_mudou(1000, str(vazio)) == (None, 1000)


def novo_estado(resultado, matricula="1"):
    return {"identidade": matricula, "seguidos": 8, "caixa": None, "resultado": resultado, "similaridade": 0.9}


def test_matriz_mudou_recalcula_a_pessoa_na_frente_da_camera(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CAMINHO_HISTORICO", str(tmp_path / "hist.csv"))
    monkeypatch.setattr(config, "SOM_ATIVO", False)
    nomes = {"1": "Joao"}
    antiga = pd.DataFrame([["1", "Prensa_B", "L", "2099-12-31"]], columns=["Matricula", "Celula", "Nivel", "Validade"])
    nova = antiga.assign(Nivel="U")

    estado = novo_estado(main.decidir_acesso("1", 0.9, "Prensa_B", antiga, nomes))
    assert estado["resultado"][0] == acesso.SUPERVISAO

    main.reavaliar_acesso(estado, "Prensa_B", nova, nomes)
    assert estado["resultado"][0] == acesso.LIBERADO
    # os dois status entraram no historico, mesmo dentro dos 5 minutos
    assert pd.read_csv(config.CAMINHO_HISTORICO)["Status"].tolist() == ["SUPERVISAO", "LIBERADO"]


def test_reavaliar_sem_ninguem_confirmado_nao_faz_nada(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CAMINHO_HISTORICO", str(tmp_path / "hist.csv"))
    estado = novo_estado(None)
    main.reavaliar_acesso(estado, "Prensa_B", pd.DataFrame(columns=["Matricula", "Celula", "Nivel", "Validade"]), {})
    assert estado["resultado"] is None
    assert not os.path.exists(config.CAMINHO_HISTORICO)


# ---------- 3) Encodings em .npz (sem pickle) ----------
def test_encodings_npz_ida_e_volta(tmp_path):
    arq = str(tmp_path / "enc.npz")
    original = {"1": [np.arange(128, dtype=np.float32), np.ones(128, dtype=np.float32)], "1001": [np.zeros(128, dtype=np.float32)]}
    reconhecimento.salvar_encodings(original, arq)
    lido = reconhecimento.carregar_encodings(arq)
    assert set(lido) == {"1", "1001"}
    assert len(lido["1"]) == 2
    assert np.array_equal(lido["1"][0], original["1"][0])


def test_encodings_npz_nao_usa_pickle(tmp_path):
    arq = str(tmp_path / "enc.npz")
    reconhecimento.salvar_encodings({"1": [np.ones(128, dtype=np.float32)]}, arq)
    with np.load(arq, allow_pickle=False) as f:      # falharia se houvesse objetos pickle
        assert f["1"].shape == (1, 128)


def test_sem_arquivo_de_encodings_retorna_vazio(tmp_path):
    assert reconhecimento.carregar_encodings(str(tmp_path / "nao_existe.npz")) == {}
