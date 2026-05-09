import pygame
import math
import random

from constants import (
    WIDTH, HEIGHT, HUD_H,
    C_TARGET, C_TARGET_RIM, C_MOVING, C_MOVING_RIM,
    C_GOLD, C_BOMB, C_WHITE,
)


class GameObject:
    def __init__(self, x: float, y: float):
        self.x = float(x)
        self.y = float(y)
        
    def draw(self, surf: pygame.Surface) -> None:
        pass
    
    
class Target(GameObject):
    TYPE = "normal"
    COLOR = C_TARGET
    RIM = C_TARGET_RIM
    POINTS = 1
    
    def __init__(self, x, y, radius, lifetime_ms, shrink=True, flicker=False):
        super().__init__(x, y)
        self.radius = radius
        self._base_rad = radius
        self.lifetime_ms = lifetime_ms
        self.spawn_time = pygame.time.get_ticks()
        self.shrink = shrink
        self.flicker = flicker
        self._flicker_phase = 0
        self._visible = True
        self._last_update_t = pygame.time.get_ticks()
        
    def is_clicked(self, mx, my) -> bool:
        if not self._visible:
            return False
        return math.hypot(mx - self.x, my - self.y) <= self.radius
    
    def is_expired(self) -> bool:
        return pygame.time.get_ticks() - self.spawn_time >= self.lifetime_ms
    
    def age_ratio(self) -> float:
        age = pygame.time.get_ticks() - self.spawn_time
        return min(age / self.lifetime_ms, 1.0)
    
    def _grow_scale(self) -> float:
        age = pygame.time.get_ticks() - self.spawn_time
        return min(age / 110, 1.0)
    
    def update(self):
        now = pygame.time.get_ticks()
        dt = now - self._last_update_t
        self._last_update_t = now
        
        if self.shrink:
            self.radius = max(6, self._base_rad * (1.0 - self.age_ratio() * 0.40))
            
        if self.flicker:
            self._flicker_phase += dt
            if self._flicker_phase > 700:
                self._flicker_phase = 0
            self._visible = self._flicker_phase < 550
            
    def draw(self, surf: pygame.Surface):
        if not self._visible:
            return
        scale = self._grow_scale()
        r = int(self.radius * scale)
        if r < 1:
            return
        
        ratio = self.age_ratio()
        alpha = max(0, int(255 * (1.0 - ratio ** 2.2)))
        
        gr = r + 10
        g_surf = pygame.Surface((gr * 2 + 4, gr * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(
            g_surf, (*self.COLOR, max(0, int(50 * (1 - ratio)))),
            (gr + 2, gr + 2), gr)
        surf.blit(g_surf, (int(self.x) - gr - 2, int(self.y) - gr - 2))
        
        t_surf = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(t_surf, (*self.COLOR, alpha), (r + 2, r + 2), r)
        pygame.draw.circle(t_surf, (*self.RIM,   alpha), (r + 2, r + 2), r, 2)
        if r > 7:
            pygame.draw.circle(
                t_surf, (*C_WHITE, alpha),
                (r + 2, r + 2), max(3, r // 5))
        surf.blit(t_surf, (int(self.x) - r - 2, int(self.y) - r - 2))
        
        if ratio > 0.18 and r > 3:
            arc_rect = pygame.Rect(int(self.x) - r, int(self.y) - r, r * 2, r * 2)
            arc_angle = math.pi * 2 * (1 - ratio)
            try:
                pygame.draw.arc(
                    surf, C_GOLD, arc_rect,
                    math.pi / 2 - arc_angle, math.pi / 2, 2)
            except Exception:
                pass
            
            
class MovingTarget(Target):
    TYPE = "moving"
    COLOR = C_MOVING
    RIM = C_MOVING_RIM
    POINTS = 2
    
    def __init__(self, x, y, radius, lifetime_ms, **kw):
        super().__init__(x, y, radius, lifetime_ms, **kw)
        speed = random.uniform(1.8, 3.8)
        angle = random.uniform(0, math.tau)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        
    def update(self):
        super().update()
        self.x += self.vx
        self.y += self.vy
        margin = self.radius + 4
        if self.x < margin or self.x > WIDTH - margin:
            self.vx *= -1
            self.x = max(margin, min(WIDTH - margin, self.x))
        if self.y < HUD_H + margin or self.y > HEIGHT - margin:
            self.vy *= -1
            self.y = max(HUD_H + margin, min(HEIGHT - margin, self.y))
            
            
class GoldenTarget(Target):
    TYPE = "golden"
    COLOR = C_GOLD
    RIM = (255, 240, 160)
    POINTS = 3
    
    def __init__(self, x, y, radius, lifetime_ms, **kw):
        super().__init__(x, y, max(12, int(radius * 0.75)), lifetime_ms, **kw)
        
        
class BombTarget(Target):
    TYPE = "bomb"
    COLOR = C_BOMB
    RIM = (220, 100, 100)
    POINTS = -2
    
    def __init__(self, x, y, radius, lifetime_ms, **kw):
        kw["shrink"] = False
        kw["flicker"] = False
        super().__init__(x, y, radius, lifetime_ms, **kw)
        
        