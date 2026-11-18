"""
atualizar_encodings.py - Le as fotos de dataset/<matricula>/ e gera data/encodings.npz.
Rode com:  python atualizar_encodings.py
Assim o main.py nao precisa reprocessar as fotos a cada execucao.
"""
import os
import shutil

import cv2

import config
import reconhecimento


def gerar_encodings():
    """Percorre as fotos, gera os vetores e salva o .npz. Retorna o dicionario gerado."""
    detector = reconhecimento.criar_detector()
    reconhecedor = reconhecimento.criar_reconhecedor()
    encodings = {}

    if not os.path.isdir(config.PASTA_DATASET):
        os.makedirs(config.PASTA_DATASET)

    for matricula in sorted(os.listdir(config.PASTA_DATASET)):
        pasta = os.path.join(config.PASTA_DATASET, matricula)
        if not os.path.isdir(pasta):
            continue
        vetores = []
        for nome_arquivo in sorted(os.listdir(pasta)):
            imagem = cv2.imread(os.path.join(pasta, nome_arquivo))
            if imagem is None:
                continue                      # nao era imagem
            rostos = reconhecimento.detectar_rostos(detector, imagem)
            if len(rostos) != 1:              # exige exatamente 1 rosto na foto
                print(f"  Ignorada ({len(rostos)} rostos): {matricula}/{nome_arquivo}")
                continue
            vetores.append(reconhecimento.gerar_encoding(reconhecedor, imagem, rostos[0]))
        if vetores:
            encodings[matricula] = vetores
            print(f"Operador {matricula}: {len(vetores)} foto(s) processada(s)")
            if config.APAGAR_FOTOS_APOS_ENCODINGS:        # LGPD: guarda so os vetores
                shutil.rmtree(pasta)
                print(f"  Fotos de {matricula} apagadas (LGPD).")

    # Se as fotos foram apagadas antes, mantemos os vetores ja salvos
    antigos = reconhecimento.carregar_encodings()
    for matricula, vetores in antigos.items():
        encodings.setdefault(matricula, vetores)

    reconhecimento.salvar_encodings(encodings)
    print(f"Salvo {config.CAMINHO_ENCODINGS} com {len(encodings)} operador(es).")
    return encodings


if __name__ == "__main__":
    gerar_encodings()
