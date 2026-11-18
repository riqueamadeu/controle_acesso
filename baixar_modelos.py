"""
baixar_modelos.py - Baixa os dois modelos do OpenCV para a pasta modelos/.
  - YuNet (detecta rostos)  ~ 0,2 MB
  - SFace (gera o vetor do rosto) ~ 37 MB
Rode uma vez:  python baixar_modelos.py
Fonte: https://github.com/opencv/opencv_zoo
"""
import os
import urllib.request

import config

URL_BASE = "https://github.com/opencv/opencv_zoo/raw/main/models/"
MODELOS = [
    (config.MODELO_DETECTOR, URL_BASE + "face_detection_yunet/face_detection_yunet_2023mar.onnx"),
    (config.MODELO_RECONHECEDOR, URL_BASE + "face_recognition_sface/face_recognition_sface_2021dec.onnx"),
]


def baixar(caminho, url):
    """Baixa um arquivo (pula se ja existe). Baixa para .tmp e so renomeia no final."""
    nome = os.path.basename(caminho)
    if os.path.exists(caminho):
        print(f"Ja existe: {nome}")
        return
    print(f"Baixando {nome} ...")
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    temporario = caminho + ".tmp"
    urllib.request.urlretrieve(url, temporario)
    os.replace(temporario, caminho)
    print(f"OK: {nome} ({os.path.getsize(caminho) / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    for caminho, url in MODELOS:
        try:
            baixar(caminho, url)
        except Exception as erro:
            print(f"ERRO ao baixar {os.path.basename(caminho)}: {erro}")
            print("Verifique a internet ou baixe manualmente em https://github.com/opencv/opencv_zoo")
            raise SystemExit(1)
