import pygame
import os
import multiprocessing
from ai_controller import ai_process
from spritesheet import load_sprite_sheet
from fighter import Fighter

# =====================
# GLOBAL CONSTANTS (Để tránh NameError)
# =====================
WIDTH, HEIGHT = 1500, 700
FPS = 120  # Increased from 60 for smoother gameplay

# =====================
# GAME LOGIC FUNCTION
# =====================
def main():
    # 1. INIT PYGAME (Chỉ chạy trong Main Process)
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("FPS Boxing - AI Controlled")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 48)

    # 2. KHỞI ĐỘNG AI PROCESS
    # Queue và Event phải tạo trong main để share
    ai_queue = multiprocessing.Queue(maxsize=1)
    stop_event = multiprocessing.Event()
    
    ai_proc = multiprocessing.Process(target=ai_process, args=(ai_queue, stop_event))
    ai_proc.start()

    # 3. PATHS & ASSETS
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    ASSETS = os.path.join(BASE_DIR, "assets")

    # Load Background
    # Lưu ý: convert() chỉ chạy được sau khi có set_mode() ở trên
    try:
        bg_path = os.path.join(ASSETS, "bg", "Bg.png")
        if os.path.exists(bg_path):
            bg = pygame.image.load(bg_path).convert()
            bg = pygame.transform.scale(bg, (WIDTH, HEIGHT))
        else:
            raise FileNotFoundError("Bg.png not found")
    except Exception as e:
        print(f"Warning: {e}. Using Default Background.")
        bg = pygame.Surface((WIDTH, HEIGHT))
        bg.fill((30, 30, 30))

    # Animation Configs
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

    # Hàm load asset nội bộ
    def load_fighter(folder, anim_config):
        animations = {}
        if not os.path.exists(folder):
            print(f"Error: Folder {folder} not found!")
            return animations

        for state_name, (filename, frame_count, speed) in anim_config.items():
            path = os.path.join(folder, filename)
            try:
                # Load spritesheet cần màn hình đã init, nên để trong main() là đúng
                animations[state_name] = {
                    "frames": load_sprite_sheet(path, frame_count, 3.5),
                    "speed": speed,
                }
            except Exception as e:
                print(f"Missing asset: {filename} ({e})")
        return animations

    # Load Fighters
    player_folder = os.path.join(ASSETS, "player")
    enemy_folder = os.path.join(ASSETS, "enemy")

    try:
        p_anims = load_fighter(player_folder, PLAYER_ANIM)
        e_anims = load_fighter(enemy_folder, ENEMY_ANIM)
        
        # Tạo object Fighter
        # Cần kiểm tra nếu anim rỗng để tránh crash
        if not p_anims or not e_anims:
            print("WARNING: Assets failed to load. Game might crash or look wrong.")

        player = Fighter(p_anims, (WIDTH // 2, HEIGHT - 100))
        enemy = Fighter(e_anims, (WIDTH // 2, HEIGHT))
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        return # Thoát game nếu lỗi nặng

    # 4. GAME STATES
    MENU, PLAY, TUTORIAL = "menu", "play", "tutorial"
    state = MENU
    menu_index = 0

    def draw_menu():
        screen.fill((20, 20, 20))
        options = ["PLAY", "TUTORIAL", "EXIT"]
        for i, text in enumerate(options):
            color = (255, 0, 0) if i == menu_index else (200, 200, 200)
            label = font.render(text, True, color)
            screen.blit(label, (WIDTH // 2 - 60, 320 + i * 70))
        
        note = font.render("Use Arrow Keys & Enter", True, (100, 100, 100))
        screen.blit(note, (WIDTH // 2 - 150, 600))

    def draw_tutorial():
        screen.fill((10, 10, 10))
        lines = [
            "--- AI CONTROLS ---",
            "Left Punch  : Punch Left side",
            "Right Punch : Punch Right side",
            "Straight    : Punch to Center Camera",
            "Defend      : Guard face with both hands",
            "",
            "--- KEYBOARD ---",
            "A / D / W : Punch L / R / Straight",
            "S (Hold)  : Defend",
            "ESC       : Back",
        ]
        for i, line in enumerate(lines):
            col = (255, 200, 0) if "---" in line else (220, 220, 220)
            txt = font.render(line, True, col)
            screen.blit(txt, (180, 150 + i * 45))

    # 5. MAIN LOOP
    running = True
    ai_defend_active = False

    try:
        while running:
            clock.tick(FPS)

            # --- READ AI INPUT ---
            ai_cmd = None
            while not ai_queue.empty():
                ai_cmd = ai_queue.get()
            
            if ai_cmd == "DEFEND_ON": ai_defend_active = True
            elif ai_cmd == "DEFEND_OFF": ai_defend_active = False

            # --- EVENT HANDLING ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if state == MENU and event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP: menu_index = (menu_index - 1) % 3
                    elif event.key == pygame.K_DOWN: menu_index = (menu_index + 1) % 3
                    elif event.key == pygame.K_RETURN:
                        if menu_index == 0: state = PLAY
                        elif menu_index == 1: state = TUTORIAL
                        elif menu_index == 2: running = False

                if state != MENU and event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE: state = MENU

            # --- GAME LOGIC ---
            if state == MENU:
                draw_menu()
            
            elif state == TUTORIAL:
                draw_tutorial()
            
            elif state == PLAY:
                # ATTACK LOGIC
                if not player.is_attacking:
                    # AI Triggers
                    if ai_cmd == "PUNCH_L": player.set_state("punch_l")
                    elif ai_cmd == "PUNCH_R": player.set_state("punch_r")
                    elif ai_cmd == "PUNCH_S": player.set_state("punch_s")
                    
                    # Keyboard Triggers
                    keys = pygame.key.get_pressed()
                    if keys[pygame.K_a]: player.set_state("punch_l")
                    if keys[pygame.K_d]: player.set_state("punch_r")
                    if keys[pygame.K_w]: player.set_state("punch_s")

                # DEFEND LOGIC
                keys = pygame.key.get_pressed()
                if not player.is_attacking:
                    if ai_defend_active or keys[pygame.K_s]:
                        player.set_state("defend")
                    else:
                        player.set_state("idle")

                # Update & Draw
                screen.blit(bg, (0, 0))
                player.update()
                enemy.update()
                enemy.draw(screen)
                player.draw(screen)
                
                # Debug UI
                status = "AI GUARD" if ai_defend_active else ""
                if ai_cmd and "PUNCH" in ai_cmd: status = f"AI {ai_cmd}"
                if status:
                    dbg = font.render(status, True, (0, 255, 0))
                    screen.blit(dbg, (20, 20))

            pygame.display.flip()

    except KeyboardInterrupt:
        pass
    finally:
        # Dọn dẹp tiến trình AI khi thoát
        stop_event.set()
        ai_proc.join()
        pygame.quit()
        print("Game Closed.")

# =====================
# ENTRY POINT
# =====================
if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()