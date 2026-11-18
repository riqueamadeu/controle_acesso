"""
cadastrar_operador.py - Cadastra um novo operador usando a webcam.
Rode com:  python cadastrar_operador.py
"""
import os
import csv
import shutil

import cv2

import acesso
import config
import reconhecimento
import atualizar_encodings


def pedir_dados():
    """Pergunta matricula, nome e funcao no terminal. Retorna None se cancelar."""
    operadores = acesso.carregar_operadores()
    matricula = input("Matricula (letras/numeros): ").strip()
    if not matricula.isalnum():
        print("Matricula invalida (use so letras e numeros).")
        return None
    if matricula in operadores["Matricula"].values:
        print(f"Ja existe um operador com a matricula {matricula}.")
        return None
    nome = input("Nome: ").strip()
    funcao = input("Funcao: ").strip()
    if not nome:
        print("Nome nao pode ser vazio.")
        return None

    # LGPD: rosto e dado biometrico, entao precisamos do consentimento
    print("\nAVISO LGPD: sua imagem facial e um dado biometrico e sera usada apenas")
    print("para controlar o acesso as celulas de producao.")
    if input("Voce consente com o uso? (s/n): ").strip().lower() != "s":
        print("Sem consentimento. Cadastro cancelado.")
        return None
    return matricula, nome, funcao


def capturar_fotos(matricula):
    """Abre a camera e salva NUM_FOTOS_CADASTRO fotos validas. Retorna quantas salvou."""
    camera = reconhecimento.abrir_camera()
    if camera is None:
        return 0
    detector = reconhecimento.criar_detector()
    pasta = os.path.join(config.PASTA_DATASET, matricula)
    os.makedirs(pasta, exist_ok=True)

    salvas = 0
    mensagem = ""
    print("\nUma janela 'Cadastro' vai abrir. CLIQUE NELA para ela receber o teclado")
    print("(se nao aparecer, procure no Dock ou use Cmd+Tab).")
    print("ESPACO = tirar foto | q = cancelar. Varie levemente o angulo do rosto a cada foto.")
    cv2.namedWindow("Cadastro")
    cv2.setWindowProperty("Cadastro", cv2.WND_PROP_TOPMOST, 1)   # tenta deixar a janela na frente
    while salvas < config.NUM_FOTOS_CADASTRO:
        ret, frame = camera.read()
        if not ret:
            print("Falha ao ler a camera.")
            break
        tela = frame.copy()
        texto = f"Foto {salvas + 1}/{config.NUM_FOTOS_CADASTRO} - ESPACO para capturar"
        cv2.putText(tela, texto, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(tela, mensagem, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        cv2.imshow("Cadastro", tela)

        tecla = cv2.waitKey(1) & 0xFF
        if tecla == ord("q"):
            break
        if tecla == 32:  # espaco
            rostos = reconhecimento.detectar_rostos(detector, frame)
            if len(rostos) != 1:
                mensagem = f"Foto descartada: {len(rostos)} rostos (precisa de 1)"
                print(mensagem)
                continue
            salvas += 1
            cv2.imwrite(os.path.join(pasta, f"{matricula}_{salvas}.jpg"), frame)
            print(f"Foto {salvas}/{config.NUM_FOTOS_CADASTRO} salva.")
            mensagem = ""

    camera.release()
    cv2.destroyAllWindows()
    return salvas


def adicionar_ao_csv(matricula, nome, funcao):
    """Acrescenta o operador no final de operadores.csv."""
    with open(config.CAMINHO_OPERADORES, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([matricula, nome, funcao])


def main():
    dados = pedir_dados()
    if dados is None:
        return
    matricula, nome, funcao = dados
    salvas = capturar_fotos(matricula)
    if salvas < config.NUM_FOTOS_CADASTRO:
        print(f"Cadastro incompleto ({salvas} foto(s)). Nada foi cadastrado.")
        shutil.rmtree(os.path.join(config.PASTA_DATASET, matricula), ignore_errors=True)
        return
    adicionar_ao_csv(matricula, nome, funcao)
    atualizar_encodings.gerar_encodings()
    print(f"\nOperador {nome} ({matricula}) cadastrado!")
    print("Lembre-se de incluir a matricula em data/matriz_qualificacao.csv.")


if __name__ == "__main__":
    main()
