"""
acesso.py - Regras de negocio (SEM camera).
Aqui ficam: verificar se o operador pode entrar na celula e gravar o historico.

Niveis da matriz de versatilidade (modelo ILUO):
  I = em treinamento | L = opera com supervisao | U = opera sozinho | O = pode treinar outros
"""
import os
import csv
import shutil
from datetime import date, datetime, timedelta

import pandas as pd

import config

# Textos dos status (usados no main.py e nos testes)
LIBERADO = "LIBERADO"
SUPERVISAO = "SUPERVISAO"
NEGADO = "NEGADO"

COLUNAS_HISTORICO = ["Data", "Hora", "Matricula", "Nome", "Celula", "Status", "Motivo", "Similaridade"]


def garantir_arquivo(caminho, exemplo):
    """Se o arquivo real nao existe, cria uma copia a partir do arquivo de exemplo."""
    if not os.path.exists(caminho):
        shutil.copyfile(exemplo, caminho)
        print(f"Criado {os.path.basename(caminho)} a partir do exemplo.")


def carregar_matriz(caminho=None):
    """Le a matriz de qualificacao do CSV (Matricula sempre como texto)."""
    if caminho is None:
        garantir_arquivo(config.CAMINHO_MATRIZ, config.CAMINHO_MATRIZ_EXEMPLO)
        caminho = config.CAMINHO_MATRIZ
    return pd.read_csv(caminho, dtype=str)


def matriz_mudou(ultimo_mtime, caminho=None):
    """
    Compara a data de modificacao do CSV da matriz com a ultima conhecida.
    Retorna (matriz_nova, mtime): matriz_nova e None se nada mudou (ou se o arquivo
    nao pode ser lido agora, ex.: o Excel esta salvando - tentamos de novo na proxima checagem).
    """
    caminho = caminho or config.CAMINHO_MATRIZ
    try:
        mtime = os.path.getmtime(caminho)
        if mtime == ultimo_mtime:
            return None, ultimo_mtime
        return pd.read_csv(caminho, dtype=str), mtime
    except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError):
        return None, ultimo_mtime


def carregar_operadores(caminho=None):
    """Le a lista de operadores do CSV (Matricula sempre como texto)."""
    if caminho is None:
        garantir_arquivo(config.CAMINHO_OPERADORES, config.CAMINHO_OPERADORES_EXEMPLO)
        caminho = config.CAMINHO_OPERADORES
    return pd.read_csv(caminho, dtype=str)


def verificar_acesso(matricula, celula, matriz, hoje=None):
    """
    Decide se o operador pode entrar na celula.
    matricula: texto da matricula, ou None se o rosto nao foi reconhecido
    matriz: DataFrame com Matricula, Celula, Nivel, Validade
    hoje: data de referencia (padrao = hoje; passamos uma data fixa nos testes)
    Retorna (status, motivo).
    """
    if hoje is None:
        hoje = date.today()

    # 1) Rosto nao reconhecido
    if matricula is None:
        return NEGADO, "Operador nao cadastrado"

    # 2) Procura a linha do operador para esta celula
    linhas = matriz[(matriz["Matricula"] == matricula) & (matriz["Celula"] == celula)]
    if linhas.empty:
        return NEGADO, "Sem treinamento para esta celula"

    nivel = linhas.iloc[0]["Nivel"].strip().upper()
    validade = datetime.strptime(linhas.iloc[0]["Validade"].strip(), "%Y-%m-%d").date()

    # 3) Treinamento vencido
    if validade < hoje:
        return NEGADO, "Treinamento vencido em " + validade.strftime("%d/%m/%Y")

    # 4) Nivel I ou L: so com supervisao
    if nivel in ("I", "L"):
        return SUPERVISAO, f"Liberado somente com supervisao (nivel {nivel})"

    # 5) Nivel U ou O: liberado (com aviso se a validade esta perto)
    if nivel in ("U", "O"):
        dias = (validade - hoje).days
        if dias <= config.DIAS_AVISO_RECICLAGEM:
            return LIBERADO, f"Reciclagem vence em {dias} dias"
        return LIBERADO, ""

    # Nivel digitado errado na planilha: por seguranca, nega
    return NEGADO, f"Nivel invalido na matriz ({nivel})"


def ja_registrado_recentemente(matricula, celula, agora, caminho=None, status=None):
    """
    True se a mesma matricula+celula foi registrada ha menos de INTERVALO_MINUTOS
    COM O MESMO STATUS. Se o status mudou (ex.: NEGADO -> LIBERADO), nao conta como repeticao.
    (status=None ignora o status e so olha matricula+celula.)
    """
    caminho = caminho or config.CAMINHO_HISTORICO
    if not os.path.exists(caminho):
        return False
    historico = pd.read_csv(caminho, dtype=str)
    do_operador = historico[(historico["Matricula"] == matricula) & (historico["Celula"] == celula)]
    if do_operador.empty:
        return False
    ultima = do_operador.iloc[-1]
    if status is not None and ultima["Status"] != status:
        return False
    momento = datetime.strptime(ultima["Data"] + " " + ultima["Hora"], "%Y-%m-%d %H:%M:%S")
    return agora - momento < timedelta(minutes=config.INTERVALO_MINUTOS)


def registrar_acesso(matricula, nome, celula, status, motivo, similaridade, agora=None, caminho=None):
    """
    Grava uma linha no historico (modo append: nunca apaga o que ja existe).
    Retorna True se gravou, False se foi ignorado pelo intervalo minimo.
    Desconhecidos (matricula None) sao gravados com Matricula "DESCONHECIDO".
    """
    caminho = caminho or config.CAMINHO_HISTORICO
    agora = agora or datetime.now()
    matricula = matricula or "DESCONHECIDO"

    if ja_registrado_recentemente(matricula, celula, agora, caminho, status):
        return False

    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    arquivo_novo = not os.path.exists(caminho)
    with open(caminho, "a", newline="", encoding="utf-8") as f:   # "a" = append
        escritor = csv.writer(f)
        if arquivo_novo:                       # cabecalho so se o arquivo nao existia
            escritor.writerow(COLUNAS_HISTORICO)
        escritor.writerow([
            agora.strftime("%Y-%m-%d"), agora.strftime("%H:%M:%S"),
            matricula, nome, celula, status, motivo,
            f"{similaridade:.3f}",
        ])
    return True
