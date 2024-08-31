import cv2
import mediapipe as mp

video = cv2.VideoCapture(0)

hand = mp.solutions.hands
Hand = hand.Hands(max_num_hands=2)
mpDraw = mp.solutions.drawing_utils

while True:
    check, img = video.read()
    imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = Hand.process(imgRGB)
    handsPoints = results.multi_hand_landmarks
    h, w, _ = img.shape
    contador_esquerda = 0
    contador_direita = 0

    if handsPoints:
        for points in handsPoints:
            mpDraw.draw_landmarks(img, points, hand.HAND_CONNECTIONS)
            pontos = []
            for id, cord in enumerate(points.landmark):
                cx, cy = int(cord.x * w), int(cord.y * h)
                pontos.append((cx, cy))

            dedos = [8, 12, 16, 20]
            contador = 0
            if pontos:
                # Verifica se é a mão esquerda ou direita
                if pontos[17][0] < pontos[5][0]:  # Mão esquerda
                    if pontos[4][0] > pontos[3][0]:
                        contador += 1
                    for x in dedos:
                        if pontos[x][1] < pontos[x - 2][1]:
                            contador += 1
                    contador_esquerda = contador
                else:  # Mão direita
                    if pontos[4][0] < pontos[3][0]:
                        contador += 1
                    for x in dedos:
                        if pontos[x][1] < pontos[x - 2][1]:
                            contador += 1
                    contador_direita = contador


    # Calcula a soma dos contadores
    soma_contadores = contador_esquerda + contador_direita

    # Desenha os contadores na tela
    # cv2.rectangle(img, (10, 10), (90, 100), (255, 0, 0), -1)
    cv2.putText(img, "Direita", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(img, str(contador_esquerda), (30, 80), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 5)
    # cv2.rectangle(img, (w - 130, 10), (w - 10, 100), (255, 0, 0), -1)
    cv2.putText(img, "Esquerda", (w - 130, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(img, str(contador_direita), (w - 110, 80), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 5)

    # Desenha a soma dos contadores no meio da tela, na parte superior
    cv2.putText(img, "Total", (w // 2 - 30, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    cv2.putText(img, str(soma_contadores), (w // 2 - 30, 80), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 5)

    cv2.imshow("Imagem da WebCam", img)
    cv2.waitKey(1)