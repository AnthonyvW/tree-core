import pygame
import time

from UI.Button import Button
from Camera.DefaultCamera import DefaultCamera
from Camera.AmScopeCamera import AmscopeCamera
from printer import printer

pygame.init()
pygame.display.set_caption("Tree Ring Imaging Machine v2")
width, height = (1280,720)
#scale = min(width/src.width, height/src.height)
screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)

# A clock to limit the frame rate.
clock = pygame.time.Clock()  

movementSystem = printer()
camera = AmscopeCamera(width-500,height)
time.sleep(1.5)
camera.resize(width - 500, height)

def func1():
    pass

buttons = [
    Button(movementSystem.moveXLeft    , width - 400, 500, 40, 40),
    Button(movementSystem.moveXRight   , width - 300, 500, 40, 40),
    Button(movementSystem.moveYForward , width - 350, 450, 40, 40),
    Button(movementSystem.moveYBackward, width - 350, 550, 40, 40),
    Button(movementSystem.moveZUp      , width - 250, 475, 40, 40),
    Button(movementSystem.moveZDown    , width - 250, 525, 40, 40),
    Button(camera.takeStillImage       , width - 350, 350, 40, 40),
    ]

running = True
while running:
    clock.tick(60)
    # Mouse Position
    pos = pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.VIDEORESIZE:
            width, height = screen.get_size()

            camera.resize(width-500, height)

            buttons[0].setPosition(width - 400, 500)
            buttons[1].setPosition(width - 300, 500)
            buttons[2].setPosition(width - 350, 450)
            buttons[3].setPosition(width - 350, 550)
            buttons[4].setPosition(width - 250, 475)
            buttons[5].setPosition(width - 250, 525)
            buttons[6].setPosition(width - 350, 350)

            print(width, height)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            for button in buttons:
                button.CheckButton(pos[0], pos[1], True)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
        elif event.type == pygame.KEYUP:
            background_color = pygame.Color(255,0,0)
            screen.fill(background_color)

    # Update
    camera.update()
    for button in buttons:
        button.CheckButton(pos[0], pos[1], False)

    # Rendering
    screen.fill([60,60,60])

    # Draw Buttons
    for button in buttons:
        button.draw(screen)

    # Draw Camera

    screen.blit(camera.getFrame(), (0,0))

    pygame.display.flip()
    pygame.display.update()

pygame.quit()