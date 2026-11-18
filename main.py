"""
main.py - Loop principal: camera -> reconhece o rosto -> verifica acesso -> registra -> mostra na tela.
Uso:  python main.py                      (mostra menu para escolher a celula)
      python main.py --celula Prensa_B
Tecla q = sair.
"""
import argparse
import os
import subprocess
import sys
import time
import unicodedata
from datetime import datetime

import cv2

import acesso
import config
import reconhecimento

# Cores em BGR (o OpenCV usa Blue-Green-Red, nao RGB)
CORES = {
    acesso.LIBERADO: (0, 200, 0),      # verde
    acesso.SUPERVISAO: (0, 220, 255),  # amarelo
    acesso.NEGADO: (0, 0, 220),        # vermelho
}
COR_VERIFICANDO = (200, 200, 200)      # cinza enquanto confirma o rosto


def remover_acentos(texto):
    """cv2.putText nao desenha acentos, entao 'Joao' em vez de 'João'."""
    normalizado = unicodedata.normalize("NFD", texto)
    return "".join(c for c in normalizado if unicodedata.category(c) != "Mn")


def escolher_celula():
    """Le --celula da linha de comando; se nao veio, mostra um menu numerado."""
    parser = argparse.ArgumentParser(description="Controle de acesso por reconhecimento facial")
    parser.add_argument("--celula", help="Nome da celula: " + ", ".join(config.CELULAS))
    args = parser.parse_args()

    if args.celula:
        if args.celula not in config.CELULAS:
            parser.error(f"Celula invalida. Opcoes: {', '.join(config.CELULAS)}")
        return args.celula

    print("Escolha a celula de producao:")
    for i, nome in enumerate(config.CELULAS, start=1):
        print(f"  {i}) {nome}")
    while True:
        escolha = input("Numero: ").strip()
        if escolha.isdigit() and 1 <= int(escolha) <= len(config.CELULAS):
            return config.CELULAS[int(escolha) - 1]
        print("Opcao invalida.")


def tocar_alerta():
    """
    Toca um som de alerta sem travar o video e SEM derrubar o programa se o som falhar.
      Mac: afplay | Windows: winsound | outros (Linux): "beep" do terminal
    """
    if not config.SOM_ATIVO:
        return
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["afplay", config.ARQUIVO_SOM])      # Popen nao espera terminar
        elif sys.platform.startswith("win"):
            import winsound
            winsound.PlaySound("SystemHand", winsound.SND_ALIAS | winsound.SND_ASYNC)
        else:
            print("\a", end="", flush=True)
    except Exception as erro:       # som e opcional: nunca pode fechar o sistema
        print(f"(Nao foi possivel tocar o alerta: {erro})")


def desenhar_faixa(frame, texto, cor):
    """Faixa grande na parte de baixo com a mensagem (a fonte diminui se o texto for longo)."""
    altura, largura = frame.shape[:2]
    cv2.rectangle(frame, (0, altura - 70), (largura, altura), cor, -1)
    escala = 0.9
    while cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, escala, 2)[0][0] > largura - 20 and escala > 0.3:
        escala -= 0.05
    cv2.putText(frame, texto, (10, altura - 25), cv2.FONT_HERSHEY_SIMPLEX, escala, (0, 0, 0), 2)


def montar_mensagem(status, motivo, nome):
    """Texto da faixa, ex.: 'ACESSO LIBERADO - Joao Silva'."""
    if status == acesso.LIBERADO:
        texto = f"ACESSO LIBERADO - {nome}"
        if motivo:
            texto += f" ({motivo})"        # aviso de reciclagem
    elif status == acesso.SUPERVISAO:
        texto = f"{nome}: {motivo}"
    else:
        texto = f"ACESSO NEGADO: {motivo}"
    return remover_acentos(texto)


def encontrar_rosto(frame, detector, reconhecedor, encodings):
    """
    Procura o maior rosto no frame e descobre quem e.
    Retorna (caixa, matricula, similaridade) ou None se nao ha rosto.
    """
    # Reduz o frame para 1/4 so para DETECTAR (mais rapido)
    pequeno = cv2.resize(frame, None, fx=config.ESCALA_FRAME, fy=config.ESCALA_FRAME)
    rostos = reconhecimento.detectar_rostos(detector, pequeno)
    if not rostos:
        return None

    # Pega o maior rosto e volta as coordenadas para o tamanho original
    rosto = max(rostos, key=lambda r: r[2] * r[3]).copy()
    rosto[:14] = rosto[:14] / config.ESCALA_FRAME
    caixa = tuple(int(v) for v in rosto[:4])

    # O vetor e gerado no frame ORIGINAL (mais nitido que o reduzido)
    vetor = reconhecimento.gerar_encoding(reconhecedor, frame, rosto)
    matricula, similaridade = reconhecimento.identificar(encodings, vetor)
    return caixa, matricula, similaridade


def confirmou(estado, matricula):
    """
    Conta quantos frames seguidos a mesma identidade apareceu.
    Retorna True so no frame em que atinge FRAMES_CONFIRMACAO.
    """
    if matricula == estado["identidade"]:
        estado["seguidos"] += 1
    else:                                   # mudou a pessoa: recomeca a contagem
        estado["identidade"] = matricula
        estado["seguidos"] = 1
        estado["resultado"] = None
    return estado["seguidos"] == config.FRAMES_CONFIRMACAO


def decidir_acesso(matricula, similaridade, celula, matriz, nomes):
    """Verifica a matriz, grava no historico e devolve (status, mensagem) para a tela."""
    nome = nomes.get(matricula, "")
    status, motivo = acesso.verificar_acesso(matricula, celula, matriz)
    acesso.registrar_acesso(matricula, nome, celula, status, motivo, similaridade)
    if status == acesso.NEGADO:
        tocar_alerta()
    return status, montar_mensagem(status, motivo, nome)


def reavaliar_acesso(estado, celula, matriz, nomes):
    """
    A matriz mudou: se ha alguem confirmado na frente da camera, decide de novo com a matriz nova
    (o resultado novo aparece na tela e, se o status mudou, entra no historico).
    """
    if estado["resultado"] is not None:
        estado["resultado"] = decidir_acesso(estado["identidade"], estado["similaridade"], celula, matriz, nomes)


def desenhar_tela(frame, celula, caixa, resultado):
    """Desenha cabecalho, retangulo no rosto e faixa com a mensagem."""
    if caixa:
        x, y, w, h = caixa
        cor = CORES[resultado[0]] if resultado else COR_VERIFICANDO
        cv2.rectangle(frame, (x, y), (x + w, y + h), cor, 3)
    if resultado:
        desenhar_faixa(frame, resultado[1], CORES[resultado[0]])
    elif caixa:
        desenhar_faixa(frame, "Verificando...", COR_VERIFICANDO)

    cabecalho = f"{celula} | {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    cv2.rectangle(frame, (0, 0), (frame.shape[1], 35), (0, 0, 0), -1)
    cv2.putText(frame, cabecalho, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)


def main():
    celula = escolher_celula()

    # Carrega os dados uma vez so, antes de abrir a camera
    matriz = acesso.carregar_matriz()
    mtime_matriz = os.path.getmtime(config.CAMINHO_MATRIZ)
    ultima_checagem = time.time()
    operadores = acesso.carregar_operadores()
    nomes = dict(zip(operadores["Matricula"], operadores["Nome"]))
    encodings = reconhecimento.carregar_encodings()
    if not encodings:
        print("Aviso: data/encodings.npz vazio. Cadastre operadores ou rode atualizar_encodings.py.")

    detector = reconhecimento.criar_detector()
    reconhecedor = reconhecimento.criar_reconhecedor()
    camera = reconhecimento.abrir_camera()
    if camera is None:
        return

    # Estado: o que ja sabemos sobre a pessoa que esta na frente da camera
    estado = {"identidade": "nenhuma", "seguidos": 0, "caixa": None, "resultado": None, "similaridade": 0.0}
    contador_frames = 0

    print(f"Celula: {celula}. Pressione 'q' na janela para sair.")
    while True:
        ret, frame = camera.read()
        if not ret:
            print("Falha ao ler a camera.")
            break
        contador_frames += 1

        # De poucos em poucos segundos, confere se o CSV da matriz foi editado
        if time.time() - ultima_checagem >= config.SEGUNDOS_CHECAR_MATRIZ:
            ultima_checagem = time.time()
            nova, mtime_matriz = acesso.matriz_mudou(mtime_matriz)
            if nova is not None:
                matriz = nova
                print("Matriz de qualificacao atualizada.")
                reavaliar_acesso(estado, celula, matriz, nomes)

        # Processa so 1 a cada N frames (desempenho)
        if contador_frames % config.PROCESSAR_1_A_CADA == 0:
            achado = encontrar_rosto(frame, detector, reconhecedor, encodings)
            if achado is None:                  # ninguem na frente da camera
                estado = {"identidade": "nenhuma", "seguidos": 0, "caixa": None, "resultado": None, "similaridade": 0.0}
            else:
                estado["caixa"], matricula, similaridade = achado
                if confirmou(estado, matricula):          # decide uma unica vez
                    estado["similaridade"] = similaridade
                    estado["resultado"] = decidir_acesso(matricula, similaridade, celula, matriz, nomes)

        desenhar_tela(frame, celula, estado["caixa"], estado["resultado"])
        cv2.imshow("Controle de Acesso", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    camera.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
