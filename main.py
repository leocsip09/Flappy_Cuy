import pygame
from sys import exit
import random
import cv2
import mediapipe as mp

pygame.init()
clock = pygame.time.Clock()
img = cv2.imread('mano.png', 1)
fuente = cv2.FONT_HERSHEY_SIMPLEX

# Ventana
altura_ventana = 720
ancho_ventana = 551
ventana = pygame.display.set_mode((ancho_ventana, altura_ventana))

# Imagenes
def scale_up(image, scale_factor):
    new_width = int(image.get_width() * scale_factor)
    new_height = int(image.get_height() * scale_factor)
    return pygame.transform.scale(image, (new_width, new_height))

scale_factor_cuy = 1.15
imagenes_cuy = [scale_up(pygame.image.load("imgs/cuy_abajo.png"), scale_factor_cuy),
                scale_up(pygame.image.load("imgs/cuy_med.png"), scale_factor_cuy),
                scale_up(pygame.image.load("imgs/cuy_arriba.png"), scale_factor_cuy)]

scale_factor_inicio_fin = 1.7
imagen_game_over = scale_up(pygame.image.load("imgs/fin.png"), scale_factor_inicio_fin)
imagen_inicio = scale_up(pygame.image.load("imgs/inicio.png"), scale_factor_inicio_fin)
imagen_lineaCielo = pygame.image.load("imgs/fondo.png")
imagen_piso = pygame.image.load("imgs/piso.png")
imagen_obst_arriba = pygame.image.load("imgs/pipe_top.png")
imagen_obst_abajo = pygame.image.load("imgs/pipe_bottom.png")


# Juego
velocidad = 1
cuy_pos = (100, 250)
puntaje = 0
fuente = pygame.font.SysFont('Segoe', 26)
juego_detenido = True


class Cuy(pygame.sprite.Sprite):
    def __init__(self):
        pygame.sprite.Sprite.__init__(self)
        self.image = imagenes_cuy[0]
        self.rect = self.image.get_rect()
        self.rect.center = cuy_pos
        self.indice_imagen = 0
        self.vel = 0
        self.salto = False
        self.vivo = True

    def update(self, entrada):
        # Animate Bird
        if self.vivo:
            self.indice_imagen += 1
        if self.indice_imagen >= 30:
            self.indice_imagen = 0
        self.image = imagenes_cuy[self.indice_imagen // 10]

        # Gravedad y  Flap
        self.vel += 0.5
        if self.vel > 7:
            self.vel = 7
        if self.rect.y < 500:
            self.rect.y += int(self.vel)
        if self.vel == 0:
            self.salto = False

        # Rotate Bird
        self.image = pygame.transform.rotate(self.image, self.vel * -7)

        # User Input
        if entrada[pygame.K_SPACE] and not self.salto and self.rect.y > 0 and self.vivo:
            self.salto = True
            self.vel = -7


class Obstaculo(pygame.sprite.Sprite):
    def __init__(self, x, y, imagen, tipo_obst):
        pygame.sprite.Sprite.__init__(self)
        self.image = imagen
        self.rect = self.image.get_rect()
        self.rect.x, self.rect.y = x, y
        self.enter, self.salida, self.pasado = False, False, False
        self.tipo_obst = tipo_obst

    def update(self):
        # Mover Obstaculo
        self.rect.x -= velocidad
        if self.rect.x <= -ancho_ventana:
            self.kill()

        # Puntaje
        global puntaje
        if self.tipo_obst == 'bottom':
            if cuy_pos[0] > self.rect.topleft[0] and not self.pasado:
                self.enter = True
            if cuy_pos[0] > self.rect.topright[0] and not self.pasado:
                self.salida = True
            if self.enter and self.salida and not self.pasado:
                self.pasado = True
                puntaje += 1


class Piso(pygame.sprite.Sprite):
    def __init__(self, x, y):
        pygame.sprite.Sprite.__init__(self)
        self.image = imagen_piso
        self.rect = self.image.get_rect()
        self.rect.x, self.rect.y = x, y

    def update(self):
        # Mover suelo
        self.rect.x -= velocidad
        if self.rect.x <= -ancho_ventana:
            self.kill()


def salir_juego():
    # Salir del juego
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.7)

# Función para obtener el estado de la mano (abierto/cerrado)
def obtener_estado_mano(puntos_de_mano):
    if not puntos_de_mano:
        return "cerrado"

    # Calculamos la distancia entre la punta del dedo índice y el pulgar
    dedo_indice = puntos_de_mano.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    pulgar = puntos_de_mano.landmark[mp_hands.HandLandmark.THUMB_TIP]
    distancia = ((dedo_indice.x - pulgar.x)**2 + (dedo_indice.y - pulgar.y)**2)**0.5

    # Si la distancia es mayor a un umbral, consideramos que la mano está abierta
    if distancia > 0.08:
        return "abierto"
    else:
        return "cerrado"

def main():
    # Inicializamos la cámara web para el reconocimiento de manos
    cap = cv2.VideoCapture(0)
    cap.set(3, ancho_ventana)
    cap.set(4, altura_ventana)

    global puntaje

    cv2.namedWindow("Reconocimiento de Mano", cv2.WINDOW_NORMAL)

    #Inicializamos el cuy xd
    cuy = pygame.sprite.GroupSingle()
    cuy.add(Cuy())

    # Confi de tubos
    temp_tubos = 0
    tubos = pygame.sprite.Group()

    # Suelo inicial
    x_pos_piso, y_pos_piso = 0, 520
    piso = pygame.sprite.Group()
    piso.add(Piso(x_pos_piso, y_pos_piso))

    ejecutando = True
    while ejecutando:
        # Quit
        salir_juego()

        # Reset cada frame
        ventana.fill((0, 0, 0))

        entrada = pygame.key.get_pressed()

        # Dibujar fondo
        ventana.blit(imagen_lineaCielo, (0, 0))

        ret, imagen = cap.read()
        imagen = cv2.cvtColor(cv2.flip(imagen, 1), cv2.COLOR_BGR2RGB)
        resultado = hands.process(imagen)
        if resultado.multi_hand_landmarks:

            for hand_landmarks in resultado.multi_hand_landmarks:
                estado_mano = obtener_estado_mano(hand_landmarks)
                altura, ancho, _ = imagen.shape

                # Dibujar nodos (puntos) de la mano
                for landmark in hand_landmarks.landmark:
                    x, y = int(landmark.x * ancho), int(landmark.y * altura)
                    cv2.circle(imagen, (x, y), 7, (255, 0, 0), -1)


                # Dibujar líneas entre los nodos de los dedos
                conexiones = mp_hands.HAND_CONNECTIONS
                for conexion in conexiones:
                    x0, y0 = int(hand_landmarks.landmark[conexion[0]].x * ancho), int(
                        hand_landmarks.landmark[conexion[0]].y * altura)
                    x1, y1 = int(hand_landmarks.landmark[conexion[1]].x * ancho), int(
                        hand_landmarks.landmark[conexion[1]].y * altura)
                    cv2.line(imagen, (x0, y0), (x1, y1), (0, 255, 0), 2)

                if estado_mano == "abierto" and not cuy.sprite.salto and cuy.sprite.rect.y > 0 and cuy.sprite.vivo:
                    cuy.sprite.salto = True
                    cuy.sprite.vel = -7


        cv2.imshow("Reconocimiento de Mano", cv2.cvtColor(imagen, cv2.COLOR_RGB2BGR))

        # Spawn piso
        if len(piso) <= 2:
            piso.add(Piso(ancho_ventana, y_pos_piso))

        # Dibujar todas las cosas
        tubos.draw(ventana)
        piso.draw(ventana)
        cuy.draw(ventana)

        # Mostrar puntuacion
        puntaje_texto = fuente.render('Puntaje: ' + str(puntaje), True, pygame.Color(255, 255, 255))
        ventana.blit(puntaje_texto, (20, 20))

        # Actualizamos los objetos
        if cuy.sprite.vivo:
            tubos.update()
            piso.update()
        cuy.update(entrada)

        # Detector de choque
        colision_obst = pygame.sprite.spritecollide(cuy.sprites()[0], tubos, False)
        colision_piso = pygame.sprite.spritecollide(cuy.sprites()[0], piso, False)
        if colision_obst or colision_piso:
            cuy.sprite.vivo = False
            if colision_piso:
                ventana.blit(imagen_game_over, (ancho_ventana // 2 - imagen_game_over.get_width() // 2,
                                                altura_ventana // 2 - imagen_game_over.get_height() // 2))
                if entrada[pygame.K_r]:
                    puntaje = 0
                    break

        # Aparicion de tubos
        if temp_tubos <= 0 and cuy.sprite.vivo:
            x_top, x_bottom = 550, 550
            y_top = random.randint(-600, -480)
            y_bottom = y_top + random.randint(150, 180) + imagen_obst_abajo.get_height()
            tubos.add(Obstaculo(x_top, y_top, imagen_obst_arriba, 'top'))
            tubos.add(Obstaculo(x_bottom, y_bottom, imagen_obst_abajo, 'bottom'))
            temp_tubos = random.randint(180, 250)
        temp_tubos -= 1



        clock.tick(60)
        pygame.display.update()


# Menu
def menu():
    global juego_detenido

    while juego_detenido:
        salir_juego()

        # Dibujar Menu
        ventana.fill((0, 0, 0))
        ventana.blit(imagen_lineaCielo, (0, 0))
        ventana.blit(imagen_piso, (0, 520))
        ventana.blit(imagenes_cuy[0], (100, 250))
        ventana.blit(imagen_inicio, (ancho_ventana // 2 - imagen_inicio.get_width() // 2,
                                     altura_ventana // 2 - imagen_inicio.get_height() // 2))

        # Entrada
        entrada = pygame.key.get_pressed()
        if entrada[pygame.K_SPACE]:
            main()

        pygame.display.update()


menu()
