import pygame


class Timer:
    def __init__(self, duration_s: float):
        self.duration   = int(duration_s * 1000)
        self.start_time = None
        
    def start(self):
        self.start_time = pygame.time.get_ticks()
        
    def get_time_left(self) -> float:
        if self.start_time is None:
            return self.duration / 1000
        elapsed = pygame.time.get_ticks() - self.start_time
        return max(0.0, (self.duration - elapsed) / 1000)
    
    def is_time_up(self) -> bool:
        return self.get_time_left() <= 0.0
    
    