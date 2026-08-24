import pygame
import math


class TouchControls:
    def __init__(self):
        self.surf = pygame.display.get_surface()
        self.w, self.h = self.surf.get_size()
        self.min_dim = min(self.w, self.h)

        self.joy_radius = int(self.min_dim * 0.11)
        self.knob_radius = max(10, int(self.joy_radius * 0.45))
        self.button_radius = int(self.min_dim * 0.075)
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
        return math.hypot(pos[0] - center[0], pos[1] - center[1]) <= radius

    def _calc_joy(self):
        dx = self.joy_current[0] - self.joy_center[0]
        dy = self.joy_current[1] - self.joy_center[1]
        dist = math.hypot(dx, dy)
        maxr = max(1, self.joy_radius)

        if dist > maxr:
            dx = dx / dist * maxr
            dy = dy / dist * maxr
            dist = maxr

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

                # Левая половина — джойстик
                if pos[0] < self.w * 0.55 and self.joy_id is None:
                    self.joy_id = fid
                    self.joy_center = pos
                    self.joy_current = pos
                    self._calc_joy()

                # Правая половина вне кнопок — тоже прыжок
                elif pos[0] >= self.w * 0.55:
                    self.jump_requested = True

            # Движение пальца/мыши
            elif e.type == pygame.FINGERMOTION or e.type == pygame.MOUSEMOTION:
                fid = getattr(e, "finger_id", -1)

                if e.type == pygame.MOUSEMOTION:
                    fid = -1
                    if self.joy_id == -1 and pygame.mouse.get_pressed()[0]:
                        self.joy_current = self._get_pos(e)
                        self._calc_joy()
                else:
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