import pygame
import os

from spritesheet import load_sprite_sheet
from fighter import Fighter


pygame.init()

WIDTH, HEIGHT = 1500, 700
FPS = 60

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("FPS Boxing")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 48)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(BASE_DIR, "assets")


MENU = "menu"
PLAY = "play"
TUTORIAL = "tutorial"

state = MENU
menu_index = 0

bg_path = os.path.join(ASSETS, "bg", "Bg.png")
bg = pygame.image.load(bg_path).convert()
bg = pygame.transform.scale(bg, (WIDTH, HEIGHT))


PLAYER_ANIM = {
    "idle": ("Idle.png", 3, 0.08),
    "punch_l": ("LP.png", 6, 0.18),
    "punch_r": ("RP.png", 6, 0.18),
    "punch_s": ("SP.png", 5, 0.25),
    "defend": ("def.png", 9, 0.15),
}


ENEMY_ANIM = {
    "idle": ("Idle.png", 4, 0.07),
    "punch_l": ("LP.png", 5, 0.25),
    "punch_r": ("RP.png", 5, 0.25),
    "punch_s": ("SP.png", 5, 0.30),
    "defend": ("def.png", 2, 0.12),
    "GHR": ("GHR.png", 3, 0.18),
    "GHL": ("GHL.png", 3, 0.18),
    "GHS": ("GHS.png", 2, 0.20),
    "GHRdef": ("GHRdef.png", 3, 0.14),
    "GHLdef": ("GHLdef.png", 3, 0.14),
}


def load_fighter(folder, anim_config):
    animations = {}

    for state, (filename, frame_count, speed) in anim_config.items():
        animations[state] = {
            "frames": load_sprite_sheet(
                os.path.join(folder, filename), frame_count, 3.5
            ),
            "speed": speed,
        }

    return animations


player_folder = os.path.join(ASSETS, "player")
enemy_folder = os.path.join(ASSETS, "enemy")

player = Fighter(load_fighter(player_folder, PLAYER_ANIM), (WIDTH // 2, HEIGHT - 100))

enemy = Fighter(load_fighter(enemy_folder, ENEMY_ANIM), (WIDTH // 2, HEIGHT))


def draw_menu():
    screen.fill((20, 20, 20))
    options = ["PLAY", "TUTORIAL", "EXIT"]

    for i, text in enumerate(options):
        color = (255, 0, 0) if i == menu_index else (200, 200, 200)
        label = font.render(text, True, color)
        screen.blit(label, (WIDTH // 2 - 60, 320 + i * 70))


def draw_tutorial():
    screen.fill((10, 10, 10))
    lines = [
        "FPS BOXING TUTORIAL",
        "",
        "A  : Punch Left",
        "D  : Punch Right",
        "S  : Defend",
        "",
        "ESC : Back to Menu",
    ]

    for i, line in enumerate(lines):
        txt = font.render(line, True, (220, 220, 220))
        screen.blit(txt, (180, 200 + i * 45))


running = True
while running:
    clock.tick(FPS)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # ===== MENU INPUT =====
        if state == MENU and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                menu_index = (menu_index - 1) % 3
            elif event.key == pygame.K_DOWN:
                menu_index = (menu_index + 1) % 3
            elif event.key == pygame.K_RETURN:
                if menu_index == 0:
                    state = PLAY
                elif menu_index == 1:
                    state = TUTORIAL
                elif menu_index == 2:
                    running = False

        # ===== TUTORIAL INPUT =====
        if state == TUTORIAL and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                state = MENU

        # ===== PLAY INPUT (EVENT – PUNCH) =====
        if state == PLAY and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                state = MENU

            # 👊 PUNCH – NHẤN 1 LẦN
            if not player.is_attacking:
                if event.key == pygame.K_a:
                    player.set_state("punch_l")
                elif event.key == pygame.K_d:
                    player.set_state("punch_r")
                elif event.key == pygame.K_w:
                    player.set_state("punch_s")

    if state == MENU:
        draw_menu()

    elif state == TUTORIAL:
        draw_tutorial()

    elif state == PLAY:
        # BACKGROUND
        screen.blit(bg, (0, 0))

        # ===== HOLD INPUT (DEFEND) =====
        keys = pygame.key.get_pressed()

        if not player.is_attacking:
            if keys[pygame.K_s]:
                player.set_state("defend")
            else:
                player.set_state("idle")

        # UPDATE
        player.update()
        enemy.update()

        # DRAW
        enemy.draw(screen)
        player.draw(screen)

    pygame.display.flip()

pygame.quit()
