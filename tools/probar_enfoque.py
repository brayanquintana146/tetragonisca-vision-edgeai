"""
Ayuda a enfocar a mano una webcam en Windows antes de contar.

Apaga el autoenfoque, abre la ventana de ajustes del driver y muestra la imagen en vivo con un
número de nitidez del centro (varianza del laplaciano): cuanto más alto, más nítido. Se mueve el
enfoque en los ajustes hasta que el número llegue a su máximo con la piquera en el centro.

Uso: python tools/probar_enfoque.py [índice de la cámara, 1 por defecto]
Teclas: s = abrir los ajustes del driver, q = salir.
"""
import cv2, sys
idx = int(sys.argv[1]) if len(sys.argv) > 1 else 1
cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
if not cap.isOpened():
    print(f"No se pudo abrir la cámara {idx}. Cierra la app Cámara de Windows.")
    sys.exit(1)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
cap.set(cv2.CAP_PROP_SETTINGS, 1)  # ventana de ajustes del driver
while True:
    ok, f = cap.read()
    if not ok:
        break
    g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
    h, w = g.shape
    centro = g[h//4:3*h//4, w//4:3*w//4]
    nitidez = cv2.Laplacian(centro, cv2.CV_64F).var()
    cv2.rectangle(f, (w//4, h//4), (3*w//4, 3*h//4), (0, 255, 255), 2)
    cv2.putText(f, f"nitidez {nitidez:.0f}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
    cv2.imshow("Enfoque (q salir, s ajustes)", f)
    k = cv2.waitKey(1) & 0xFF
    if k == ord("q"):
        break
    if k == ord("s"):
        cap.set(cv2.CAP_PROP_SETTINGS, 1)
cap.release()
cv2.destroyAllWindows()
