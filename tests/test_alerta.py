"""Testes do som de alerta: nunca pode derrubar o programa, em nenhum sistema."""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
import main


def test_mac_usa_afplay(monkeypatch):
    chamadas = []
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(main.subprocess, "Popen", lambda args: chamadas.append(args))
    main.tocar_alerta()
    assert chamadas and chamadas[0][0] == "afplay"


def test_falha_do_som_nao_derruba(monkeypatch):
    def quebra(args):
        raise FileNotFoundError("afplay")
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(main.subprocess, "Popen", quebra)
    main.tocar_alerta()   # nao deve levantar excecao


def test_windows_usa_winsound(monkeypatch):
    tocados = []
    falso = types.SimpleNamespace(SND_ALIAS=1, SND_ASYNC=2, PlaySound=lambda nome, flags: tocados.append(nome))
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setitem(sys.modules, "winsound", falso)
    main.tocar_alerta()
    assert tocados == ["SystemHand"]


def test_linux_usa_beep_do_terminal(monkeypatch, capsys):
    monkeypatch.setattr(sys, "platform", "linux")
    main.tocar_alerta()
    assert "\a" in capsys.readouterr().out


def test_som_desativado_nao_toca(monkeypatch):
    monkeypatch.setattr(config, "SOM_ATIVO", False)
    monkeypatch.setattr(main.subprocess, "Popen", lambda args: (_ for _ in ()).throw(AssertionError("tocou")))
    monkeypatch.setattr(sys, "platform", "darwin")
    main.tocar_alerta()
