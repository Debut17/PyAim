import json
import os

from constants import SETTINGS_FILE


class Settings:
    DEFAULTS = {
        "duration": 30,
        "max_targets": 1,
        "sound_on": True,
        "crosshair": "cross",
        "moving_pct": 15,
        "golden_pct": 10,
        "bomb_pct": 5,
        "shrink": True,
        "flicker_pct": 8,
    }
    
    def __init__(self):
        self._d = dict(self.DEFAULTS)
        self._load()
        
    def _load(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE) as f:
                    self._d.update(json.load(f))
            except Exception:
                pass
            
    def save(self):
        with open(SETTINGS_FILE, "w") as f:
            json.dump(self._d, f, indent=2)
            
    def __getattr__(self, k):
        if k.startswith("_"):
            raise AttributeError(k)
        return self._d.get(k, self.DEFAULTS.get(k))
    
    def __setattr__(self, k, v):
        if k.startswith("_") or k == "DEFAULTS":
            super().__setattr__(k, v)
        else:
            self._d[k] = v
            
    def cycle(self, key: str, options: list):
        current = self._d.get(key, options[0])
        idx = options.index(current) if current in options else 0
        self._d[key] = options[(idx + 1) % len(options)]
        self.save()
        
        