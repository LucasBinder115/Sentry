import cv2
import easyocr

# Inicia o leitor OCR uma única vez
reader = easyocr.Reader(['pt'], gpu=False)  # GPU desativada (se não tiver)

def detectar_placa():
    cap = cv2.VideoCapture(0)  # Usa a webcam padrão
    ret, frame = cap.read()
    cap.release()

    if not ret:
        return None, "Erro ao capturar imagem da câmera."

    # OCR na imagem capturada
    resultados = reader.readtext(frame)

    # Filtrar possíveis placas
    for (bbox, texto, confianca) in resultados:
        if len(texto) >= 6 and confianca > 0.5:
            # Remove espaços e símbolos que não pertencem a placas
            placa = ''.join(filter(str.isalnum, texto.upper()))
            return placa, None

    return None, "Nenhuma placa detectada com confiança suficiente."
