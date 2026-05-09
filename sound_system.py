import pygame


class SoundSystem:
    RATE = 44100
    
    def __init__(self):
        self._sounds = {}
        self._ok = False
        try:
            pygame.mixer.init(frequency=self.RATE, size=-16, channels=2, buffer=512)
            import numpy as np
            self._np = np
            self._ok = True
            self._sounds = {
                "hit": self._tone(800,   80, 0.30),
                "miss": self._tone(180,  160, 0.25),
                "combo": self._tone(1200,  60, 0.22),
                "golden": self._tone(1500, 110, 0.28),
                "bomb": self._noise(220,      0.30),
                "start": self._sweep(400, 800, 200, 0.20),
                "end": self._sweep(800, 250, 350, 0.18),
                "life": self._tone(300,  250, 0.30),
            }
        except Exception:
            pass
        
    def _tone(self, freq, dur_ms, vol):
        n = int(self.RATE * dur_ms / 1000)
        t = self._np.linspace(0, dur_ms / 1000, n, endpoint=False)
        w = self._np.sin(2 * self._np.pi * freq * t)
        w *= self._np.linspace(1.0, 0.0, n)
        return self._arr_to_sound(w, vol)
    
    def _noise(self, dur_ms, vol):
        n = int(self.RATE * dur_ms / 1000)
        rng = self._np.random.default_rng(42)
        w = rng.uniform(-1, 1, n)
        w  *= self._np.linspace(1.0, 0.0, n)
        return self._arr_to_sound(w, vol)
    
    def _sweep(self, f0, f1, dur_ms, vol):
        n = int(self.RATE * dur_ms / 1000)
        t = self._np.linspace(0, dur_ms / 1000, n, endpoint=False)
        f = self._np.linspace(f0, f1, n)
        w = self._np.sin(2 * self._np.pi * self._np.cumsum(f) / self.RATE)
        w *= self._np.linspace(1.0, 0.0, n)
        return self._arr_to_sound(w, vol)
    
    def _arr_to_sound(self, w, vol):
        arr = (w * 32767 * vol).astype(self._np.int16)
        stereo = self._np.column_stack([arr, arr])
        return pygame.sndarray.make_sound(stereo)
    
    def play(self, name: str) -> None:
        if not self._ok:
            return
        s = self._sounds.get(name)
        if s:
            s.play()
            
    def set_volume(self, v: float) -> None:
        for s in self._sounds.values():
            if s:
                s.set_volume(v)
                
                