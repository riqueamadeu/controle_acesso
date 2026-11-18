# Controle de Presença e Acesso a Células de Produção (Reconhecimento Facial)

Sistema em Python que reconhece o operador pela webcam, registra data/hora de entrada na célula
e **bloqueia** quem não tem treinamento válido (matriz de versatilidade ILUO).

## Como funciona (resumo para a banca)
1. A webcam captura o rosto → o **YuNet** (OpenCV) encontra o rosto.
2. O **SFace** (OpenCV) transforma o rosto em um vetor de 128 números.
3. Comparamos com os vetores cadastrados; vence o de **maior similaridade do cosseno** (aceita só se ≥ `LIMIAR_SIMILARIDADE`, padrão 0.363, valor recomendado pelo OpenCV).
4. Só depois de a mesma pessoa aparecer em 8 frames seguidos (`FRAMES_CONFIRMACAO`), `acesso.py` consulta a matriz.
5. O resultado (LIBERADO / SUPERVISAO / NEGADO) aparece na tela e é gravado em `registros/historico_acessos.csv`.

> **Por que não dlib/face_recognition?** No macOS atual o `dlib` não compila (erro `fp.h file not found`
> na biblioteca libpng embutida, incompatível com o SDK novo do macOS). Por isso usamos os modelos
> de reconhecimento facial nativos do OpenCV, que não precisam de compilação.

## Rodar do zero (macOS)
Passo a passo para quem acabou de clonar o repositório.

```bash
# 1) Python 3.12 (precisa do Homebrew: https://brew.sh)
brew install python@3.12

# 2) Clonar o repositório e entrar na pasta
git clone <URL-DO-REPOSITORIO> controle_acesso
cd controle_acesso

# 3) Ambiente virtual e dependências
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 4) Baixar os modelos de reconhecimento facial (YuNet e SFace, ~37 MB) para modelos/
python baixar_modelos.py

# 5) Cadastrar um operador (usa a webcam)
python cadastrar_operador.py

# 6) Editar a matriz de qualificação (veja a seção abaixo), depois rodar
python main.py
```

**O que vem pronto e o que é criado na sua máquina:**
- O repositório traz só dados de **exemplo** (`data/operadores_exemplo.csv` e `data/matriz_qualificacao_exemplo.csv`, com operadores fictícios).
- Na primeira execução, o programa cria `data/operadores.csv` e `data/matriz_qualificacao.csv` a partir dos exemplos. **Esses são os arquivos reais, que você edita**, e eles não vão para o GitHub (estão no `.gitignore`).
- As fotos (`dataset/`), os vetores (`data/encodings.npz`) e o histórico (`registros/`) também ficam só na sua máquina, pois são dados biométricos e pessoais (LGPD).
- Os modelos `.onnx` não vão no repositório: o `baixar_modelos.py` baixa de <https://github.com/opencv/opencv_zoo>.

> **Dica:** não deixe o projeto dentro do iCloud Drive (a `.venv` tem milhares de arquivos e é sincronizada, o que causa lentidão e erros). Use uma pasta como `~/Projetos`.
> Toda vez que abrir um terminal novo, entre na pasta e rode `source .venv/bin/activate` antes dos comandos `python`.

## Outros sistemas (Windows e Linux)
O código foi **desenvolvido e testado no macOS**. Ele usa só OpenCV, numpy e pandas, que têm instalação pronta
no Windows e no Linux, mas **não testamos nesses sistemas**. O que muda:

| | Mac | Windows (PowerShell) | Linux |
|---|---|---|---|
| Python | `brew install python@3.12` | instalar de python.org (3.11 ou 3.12) | `sudo apt install python3-venv` |
| Criar a `.venv` | `python3.12 -m venv .venv` | `py -3.12 -m venv .venv` | `python3 -m venv .venv` |
| Ativar | `source .venv/bin/activate` | `.venv\Scripts\Activate.ps1` | `source .venv/bin/activate` |
| Comandos `python ...` | iguais | iguais | iguais |
| Som de alerta | `afplay` | som padrão de erro | "beep" do terminal |

- Se o PowerShell bloquear a ativação, rode uma vez: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- O som é opcional e **nunca derruba o programa**: se falhar, aparece só um aviso. Para desligar, use `SOM_ATIVO = False` em `config.py`.
- No Windows, o comando `echo "..." >> arquivo` e o `open` do README não valem como estão: edite o CSV no Excel/Bloco de Notas.
- O índice da câmera pode ser diferente: ajuste `INDICE_CAMERA` em `config.py`.

**Antes de usar em outro computador, rode o teste de câmera** (10 segundos): ele confere os modelos, a câmera,
a janela de vídeo e a detecção de rosto, e diz onde falhou:
```bash
python baixar_modelos.py     # se ainda nao baixou os modelos
python testar_camera.py      # aperte q na janela para terminar; o final mostra TUDO OK ou as falhas
```

## Cadastrar um operador
```bash
python cadastrar_operador.py
```
Informe matrícula, nome e função, aceite o termo de consentimento (LGPD) e tire 5 fotos com **ESPAÇO**,
variando levemente o ângulo do rosto (clique na janela da câmera antes). Fotos com 0 ou 2+ rostos são descartadas.
Os vetores são gerados automaticamente. Depois, **inclua a matrícula na matriz** (abaixo).

Se colocar fotos manualmente em `dataset/<matricula>/`, rode `python atualizar_encodings.py`.

## Editar a matriz de qualificação
Edite `data/matriz_qualificacao.csv` (no Excel/Numbers, salvando como CSV, ou no VS Code). Colunas:
`Matricula,Celula,Nivel,Validade` (Validade no formato `AAAA-MM-DD`). Para adicionar uma linha pelo terminal:
```bash
echo "4,Prensa_B,U,2027-12-31" >> data/matriz_qualificacao.csv   # use >> (acrescenta); um só > apaga o arquivo
```

| Nível | Significado | Resultado |
|---|---|---|
| I | em treinamento | SUPERVISAO |
| L | opera com supervisão | SUPERVISAO |
| U | opera sozinho | LIBERADO |
| O | pode treinar outros | LIBERADO |

Sem linha para a célula → NEGADO. Validade vencida → NEGADO. Vence em até 30 dias → aviso de reciclagem.
As células disponíveis ficam em `config.py` (`CELULAS`).

## Rodar
```bash
source .venv/bin/activate
python main.py                       # menu para escolher a célula
python main.py --celula Prensa_B     # escolhe direto
```
Tecla **q** na janela para sair. Rodar os testes (não precisam de câmera): `pytest -v`

## Roteiro sugerido de demonstração
1. Mostrar o `config.py`, `data/matriz_qualificacao.csv` e rodar `pytest -v` (43 testes passando).
2. Cadastrar um integrante ao vivo (`cadastrar_operador.py`) e explicar o consentimento LGPD.
3. Incluir o integrante na matriz: nível `U` em uma célula, `L` em outra, nenhum em uma terceira.
4. `python main.py --celula <célula com U>` → faixa **verde** "ACESSO LIBERADO".
5. Trocar para a célula com `L` → faixa **amarela** (supervisão).
6. Trocar para a célula sem treinamento → faixa **vermelha** "ACESSO NEGADO" + som.
7. Mostrar alguém não cadastrado → "Operador nao cadastrado".
8. Abrir `registros/historico_acessos.csv` mostrando que **negados e desconhecidos também são registrados**.
9. (Opcional) Colocar uma validade vencida/próxima na matriz e mostrar o "Treinamento vencido" / aviso de reciclagem.

## Solução de problemas
- **"Não foi possível abrir a câmera"**: Ajustes do Sistema > Privacidade e Segurança > Câmera →
  permita o Terminal / VS Code (reinicie o app). Feche Zoom/FaceTime.
- **Abriu a câmera errada / iPhone**: mude `INDICE_CAMERA` em `config.py` (0, 1, 2...). Com Continuity
  Camera o iPhone pode aparecer como outro índice.
- **Reconhece a pessoa errada**: **aumente** `LIMIAR_SIMILARIDADE` (mais rigoroso, ex.: 0.45). **Não reconhece ninguém**: diminua
  um pouco (ex.: 0.30), melhore a iluminação ou recadastre com fotos melhores.
- **Erro ao instalar dlib (`fp.h file not found`)**: é o motivo de este projeto não usar dlib (ver acima).
  Se mesmo assim quiser dlib, precisaria de `brew install cmake` e de uma versão do dlib compatível com o SDK.
- **Sem som**: confira `SOM_ATIVO` em `config.py`; o som usa o `afplay` do macOS.

## LGPD
O rosto é **dado pessoal sensível (biométrico)** — Lei 13.709/2018, art. 5º, II e art. 11.
- Coleta **somente com consentimento** explícito (o cadastro pede e cancela se negado).
- Finalidade única: controle de acesso às células. Não usar para outros fins.
- Minimização: com `APAGAR_FOTOS_APOS_ENCODINGS = True` em `config.py`, as fotos são apagadas e
  só ficam os vetores numéricos (`encodings.npz`) - não é possível reconstruir o rosto a partir deles com facilidade,
  mas continuam sendo dados biométricos e devem ser protegidos.
- O titular pode pedir exclusão: apague `dataset/<matricula>/`, a linha em `operadores.csv`, e rode
  `atualizar_encodings.py` (ou remova a matrícula do `encodings.npz`).
- O histórico guarda matrícula, nome e horário; defina por quanto tempo será mantido.
