"""
testar_camera.py - Diagnostico rapido para rodar em QUALQUER computador (Mac, Windows, Linux).
Verifica 4 coisas: modelos, camera, janela de video e deteccao de rosto.
Uso:  python testar_camera.py     (aperte 'q' na janela para terminar)
"""
import os
import sys
import time

import cv2

import config
import reconhecimento


def ok(texto):
    print(f"  [OK]   {texto}")


def falha(texto):
    print(f"  [FALHA] {texto}")


def testar_modelos():
    """1) Os arquivos dos modelos existem e carregam?"""
    print("1) Modelos de reconhecimento facial")
    for caminho in (config.MODELO_DETECTOR, config.MODELO_RECONHECEDOR):
        if not os.path.exists(caminho):
            falha(f"Falta {os.path.basename(caminho)}. Rode: python baixar_modelos.py")
            return None
    try:
        detector = reconhecimento.criar_detector()
        reconhecedor = reconhecimento.criar_reconhecedor()
    except Exception as erro:
        falha(f"Nao foi possivel carregar os modelos: {erro}")
        return None
    ok("Modelos carregados")
    return detector, reconhecedor


def abrir_e_ler(indice, backend=None):
    """Tenta abrir a camera e ler um frame (por ate 3 segundos, pois algumas demoram)."""
    camera = cv2.VideoCapture(indice) if backend is None else cv2.VideoCapture(indice, backend)
    if camera.isOpened():
        inicio = time.time()
        while time.time() - inicio < 3:
            lido, _ = camera.read()
            if lido:
                return camera
            time.sleep(0.1)
    camera.release()
    return None


def testar_camera():
    """2) Alguma camera abre? Testa os indices 0 a 3 (e o modo DirectShow no Windows)."""
    print("2) Camera")
    backends = [(None, "padrao")]
    if sys.platform.startswith("win"):
        backends.append((cv2.CAP_DSHOW, "DirectShow"))
    for indice in range(4):
        for backend, nome in backends:
            camera = abrir_e_ler(indice, backend)
            if camera is not None:
                ok(f"Camera funcionando: indice {indice} (modo {nome}). "
                   f"Tamanho {int(camera.get(3))}x{int(camera.get(4))}")
                if indice != config.INDICE_CAMERA:
                    print(f"         Atencao: config.py usa INDICE_CAMERA = {config.INDICE_CAMERA}. "
                          f"Mude para {indice} se a camera errada abrir.")
                return camera
    falha("Nenhuma camera abriu (indices 0 a 3).")
    print("         Mac: Ajustes do Sistema > Privacidade e Seguranca > Camera.")
    print("         Windows: Configuracoes > Privacidade e seguranca > Camera.")
    print("         Feche apps que usam a camera (Zoom, Teams, FaceTime).")
    return None


def testar_janela_e_rosto(camera, detector, reconhecedor):
    """3) A janela aparece e 4) um rosto e detectado e vira um vetor de 128 numeros?"""
    print("3) Janela de video e 4) Deteccao de rosto")
    print("   Uma janela vai abrir. Fique de frente para a camera por alguns segundos e aperte 'q'.")
    frames, com_rosto, vetor_ok = 0, 0, False
    try:
        while True:
            lido, frame = camera.read()
            if not lido:
                falha("A camera parou de enviar imagens.")
                break
            frames += 1
            rostos = reconhecimento.detectar_rostos(detector, frame)
            if rostos:
                com_rosto += 1
                x, y, w, h = (int(v) for v in rostos[0][:4])
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 200, 0), 3)
                vetor = reconhecimento.gerar_encoding(reconhecedor, frame, rostos[0])
                vetor_ok = vetor_ok or vetor.shape == (128,)
            texto = "Rosto detectado" if rostos else "Procurando rosto... (q = sair)"
            cv2.putText(frame, texto, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.imshow("Teste de camera", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    except cv2.error as erro:
        falha(f"Erro ao mostrar a janela: {erro}")
        return False, False
    finally:
        camera.release()
        cv2.destroyAllWindows()

    if frames:
        ok(f"Janela abriu e mostrou {frames} imagens")
    else:
        falha("Nenhuma imagem foi mostrada")
    if vetor_ok:
        ok(f"Rosto detectado em {com_rosto} imagens e vetor de 128 numeros gerado")
    else:
        falha("Nenhum rosto foi detectado (melhore a luz e fique de frente para a camera)")
    return frames > 0, vetor_ok


def main():
    print(f"Sistema: {sys.platform} | Python {sys.version.split()[0]} | OpenCV {cv2.__version__}\n")
    modelos = testar_modelos()
    camera = testar_camera() if modelos else None
    janela_ok, rosto_ok = (False, False)
    if camera is not None:
        janela_ok, rosto_ok = testar_janela_e_rosto(camera, *modelos)

    print("\nRESULTADO:")
    if modelos and camera is not None and janela_ok and rosto_ok:
        print("  TUDO OK: este computador pode rodar o sistema.")
    else:
        print("  HOUVE FALHAS (veja [FALHA] acima). Envie esta saida para quem mantem o projeto.")


if __name__ == "__main__":
    main()
