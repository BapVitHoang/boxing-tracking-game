import pygame


class Fighter:
    def __init__(self, animations, pos):
        self.animations = animations
        self.state = "idle"

        self.frames = animations[self.state]["frames"]
        self.speed = animations[self.state]["speed"]

        self.index = 0
        self.center = pos

        self.is_attacking = False  # 👈 FIX LỖI Ở ĐÂY

    def set_state(self, state):
        if self.state != state:
            self.state = state
            self.frames = self.animations[state]["frames"]
            self.speed = self.animations[state]["speed"]
            self.index = 0

            # 👊 Check attack state
            self.is_attacking = "punch" in state or "GH" in state

    def update(self):
        self.index += self.speed

        if self.index >= len(self.frames):
            if self.is_attacking:
                self.state = "idle"
                self.frames = self.animations["idle"]["frames"]
                self.speed = self.animations["idle"]["speed"]
                self.index = 0
                self.is_attacking = False
            else:
                self.index = 0

    def draw(self, screen):
        frame = self.frames[int(self.index)]
        rect = frame.get_rect()
        pygame.draw.circle(screen, (255, 0, 0), self.center, 4)
        rect.midbottom = self.center
        screen.blit(frame, rect)
