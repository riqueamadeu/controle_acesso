"""Testes das regras de acesso. Nao usam camera. Rode com: pytest -v"""
import os
import sys
from datetime import date, datetime

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np

import acesso
import config
import reconhecimento

HOJE = date(2026, 6, 1)   # data fixa para os testes

MATRIZ = pd.DataFrame([
    # Matricula, Celula, Nivel, Validade
    ["1", "Prensa_B", "U", "2027-01-01"],   # liberado normal
    ["2", "Prensa_B", "O", "2027-01-01"],   # liberado (nivel O)
    ["3", "Prensa_B", "I", "2027-01-01"],   # supervisao (I)
    ["4", "Prensa_B", "L", "2027-01-01"],   # supervisao (L)
    ["5", "Prensa_B", "U", "2026-05-31"],   # vencido
    ["6", "Prensa_B", "U", "2026-06-20"],   # vence em 19 dias
    ["7", "Prensa_B", "U", "2026-07-01"],   # vence em exatamente 30 dias
    ["8", "Prensa_B", "U", "2026-06-01"],   # vence hoje (ainda valido)
    ["9", "Prensa_B", "U", "2026-07-02"],   # 31 dias: sem aviso
], columns=["Matricula", "Celula", "Nivel", "Validade"])


def test_rosto_nao_reconhecido():
    assert acesso.verificar_acesso(None, "Prensa_B", MATRIZ, HOJE) == (acesso.NEGADO, "Operador nao cadastrado")


def test_sem_treinamento_para_a_celula():
    assert acesso.verificar_acesso("1", "Solda_C", MATRIZ, HOJE) == (acesso.NEGADO, "Sem treinamento para esta celula")


def test_matricula_fora_da_matriz():
    assert acesso.verificar_acesso("999", "Prensa_B", MATRIZ, HOJE)[0] == acesso.NEGADO


def test_treinamento_vencido():
    assert acesso.verificar_acesso("5", "Prensa_B", MATRIZ, HOJE) == (acesso.NEGADO, "Treinamento vencido em 31/05/2026")


@pytest.mark.parametrize("mat,nivel", [("3", "I"), ("4", "L")])
def test_niveis_I_e_L_exigem_supervisao(mat, nivel):
    assert acesso.verificar_acesso(mat, "Prensa_B", MATRIZ, HOJE) == (
        acesso.SUPERVISAO, f"Liberado somente com supervisao (nivel {nivel})")


@pytest.mark.parametrize("mat", ["1", "2"])
def test_niveis_U_e_O_liberados(mat):
    assert acesso.verificar_acesso(mat, "Prensa_B", MATRIZ, HOJE) == (acesso.LIBERADO, "")


def test_aviso_de_reciclagem():
    assert acesso.verificar_acesso("6", "Prensa_B", MATRIZ, HOJE) == (acesso.LIBERADO, "Reciclagem vence em 19 dias")


def test_aviso_no_limite_de_30_dias():
    assert acesso.verificar_acesso("7", "Prensa_B", MATRIZ, HOJE) == (acesso.LIBERADO, "Reciclagem vence em 30 dias")


def test_vence_hoje_ainda_vale():
    assert acesso.verificar_acesso("8", "Prensa_B", MATRIZ, HOJE) == (acesso.LIBERADO, "Reciclagem vence em 0 dias")


def test_sem_aviso_com_31_dias():
    assert acesso.verificar_acesso("9", "Prensa_B", MATRIZ, HOJE) == (acesso.LIBERADO, "")


# ---------- Registro no historico ----------
def test_registro_cria_cabecalho_e_grava(tmp_path):
    arq = str(tmp_path / "hist.csv")
    agora = datetime(2026, 6, 1, 8, 0, 0)
    assert acesso.registrar_acesso("1", "Joao", "Prensa_B", "LIBERADO", "", 0.9, agora, arq)
    linhas = open(arq, encoding="utf-8").read().splitlines()
    assert linhas[0] == "Data,Hora,Matricula,Nome,Celula,Status,Motivo,Similaridade"
    assert linhas[1] == "2026-06-01,08:00:00,1,Joao,Prensa_B,LIBERADO,,0.900"


def test_intervalo_minimo_bloqueia_repeticao(tmp_path):
    arq = str(tmp_path / "hist.csv")
    assert acesso.registrar_acesso("1", "Joao", "Prensa_B", "LIBERADO", "", 0.9, datetime(2026, 6, 1, 8, 0), arq)
    # 4 minutos depois: ignorado
    assert not acesso.registrar_acesso("1", "Joao", "Prensa_B", "LIBERADO", "", 0.9, datetime(2026, 6, 1, 8, 4), arq)
    assert len(pd.read_csv(arq)) == 1


def test_registra_de_novo_apos_o_intervalo(tmp_path):
    arq = str(tmp_path / "hist.csv")
    acesso.registrar_acesso("1", "Joao", "Prensa_B", "LIBERADO", "", 0.9, datetime(2026, 6, 1, 8, 0), arq)
    # volta do almoco
    assert acesso.registrar_acesso("1", "Joao", "Prensa_B", "LIBERADO", "", 0.9, datetime(2026, 6, 1, 13, 0), arq)
    assert len(pd.read_csv(arq)) == 2


def test_intervalo_e_por_matricula_e_celula(tmp_path):
    arq = str(tmp_path / "hist.csv")
    t = datetime(2026, 6, 1, 8, 0)
    acesso.registrar_acesso("1", "Joao", "Prensa_B", "LIBERADO", "", 0.9, t, arq)
    assert acesso.registrar_acesso("1", "Joao", "Solda_C", "NEGADO", "x", 0.9, t, arq)   # outra celula
    assert acesso.registrar_acesso("2", "Maria", "Prensa_B", "LIBERADO", "", 0.9, t, arq)  # outra pessoa


def test_historico_nunca_e_sobrescrito(tmp_path):
    arq = str(tmp_path / "hist.csv")
    acesso.registrar_acesso("1", "Joao", "Prensa_B", "LIBERADO", "", 0.9, datetime(2026, 6, 1, 8, 0), arq)
    acesso.registrar_acesso("2", "Maria", "Prensa_B", "LIBERADO", "", 0.9, datetime(2026, 6, 1, 8, 1), arq)
    assert len(pd.read_csv(arq)) == 2


def test_registra_negado_e_desconhecido(tmp_path):
    arq = str(tmp_path / "hist.csv")
    acesso.registrar_acesso(None, "", "Prensa_B", "NEGADO", "Operador nao cadastrado", 0.3, datetime(2026, 6, 1, 8, 0), arq)
    linha = open(arq, encoding="utf-8").read().splitlines()[1]
    assert linha == "2026-06-01,08:00:00,DESCONHECIDO,,Prensa_B,NEGADO,Operador nao cadastrado,0.300"


def test_intervalo_usa_config(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "INTERVALO_MINUTOS", 1)
    arq = str(tmp_path / "hist.csv")
    acesso.registrar_acesso("1", "Joao", "Prensa_B", "LIBERADO", "", 0.9, datetime(2026, 6, 1, 8, 0), arq)
    assert acesso.registrar_acesso("1", "Joao", "Prensa_B", "LIBERADO", "", 0.9, datetime(2026, 6, 1, 8, 2), arq)


# ---------- Reconhecimento: limiar de similaridade (vetores sinteticos, sem camera) ----------
VET_A = np.array([1.0, 0.0])
ENCODINGS = {"1": [VET_A], "2": [np.array([0.0, 1.0]), np.array([0.8, 0.6])]}  # operador 2 tem 2 vetores


def test_identifica_o_mais_parecido():
    matricula, sim = reconhecimento.identificar(ENCODINGS, np.array([1.0, 0.05]))
    assert matricula == "1" and sim > 0.99


def test_usa_o_melhor_vetor_entre_varios_do_mesmo_operador():
    # parecido com o 2o vetor do operador 2 (0.8, 0.6)
    matricula, _ = reconhecimento.identificar(ENCODINGS, np.array([0.8, 0.6]))
    assert matricula == "2"


def test_abaixo_do_limiar_e_desconhecido():
    # (0, -1) tem similaridade <= 0 com todos
    matricula, sim = reconhecimento.identificar(ENCODINGS, np.array([0.0, -1.0]))
    assert matricula is None and sim < config.LIMIAR_SIMILARIDADE


def test_limiar_padrao_e_0363():
    assert config.LIMIAR_SIMILARIDADE == 0.363


def test_limiar_exato_e_aceito(monkeypatch):
    # vetor com similaridade exatamente igual ao limiar de teste (>= aceita)
    monkeypatch.setattr(config, "LIMIAR_SIMILARIDADE", 0.6)
    matricula, _ = reconhecimento.identificar({"1": [VET_A]}, np.array([0.6, 0.8]))
    assert matricula == "1"
    monkeypatch.setattr(config, "LIMIAR_SIMILARIDADE", 0.61)
    assert reconhecimento.identificar({"1": [VET_A]}, np.array([0.6, 0.8]))[0] is None


def test_sem_encodings_cadastrados():
    assert reconhecimento.identificar({}, VET_A)[0] is None


# ---------- Arquivos reais criados a partir dos exemplos ----------
def test_cria_arquivos_reais_a_partir_dos_exemplos(tmp_path, monkeypatch):
    ops, mat = tmp_path / "operadores.csv", tmp_path / "matriz.csv"
    monkeypatch.setattr(config, "CAMINHO_OPERADORES", str(ops))
    monkeypatch.setattr(config, "CAMINHO_MATRIZ", str(mat))
    assert not ops.exists() and not mat.exists()
    operadores = acesso.carregar_operadores()
    matriz = acesso.carregar_matriz()
    assert ops.exists() and mat.exists()
    assert list(operadores.columns) == ["Matricula", "Nome", "Funcao"]
    assert list(matriz.columns) == ["Matricula", "Celula", "Nivel", "Validade"]


def test_nao_sobrescreve_arquivo_real_existente(tmp_path, monkeypatch):
    ops = tmp_path / "operadores.csv"
    ops.write_text("Matricula,Nome,Funcao\n7,Eu,Teste\n", encoding="utf-8")
    monkeypatch.setattr(config, "CAMINHO_OPERADORES", str(ops))
    assert acesso.carregar_operadores()["Nome"].tolist() == ["Eu"]
