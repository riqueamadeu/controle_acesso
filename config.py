"""
config.py - Todas as constantes do sistema ficam aqui.
Para mudar o comportamento (camera, limiar de similaridade, celulas...) edite SO este arquivo.
"""
import os

# Pasta onde este arquivo esta (assim os caminhos funcionam de qualquer lugar)
PASTA_BASE = os.path.dirname(os.path.abspath(__file__))

# ---------- Caminhos ----------
CAMINHO_OPERADORES = os.path.join(PASTA_BASE, "data", "operadores.csv")
CAMINHO_MATRIZ = os.path.join(PASTA_BASE, "data", "matriz_qualificacao.csv")
# Versoes de exemplo (vao para o GitHub). Se os arquivos acima nao existirem,
# o programa cria uma copia a partir destes.
CAMINHO_OPERADORES_EXEMPLO = os.path.join(PASTA_BASE, "data", "operadores_exemplo.csv")
CAMINHO_MATRIZ_EXEMPLO = os.path.join(PASTA_BASE, "data", "matriz_qualificacao_exemplo.csv")
CAMINHO_ENCODINGS = os.path.join(PASTA_BASE, "data", "encodings.npz")
PASTA_DATASET = os.path.join(PASTA_BASE, "dataset")
CAMINHO_HISTORICO = os.path.join(PASTA_BASE, "registros", "historico_acessos.csv")

# Modelos de rede neural do OpenCV (YuNet detecta rosto, SFace gera o vetor)
MODELO_DETECTOR = os.path.join(PASTA_BASE, "modelos", "face_detection_yunet_2023mar.onnx")
MODELO_RECONHECEDOR = os.path.join(PASTA_BASE, "modelos", "face_recognition_sface_2021dec.onnx")

# ---------- Celulas de producao ----------
CELULAS = ["Linha_Montagem_A", "Prensa_B", "Solda_C"]

# ---------- Reconhecimento ----------
# Similaridade do cosseno do SFace: MAIOR = mais parecido (1 = identico, 0 = sem relacao).
# Aceita o operador somente se a MAIOR similaridade encontrada for >= a este limiar.
# 0.363 e o valor recomendado pelo OpenCV para o SFace.
# Subir o valor = mais rigoroso (menos falsos positivos); baixar = mais permissivo.
LIMIAR_SIMILARIDADE = 0.363
FRAMES_CONFIRMACAO = 8     # mesma pessoa em N frames processados seguidos
PROCESSAR_1_A_CADA = 2     # processa 1 frame a cada N (desempenho)
ESCALA_FRAME = 0.25        # reduz o frame para 1/4 antes de detectar

# ---------- Registro ----------
INTERVALO_MINUTOS = 5      # nao repete registro da mesma matricula+celula
DIAS_AVISO_RECICLAGEM = 30
SEGUNDOS_CHECAR_MATRIZ = 3 # a cada quantos segundos confere se o CSV da matriz mudou

# ---------- Camera ----------
# 0 normalmente e a webcam do Mac. Com Continuity Camera o iPhone pode ser 1 ou 2.
INDICE_CAMERA = 0

# ---------- Cadastro ----------
NUM_FOTOS_CADASTRO = 5
APAGAR_FOTOS_APOS_ENCODINGS = False   # True = LGPD: guarda so os vetores, apaga as fotos

# ---------- Som ----------
SOM_ATIVO = True
# Som usado so no Mac (no Windows usa o som padrao de erro; nos outros, o beep do terminal)
ARQUIVO_SOM = "/System/Library/Sounds/Basso.aiff"
