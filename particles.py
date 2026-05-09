import pygame
import math
import random


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "radius", "color", "life", "max_life")
    
    def __init__(self, x, y, color):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(1.5, 5.5)
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.radius = random.uniform(2, 5)
        self.color = color
        self.life = random.randint(18, 36)
        self.max_life = self.life
        
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.92
        self.vy *= 0.92
        self.life -= 1
        
    def draw(self, surf: pygame.Surface):
        alpha = max(0, int(255 * self.life / self.max_life))
        r = max(1, int(self.radius * self.life / self.max_life))
        s = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (r + 1, r + 1), r)
        surf.blit(s, (int(self.x) - r - 1, int(self.y) - r - 1))
        
        
class ParticleSystem:
    def __init__(self):
        self._particles: list[Particle] = []
        
    def burst(self, x, y, color, count=14):
        for _ in range(count):
            self._particles.append(Particle(x, y, color))
            
    def update_and_draw(self, surf: pygame.Surface):
        alive = []
        for p in self._particles:
            p.update()
            if p.life > 0:
                p.draw(surf)
                alive.append(p)
        self._particles = alive
        
    def clear(self):
        self._particles = []
        
        