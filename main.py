# =============================================================================
#  PyAim v4.0
#  Panuwitch Sowkasem  |  Student ID : 6810545867
# 
#  5 game modes  : Classic, Precision, Speed, Endurance, Practice
#  Target types  : Normal, Moving (bounces), Golden (3x pts), Bomb (avoid)
#  Flicker targets that briefly vanish
#  Combo multiplier (max x5)
#  3-lives system in Endurance mode
#  Settings screen (duration, max targets, sound, crosshair)
#  Pause menu (P key)
#  Sound effects (hit, miss, combo, game-end)
#  Particle burst on hit: screen shake on miss/bomb
#  Custom crosshair cursor
#  Full stats: 7 graphs + summary panel
#  Leaderboard screen
# =============================================================================

import pygame, sys, math, random, csv, os, io, time, json, statistics
from datetime import datetime

WIDTH, HEIGHT = 1000, 700
HUD_H = 58
FPS = 60
DATA_FILE = "pyaim_data.csv"
SETTINGS_FILE = "pyaim_settings.json"
BEST_FILE = "pyaim_best.json"

DIFFICULTIES = { #(radius, lifetime_ms, spawn_delay_ms, duration_s)
    "Easy": (45, 3000, 1200, 30),
    "Normal": (30, 2000, 900, 30),
    "Hard": (18, 1200, 600, 30),
}

MODES = ["Classic", "Precision", "Speed", "Endurance", "Practice"]
MODE_DESC = {
    "Classic": "Timed. Hit as many targets as possible.",
    "Precision": "20 targets. Accuracy is everything.",
    "Speed": "15 seconds. Small targets spawn fast.",
    "Endurance": "No timer. Lose a life on each miss.",
    "Practice": "No score, no timer. Free warm-up.",
}

C_BG = ( 12,  12,  18)
C_PANEL = ( 22,  22,  32)
C_ACCENT = ( 80, 220, 140) # green
C_RED = (255,  80, 100) # red
C_BLUE = ( 80, 160, 255) # blue
C_WHITE = (240, 240, 245)
C_GRAY = (120, 120, 135)
C_DARKGRAY = ( 45,  45,  58)
C_GOLD = (255, 200,  60) # golden targets
C_BOMB = (0,  0,  0) # bomb targets
C_TARGET = (255,  70,  90)
C_TARGET_RIM = (255, 140, 150)
C_MOVING = ( 80, 180, 255) # moving targets
C_MOVING_RIM = (160, 210, 255)


class SoundSystem:
    RATE = 44100
    def __init__(self):
        self._sounds: dict[str, pygame.mixer.Sound | None] = {}
        self._ok = False
        try:
            pygame.mixer.init(frequency=self.RATE, size=-16, channels=2, buffer=512)
            import numpy as np
            self._np = np
            self._ok = True
            self._sounds = {
                "hit": self._tone(800,  80,  0.30),
                "miss": self._tone(180, 160,  0.25),
                "combo": self._tone(1200, 60,  0.22),
                "golden": self._tone(1500, 110, 0.28),
                "bomb": self._noise(220,  0.30),
                "start": self._sweep(400, 800, 200, 0.20),
                "end": self._sweep(800, 250, 350, 0.18),
                "life": self._tone(300, 250,  0.30),
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
        w *= self._np.linspace(1.0, 0.0, n)
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


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "radius", "color", "life", "max_life")
    def __init__(self, x, y, color):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(1.5, 5.5)
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(angle) * speed, math.sin(angle) * speed
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
        if self.shrink:
            self.radius = max(6, self._base_rad * (1.0 - self.age_ratio() * 0.40))
            
        if self.flicker:
            self._flicker_phase += self._clock_dt()
            if self._flicker_phase > 700:
                self._flicker_phase = 0
            self._visible = self._flicker_phase < 550
            
    _last_tick = pygame.time.get_ticks if pygame else (lambda: 0)
    _prev_t = 0
    
    def _clock_dt(self):
        now = pygame.time.get_ticks()
        dt = now - Target._prev_t
        Target._prev_t = now
        return dt
    
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
        pygame.draw.circle(g_surf, (*self.COLOR, max(0, int(50 * (1 - ratio)))),
                        (gr + 2, gr + 2), gr)
        surf.blit(g_surf, (int(self.x) - gr - 2, int(self.y) - gr - 2))
        
        t_surf = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(t_surf, (*self.COLOR, alpha), (r + 2, r + 2), r)
        pygame.draw.circle(t_surf, (*self.RIM,   alpha), (r + 2, r + 2), r, 2)
        if r > 7:
            pygame.draw.circle(t_surf, (*C_WHITE, alpha),
                               (r + 2, r + 2), max(3, r // 5))
        surf.blit(t_surf, (int(self.x) - r - 2, int(self.y) - r - 2))
        
        if ratio > 0.18 and r > 3:
            arc_rect = pygame.Rect(int(self.x) - r, int(self.y) - r, r * 2, r * 2)
            arc_angle = math.pi * 2 * (1 - ratio)
            try:
                pygame.draw.arc(surf, C_GOLD, arc_rect,
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
            self.x = max(margin, min(WIDTH  - margin, self.x))
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


class Player:
    def __init__(self):
        self.total_clicks = 0
        self.hits = 0
        self.misses = 0
        
    def register_hit(self):
        self.total_clicks += 1
        self.hits += 1
        
    def register_miss(self):
        self.total_clicks += 1
        self.misses += 1
        
    def get_accuracy(self) -> float:
        return (self.hits / self.total_clicks * 100) if self.total_clicks else 0.0
    
    def reset(self):
        self.total_clicks = self.hits = self.misses = 0


class Timer:
    def __init__(self, duration_s: float):
        self.duration = int(duration_s * 1000)
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


class ScoreManager:
    def __init__(self):
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        
    def add_score(self, points: int = 1) -> int:
        self.combo = min(self.combo + 1, 5)
        self.max_combo = max(self.max_combo, self.combo)
        gained = points * self.combo
        self.score += gained
        return gained
    
    def break_combo(self):
        self.combo = 0
        
    def reset(self):
        self.score = self.combo = self.max_combo = 0
        
    def get_score(self) -> int:
        return self.score


class DataCollector:
    FIELDS = [
        "round", "target_x", "target_y", "target_size",
        "spawn_time", "click_time", "reaction_time",
        "result", "score", "difficulty",
        "session_id", "mode", "combo", "target_type",
    ]
    
    def __init__(self, filename: str = DATA_FILE):
        self.filename = filename
        self.records: list = []
        self._ensure_header()
        
    def _ensure_header(self):
        if not os.path.exists(self.filename):
            with open(self.filename, "w", newline="") as f:
                csv.writer(f).writerow(self.FIELDS)
                
    def record_click(self, *, round_n, target_x, target_y, target_size,
                    spawn_time, click_time, result, score, difficulty,
                    session_id, mode, combo, target_type):
        reaction_time = (
            round((click_time - spawn_time) * 1000, 1)
            if result == "hit" else None
        )
        self.records.append([
            round_n,
            round(target_x, 1), round(target_y, 1), target_size,
            round(spawn_time, 3), round(click_time, 3),
            reaction_time, result, score, difficulty,
            session_id, mode, combo, target_type,
        ])
        
    def save_to_csv(self):
        with open(self.filename, "a", newline="") as f:
            csv.writer(f).writerows(self.records)
        self.records = []
        
    def load_data(self) -> list[dict]:
        if not os.path.exists(self.filename):
            return []
        with open(self.filename, "r") as f:
            return list(csv.DictReader(f))


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


class StatsRenderer:
    BG = "#0C0C12"; PANEL = "#16161F"
    GRN = "#50DC8C"; RED = "#FF4F64"; BLU = "#50A0FF"
    GLD = "#FFC83C"; WHT = "#F0F0F5"; GRY = "#787887"
    ORG = "#FF8C42"

    X_ZONES = {"Left": (0, 333), "Centre": (333, 667), "Right": (667, 1000)}
    Y_ZONES = {"Top": (HUD_H, HUD_H+214), "Middle": (HUD_H+214, HUD_H+428),
                "Bottom": (HUD_H+428, HEIGHT)}
    
    @staticmethod
    def _f(v):
        try: return float(v)
        except: return None
        
    def _x_zone(self, x) -> str:
        x = self._f(x) or 0
        for n, (lo, hi) in self.X_ZONES.items():
            if lo <= x < hi: return n
        return "Right"
    
    def _y_zone(self, y) -> str:
        y = self._f(y) or 0
        for n, (lo, hi) in self.Y_ZONES.items():
            if lo <= y < hi: return n
        return "Bottom"
    
    def build_surface(self, data: list[dict],
                    export_path: str | None = None) -> pygame.Surface:
        
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.gridspec as gs_mod
        import numpy as np
        
        hits = [r for r in data if r.get("result") == "hit"]
        misses = [r for r in data if r.get("result") == "miss"]
        
        rt_raw = [self._f(r["reaction_time"]) for r in hits]
        rt_ms = [v for v in rt_raw if v is not None]
        
        rounds: dict[int, int] = {}
        for r in data:
            rn = int(self._f(r.get("round")) or 0)
            sc = int(self._f(r.get("score"))  or 0)
            rounds[rn] = max(rounds.get(rn, 0), sc)
            
        avg_rt = (sum(rt_ms) / len(rt_ms))  if rt_ms else None
        std_rt = statistics.stdev(rt_ms)     if len(rt_ms) > 1 else None
        acc = (len(hits) / len(data) * 100) if data else 0
        best_sc = max(rounds.values(), default=0)
        
        try:
            times = sorted(self._f(r.get("click_time")) or 0 for r in hits)
            span = (times[-1] - times[0]) / 60 if len(times) > 1 else 1
            tpm = len(hits) / span if span > 0 else 0
        except Exception:
            tpm = 0
            
        plt.rcParams.update({
            "figure.facecolor": self.BG, "axes.facecolor": self.PANEL,
            "axes.edgecolor": "#2A2A3A", "axes.labelcolor": self.GRY,
            "xtick.color": self.GRY, "ytick.color": self.GRY,
            "text.color": self.WHT, "grid.color": "#2A2A3A",
            "grid.linewidth": 0.6, "font.family": "DejaVu Sans",
            "axes.spines.top": False, "axes.spines.right": False,
            "axes.titlesize": 9, "axes.labelsize": 7.5,
            "xtick.labelsize": 7, "ytick.labelsize": 7,
        })
        
        fig = plt.figure(figsize=(16, 10))
        fig.suptitle("PyAim — Performance Analysis",
                    fontsize=15, fontweight="bold", color=self.WHT, y=0.985)
        
        outer = gs_mod.GridSpec(1, 2, figure=fig,
                                width_ratios=[3, 1],
                                left=0.05, right=0.97,
                                top=0.95, bottom=0.07,
                                wspace=0.06)
        
        lgs = gs_mod.GridSpecFromSubplotSpec(
            3, 3, subplot_spec=outer[0],
            hspace=0.54, wspace=0.42)
        
        rgs = gs_mod.GridSpecFromSubplotSpec(
            2, 1, subplot_spec=outer[1],
            hspace=0.30)
        
        def ax(r, c): return fig.add_subplot(lgs[r, c])
        
        a1 = ax(0, 0)
        if rt_ms:
            a1.hist(rt_ms, bins=20, color=self.GRN,
                    edgecolor=self.BG, linewidth=0.3, alpha=0.9)
            a1.axvline(avg_rt, color=self.GLD, linestyle="--",
                        linewidth=1.4, label=f"Mean {avg_rt:.0f} ms")
            if std_rt:
                a1.axvspan(avg_rt - std_rt, avg_rt + std_rt,
                        alpha=0.10, color=self.GLD, label=f"±SD {std_rt:.0f}")
            a1.legend(fontsize=7, framealpha=0)
        else:
            a1.text(0.5, 0.5, "No hit data yet", ha="center", va="center",
                    transform=a1.transAxes, color=self.GRY, fontsize=8)
        a1.set_title("Graph 1 — Reaction Time (ms)")
        a1.set_xlabel("ms"); a1.set_ylabel("Frequency"); a1.grid(axis="y")
        
        a2 = ax(0, 1)
        if rounds:
            rns = sorted(rounds.keys())
            cols = [self.GRN if i == len(rns)-1 else self.BLU
                    for i in range(len(rns))]
            a2.bar([str(r) for r in rns], [rounds[r] for r in rns],
                    color=cols, edgecolor=self.BG, linewidth=0.3)
            a2.grid(axis="y")
        else:
            a2.text(0.5, 0.5, "No data yet", ha="center", va="center",
                    transform=a2.transAxes, color=self.GRY, fontsize=8)
        a2.set_title("Graph 2 — Score per Round")
        a2.set_xlabel("Round"); a2.set_ylabel("Score")
        
        a3 = ax(0, 2)
        hc, mc = len(hits), len(misses)
        if hc + mc:
            _, texts, autos = a3.pie(
                [hc, mc], labels=["Hit", "Miss"],
                autopct="%1.1f%%", colors=[self.GRN, self.RED],
                wedgeprops={"linewidth": 2, "edgecolor": self.BG},
                startangle=90, textprops={"color": self.WHT, "fontsize": 8})
            for au in autos:
                au.set_color(self.BG); au.set_fontweight("bold"); au.set_fontsize(7)
        else:
            a3.text(0.5, 0.5, "No data yet", ha="center", va="center",
                    transform=a3.transAxes, color=self.GRY, fontsize=8)
        a3.set_title("Graph 3 — Hit vs Miss")
        
        a4 = ax(1, 0)
        if data:
            scores = [self._f(r.get("score")) or 0 for r in data]
            a4.plot(scores, color=self.GRN, linewidth=1.8)
            a4.fill_between(range(len(scores)), scores, alpha=0.14, color=self.GRN)
            a4.grid(axis="y")
        else:
            a4.text(0.5, 0.5, "No data yet", ha="center", va="center",
                    transform=a4.transAxes, color=self.GRY, fontsize=8)
        a4.set_title("Graph 4 — Score Progression")
        a4.set_xlabel("Click #"); a4.set_ylabel("Score")
        
        a5a = ax(1, 1)
        xc = {z: 0 for z in self.X_ZONES}
        for r in hits:
            xc[self._x_zone(r.get("target_x"))] += 1
        a5a.bar(list(xc.keys()), list(xc.values()),
                color=[self.BLU, self.GRN, self.RED],
                edgecolor=self.BG, linewidth=0.3)
        a5a.grid(axis="y")
        a5a.set_title("Graph 5a — Hits by X Zone")
        a5a.set_xlabel("Zone (Left / Centre / Right)")
        a5a.set_ylabel("Hit Count")
        
        a5b = ax(1, 2)
        yc = {z: 0 for z in self.Y_ZONES}
        for r in hits:
            yc[self._y_zone(r.get("target_y"))] += 1
        a5b.bar(list(yc.keys()), list(yc.values()),
                color=[self.BLU, self.GRN, self.RED],
                edgecolor=self.BG, linewidth=0.3)
        a5b.grid(axis="y")
        a5b.set_title("Graph 5b — Hits by Y Zone")
        a5b.set_xlabel("Zone (Top / Middle / Bottom)")
        a5b.set_ylabel("Hit Count")
        
        a6 = fig.add_subplot(lgs[2, :])
        hx = [self._f(r.get("target_x")) for r in hits]
        hy = [self._f(r.get("target_y")) for r in hits]
        hx = [v for v in hx if v is not None]
        hy = [v for v in hy if v is not None]
        if len(hx) > 1:
            heatmap, xedges, yedges = np.histogram2d(
                hx, hy, bins=[20, 13],
                range=[[0, WIDTH], [HUD_H, HEIGHT]])
            extent = [0, WIDTH, HUD_H, HEIGHT]
            im = a6.imshow(heatmap.T, origin="lower", extent=extent,
                        cmap="YlOrRd", aspect="auto", alpha=0.9)
            fig.colorbar(im, ax=a6, fraction=0.015, pad=0.01,
                        label="Hit Density").ax.yaxis.label.set_color(self.GRY)
            mx_v = [self._f(r.get("target_x")) for r in misses if self._f(r.get("target_x"))]
            my_v = [self._f(r.get("target_y")) for r in misses if self._f(r.get("target_y"))]
            if mx_v:
                a6.scatter(mx_v, my_v, c=self.RED, s=6, alpha=0.35,
                        label="Misses", marker="x")
        else:
            a6.text(0.5, 0.5, "Not enough data for heatmap",
                    ha="center", va="center",
                    transform=a6.transAxes, color=self.GRY, fontsize=9)
        a6.set_title("Graph 6 — Click Heatmap (hit density + miss positions)")
        a6.set_xlabel("X (pixels)"); a6.set_ylabel("Y (pixels)")
        a6.set_xlim(0, WIDTH); a6.set_ylim(HUD_H, HEIGHT)
        a6.invert_yaxis()
        if len(hx) > 1:
            a6.legend(fontsize=7, framealpha=0)
            
        ax_sum = fig.add_subplot(rgs[0])
        ax_sum.axis("off")
        lines = [
            ("Total records",      f"{len(data)}"),
            ("Sessions / rounds",  f"{len(rounds)}"),
            ("Best score",         f"{best_sc}"),
            ("Accuracy",           f"{acc:.1f} %"),
            ("Avg reaction",       f"{avg_rt:.0f} ms" if avg_rt else "—"),
            ("Std dev reaction",   f"{std_rt:.0f} ms" if std_rt else "—"),
            ("Targets / min",      f"{tpm:.1f}"),
            ("Max hits",           f"{hc}"),
            ("Max misses",         f"{mc}"),
        ]
        col_colors = [[self.PANEL, self.PANEL]] * len(lines)
        tbl = ax_sum.table(
            cellText=[[l, v] for l, v in lines],
            cellColours=col_colors,
            cellLoc="left", loc="center",
            bbox=[0, 0, 1, 1])
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(8)
        for (row, col), cell in tbl.get_celld().items():
            cell.set_edgecolor("#2A2A3A")
            cell.set_linewidth(0.4)
            cell.set_facecolor(self.PANEL)
            cell.set_text_props(
                color=self.GLD if col == 1 else self.GRY,
                fontweight="bold" if col == 1 else "normal")
        ax_sum.set_title("Summary Stats", fontsize=9,
                        color=self.WHT, pad=6)
        
        ax_type = fig.add_subplot(rgs[1])
        type_counts: dict[str, int] = {}
        for r in data:
            tt = r.get("target_type", "normal") or "normal"
            type_counts[tt] = type_counts.get(tt, 0) + 1
        if type_counts:
            tc_colors = {
                "normal":  self.GRN, "moving": self.BLU,
                "golden":  self.GLD, "bomb":   self.RED}
            ax_type.barh(
                list(type_counts.keys()),
                list(type_counts.values()),
                color=[tc_colors.get(k, self.GRY) for k in type_counts])
            ax_type.grid(axis="x")
        else:
            ax_type.text(0.5, 0.5, "No type data",
                        ha="center", va="center",
                        transform=ax_type.transAxes,
                        color=self.GRY, fontsize=8)
        ax_type.set_title("Target Types Hit", fontsize=9, color=self.WHT, pad=6)
        ax_type.set_xlabel("Count")
        
        if export_path:
            fig.savefig(export_path, dpi=130, bbox_inches="tight",
                        facecolor=self.BG, edgecolor="none")
            
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=105,
                    bbox_inches="tight", facecolor=self.BG, edgecolor="none")
        plt.close(fig)
        buf.seek(0)
        return pygame.image.load(buf, "s.png").convert()


class Game:
    def __init__(self):
        pygame.init()
        pygame.mouse.set_visible(False)
        self.screen  = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("PyAim v4.0")
        self.clock   = pygame.time.Clock()
        self._canvas = pygame.Surface((WIDTH, HEIGHT))
        
        self.f_xl = pygame.font.SysFont("Segoe UI", 68, bold=True)
        self.f_lg = pygame.font.SysFont("Segoe UI", 36, bold=True)
        self.f_md = pygame.font.SysFont("Segoe UI", 24, bold=True)
        self.f_sm = pygame.font.SysFont("Segoe UI", 18)
        self.f_xs = pygame.font.SysFont("Segoe UI", 14)
        self.f_ti = pygame.font.SysFont("Segoe UI", 12)
        
        self.settings       = Settings()
        self.sounds         = SoundSystem()
        self.particles      = ParticleSystem()
        self.player         = Player()
        self.score_manager  = ScoreManager()
        self.data_collector = DataCollector()
        self.stats_renderer = StatsRenderer()
        self.timer: Timer | None = None
        
        self.state      = "MENU"
        self.running    = True
        self.difficulty = "Normal"
        self.mode       = "Classic"
        self.round_n    = 0
        
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.targets: list[Target]  = []
        self._last_spawn            = 0
        self._precision_remaining   = 20
        self._lives                 = 3 
        self._combo_display         = []
        
        self._hit_fx : list[tuple]  = []
        self._miss_fx: list[tuple]  = []
        self._shake_frames          = 0
        self._shake_amount          = 0
        
        self._diff_keys  = list(DIFFICULTIES.keys())
        self._diff_idx   = 1
        self._mode_idx   = 0
        
        self._stats_surf    : pygame.Surface | None = None
        self._stats_loading = False
        self._stats_msg     = "Building charts…"
        self._prev_state    = "MENU"
        
        self._bg_t = 0.0
        
        self._best = self._load_best()
        
        if not self.settings.sound_on:
            self.sounds.set_volume(0)
            
    def _load_best(self) -> dict:
        if os.path.exists(BEST_FILE):
            try:
                with open(BEST_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    def _save_best(self, key: str, score: int):
        if score > self._best.get(key, 0):
            self._best[key] = score
            try:
                with open(BEST_FILE, "w") as f:
                    json.dump(self._best, f, indent=2)
            except Exception:
                pass
            
    def _preset(self):
        return DIFFICULTIES[self.difficulty]
    
    def _make_target(self) -> Target:
        radius, lifetime, _, _ = self._preset()
        
        if self.mode == "Speed":
            radius = max(12, radius - 8)
            lifetime = max(800, int(lifetime * 0.65))
            
        margin = radius + 14
        x = random.randint(margin, WIDTH - margin)
        y = random.randint(HUD_H + margin, HEIGHT - margin)
        
        flicker = (random.randint(1, 100) <= self.settings.flicker_pct
                    and self.mode not in ("Practice",))
        shrink = self.settings.shrink
        
        roll = random.randint(1, 100)
        gp = self.settings.golden_pct
        bp = self.settings.bomb_pct
        mp = self.settings.moving_pct
        
        if roll <= bp and self.mode not in ("Precision", "Practice", "Speed"):
            return BombTarget(x, y, radius, lifetime, shrink=shrink, flicker=False)
        elif roll <= bp + gp and self.mode not in ("Speed",):
            return GoldenTarget(x, y, radius, lifetime, shrink=shrink, flicker=flicker)
        elif roll <= bp + gp + mp and self.mode not in ("Precision",):
            return MovingTarget(x, y, radius, lifetime, shrink=shrink, flicker=flicker)
        else:
            return Target(x, y, radius, lifetime, shrink=shrink, flicker=flicker)
        
    def _spawn_batch(self):
        count = self.settings.max_targets if self.mode == "Speed" else 1
        for _ in range(count):
            if self.mode == "Precision" and self._precision_remaining <= 0:
                break
            self.targets.append(self._make_target())
            if self.mode == "Precision":
                self._precision_remaining -= 1
                
    def start_game(self):
        self.player.reset()
        self.score_manager.reset()
        self.particles.clear()
        self.targets.clear()
        self._hit_fx.clear(); self._miss_fx.clear()
        self._combo_display.clear()
        self._shake_frames = 0
        
        if self.mode == "Speed":
            dur = 15
        elif self.mode in ("Endurance", "Precision", "Practice"):
            dur = 9999
        else:
            dur = self.settings.duration
            
        self.timer = Timer(dur)
        self.timer.start()
        self._last_spawn = pygame.time.get_ticks()
        self._precision_remaining = 20
        self._lives = 3
        self.round_n += 1
        self._spawn_batch()
        self.state = "PLAYING"
        self.sounds.play("start")
        
    def end_game(self):
        self.data_collector.save_to_csv()
        self._stats_surf    = None
        best_key            = f"{self.mode}_{self.difficulty}"
        self._save_best(best_key, self.score_manager.get_score())
        try:
            data = self.data_collector.load_data()
            if data:
                export_name = (f"pyaim_stats_{self.session_id}.png")
                self.stats_renderer.build_surface(data, export_path=export_name)
        except Exception:
            pass
        self.sounds.play("end")
        self.state = "RESULTS"
        
    def _open_stats(self, back_to="MENU"):
        self._prev_state    = back_to
        self.state          = "STATS"
        self._stats_surf    = None
        self._stats_loading = True
        self._stats_msg     = "Building charts…"
        
    def _trigger_shake(self, amount=6, frames=12):
        self._shake_frames = frames
        self._shake_amount = amount
        
    def update(self):
        self._bg_t += 0.016
        
        if self.state != "PLAYING":
            return
        
        now = pygame.time.get_ticks()
        _, _, spawn_delay, _ = self._preset()
        if self.mode == "Speed":
            spawn_delay = max(300, spawn_delay - 300)
            
        if self.mode in ("Classic", "Speed") and self.timer.is_time_up():
            self.end_game()
            return
        
        desired = self.settings.max_targets if self.mode == "Speed" else 1
        if (len(self.targets) < desired
                and now - self._last_spawn >= spawn_delay
                and not (self.mode == "Precision"
                        and self._precision_remaining <= 0)):
            self._spawn_batch()
            self._last_spawn = now
            
        for t in self.targets:
            Target._prev_t = now
            t.update()
            
        for t in self.targets[:]:
            if t.is_expired() and not isinstance(t, BombTarget):
                self._on_target_miss(t, now)
                self.targets.remove(t)
                self._last_spawn = now
                
            elif t.is_expired() and isinstance(t, BombTarget):
                self.targets.remove(t)
                self._last_spawn = now
                
        if (self.mode == "Precision"
                and self._precision_remaining <= 0
                and not self.targets):
            self.end_game()
            return
        
        
        self._hit_fx  = [(x, y, b) for x, y, b in self._hit_fx  if now - b < 450]
        self._miss_fx = [(x, y, b) for x, y, b in self._miss_fx if now - b < 450]
        self._combo_display = [(x, y, txt, b, c)
                            for x, y, txt, b, c in self._combo_display
                            if now - b < 700]
        
        if self._shake_frames > 0:
            self._shake_frames -= 1
            
    def _on_target_miss(self, t: Target, now: int):
        if self.mode == "Practice":
            return
        self.player.register_miss()
        self.score_manager.break_combo()
        self.data_collector.record_click(
            round_n=self.round_n, target_x=t.x, target_y=t.y,
            target_size=t._base_rad, spawn_time=t.spawn_time / 1000,
            click_time=time.time(), result="miss",
            score=self.score_manager.get_score(), difficulty=self.difficulty,
            session_id=self.session_id, mode=self.mode,
            combo=0, target_type=t.TYPE)
        self._miss_fx.append((t.x, t.y, now))
        if self.mode == "Endurance":
            self._lives -= 1
            self.sounds.play("life")
            self._trigger_shake(8, 14)
            if self._lives <= 0:
                self.end_game()
                
    def draw(self):
        self._canvas.fill(C_BG)
        self._draw_bg_grid()
        
        {
            "MENU":        self._draw_menu,
            "SETTINGS":    self._draw_settings,
            "PLAYING":     self._draw_playing,
            "PAUSED":      self._draw_paused,
            "RESULTS":     self._draw_results,
            "STATS":       self._draw_stats,
            "LEADERBOARD": self._draw_leaderboard,
        }[self.state]()
        
        self.particles.update_and_draw(self._canvas)
        
        self._draw_crosshair()
        
        if self._shake_frames > 0:
            sx = random.randint(-self._shake_amount, self._shake_amount)
            sy = random.randint(-self._shake_amount, self._shake_amount)
        else:
            sx = sy = 0
        self.screen.fill(C_BG)
        self.screen.blit(self._canvas, (sx, sy))
        pygame.display.flip()
        
    def _draw_bg_grid(self):
        pulse     = 0.28 + 0.18 * math.sin(self._bg_t * 0.6)
        dot_alpha = int(pulse * 55)
        col       = (30, 30, 46)
        for gx in range(0, WIDTH + 1, 48):
            for gy in range(0, HEIGHT + 1, 48):
                pygame.draw.circle(self._canvas, col, (gx, gy), 1)
                
    def _draw_crosshair(self):
        mx, my = pygame.mouse.get_pos()
        style  = self.settings.crosshair
        if style == "none":
            return
        col = C_WHITE
        if style == "cross":
            pygame.draw.line(self._canvas, col, (mx - 12, my), (mx + 12, my), 1)
            pygame.draw.line(self._canvas, col, (mx, my - 12), (mx, my + 12), 1)
            pygame.draw.circle(self._canvas, col, (mx, my), 4, 1)
        elif style == "dot":
            pygame.draw.circle(self._canvas, col, (mx, my), 3)
            pygame.draw.circle(self._canvas, C_BG, (mx, my), 1)
            
    def _draw_menu(self):
        c = self._canvas
        self._bc(self.f_xl.render("PyAim", True, C_ACCENT), 70)
        self._bc(self.f_sm.render("Train your aim. Track your stats.", True, C_GRAY), 148)
        
        self._bc(self.f_md.render("Mode", True, C_WHITE), 192)
        mw, mh = 150, 40
        total_m = len(MODES) * mw + (len(MODES) - 1) * 10
        mx0     = WIDTH // 2 - total_m // 2
        for i, m in enumerate(MODES):
            bx, by  = mx0 + i * (mw + 10), 228
            sel     = (i == self._mode_idx)
            pygame.draw.rect(c, C_BLUE if sel else C_DARKGRAY,
                            (bx, by, mw, mh), border_radius=7)
            t = self.f_xs.render(m, True, C_BG if sel else C_WHITE)
            c.blit(t, (bx + mw//2 - t.get_width()//2, by + mh//2 - t.get_height()//2))
            
        desc = MODE_DESC.get(self.mode, "")
        self._bc(self.f_xs.render(desc, True, C_GRAY), 278)
        
        self._bc(self.f_md.render("Difficulty", True, C_WHITE), 308)
        dw, dh    = 148, 42
        total_d   = len(self._diff_keys) * dw + (len(self._diff_keys) - 1) * 14
        dx0       = WIDTH // 2 - total_d // 2
        for i, dk in enumerate(self._diff_keys):
            bx, by  = dx0 + i * (dw + 14), 344
            sel     = (i == self._diff_idx)
            pygame.draw.rect(c, C_ACCENT if sel else C_DARKGRAY,
                            (bx, by, dw, dh), border_radius=7)
            t = self.f_sm.render(dk, True, C_BG if sel else C_WHITE)
            c.blit(t, (bx + dw//2 - t.get_width()//2, by + dh//2 - t.get_height()//2))
            
        best_key = f"{self.mode}_{self.difficulty}"
        best_val = self._best.get(best_key)
        if best_val:
            pb = self.f_xs.render(f"Personal best: {best_val} pts", True, C_GOLD)
            self._bc(pb, 398)
            
        self._btn(WIDTH//2 - 118, 420, 236, 54, "PLAY",       C_ACCENT,   C_BG,    self.f_lg)
        self._btn(WIDTH//2 - 118, 484, 111, 42, "Settings",   C_DARKGRAY, C_WHITE, self.f_sm)
        self._btn(WIDTH//2 +   7, 484, 111, 42, "Leaderboard",C_DARKGRAY, C_WHITE, self.f_sm)
        
        data_count = len(self.data_collector.load_data())
        has_data   = data_count > 0
        label      = f"Analysis  ({data_count} records)" if has_data else "Analysis  (no data yet)"
        self._btn(WIDTH//2 - 118, 536, 236, 40, label,
                C_BLUE if has_data else C_DARKGRAY,
                C_BG   if has_data else C_GRAY, self.f_xs)
        
        self._bc(self.f_ti.render("P = pause  |  ESC = quit", True, C_DARKGRAY), 594)
        
    def _draw_settings(self):
        c = self._canvas
        self._bc(self.f_lg.render("Settings", True, C_WHITE), 60)
        
        rows = [
            ("Game Duration",    f"{self.settings.duration}s",
            [15, 30, 60, 90], "duration"),
            ("Max Targets",      str(self.settings.max_targets),
            [1, 2, 3], "max_targets"),
            ("Sound",            "On" if self.settings.sound_on else "Off",
            [True, False], "sound_on"),
            ("Crosshair",        self.settings.crosshair.capitalize(),
            ["cross", "dot", "none"], "crosshair"),
            ("Moving Targets %", f"{self.settings.moving_pct}%",
            [0, 10, 15, 25, 40], "moving_pct"),
            ("Golden Targets %", f"{self.settings.golden_pct}%",
            [0, 5, 10, 20], "golden_pct"),
            ("Bomb Targets %",   f"{self.settings.bomb_pct}%",
            [0, 5, 10], "bomb_pct"),
            ("Shrinking Targets","On" if self.settings.shrink else "Off",
            [True, False], "shrink"),
        ]
        
        row_h = 52
        sy    = 130
        for i, (label, val, opts, key) in enumerate(rows):
            ry = sy + i * row_h
            pygame.draw.rect(c, C_PANEL, (80, ry, 840, row_h - 4), border_radius=6)
            lt = self.f_sm.render(label, True, C_GRAY)
            vt = self.f_sm.render(val, True, C_ACCENT)
            at = self.f_xs.render("click to cycle →", True, C_DARKGRAY)
            c.blit(lt, (100, ry + 14))
            c.blit(vt, (500, ry + 14))
            c.blit(at, (720, ry + 18))
            
        self._btn(WIDTH//2 - 80, sy + len(rows) * row_h + 12, 160, 44,
                "← Back", C_DARKGRAY, C_WHITE, self.f_sm)
        
    def _draw_playing(self):
        c   = self._canvas
        now = pygame.time.get_ticks()
        
        pygame.draw.rect(c, C_PANEL, (0, 0, WIDTH, HUD_H))
        
        sc = self.f_lg.render(str(self.score_manager.get_score()), True, C_ACCENT)
        c.blit(sc, (16, 8))
        c.blit(self.f_ti.render("SCORE", True, C_GRAY), (20 + sc.get_width() + 4, 22))
        
        combo = self.score_manager.combo
        if combo > 1:
            col  = [C_WHITE, C_ACCENT, C_GOLD, C_BLUE, C_RED, C_GOLD][min(combo, 5)]
            cmbt = self.f_md.render(f"x{combo}", True, col)
            c.blit(cmbt, (16, 36))
            
        acc = self.player.get_accuracy()
        ac  = self.f_lg.render(f"{acc:.1f}%", True, C_WHITE)
        c.blit(ac, (WIDTH // 2 - ac.get_width() // 2, 8))
        al = self.f_ti.render("ACCURACY", True, C_GRAY)
        c.blit(al, (WIDTH // 2 - al.get_width() // 2, 38))
        
        if self.mode == "Endurance":
            for li in range(3):
                col = C_RED if li < self._lives else C_DARKGRAY
                pygame.draw.circle(c, col, (WIDTH - 28 - li * 28, 28), 10)
            rl = self.f_ti.render("LIVES", True, C_GRAY)
            c.blit(rl, (WIDTH - 28 - 2 * 28 - rl.get_width() - 8, 22))
        elif self.mode == "Precision":
            pr  = self.f_lg.render(str(max(0, self._precision_remaining)), True, C_WHITE)
            prl = self.f_ti.render("REMAINING", True, C_GRAY)
            c.blit(pr,  (WIDTH - pr.get_width() - 16, 8))
            c.blit(prl, (WIDTH - prl.get_width() - 16, 38))
        elif self.mode != "Practice":
            tl    = self.timer.get_time_left()
            color = C_RED if tl < 5 else C_WHITE
            tc    = self.f_lg.render(f"{tl:.1f}s", True, color)
            tll   = self.f_ti.render("TIME LEFT", True, C_GRAY)
            c.blit(tc,  (WIDTH - tc.get_width()   - 16, 8))
            c.blit(tll, (WIDTH - tll.get_width()  - 16, 38))
            
        hm = self.f_ti.render(
            f"Hits {self.player.hits}  Misses {self.player.misses}", True, C_GRAY)
        c.blit(hm, (WIDTH//2 - hm.get_width()//2 + 188, 18))
        
        mb = self.f_ti.render(f"{self.mode.upper()} / {self.difficulty.upper()}", True, C_BLUE)
        c.blit(mb, (WIDTH//2 - mb.get_width()//2 - 188, 18))
        
        pygame.draw.line(c, C_DARKGRAY, (0, HUD_H), (WIDTH, HUD_H), 1)
        
        for x, y, b in self._hit_fx:
            age   = now - b
            alpha = max(0, 185 - int(185 * age / 450))
            r     = 16 + int(26 * age / 450)
            fs    = pygame.Surface((r*2+4, r*2+4), pygame.SRCALPHA)
            pygame.draw.circle(fs, (*C_ACCENT, alpha), (r+2, r+2), r, 3)
            c.blit(fs, (int(x) - r - 2, int(y) - r - 2))
            
        for x, y, b in self._miss_fx:
            age   = now - b
            alpha = max(0, 160 - int(160 * age / 450))
            sz    = 12
            ms    = pygame.Surface((sz*2, sz*2), pygame.SRCALPHA)
            pygame.draw.line(ms, (*C_RED, alpha), (0, 0),     (sz*2, sz*2), 3)
            pygame.draw.line(ms, (*C_RED, alpha), (sz*2, 0),  (0, sz*2),    3)
            c.blit(ms, (int(x)-sz, int(y)-sz))
            
        for x, y, txt, b, col in self._combo_display:
            age   = now - b
            alpha = max(0, 220 - int(220 * age / 700))
            rise  = int(30 * age / 700)
            ts    = pygame.Surface((120, 36), pygame.SRCALPHA)
            ft    = self.f_md.render(txt, True, (*col, alpha))
            ts.blit(ft, (0, 0))
            c.blit(ts, (int(x) - ft.get_width()//2, int(y) - rise - 20))
            
        for t in self.targets:
            t.draw(c)
            
        if self.mode == "Practice":
            pw = self.f_lg.render("PRACTICE — no scoring", True, C_DARKGRAY)
            c.blit(pw, (WIDTH//2 - pw.get_width()//2, HEIGHT//2 - 20))
            
    def _draw_paused(self):
        self._draw_playing()
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self._canvas.blit(overlay, (0, 0))
        
        self._bc(self.f_xl.render("PAUSED", True, C_WHITE), 230)
        self._bc(self.f_sm.render("P or ESC  →  resume", True, C_GRAY), 320)
        self._btn(WIDTH//2 - 110, 370, 220, 48,
                "Quit to Menu", C_DARKGRAY, C_WHITE, self.f_sm)
        
    def _draw_results(self):
        c = self._canvas
        self._bc(self.f_xl.render("Results", True, C_WHITE), 40)
        
        acc    = self.player.get_accuracy()
        avg_rt = self._avg_rt_this_round()
        best_k = f"{self.mode}_{self.difficulty}"
        is_pb  = (self.score_manager.get_score() >= self._best.get(best_k, 0))
        
        if is_pb and self.mode != "Practice":
            self._bc(self.f_md.render("★ New Personal Best! ★", True, C_GOLD), 112)
            
        cards = [
            ("Score",        str(self.score_manager.get_score()),              C_ACCENT),
            ("Accuracy",     f"{acc:.1f}%",                                    C_BLUE),
            ("Hits",         str(self.player.hits),                            C_ACCENT),
            ("Misses",       str(self.player.misses),                          C_RED),
            ("Avg Reaction", f"{avg_rt}ms" if avg_rt else "—",                C_GOLD),
            ("Max Combo",    f"x{self.score_manager.max_combo}",               C_GOLD),
        ]
        cw, ch  = 148, 84
        total_w = len(cards) * cw + (len(cards)-1) * 12
        sx      = WIDTH // 2 - total_w // 2
        for i, (lbl, val, col) in enumerate(cards):
            cx, cy = sx + i*(cw+12), 140
            pygame.draw.rect(c, C_PANEL, (cx, cy, cw, ch), border_radius=9)
            pygame.draw.rect(c, col,    (cx, cy, cw,  3),  border_radius=2)
            vt = self.f_md.render(val,           True, col)
            lt = self.f_ti.render(lbl.upper(),   True, C_GRAY)
            c.blit(vt, (cx + cw//2 - vt.get_width()//2, cy + 14))
            c.blit(lt, (cx + cw//2 - lt.get_width()//2, cy + 56))
            
        bw, bh = 178, 48; gap = 14
        total_b = bw * 3 + gap * 2
        bx1 = WIDTH // 2 - total_b // 2
        bx2, bx3 = bx1 + bw + gap, bx1 + bw*2 + gap*2
        by  = 268
        self._btn(bx1, by, bw, bh, "Play Again",  C_ACCENT,    C_BG,    self.f_sm)
        self._btn(bx2, by, bw, bh, "Analysis",    C_BLUE,      C_BG,    self.f_sm)
        self._btn(bx3, by, bw, bh, "Main Menu",   C_DARKGRAY,  C_WHITE, self.f_sm)
        
        data = self.data_collector.load_data()
        if data:
            rounds_sc: dict[str, int] = {}
            for row in data:
                rn = str(row.get("round", "?"))
                sc = int(float(row.get("score") or 0))
                rounds_sc[rn] = max(rounds_sc.get(rn, 0), sc)
            top = sorted(rounds_sc.items(), key=lambda x: -x[1])[:5]
            lx, ly = 60, 346
            c.blit(self.f_xs.render("TOP ROUNDS", True, C_GRAY), (lx, ly))
            for j, (rn, sc) in enumerate(top):
                col = C_GOLD if rn == str(self.round_n) else C_WHITE
                c.blit(self.f_xs.render(f"  Round {rn}  →  {sc} pts", True, col),
                       (lx, ly + 22 + j * 22))
                
        self._bc(self.f_ti.render(
            f"Stats auto-exported → pyaim_stats_{self.session_id}.png",
            True, C_DARKGRAY), 460)
        
    def _draw_stats(self):
        c = self._canvas
        
        if self._stats_surf is None and self._stats_loading:
            msg = self.f_lg.render(self._stats_msg, True, C_GRAY)
            c.blit(msg, (WIDTH//2 - msg.get_width()//2, HEIGHT//2 - 30))
            self.screen.blit(c, (0, 0))
            pygame.display.flip()
            
            data = self.data_collector.load_data()
            if not data:
                self._stats_msg     = "No data yet — play a round first!"
                self._stats_loading = False
                return
            try:
                self._stats_surf    = self.stats_renderer.build_surface(data)
                self._stats_loading = False
            except Exception as e:
                self._stats_msg     = f"Chart error: {e}"
                self._stats_loading = False
            return
        
        if self._stats_surf is None:
            msg = self.f_lg.render(self._stats_msg, True, C_GRAY)
            c.blit(msg, (WIDTH//2 - msg.get_width()//2, HEIGHT//2 - 30))
        else:
            sw, sh = self._stats_surf.get_size()
            scale  = min(WIDTH / sw, (HEIGHT - 52) / sh)
            dw, dh = int(sw*scale), int(sh*scale)
            scaled = pygame.transform.smoothscale(self._stats_surf, (dw, dh))
            c.blit(scaled, (WIDTH//2 - dw//2, 4))
            
        self._btn(WIDTH//2 - 88, HEIGHT - 48, 176, 40,
                "← Back", C_DARKGRAY, C_WHITE, self.f_sm)
        
    def _draw_leaderboard(self):
        c = self._canvas
        self._bc(self.f_lg.render("Leaderboard", True, C_WHITE), 50)
        
        data = self.data_collector.load_data()
        if not data:
            self._bc(self.f_sm.render("No sessions recorded yet.", True, C_GRAY), 200)
        else:
            entries: dict = {}
            hits_m:  dict = {}
            total_m: dict = {}
            for row in data:
                key = (str(row.get("round","?")),
                    row.get("mode","?"),
                    row.get("difficulty","?"))
                sc  = int(float(row.get("score") or 0))
                if key not in entries or sc > entries[key]["score"]:
                    entries[key] = {"score": sc}
                res = row.get("result","")
                hits_m[key]  = hits_m.get(key, 0)  + (1 if res == "hit" else 0)
                total_m[key] = total_m.get(key, 0) + 1
                
            for k in entries:
                tot = total_m.get(k, 1)
                entries[k]["acc"] = hits_m.get(k, 0) / tot * 100 if tot else 0
                
            top10 = sorted(entries.items(), key=lambda x: -x[1]["score"])[:10]
            
            headers = ["#", "Round", "Mode", "Difficulty", "Score", "Accuracy"]
            col_x   = [60, 110, 200, 330, 470, 590]
            
            hy = 110
            pygame.draw.rect(c, C_PANEL, (50, hy - 6, 880, 30), border_radius=4)
            for hi2, h in enumerate(headers):
                ht = self.f_xs.render(h.upper(), True, C_GRAY)
                c.blit(ht, (col_x[hi2], hy))
                
            for j, ((rn, mode, diff), vals) in enumerate(top10):
                ry  = hy + 34 + j * 32
                alt = C_PANEL if j % 2 == 0 else (28, 28, 40)
                pygame.draw.rect(c, alt, (50, ry - 6, 880, 30), border_radius=4)
                cells = [
                    str(j+1), rn, mode, diff,
                    str(vals["score"]), f"{vals['acc']:.1f}%"
                ]
                for ci, cell in enumerate(cells):
                    col = C_GOLD if ci == 4 else C_WHITE
                    ct  = self.f_xs.render(cell, True, col)
                    c.blit(ct, (col_x[ci], ry))
                    
        self._btn(WIDTH//2 - 88, HEIGHT - 55, 176, 42,
                "← Back", C_DARKGRAY, C_WHITE, self.f_sm)
        
    def handle_events(self):
        now = pygame.time.get_ticks()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                
            elif event.type == pygame.KEYDOWN:
                k = event.key
                if k == pygame.K_p:
                    if self.state == "PLAYING":
                        self.state = "PAUSED"
                    elif self.state == "PAUSED":
                        self.state = "PLAYING"
                elif k == pygame.K_ESCAPE:
                    if self.state in ("PLAYING", "PAUSED"):
                        self.end_game()
                    elif self.state in ("STATS", "SETTINGS",
                                        "LEADERBOARD"):
                        self.state = "MENU"
                    else:
                        self.running = False
                        
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._on_click(*event.pos, now)
                
    def _on_click(self, mx, my, now):
        
        if self.state == "MENU":
            mw, mh   = 150, 40
            total_m  = len(MODES) * mw + (len(MODES)-1) * 10
            mx0      = WIDTH//2 - total_m//2
            for i, m in enumerate(MODES):
                bx, by = mx0 + i*(mw+10), 228
                if bx <= mx <= bx+mw and by <= my <= by+mh:
                    self._mode_idx = i
                    self.mode      = MODES[i]
                    return
                
            dw, dh   = 148, 42
            total_d  = len(self._diff_keys) * dw + (len(self._diff_keys)-1) * 14
            dx0      = WIDTH//2 - total_d//2
            for i, dk in enumerate(self._diff_keys):
                bx, by = dx0 + i*(dw+14), 344
                if bx <= mx <= bx+dw and by <= my <= by+dh:
                    self._diff_idx  = i
                    self.difficulty = dk
                    return
                
            if WIDTH//2-118 <= mx <= WIDTH//2+118 and 420 <= my <= 474:
                self.start_game()
            elif WIDTH//2-118 <= mx <= WIDTH//2-7 and 484 <= my <= 526:
                self.state = "SETTINGS"
            elif WIDTH//2+7 <= mx <= WIDTH//2+118 and 484 <= my <= 526:
                self.state = "LEADERBOARD"
            elif WIDTH//2-118 <= mx <= WIDTH//2+118 and 536 <= my <= 576:
                if self.data_collector.load_data():
                    self._open_stats("MENU")
                    
        elif self.state == "SETTINGS":
            rows = [
                ("duration",   [15, 30, 60, 90]),
                ("max_targets",[1, 2, 3]),
                ("sound_on",   [True, False]),
                ("crosshair",  ["cross", "dot", "none"]),
                ("moving_pct", [0, 10, 15, 25, 40]),
                ("golden_pct", [0, 5, 10, 20]),
                ("bomb_pct",   [0, 5, 10]),
                ("shrink",     [True, False]),
            ]
            row_h = 52; sy = 130
            for i, (key, opts) in enumerate(rows):
                ry = sy + i * row_h
                if 80 <= mx <= 920 and ry <= my <= ry + row_h - 4:
                    self.settings.cycle(key, opts)
                    if key == "sound_on":
                        self.sounds.set_volume(1.0 if self.settings.sound_on else 0)
                    return
                
            by_back = sy + len(rows) * row_h + 12
            if WIDTH//2-80 <= mx <= WIDTH//2+80 and by_back <= my <= by_back + 44:
                self.state = "MENU"
                
        elif self.state == "PLAYING":
            hit_target = None
            for t in self.targets[:]:
                if t.is_clicked(mx, my):
                    hit_target = t
                    break
                
            if hit_target is not None:
                t         = hit_target
                click_ms  = pygame.time.get_ticks()
                pts       = t.POINTS
                
                if isinstance(t, BombTarget):
                    self.score_manager.score = max(0, self.score_manager.score + pts)
                    self.score_manager.break_combo()
                    self.player.register_miss()
                    self._trigger_shake(10, 18)
                    self.particles.burst(int(t.x), int(t.y), C_BOMB, 20)
                    self.sounds.play("bomb")
                    self._miss_fx.append((t.x, t.y, now))
                else:
                    if self.mode != "Practice":
                        gained = self.score_manager.add_score(pts)
                        self.player.register_hit()
                        if self.score_manager.combo > 1:
                            combo_col = C_GOLD if self.score_manager.combo >= 4 else C_WHITE
                            self._combo_display.append((
                                t.x, t.y,
                                f"x{self.score_manager.combo}  +{gained}",
                                now, combo_col))
                            self.sounds.play("combo")
                        else:
                            self.sounds.play(
                                "golden" if isinstance(t, GoldenTarget) else "hit")
                    else:
                        self.sounds.play("hit")
                        
                    self.particles.burst(
                        int(t.x), int(t.y),
                        C_GOLD if isinstance(t, GoldenTarget) else C_ACCENT)
                    self._hit_fx.append((t.x, t.y, now))
                    
                self.data_collector.record_click(
                    round_n=self.round_n,
                    target_x=t.x, target_y=t.y, target_size=t._base_rad,
                    spawn_time=t.spawn_time / 1000, click_time=click_ms / 1000,
                    result="bomb" if isinstance(t, BombTarget) else
                        "miss" if isinstance(t, BombTarget) else "hit",
                    score=self.score_manager.get_score(),
                    difficulty=self.difficulty,
                    session_id=self.session_id, mode=self.mode,
                    combo=self.score_manager.combo, target_type=t.TYPE)
                
                self.targets.remove(t)
                self._last_spawn = now
                
            else:
                if self.mode not in ("Practice",):
                    self.player.register_miss()
                    self.score_manager.break_combo()
                    self._miss_fx.append((mx, my, now))
                    self.sounds.play("miss")
                    if self.mode == "Endurance":
                        self._lives -= 1
                        self._trigger_shake(8, 14)
                        self.sounds.play("life")
                        if self._lives <= 0:
                            self.end_game()
                            
        elif self.state == "PAUSED":
            if WIDTH//2-110 <= mx <= WIDTH//2+110 and 370 <= my <= 418:
                self.end_game()
                
        elif self.state == "RESULTS":
            bw, bh = 178, 48; gap = 14
            total_b = bw*3 + gap*2
            bx1 = WIDTH//2 - total_b//2
            bx2, bx3 = bx1 + bw + gap, bx1 + bw*2 + gap*2
            by = 268
            if bx1 <= mx <= bx1+bw and by <= my <= by+bh:
                self.start_game()
            elif bx2 <= mx <= bx2+bw and by <= my <= by+bh:
                self._open_stats("RESULTS")
            elif bx3 <= mx <= bx3+bw and by <= my <= by+bh:
                self.state = "MENU"
                
        elif self.state == "STATS":
            if WIDTH//2-88 <= mx <= WIDTH//2+88 and HEIGHT-48 <= my <= HEIGHT-8:
                self.state = self._prev_state
                
        elif self.state == "LEADERBOARD":
            if WIDTH//2-88 <= mx <= WIDTH//2+88 and HEIGHT-55 <= my <= HEIGHT-13:
                self.state = "MENU"
                
    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()
        sys.exit()
        
    def _bc(self, surf: pygame.Surface, y: int):
        """Blit centred horizontally."""
        self._canvas.blit(surf, (WIDTH//2 - surf.get_width()//2, y))
        
    def _btn(self, x, y, w, h, label, bg, fg, font):
        pygame.draw.rect(self._canvas, bg, (x, y, w, h), border_radius=9)
        t = font.render(label, True, fg)
        self._canvas.blit(t, (x + w//2 - t.get_width()//2,
                            y + h//2 - t.get_height()//2))
        
    def _avg_rt_this_round(self) -> int | None:
        rts = []
        for row in self.data_collector.load_data():
            if (str(row.get("round")) == str(self.round_n)
                    and row.get("result") == "hit"):
                try:
                    rts.append(float(row["reaction_time"]))
                except (ValueError, TypeError):
                    pass
        return round(sum(rts) / len(rts)) if rts else None


if __name__ == "__main__":
    Game().run()

