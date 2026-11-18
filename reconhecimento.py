"""
reconhecimento.py - Detectar rostos e identificar o operador.

Usamos dois modelos prontos do proprio OpenCV (nao precisa de dlib):
  - YuNet (FaceDetectorYN): acha onde esta o rosto na imagem
  - SFace (FaceRecognizerSF): transforma o rosto em um "vetor" de 128 numeros
Rostos da mesma pessoa geram vetores parecidos (similaridade alta).
"""
import time

import cv2
import numpy as np

import config


def abrir_camera(indice=None):
    """Abre a camera. Retorna o objeto de video ou None (com mensagem) se falhar."""
    indice = config.INDICE_CAMERA if indice is None else indice
    camera = cv2.VideoCapture(indice)
    ok = False
    if camera.isOpened():
        # No Mac a camera demora um pouco para "aquecer": tentamos ler varias vezes
        for _ in range(30):
            ok, _ = camera.read()
            if ok:
                break
            time.sleep(0.1)
    if not ok:
        camera.release()
        print(f"\nERRO: nao foi possivel abrir a camera (indice {indice}).")
        print("Dicas:")
        print(" - Mac: Ajustes do Sistema > Privacidade e Seguranca > Camera: permita o Terminal / VS Code.")
        print(" - Windows: Configuracoes > Privacidade e seguranca > Camera: permita apps de area de trabalho.")
        print(" - Feche outros apps que usam a camera (Zoom, FaceTime...).")
        print(" - Tente outro indice em INDICE_CAMERA no config.py (1 ou 2 se usa o iPhone).")
        return None
    return camera


def criar_detector():
    """Cria o detector de rostos YuNet (o tamanho de entrada e ajustado a cada imagem)."""
    return cv2.FaceDetectorYN.create(config.MODELO_DETECTOR, "", (320, 320), 0.8)


def criar_reconhecedor():
    """Cria o modelo SFace que gera o vetor de cada rosto."""
    return cv2.FaceRecognizerSF.create(config.MODELO_RECONHECEDOR, "")


def detectar_rostos(detector, imagem):
    """Retorna uma lista de rostos detectados (cada um e uma linha de 15 numeros)."""
    altura, largura = imagem.shape[:2]
    detector.setInputSize((largura, altura))
    _, rostos = detector.detect(imagem)
    return [] if rostos is None else list(rostos)


def gerar_encoding(reconhecedor, imagem, rosto):
    """Recorta/alinha o rosto e devolve o vetor de 128 numeros."""
    rosto_alinhado = reconhecedor.alignCrop(imagem, rosto)
    return reconhecedor.feature(rosto_alinhado)[0]


def similaridade(vetor_a, vetor_b):
    """Similaridade do cosseno entre dois vetores. Quanto MAIOR, mais parecidos (max 1)."""
    return float(np.dot(vetor_a, vetor_b) / (np.linalg.norm(vetor_a) * np.linalg.norm(vetor_b)))


def carregar_encodings(caminho=None):
    """Le data/encodings.npz (sem pickle) -> dicionario {matricula: [vetor, vetor, ...]}."""
    caminho = caminho or config.CAMINHO_ENCODINGS
    try:
        with np.load(caminho, allow_pickle=False) as arquivo:
            return {matricula: list(arquivo[matricula]) for matricula in arquivo.files}
    except FileNotFoundError:
        return {}


def salvar_encodings(encodings, caminho=None):
    """Grava {matricula: [vetor, ...]} em .npz (uma matriz de numeros por matricula, sem pickle)."""
    caminho = caminho or config.CAMINHO_ENCODINGS
    np.savez(caminho, **{matricula: np.array(vetores) for matricula, vetores in encodings.items()})


def identificar(encodings, vetor):
    """
    Compara o vetor com TODOS os vetores de TODOS os operadores e fica com a MAIOR similaridade.
    Retorna (matricula, similaridade). A matricula e None se a maior similaridade
    for menor que LIMIAR_SIMILARIDADE (rosto desconhecido).
    """
    melhor_matricula, melhor_sim = None, -1.0
    for matricula, lista_de_vetores in encodings.items():
        for v in lista_de_vetores:
            s = similaridade(vetor, v)
            if s > melhor_sim:
                melhor_matricula, melhor_sim = matricula, s
    if melhor_sim >= config.LIMIAR_SIMILARIDADE:
        return melhor_matricula, melhor_sim
    return None, melhor_sim
