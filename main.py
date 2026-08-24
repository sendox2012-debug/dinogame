import pygame
import random
import math
import os

# ============================================================
# Инициализация
# ============================================================
pygame.init()

try:
    pygame.mixer.init()
except Exception:
    pass

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ICON_PATH = os.path.join(BASE_DIR, "img", "icon.png")
FONT_PATH = os.path.join(BASE_DIR, "fonts", "font.ttf")

# Иконка - не критично, если нет
try:
    if os.path.exists(ICON_PATH):
        pygame.display.set_icon(pygame.image.load(ICON_PATH))
except Exception:
    pass

# Экран: сначала пробуем fullscreen, если не вышло - окно
try:
    if os.environ.get("DINO_WINDOW") == "1":
        raise RuntimeError("Window mode requested")

    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    WIDTH, HEIGHT = screen.get_size()

    if WIDTH < 320 or HEIGHT < 240:
        raise RuntimeError("Bad fullscreen size")
except Exception:
    screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
    WIDTH, HEIGHT = screen.get_size()

pygame.mouse.set_visible(True)
clock = pygame.time.Clock()
FPS = 60

# ============================================================
# Базовые константы
# ============================================================
HORIZON = int(HEIGHT * 0.35)
FAR_Y = int(HEIGHT * 0.48)
NEAR_Y = int(HEIGHT * 0.88)

GRAVITY = max(0.95, HEIGHT * 0.00115)
JUMP_POWER = max(16.0, HEIGHT * 0.020)
BASE_SPEED = max(8.0, WIDTH * 0.0075)
DEPTH_TOL = 0.26

WHITE = (255, 255, 255)
BLACK = (18, 18, 24)
GRAY = (160, 165, 175)
DARK_GRAY = (35, 35, 42)
GREEN = (46, 204, 113)
BLUE = (52, 152, 219)
RED = (231, 76, 60)
GOLD = (241, 196, 15)

SKY_TOP = (255, 183, 120)
SKY_BOTTOM = (255, 236, 190)
SUN_COLOR = (255, 214, 110)
FAR_COLOR = (233, 196, 138)
GROUND_COLOR = (226, 186, 124)
GROUND_LINE = (196, 152, 88)
CACTUS_COLOR = (39, 174, 96)
BIRD_COLOR = (139, 69, 19)


# ============================================================
# Утилиты
# ============================================================
def clamp(v, a, b):
    return max(a, min(b, v))


def lerp(a, b, t):
    return a + (b - a) * t


def shade(c, amt):
    return tuple(max(0, min(255, ch + amt)) for ch in c)


def load_font(size, bold=False):
    size = max(12, int(size))
    try:
        if os.path.exists(FONT_PATH):
            f = pygame.font.Font(FONT_PATH, size)
            if bold:
                f.set_bold(True)
            return f
    except Exception:
        pass

    try:
        return pygame.font.SysFont("dejavusans,arial,segoeui", size, bold=bold)
    except Exception:
        return pygame.font.Font(None, size)


font_title = load_font(HEIGHT * 0.070, True)
font_main = load_font(HEIGHT * 0.035, True)
font_small = load_font(HEIGHT * 0.022, False)


def draw_rounded_rect(surf, color, rect, radius=10):
    rect = pygame.Rect(rect)
    radius = max(0, min(int(radius), min(rect.width, rect.height) // 2))
    pygame.draw.rect(surf, color, rect, border_radius=radius)


def draw_text_centered(surf, text, font, color, x, y, shadow_color=(0, 0, 0)):
    if not text:
        return
    main = font.render(text, True, color)
    shadow = font.render(text, True, shadow_color)
    rect = main.get_rect(center=(int(x), int(y)))
    surf.blit(shadow, (rect.x + 2, rect.y + 3))
    surf.blit(main, rect)


# ============================================================
# Статичный фон
# ============================================================
SKY = pygame.Surface((WIDTH, HEIGHT))
for y in range(0, HEIGHT, 2):
    r = y / HEIGHT
    c = (
        int(SKY_TOP[0] * (1 - r) + SKY_BOTTOM[0] * r),
        int(SKY_TOP[1] * (1 - r) + SKY_BOTTOM[1] * r),
        int(SKY_TOP[2] * (1 - r) + SKY_BOTTOM[2] * r),
    )
    pygame.draw.rect(SKY, c, (0, y, WIDTH, 2))

SUN_X = int(WIDTH * 0.78)
SUN_Y = int(HEIGHT * 0.18)
SUN_R = int(min(WIDTH, HEIGHT) * 0.35)
SUN_GLOW = pygame.Surface((SUN_R * 2, SUN_R * 2), pygame.SRCALPHA)
for rad in range(SUN_R, 0, -4):
    a = int(100 * (1 - rad / SUN_R) ** 2)
    pygame.draw.circle(SUN_GLOW, SUN_COLOR + (a,), (SUN_R, SUN_R), rad)


# ============================================================
# Мобильное управление: джойстик + кнопки
# ============================================================
class TouchControls:
    def __init__(self):
        surf = pygame.display.get_surface()
        if surf is None:
            self.w, self.h = 1280, 720
        else:
            self.w, self.h = surf.get_size()

        self.min_dim = min(self.w, self.h)

        self.joy_radius = max(30, int(self.min_dim * 0.11))
        self.knob_radius = max(12, int(self.joy_radius * 0.45))
        self.button_radius = max(24, int(self.min_dim * 0.075))
        self.pause_radius = max(18, int(self.min_dim * 0.038))

        self.joy_center_default = (int(self.w * 0.16), int(self.h * 0.78))
        self.jump_btn = (int(self.w * 0.88), int(self.h * 0.78))
        self.duck_btn = (int(self.w * 0.72), int(self.h * 0.84))
        self.pause_btn = (int(self.w * 0.50), int(self.h * 0.07))

        self.font = pygame.font.Font(None, max(18, int(self.min_dim * 0.04)))
        self.reset()

    def reset(self):
        self.joy_id = None
        self.joy_center = self.joy_center_default
        self.joy_current = self.joy_center_default
        self.joy_x = 0.0
        self.joy_y = 0.0

        self.jump_requested = False
        self.duck_held = False
        self.pause_pressed = False

        self.active_jump_ids = set()
        self.active_duck_ids = set()

    def _inside(self, pos, center, radius):
        dx = pos[0] - center[0]
        dy = pos[1] - center[1]
        return dx * dx + dy * dy <= radius * radius

    def _calc_joy(self):
        dx = self.joy_current[0] - self.joy_center[0]
        dy = self.joy_current[1] - self.joy_center[1]
        dist = math.hypot(dx, dy)
        maxr = max(1, self.joy_radius)

        if dist > maxr:
            dx = dx / dist * maxr
            dy = dy / dist * maxr

        self.joy_x = dx / maxr
        self.joy_y = dy / maxr

        if abs(self.joy_x) < 0.15:
            self.joy_x = 0.0
        if abs(self.joy_y) < 0.15:
            self.joy_y = 0.0

    def _get_pos(self, e):
        if e.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
            return int(e.x * self.w), int(e.y * self.h)
        return getattr(e, "pos", (0, 0))

    def update(self, events):
        self.pause_pressed = False

        for e in events:
            # Нажатие
            if e.type == pygame.FINGERDOWN or (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1):
                fid = getattr(e, "finger_id", -1)
                if e.type == pygame.MOUSEBUTTONDOWN:
                    fid = -1

                pos = self._get_pos(e)

                # Пауза
                if self._inside(pos, self.pause_btn, self.pause_radius * 1.5):
                    self.pause_pressed = True
                    continue

                # Кнопка прыжка
                if self._inside(pos, self.jump_btn, self.button_radius * 1.35):
                    self.active_jump_ids.add(fid)
                    self.jump_requested = True
                    continue

                # Кнопка приседа
                if self._inside(pos, self.duck_btn, self.button_radius * 1.35):
                    self.active_duck_ids.add(fid)
                    self.duck_held = True
                    continue

                # Левая половина - джойстик
                if pos[0] < self.w * 0.55 and self.joy_id is None:
                    self.joy_id = fid
                    self.joy_center = pos
                    self.joy_current = pos
                    self._calc_joy()

                # Правая половина вне кнопок - тоже прыжок
                elif pos[0] >= self.w * 0.55:
                    self.jump_requested = True

            # Движение
            elif e.type == pygame.FINGERMOTION or e.type == pygame.MOUSEMOTION:
                if e.type == pygame.MOUSEMOTION:
                    if self.joy_id == -1 and pygame.mouse.get_pressed()[0]:
                        self.joy_current = self._get_pos(e)
                        self._calc_joy()
                else:
                    fid = getattr(e, "finger_id", -1)
                    if fid == self.joy_id:
                        self.joy_current = self._get_pos(e)
                        self._calc_joy()

            # Отпускание
            elif e.type == pygame.FINGERUP or (e.type == pygame.MOUSEBUTTONUP and e.button == 1):
                fid = getattr(e, "finger_id", -1)
                if e.type == pygame.MOUSEBUTTONUP:
                    fid = -1

                if fid == self.joy_id:
                    self.joy_id = None
                    self.joy_center = self.joy_center_default
                    self.joy_current = self.joy_center_default
                    self.joy_x = 0.0
                    self.joy_y = 0.0

                if fid in self.active_jump_ids:
                    self.active_jump_ids.remove(fid)

                if fid in self.active_duck_ids:
                    self.active_duck_ids.remove(fid)
                    if not self.active_duck_ids:
                        self.duck_held = False

    def consume_jump(self):
        val = self.jump_requested
        self.jump_requested = False
        return val

    def draw(self, surf):
        # Джойстик
        center = self.joy_center if self.joy_id is not None else self.joy_center_default

        base = pygame.Surface((self.joy_radius * 2, self.joy_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(base, (255, 255, 255, 35), (self.joy_radius, self.joy_radius), self.joy_radius)
        pygame.draw.circle(base, (255, 255, 255, 80), (self.joy_radius, self.joy_radius), self.joy_radius, 3)
        surf.blit(base, (center[0] - self.joy_radius, center[1] - self.joy_radius))

        knob_pos = (
            center[0] + int(self.joy_x * self.joy_radius),
            center[1] + int(self.joy_y * self.joy_radius),
        )

        knob = pygame.Surface((self.knob_radius * 2, self.knob_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(knob, (255, 255, 255, 130), (self.knob_radius, self.knob_radius), self.knob_radius)
        surf.blit(knob, (knob_pos[0] - self.knob_radius, knob_pos[1] - self.knob_radius))

        # Кнопки
        self._draw_button(surf, self.jump_btn, self.button_radius, "JUMP", bool(self.active_jump_ids))
        self._draw_button(surf, self.duck_btn, self.button_radius, "DUCK", self.duck_held)
        self._draw_button(surf, self.pause_btn, self.pause_radius, "||", False)

    def _draw_button(self, surf, center, radius, label, active):
        s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)

        bg = (255, 255, 255, 95 if active else 45)
        border = (255, 255, 255, 170 if active else 90)

        pygame.draw.circle(s, bg, (radius, radius), radius)
        pygame.draw.circle(s, border, (radius, radius), radius, 3)

        txt = self.font.render(label, True, (255, 255, 255))
        s.blit(txt, txt.get_rect(center=(radius, radius)))

        surf.blit(s, (center[0] - radius, center[1] - radius))


# ============================================================
# Кнопки меню
# ============================================================
class Button:
    def __init__(self, x, y, w, h, text, action, color=BLUE):
        self.rect = pygame.Rect(int(x), int(y), int(w), int(h))
        self.text = text
        self.action = action
        self.base_color = color
        self.hover_color = shade(color, 30)
        self.hovered = False

    def update(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)

    def draw(self, surf):
        c = self.hover_color if self.hovered else self.base_color
        sh = self.rect.copy()
        sh.y += int(HEIGHT * 0.004)

        draw_rounded_rect(surf, DARK_GRAY, sh, int(HEIGHT * 0.015))
        draw_rounded_rect(surf, c, self.rect, int(HEIGHT * 0.015))
        draw_text_centered(surf, self.text, font_main, WHITE, self.rect.centerx, self.rect.centery)

    def handle_click(self, mouse_pos):
        if self.rect.collidepoint(mouse_pos):
            self.action()
            return True
        return False


# ============================================================
# Игрок
# ============================================================
STAND = [
    (0.00, 0.40), (0.10, 0.28), (0.24, 0.20), (0.40, 0.12), (0.50, 0.04), (0.56, 0.00),
    (0.98, 0.00), (0.98, 0.14), (0.80, 0.14), (0.80, 0.20), (0.98, 0.20), (0.98, 0.30),
    (0.74, 0.32), (0.62, 0.40), (0.58, 0.54), (0.50, 0.68), (0.30, 0.70), (0.16, 0.60), (0.06, 0.50)
]

DUCK = [
    (0.00, 0.30), (0.12, 0.16), (0.30, 0.06), (0.55, 0.02), (0.80, 0.06), (0.98, 0.16),
    (0.98, 0.30), (0.82, 0.30), (0.82, 0.36), (0.98, 0.36), (0.98, 0.48), (0.78, 0.52),
    (0.60, 0.60), (0.40, 0.66), (0.20, 0.62), (0.08, 0.48)
]


class Player:
    def __init__(self):
        self.world_x = 0.0
        self.z = 0.0
        self.y = 0.0
        self.vy = 0.0
        self.jumping = False
        self.ducking = False
        self.invuln = 0
        self.run_t = 0.0
        self.base_h = int(HEIGHT * 0.12)
        self.color = GREEN

    def request_jump(self):
        if not self.jumping and not self.ducking and self.y <= 0.0:
            self.vy = JUMP_POWER
            self.jumping = True

    def update(self, keys, speed, controls):
        self.world_x += speed

        # Клавиатура: глубина
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.z -= 0.065
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.z += 0.065

        # Джойстик: глубина
        if controls is not None:
            self.z += controls.joy_x * 0.085

        self.z = clamp(self.z, -1.0, 1.0)

        # Приседание
        duck = bool(keys[pygame.K_DOWN] or keys[pygame.K_s])
        if controls is not None:
            duck = duck or controls.duck_held
        self.ducking = duck and not self.jumping

        # Физика прыжка
        if self.jumping or self.y > 0.0:
            self.vy -= GRAVITY
            self.y += self.vy
            if self.y <= 0.0:
                self.y = 0.0
                self.vy = 0.0
                self.jumping = False

        self.run_t += 0.02 * speed

        if self.invuln > 0:
            self.invuln -= 1

    def draw(self, surf, project, tick):
        if self.invuln > 0 and (tick // 4) % 2 == 0:
            return

        sh_sx, sh_sy, _ = project(self.world_x, self.z, 0.0)
        sx, sy, scale = project(self.world_x, self.z, self.y)

        if self.ducking:
            outline = DUCK
            h = int(self.base_h * scale * 0.62)
            w = int(self.base_h * scale * 1.50)
        else:
            outline = STAND
            h = int(self.base_h * scale)
            w = int(self.base_h * scale * 1.25)

        # Тень
        shadow_k = clamp(1.0 - self.y / 260.0, 0.35, 1.0)
        sw = max(8, int(w * 0.9 * shadow_k))
        shh = max(4, int(h * 0.20 * shadow_k))
        shadow = pygame.Surface((sw, shh), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 95), (0, 0, sw, shh))
        surf.blit(shadow, (int(sh_sx - sw // 2), int(sh_sy - shh // 2)))

        left = int(sx - w // 2)
        top = int(sy - h)

        if not self.jumping and not self.ducking:
            top += int(math.sin(self.run_t * 2.0) * 2.0 * scale)

        c = self.color
        dark = shade(c, -55)
        light = shade(c, 45)

        pts = [(left + int(nx * w), top + int(ny * h)) for nx, ny in outline]
        pygame.draw.polygon(surf, c, pts)

        # Шипы
        for px, py in [(0.24, 0.20), (0.40, 0.12), (0.56, 0.02)]:
            x0 = left + int(px * w)
            y0 = top + int(py * h)
            pygame.draw.polygon(
                surf,
                dark,
                [
                    (x0 - int(w * 0.03), y0 + int(h * 0.03)),
                    (x0 + int(w * 0.05), y0 + int(h * 0.03)),
                    (x0 + int(w * 0.01), y0 - int(h * 0.07)),
                ],
            )

        # Брюхо
        pygame.draw.ellipse(surf, light, (left + int(w * 0.22), top + int(h * 0.44), int(w * 0.32), int(h * 0.24)))

        # Глаз
        if self.ducking:
            ex, ey = left + int(w * 0.88), top + int(h * 0.20)
        else:
            ex, ey = left + int(w * 0.87), top + int(h * 0.07)

        pygame.draw.circle(surf, WHITE, (ex, ey), max(2, int(h * 0.05)))
        pygame.draw.circle(surf, BLACK, (ex + 1, ey), max(1, int(h * 0.025)))

        # Ноги
        hip_y = top + int(h * 0.66)
        leg_w = max(2, int(w * 0.09))
        bottom = int(sy)

        for i, hx in enumerate((0.36, 0.52)):
            hpx = left + int(hx * w)

            if self.jumping:
                fx = hpx + int(w * 0.06)
                fy = hip_y + int(h * 0.18)
            else:
                ph = math.sin(self.run_t + i * math.pi)
                fx = hpx + int(ph * w * 0.16)
                lift = max(0.0, -math.cos(self.run_t + i * math.pi)) * h * 0.15
                fy = bottom - int(lift)

            pygame.draw.line(surf, dark, (hpx, hip_y), (fx, fy), leg_w)
            pygame.draw.rect(surf, dark, (fx, fy - int(h * 0.08), int(w * 0.14), int(h * 0.08)))

    def get_rect(self, project):
        sx, sy, scale = project(self.world_x, self.z, self.y)

        if self.ducking:
            h = int(self.base_h * scale * 0.62)
            w = int(self.base_h * scale * 1.50)
        else:
            h = int(self.base_h * scale)
            w = int(self.base_h * scale * 1.25)

        return pygame.Rect(
            int(sx - w * 0.40),
            int(sy - h * 0.96),
            int(w * 0.80),
            int(h * 0.96),
        )


# ============================================================
# Препятствия
# ============================================================
class Obstacle:
    def __init__(self, world_x, kind, z):
        self.world_x = float(world_x)
        self.kind = kind
        self.z = float(z)
        self.t = random.randint(0, 100)

        s = HEIGHT
        if kind == "cactus":
            self.w = s * 0.050
            self.h = random.uniform(s * 0.08, s * 0.14)
            self.fly_h = 0.0
            self.base_fly = 0.0
        else:  # bird
            self.w = s * 0.080
            self.h = s * 0.055
            self.base_fly = random.choice([s * 0.12, s * 0.22])
            self.fly_h = self.base_fly

    def update(self, speed):
        self.t += 1
        if self.kind == "bird":
            self.fly_h = self.base_fly + math.sin(self.t * 0.09) * HEIGHT * 0.02
            self.world_x -= speed * 0.12

    def height(self):
        return self.fly_h if self.kind == "bird" else 0.0

    def draw(self, surf, project):
        sx, sy, scale = project(self.world_x, self.z, self.height())
        w = max(2, int(self.w * scale))
        h = max(2, int(self.h * scale))

        # Тень для наземных
        if self.kind != "bird":
            shx, shy, _ = project(self.world_x, self.z, 0.0)
            sh_w = max(6, int(w * 0.90))
            sh_h = max(3, int(h * 0.18))
            shadow_c = shade(GROUND_COLOR, -45)
            pygame.draw.ellipse(surf, shadow_c, (int(shx - sh_w / 2), int(shy - sh_h / 2), sh_w, sh_h))

        left = int(sx - w / 2)
        top = int(sy - h)

        if self.kind == "cactus":
            pygame.draw.rect(surf, CACTUS_COLOR, (left + int(w * 0.30), top, int(w * 0.40), h), border_radius=max(1, int(w * 0.20)))
            pygame.draw.rect(surf, CACTUS_COLOR, (left, top + int(h * 0.25), int(w * 0.30), int(h * 0.30)), border_radius=max(1, int(w * 0.15)))
            pygame.draw.rect(surf, CACTUS_COLOR, (left + int(w * 0.70), top + int(h * 0.40), int(w * 0.30), int(h * 0.30)), border_radius=max(1, int(w * 0.15)))
        else:
            body_rect = pygame.Rect(left, int(sy - h * 0.35), int(w * 0.80), int(h * 0.70))
            pygame.draw.ellipse(surf, BIRD_COLOR, body_rect)

            wing_y = int(sy - h * 0.55) if (self.t // 8) % 2 == 0 else int(sy + h * 0.10)
            pygame.draw.polygon(
                surf,
                shade(BIRD_COLOR, -40),
                [
                    (left + int(w * 0.15), int(sy)),
                    (left + int(w * 0.40), wing_y),
                    (left + int(w * 0.60), int(sy)),
                ],
            )

    def get_rect(self, project):
        sx, sy, scale = project(self.world_x, self.z, self.height())
        w = max(4, int(self.w * scale))
        h = max(4, int(self.h * scale))

        if self.kind == "bird":
            return pygame.Rect(int(sx - w / 2 + 3), int(sy - h / 2 + 3), max(4, w - 6), max(4, h - 6))

        return pygame.Rect(int(sx - w / 2 + 3), int(sy - h + 3), max(4, w - 6), max(4, h - 6))


# ============================================================
# Монеты
# ============================================================
class Coin:
    def __init__(self, world_x, z):
        self.world_x = float(world_x)
        self.z = float(z)
        self.base_h = HEIGHT * random.uniform(0.05, 0.09)
        self.t = random.uniform(0.0, math.pi * 2)

    def update(self):
        self.t += 0.12

    def height(self):
        return self.base_h + math.sin(self.t) * HEIGHT * 0.006

    def draw(self, surf, project):
        sx, sy, scale = project(self.world_x, self.z, self.height())
        r = max(3, int(HEIGHT * 0.018 * scale))
        w = max(2, int(r * 2 * abs(math.cos(self.t))))

        pygame.draw.circle(surf, (255, 235, 120), (int(sx), int(sy)), r + max(2, int(r * 0.25)))
        pygame.draw.ellipse(surf, GOLD, (int(sx - w / 2), int(sy - r), w, r * 2))

    def get_rect(self, project):
        sx, sy, scale = project(self.world_x, self.z, self.height())
        r = max(3, int(HEIGHT * 0.018 * scale))
        return pygame.Rect(int(sx - r), int(sy - r), r * 2, r * 2)


# ============================================================
# Частицы
# ============================================================
class Particle:
    def __init__(self, world_x, z, y, color):
        self.world_x = float(world_x)
        self.z = float(z)
        self.y = float(y)
        self.vx = random.uniform(-3.0, 3.0)
        self.vy = random.uniform(2.0, 7.0)
        self.life = 1.0
        self.decay = random.uniform(0.03, 0.06)
        self.color = color
        self.size = random.randint(3, 6)

    def update(self):
        self.world_x += self.vx
        self.y += self.vy
        self.vy -= 0.28

        if self.y < 0:
            self.y = 0
            self.vy *= -0.3

        self.life -= self.decay

    def draw(self, surf, project):
        if self.life <= 0:
            return

        sx, sy, scale = project(self.world_x, self.z, self.y)
        s = max(1, int(self.size * self.life * scale))
        c = tuple(int(ch * self.life) for ch in self.color)
        pygame.draw.circle(surf, c, (int(sx), int(sy)), s)


# ============================================================
# Игра
# ============================================================
class Game:
    def __init__(self):
        self.state = "menu"  # menu / playing / gameover
        self.paused = False
        self.running = True

        self.player = Player()
        self.controls = TouchControls()

        self.obstacles = []
        self.coins = []
        self.particles = []

        self.tick = 0
        self.score = 0
        self.coin_count = 0
        self.hp = 3
        self.speed = BASE_SPEED

        self.spawn_timer = 50
        self.coin_timer = 70

        self.shake = 0.0
        self.cam_y = 0.0

        self.buttons = []

    # ---------- сервис ----------
    def start_game(self):
        self.player = Player()
        self.controls.reset()

        self.obstacles.clear()
        self.coins.clear()
        self.particles.clear()

        self.state = "playing"
        self.paused = False

        self.tick = 0
        self.score = 0
        self.coin_count = 0
        self.hp = 3
        self.speed = BASE_SPEED

        self.spawn_timer = 45
        self.coin_timer = 70

        self.shake = 0.0
        self.cam_y = 0.0

    def to_menu(self):
        self.state = "menu"
        self.paused = False

    def add_particles(self, world_x, z, y, color, n=12):
        for _ in range(n):
            self.particles.append(Particle(world_x, z, y, color))

    def damage(self):
        if self.player.invuln > 0:
            return

        self.hp -= 1
        self.player.invuln = 90
        self.shake = 16.0
        self.add_particles(self.player.world_x, self.player.z, self.player.y + 30, RED, 18)

        if self.hp <= 0:
            self.state = "gameover"

    # ---------- 2.5D проекция ----------
    def _shake_offset(self):
        if self.shake > 0.5:
            s = int(self.shake)
            if s > 0:
                return random.randint(-s, s), random.randint(-s, s)
        return 0, 0

    def project(self, world_x, z, y_height):
        t = clamp((z + 1.0) / 2.0, 0.0, 1.0)
        scale = 0.52 + 0.88 * t
        ground_y = FAR_Y + (NEAR_Y - FAR_Y) * t

        ox, oy = self._shake_offset()

        sx = WIDTH * 0.30 + (world_x - self.player.world_x) * scale + ox
        sy = ground_y + self.cam_y - y_height * scale + oy

        return int(sx), int(sy), scale

    # ---------- спавн ----------
    def spawn_wave(self):
        base_x = self.player.world_x + WIDTH * random.uniform(0.95, 1.35)
        pattern = random.choice(["single", "single", "double", "wall", "bird", "coins"])

        if pattern == "single":
            z = random.uniform(-0.9, 0.9)
            self.obstacles.append(Obstacle(base_x, "cactus", z))

        elif pattern == "double":
            z1 = random.uniform(-0.9, -0.1)
            z2 = random.uniform(0.1, 0.9)
            self.obstacles.append(Obstacle(base_x, "cactus", z1))
            self.obstacles.append(Obstacle(base_x + random.randint(40, 120), "cactus", z2))

        elif pattern == "wall":
            lanes = [-0.7, 0.0, 0.7]
            gap = random.choice(lanes)

            for z in lanes:
                if abs(z - gap) > 0.1:
                    self.obstacles.append(
                        Obstacle(base_x + random.randint(-20, 20), "cactus", z + random.uniform(-0.05, 0.05))
                    )

        elif pattern == "bird":
            z = random.uniform(-0.8, 0.8)
            self.obstacles.append(Obstacle(base_x, "bird", z))

            if self.score > 400 and random.random() < 0.5:
                self.obstacles.append(
                    Obstacle(base_x + 160, "bird", clamp(z + random.uniform(-0.4, 0.4), -1.0, 1.0))
                )

        elif pattern == "coins":
            z = random.uniform(-0.8, 0.8)
            for i in range(4):
                self.coins.append(Coin(base_x + i * 70, z))

    # ---------- обновление ----------
    def update(self, keys):
        if self.state != "playing" or self.paused:
            return

        self.tick += 1

        self.speed = BASE_SPEED + min(18.0, self.score * 0.02)
        self.player.update(keys, self.speed, self.controls)
        self.cam_y = -self.player.y * 0.04

        if self.shake > 0:
            self.shake *= 0.88
            if self.shake < 0.4:
                self.shake = 0.0

        # Спавн
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self.spawn_wave()
            self.spawn_timer = max(18, 46 - int(self.score / 55)) + random.randint(0, 10)

        self.coin_timer -= 1
        if self.coin_timer <= 0:
            self.coin_timer = random.randint(55, 95)
            if random.random() < 0.75:
                z = random.uniform(-0.85, 0.85)
                self.coins.append(Coin(self.player.world_x + WIDTH + random.randint(80, 240), z))

        # Обновление объектов
        for o in self.obstacles[:]:
            o.update(self.speed)
            if o.world_x < self.player.world_x - WIDTH * 0.75:
                self.obstacles.remove(o)

        for c in self.coins[:]:
            c.update()
            if c.world_x < self.player.world_x - WIDTH * 0.75:
                self.coins.remove(c)

        for p in self.particles[:]:
            p.update()
            if p.life <= 0:
                self.particles.remove(p)

        # Столкновения
        pr = self.player.get_rect(self.project)

        for o in self.obstacles[:]:
            if abs(o.z - self.player.z) < DEPTH_TOL:
                if pr.colliderect(o.get_rect(self.project)):
                    self.damage()
                    self.obstacles.remove(o)
                    break

        # Монеты
        for c in self.coins[:]:
            if abs(c.z - self.player.z) < 0.34:
                if pr.colliderect(c.get_rect(self.project)):
                    self.coin_count += 1
                    self.add_particles(c.world_x, c.z, c.height(), GOLD, 10)
                    self.coins.remove(c)

        # Счёт
        self.score = int(self.player.world_x / 12)

    # ---------- фон ----------
    def draw_world_background(self, surf):
        surf.blit(SKY, (0, 0))

        # Солнце
        surf.blit(SUN_GLOW, (SUN_X - SUN_GLOW.get_width() // 2, SUN_Y - SUN_GLOW.get_height() // 2))
        pygame.draw.circle(surf, SUN_COLOR, (SUN_X, SUN_Y), int(HEIGHT * 0.045))

        # Дальний слой дюн
        spacing = int(WIDTH / 3) + 1
        base = int(self.player.world_x * 0.15)
        tile_start = base // spacing - 1

        for i in range(7):
            tile = tile_start + i
            x = tile * spacing - base
            rnd = random.Random(tile * 7919)

            w = int(spacing * rnd.uniform(1.0, 1.7))
            h = int(HEIGHT * rnd.uniform(0.05, 0.12))
            y = HORIZON + int(HEIGHT * 0.02)

            pygame.draw.ellipse(surf, FAR_COLOR, (x, y - h, w, h * 2))

            if rnd.random() < 0.25:
                ph = int(HEIGHT * rnd.uniform(0.07, 0.14))
                px = x + int(spacing * 0.35)
                pygame.draw.polygon(
                    surf,
                    shade(FAR_COLOR, -25),
                    [
                        (px, HORIZON + int(HEIGHT * 0.02)),
                        (px + int(ph * 0.7), HORIZON - ph),
                        (px + int(ph * 1.4), HORIZON + int(HEIGHT * 0.02)),
                    ],
                )

        # Земля
        pygame.draw.rect(surf, GROUND_COLOR, (0, HORIZON, WIDTH, HEIGHT - HORIZON))

        # Туман у горизонта
        fog = pygame.Surface((WIDTH, int(HEIGHT * 0.08)), pygame.SRCALPHA)
        fog.fill(SKY_BOTTOM + (90,))
        surf.blit(fog, (0, HORIZON))

        # Горизонтальные линии глубины
        for z in (-1.0, -0.5, 0.0, 0.5, 1.0):
            _, y, _ = self.project(self.player.world_x, z, 0.0)
            w_line = 2 if abs(z) > 0.9 else 1
            pygame.draw.line(surf, GROUND_LINE, (0, int(y)), (WIDTH, int(y)), w_line)

        # Движущиеся перспективные линии
        interval = max(120, int(WIDTH * 0.10))
        start = int(self.player.world_x // interval) * interval

        for k in range(-1, 24):
            wx = start + k * interval
            prev = None

            for zi in range(0, 11):
                z = -1.0 + zi * 0.2
                sx, sy, _ = self.project(wx, z, 0.0)

                if -60 < sx < WIDTH + 60:
                    if prev is not None:
                        pygame.draw.line(surf, GROUND_LINE, prev, (sx, sy), 1)
                    prev = (sx, sy)
                else:
                    prev = None

    # ---------- отрисовка игры ----------
    def draw(self, surf):
        self.draw_world_background(surf)

        # Объекты с сортировкой по глубине
        entities = []

        for o in self.obstacles:
            entities.append((o.z, "obs", o))
        for c in self.coins:
            entities.append((c.z, "coin", c))
        for p in self.particles:
            entities.append((p.z, "part", p))

        entities.append((self.player.z, "player", self.player))
        entities.sort(key=lambda x: x[0])

        for _, kind, obj in entities:
            if kind == "player":
                obj.draw(surf, self.project, self.tick)
            else:
                obj.draw(surf, self.project)

        self.draw_hud(surf)

        if self.paused and self.state == "playing":
            ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 160))
            surf.blit(ov, (0, 0))

            draw_text_centered(surf, "ПАУЗА", font_title, WHITE, WIDTH // 2, HEIGHT * 0.35)
            draw_text_centered(surf, "ESC — продолжить | M — меню", font_main, GRAY, WIDTH // 2, HEIGHT * 0.50)

        if self.state == "gameover":
            ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 170))
            surf.blit(ov, (0, 0))

            draw_text_centered(surf, "ИГРА ОКОНЧЕНА", font_title, RED, WIDTH // 2, HEIGHT * 0.30)
            draw_text_centered(surf, f"Счёт: {self.score}", font_title, WHITE, WIDTH // 2, HEIGHT * 0.43)
            draw_text_centered(surf, f"Монеты: {self.coin_count}", font_main, GOLD, WIDTH // 2, HEIGHT * 0.54)
            draw_text_centered(surf, "Тапни для рестарта | M — меню", font_main, (235, 240, 255), WIDTH // 2, HEIGHT * 0.66)

    def draw_hud(self, surf):
        pw = int(WIDTH * 0.20)
        ph = int(HEIGHT * 0.15)
        px = int(WIDTH * 0.015)
        py = int(HEIGHT * 0.02)

        draw_rounded_rect(surf, (0, 0, 0), pygame.Rect(px, py, pw, ph), int(HEIGHT * 0.015))
        draw_text_centered(surf, f"Счёт: {self.score}", font_main, WHITE, px + pw / 2, py + ph * 0.22)
        draw_text_centered(surf, f"Монеты: {self.coin_count}", font_small, GOLD, px + pw / 2, py + ph * 0.48)

        # Сердца
        for i in range(3):
            hx = int(px + pw / 2 - 45 + i * 45)
            hy = int(py + ph * 0.78)
            c = RED if i < self.hp else (70, 70, 80)

            pygame.draw.circle(surf, c, (hx - 7, hy), 7)
            pygame.draw.circle(surf, c, (hx + 7, hy), 7)
            pygame.draw.polygon(surf, c, [(hx - 13, hy + 2), (hx + 13, hy + 2), (hx, hy + 15)])

        if self.state == "playing" and self.score < 120:
            draw_text_centered(
                surf,
                "Джойстик слева | JUMP справа | DUCK — присесть",
                font_small,
                (235, 240, 255),
                WIDTH // 2,
                HEIGHT * 0.93,
            )

    # ---------- меню ----------
    def draw_menu(self, surf):
        self.draw_world_background(surf)

        pw = int(WIDTH * 0.38)
        ph = int(HEIGHT * 0.74)
        px = (WIDTH - pw) // 2
        py = (HEIGHT - ph) // 2

        draw_rounded_rect(surf, WHITE, pygame.Rect(px, py, pw, ph), int(HEIGHT * 0.02))

        self.buttons.clear()
        mouse_pos = pygame.mouse.get_pos()

        draw_text_centered(surf, "DINO XTREME 2.5D", font_title, GOLD, WIDTH // 2, py + int(HEIGHT * 0.08))

        bw = int(pw * 0.62)
        bh = int(HEIGHT * 0.075)
        bx = (WIDTH - bw) // 2
        by = py + int(HEIGHT * 0.20)
        sp = int(HEIGHT * 0.11)

        self.buttons.append(Button(bx, by, bw, bh, "Играть", self.start_game, GREEN))
        self.buttons.append(Button(bx, by + sp, bw, bh, "Выход", lambda: setattr(self, "running", False), RED))

        for b in self.buttons:
            b.update(mouse_pos)
            b.draw(surf)

        draw_text_centered(
            surf,
            "Управление: A/D — глубина, ПРОБЕЛ — прыжок",
            font_small,
            (235, 240, 255),
            WIDTH // 2,
            py + ph - int(HEIGHT * 0.05),
        )

    def handle_click(self, pos):
        for b in self.buttons:
            if b.handle_click(pos):
                return True
        return False


# ============================================================
# Основной цикл
# ============================================================
def main():
    game = Game()

    back_keys = (
        pygame.K_ESCAPE,
        getattr(pygame, "K_AC_BACK", pygame.K_ESCAPE),
    )

    while game.running:
        clock.tick(FPS)
        keys = pygame.key.get_pressed()
        events = pygame.event.get()

        for event in events:
            if event.type == pygame.QUIT:
                game.running = False

            if event.type == pygame.KEYDOWN:
                # Назад / пауза / выход из меню
                if event.key in back_keys:
                    if game.state == "playing":
                        game.paused = not game.paused
                    elif game.state == "gameover":
                        game.to_menu()
                    elif game.state == "menu":
                        game.running = False

                # Прыжок / старт
                if event.key == pygame.K_SPACE:
                    if game.state == "menu":
                        game.start_game()
                    elif game.state == "gameover":
                        game.start_game()
                    elif game.state == "playing" and game.paused:
                        game.paused = False
                    elif game.state == "playing" and not game.paused:
                        game.player.request_jump()

                # Меню
                if event.key == pygame.K_m:
                    if game.state in ("playing", "gameover"):
                        game.to_menu()

            # Мышь: меню / рестарт
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if game.state == "menu":
                    game.handle_click(event.pos)
                elif game.state == "gameover":
                    game.start_game()

            # Тач: меню / рестарт
            if event.type == pygame.FINGERDOWN:
                pos = (int(event.x * WIDTH), int(event.y * HEIGHT))

                if game.state == "menu":
                    game.handle_click(pos)
                elif game.state == "gameover":
                    game.start_game()

        # Мобильные кнопки только во время игры
        if game.state == "playing":
            game.controls.update(events)

            if game.controls.pause_pressed:
                game.paused = not game.paused

            if not game.paused and game.controls.consume_jump():
                game.player.request_jump()

        game.update(keys)

        screen.fill(BLACK)

        if game.state == "menu":
            game.draw_menu(screen)
        else:
            game.draw(screen)

            if game.state == "playing":
                game.controls.draw(screen)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()