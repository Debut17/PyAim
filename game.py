import pygame
import sys
import math
import random
import json
import os
import time
from datetime import datetime

from constants import (
    WIDTH, HEIGHT, HUD_H, FPS, BEST_FILE,
    DIFFICULTIES, MODES, MODE_DESC,
    C_BG, C_PANEL, C_ACCENT, C_RED, C_BLUE,
    C_WHITE, C_GRAY, C_DARKGRAY, C_GOLD, C_BOMB,
)
from sound_system import SoundSystem
from particles import ParticleSystem
from game_objects import (
    Target, MovingTarget, GoldenTarget, BombTarget,
)
from player import Player
from timer import Timer
from score_manager import ScoreManager
from data_collector import DataCollector
from settings import Settings
from stats_renderer import StatsRenderer


class Game:
    def __init__(self):
        pygame.init()
        pygame.mouse.set_visible(False)
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("PyAim v4.0")
        self.clock = pygame.time.Clock()
        self._canvas = pygame.Surface((WIDTH, HEIGHT))
        
        self.f_xl = pygame.font.SysFont("Segoe UI", 68, bold=True)
        self.f_lg = pygame.font.SysFont("Segoe UI", 36, bold=True)
        self.f_md = pygame.font.SysFont("Segoe UI", 24, bold=True)
        self.f_sm = pygame.font.SysFont("Segoe UI", 18)
        self.f_xs = pygame.font.SysFont("Segoe UI", 14)
        self.f_ti = pygame.font.SysFont("Segoe UI", 12)
        
        self.settings = Settings()
        self.sounds = SoundSystem()
        self.particles = ParticleSystem()
        self.player = Player()
        self.score_manager = ScoreManager()
        self.data_collector = DataCollector()
        self.stats_renderer = StatsRenderer()
        self.timer = None
        
        self.state = "MENU"
        self.running = True
        self.difficulty = "Normal"
        self.mode = "Classic"
        self.round_n = 0
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.targets: list[Target] = []
        self._last_spawn = 0
        self._precision_remaining = 20
        self._lives = 3
        self._combo_display = []
        
        self._hit_fx = []
        self._miss_fx = []
        self._shake_frames = 0
        self._shake_amount = 0
        
        self._diff_keys = list(DIFFICULTIES.keys())
        self._diff_idx = 1
        self._mode_idx = 0
        
        self._stats_surf = None
        self._stats_loading = False
        self._stats_msg = "Building charts..."
        self._prev_state = "MENU"
        
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
            return BombTarget(x, y, radius, lifetime)
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
        self._hit_fx.clear()
        self._miss_fx.clear()
        self._combo_display.clear()
        self._shake_frames = 0
        self._shake_amount = 0
        
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
        self._shake_frames = 0
        self._shake_amount = 0
        
        self.data_collector.save_to_csv()
        self._stats_surf = None
        best_key = f"{self.mode}_{self.difficulty}"
        self._save_best(best_key, self.score_manager.get_score())
        
        try:
            data = self.data_collector.load_data()
            if data:
                export_name = f"pyaim_stats_{self.session_id}.png"
                self.stats_renderer.build_surface(data, export_path=export_name)
        except Exception:
            pass
        
        self.sounds.play("end")
        self.state = "RESULTS"
        
    def _open_stats(self, back_to="MENU"):
        self._prev_state = back_to
        self.state = "STATS"
        self._stats_surf = None
        self._stats_loading = True
        self._stats_msg = "Building charts..."
        
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
        
        self._hit_fx = [(x, y, b) for x, y, b in self._hit_fx  if now - b < 450]
        self._miss_fx = [(x, y, b) for x, y, b in self._miss_fx if now - b < 450]
        self._combo_display = [
            (x, y, txt, b, c) for x, y, txt, b, c in self._combo_display
            if now - b < 700
        ]
        
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
            "MENU": self._draw_menu,
            "SETTINGS": self._draw_settings,
            "PLAYING": self._draw_playing,
            "PAUSED": self._draw_paused,
            "RESULTS": self._draw_results,
            "STATS": self._draw_stats,
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
        pulse = 0.28 + 0.18 * math.sin(self._bg_t * 0.6)
        col = (30, 30, 46)
        for gx in range(0, WIDTH + 1, 48):
            for gy in range(0, HEIGHT + 1, 48):
                pygame.draw.circle(self._canvas, col, (gx, gy), 1)
                
    def _draw_crosshair(self):
        mx, my = pygame.mouse.get_pos()
        style = self.settings.crosshair
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
        self._bc(self.f_sm.render("Train your aim. Track your stats.", True, C_GRAY), 152)
        
        self._bc(self.f_md.render("Mode", True, C_WHITE), 192)
        mw, mh = 150, 40
        total_m = len(MODES) * mw + (len(MODES) - 1) * 10
        mx0 = WIDTH // 2 - total_m // 2
        for i, m in enumerate(MODES):
            bx, by = mx0 + i * (mw + 10), 228
            sel = (i == self._mode_idx)
            pygame.draw.rect(c, C_BLUE if sel else C_DARKGRAY,
                            (bx, by, mw, mh), border_radius=7)
            t = self.f_xs.render(m, True, C_BG if sel else C_WHITE)
            c.blit(t, (bx + mw // 2 - t.get_width() // 2,
                       by + mh // 2 - t.get_height() // 2))
            
        self._bc(self.f_xs.render(MODE_DESC.get(self.mode, ""), True, C_GRAY), 278)
        
        self._bc(self.f_md.render("Difficulty", True, C_WHITE), 308)
        dw, dh = 148, 42
        total_d = len(self._diff_keys) * dw + (len(self._diff_keys) - 1) * 14
        dx0 = WIDTH // 2 - total_d // 2
        for i, dk in enumerate(self._diff_keys):
            bx, by = dx0 + i * (dw + 14), 344
            sel = (i == self._diff_idx)
            pygame.draw.rect(c, C_ACCENT if sel else C_DARKGRAY,
                            (bx, by, dw, dh), border_radius=7)
            t = self.f_sm.render(dk, True, C_BG if sel else C_WHITE)
            c.blit(t, (bx + dw // 2 - t.get_width() // 2,
                       by + dh // 2 - t.get_height() // 2))
            
        best_key = f"{self.mode}_{self.difficulty}"
        best_val = self._best.get(best_key)
        if best_val:
            self._bc(self.f_xs.render(f"Personal best: {best_val} pts", True, C_GOLD), 398)
            
        self._btn(WIDTH // 2 - 118, 420, 236, 54, "PLAY", C_ACCENT,   C_BG,    self.f_lg)
        self._btn(WIDTH // 2 - 118, 484, 111, 42, "Settings", C_DARKGRAY, C_WHITE, self.f_sm)
        self._btn(WIDTH // 2 +   7, 484, 111, 42, "Leaderboard", C_DARKGRAY, C_WHITE, self.f_sm)
        
        data_count = len(self.data_collector.load_data())
        has_data = data_count > 0
        label = (f"Analysis  ({data_count} records)"
                    if has_data else "Analysis  (no data yet)")
        self._btn(WIDTH // 2 - 118, 536, 236, 40, label,
                C_BLUE if has_data else C_DARKGRAY,
                C_BG   if has_data else C_GRAY, self.f_xs)
        
        self._bc(self.f_ti.render("P = pause  |  ESC = quit", True, C_WHITE), 594)
        
    def _draw_settings(self):
        c = self._canvas
        self._bc(self.f_lg.render("Settings", True, C_WHITE), 60)
        
        rows = [
            ("Game Duration", f"{self.settings.duration}s",
            [15, 30, 60, 90], "duration"),
            ("Max Targets", str(self.settings.max_targets),
            [1, 2, 3], "max_targets"),
            ("Sound", "On" if self.settings.sound_on else "Off",
            [True, False], "sound_on"),
            ("Crosshair", self.settings.crosshair.capitalize(),
            ["cross", "dot", "none"], "crosshair"),
            ("Moving Targets %", f"{self.settings.moving_pct}%",
            [0, 10, 15, 25, 40], "moving_pct"),
            ("Golden Targets %", f"{self.settings.golden_pct}%",
            [0, 5, 10, 20], "golden_pct"),
            ("Bomb Targets %", f"{self.settings.bomb_pct}%",
            [0, 5, 10], "bomb_pct"),
            ("Shrinking Targets","On" if self.settings.shrink else "Off",
            [True, False], "shrink"),
        ]
        
        row_h = 52
        sy = 130
        for i, (label, val, _, _key) in enumerate(rows):
            ry = sy + i * row_h
            pygame.draw.rect(c, C_PANEL, (80, ry, 840, row_h - 4), border_radius=6)
            lt = self.f_sm.render(label, True, C_GRAY)
            vt = self.f_sm.render(val, True, C_ACCENT)
            at = self.f_xs.render("click to cycle ->", True, C_DARKGRAY)
            c.blit(lt, (100, ry + 14))
            c.blit(vt, (500, ry + 14))
            c.blit(at, (720, ry + 18))
            
        self._btn(WIDTH // 2 - 80, sy + len(rows) * row_h + 12, 160, 44,
                "<- Back", C_DARKGRAY, C_WHITE, self.f_sm)
        
    def _draw_playing(self):
        c = self._canvas
        now = pygame.time.get_ticks()
        
        pygame.draw.rect(c, C_PANEL, (0, 0, WIDTH, HUD_H))
        
        sc = self.f_lg.render(str(self.score_manager.get_score()), True, C_ACCENT)
        c.blit(sc, (16, 8))
        c.blit(self.f_ti.render("SCORE", True, C_WHITE),
            (20 + sc.get_width() + 4, 35))
        
        combo = self.score_manager.combo
        if combo > 1:
            col = [C_WHITE, C_ACCENT, C_GOLD, C_BLUE, C_RED, C_GOLD][min(combo, 5)]
            cmbt = self.f_md.render(f"x{combo}", True, col)
            c.blit(cmbt, (16, 40))
            
        acc = self.player.get_accuracy()
        ac = self.f_lg.render(f"{acc:.1f}%", True, C_WHITE)
        c.blit(ac, (WIDTH // 2 - ac.get_width() // 2, 6))
        al = self.f_ti.render("ACCURACY", True, C_WHITE)
        c.blit(al, (WIDTH // 2 - al.get_width() // 2, 50))
        
        if self.mode == "Endurance":
            max_lives = 3
            life_radius = 10
            life_spacing = 28
            
            dots_center_x = WIDTH - 58
            dot_y = 28
            
            total_dots_width = (max_lives - 1) * life_spacing
            
            first_dot_x = dots_center_x - total_dots_width // 2
            
            for li in range(max_lives):
                col = C_RED if li < self._lives else C_DARKGRAY
                pygame.draw.circle(
                    c,
                    col,
                    (first_dot_x + li * life_spacing, dot_y),
                    life_radius
                )
                
            rl = self.f_ti.render("LIVES", True, C_WHITE)
            rl_rect = rl.get_rect()
            
            rl_rect.centerx = dots_center_x
            rl_rect.y = 40
            
            c.blit(rl, rl_rect)
        elif self.mode == "Precision":
            pr = self.f_lg.render(str(max(0, self._precision_remaining)), True, C_WHITE)
            prl = self.f_ti.render("REMAINING", True, C_GRAY)
            c.blit(pr,  (WIDTH - pr.get_width() - 16, 8))
            c.blit(prl, (WIDTH - prl.get_width() - 16, 38))
        elif self.mode != "Practice":
            tl = self.timer.get_time_left()
            color = C_RED if tl < 5 else C_WHITE
            tc = self.f_lg.render(f"{tl:.1f}s", True, color)
            tll = self.f_ti.render("TIME LEFT", True, C_GRAY)
            c.blit(tc, (WIDTH - tc.get_width() - 2, 6))
            c.blit(tll, (WIDTH - tll.get_width() - 16, 50))
            
        hm = self.f_ti.render(
            f"Hits {self.player.hits}  Misses {self.player.misses}", True, C_WHITE)
        c.blit(hm, (WIDTH // 2 - hm.get_width() // 2 + 188, 35))
        
        mb = self.f_ti.render(
            f"{self.mode.upper()} / {self.difficulty.upper()}", True, C_BLUE)
        c.blit(mb, (WIDTH // 2 - mb.get_width() // 2 - 188, 35))
        
        pygame.draw.line(c, C_DARKGRAY, (0, HUD_H), (WIDTH, HUD_H), 1)
        
        for x, y, b in self._hit_fx:
            age = now - b
            alpha = max(0, 185 - int(185 * age / 450))
            r = 16 + int(26 * age / 450)
            fs = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(fs, (*C_ACCENT, alpha), (r + 2, r + 2), r, 3)
            c.blit(fs, (int(x) - r - 2, int(y) - r - 2))
            
        for x, y, b in self._miss_fx:
            age = now - b
            alpha = max(0, 160 - int(160 * age / 450))
            sz = 12
            ms = pygame.Surface((sz * 2, sz * 2), pygame.SRCALPHA)
            pygame.draw.line(ms, (*C_RED, alpha), (0, 0),     (sz * 2, sz * 2), 3)
            pygame.draw.line(ms, (*C_RED, alpha), (sz * 2, 0),(0, sz * 2),       3)
            c.blit(ms, (int(x) - sz, int(y) - sz))
            
        for x, y, txt, b, col in self._combo_display:
            age = now - b
            alpha = max(0, 220 - int(220 * age / 700))
            rise = int(30 * age / 700)
            ft = self.f_md.render(txt, True, col)
            ts = pygame.Surface((ft.get_width() + 4, ft.get_height() + 4),
                                pygame.SRCALPHA)
            ts.blit(ft, (2, 2))
            c.blit(ts, (int(x) - ft.get_width() // 2, int(y) - rise - 20))
            
        for t in self.targets:
            t.draw(c)
            
        if self.mode == "Practice":
            pw = self.f_lg.render("PRACTICE - no scoring", True, C_DARKGRAY)
            c.blit(pw, (WIDTH // 2 - pw.get_width() // 2, HEIGHT // 2 - 20))
            
    def _draw_paused(self):
        self._draw_playing()
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self._canvas.blit(overlay, (0, 0))
        self._bc(self.f_xl.render("PAUSED", True, C_WHITE), 230)
        self._bc(self.f_sm.render("P or ESC -> resume", True, C_GRAY), 320)
        self._btn(WIDTH // 2 - 110, 370, 220, 48,
                "Quit to Menu", C_DARKGRAY, C_WHITE, self.f_sm)
        
    def _draw_results(self):
        c = self._canvas
        self._bc(self.f_xl.render("Results", True, C_WHITE), 40)
        
        acc = self.player.get_accuracy()
        avg_rt = self._avg_rt_this_round()
        best_k = f"{self.mode}_{self.difficulty}"
        is_pb = (self.mode != "Practice"
                and self.score_manager.get_score() >= self._best.get(best_k, 0)
                and self.score_manager.get_score() > 0)
        
        if is_pb:
            self._bc(self.f_md.render("* New Personal Best! *", True, C_GOLD), 112)
            
        cards = [
            ("Score", str(self.score_manager.get_score()), C_ACCENT),
            ("Accuracy", f"{acc:.1f}%", C_BLUE),
            ("Hits", str(self.player.hits), C_ACCENT),
            ("Misses", str(self.player.misses), C_RED),
            ("Avg Reaction", f"{avg_rt}ms" if avg_rt else "-", C_GOLD),
            ("Max Combo", f"x{self.score_manager.max_combo}", C_GOLD),
        ]
        cw, ch = 148, 84
        total_w = len(cards) * cw + (len(cards) - 1) * 12
        sx = WIDTH // 2 - total_w // 2
        for i, (lbl, val, col) in enumerate(cards):
            cx, cy = sx + i * (cw + 12), 140
            pygame.draw.rect(c, C_PANEL, (cx, cy, cw, ch), border_radius=9)
            pygame.draw.rect(c, col, (cx, cy, cw,  3),  border_radius=2)
            vt = self.f_md.render(val, True, col)
            lt = self.f_ti.render(lbl.upper(), True, C_GRAY)
            c.blit(vt, (cx + cw // 2 - vt.get_width() // 2, cy + 14))
            c.blit(lt, (cx + cw // 2 - lt.get_width() // 2, cy + 56))
            
        bw, bh = 178, 48
        gap = 14
        total_b = bw * 3 + gap * 2
        bx1 = WIDTH // 2 - total_b // 2
        bx2 = bx1 + bw + gap
        bx3 = bx2 + bw + gap
        by = 268
        self._btn(bx1, by, bw, bh, "Play Again", C_ACCENT, C_BG, self.f_sm)
        self._btn(bx2, by, bw, bh, "Analysis", C_BLUE, C_BG, self.f_sm)
        self._btn(bx3, by, bw, bh, "Main Menu", C_DARKGRAY, C_WHITE, self.f_sm)
        
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
                c.blit(self.f_xs.render(f"  Round {rn}  ->  {sc} pts", True, col),
                       (lx, ly + 22 + j * 22))
                
        self._bc(self.f_ti.render(
            f"Stats auto-exported -> pyaim_stats_{self.session_id}.png",
            True, C_DARKGRAY), 460)
        
    def _draw_stats(self):
        c = self._canvas
        
        if self._stats_surf is None and self._stats_loading:
            msg = self.f_lg.render(self._stats_msg, True, C_GRAY)
            c.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 - 30))
            self.screen.blit(c, (0, 0))
            pygame.display.flip()
            
            data = self.data_collector.load_data()
            if not data:
                self._stats_msg = "No data yet - play a round first!"
                self._stats_loading = False
                return
            try:
                self._stats_surf = self.stats_renderer.build_surface(data)
                self._stats_loading = False
            except Exception as e:
                self._stats_msg = f"Chart error: {e}"
                self._stats_loading = False
            return
        
        if self._stats_surf is None:
            msg = self.f_lg.render(self._stats_msg, True, C_GRAY)
            c.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 - 30))
        else:
            sw, sh = self._stats_surf.get_size()
            scale = min(WIDTH / sw, (HEIGHT - 52) / sh)
            dw, dh = int(sw * scale), int(sh * scale)
            scaled = pygame.transform.smoothscale(self._stats_surf, (dw, dh))
            c.blit(scaled, (WIDTH // 2 - dw // 2, 4))
            
        self._btn(WIDTH // 2 - 88, HEIGHT - 48, 176, 40,
                "<- Back", C_DARKGRAY, C_WHITE, self.f_sm)
        
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
                key = (str(row.get("round", "?")),
                    row.get("mode", "?"),
                    row.get("difficulty", "?"))
                sc = int(float(row.get("score") or 0))
                if key not in entries or sc > entries[key]["score"]:
                    entries[key] = {"score": sc}
                res = row.get("result", "")
                hits_m[key] = hits_m.get(key, 0)  + (1 if res == "hit" else 0)
                total_m[key] = total_m.get(key, 0) + 1
                
            for k in entries:
                tot = total_m.get(k, 1)
                entries[k]["acc"] = hits_m.get(k, 0) / tot * 100 if tot else 0
                
            top10 = sorted(entries.items(), key=lambda x: -x[1]["score"])[:10]
            headers = ["#", "Round", "Mode", "Difficulty", "Score", "Accuracy"]
            col_x = [60, 110, 200, 330, 470, 590]
            
            hy = 110
            pygame.draw.rect(c, C_PANEL, (50, hy - 6, 880, 30), border_radius=4)
            for hi2, h in enumerate(headers):
                c.blit(self.f_xs.render(h.upper(), True, C_GRAY), (col_x[hi2], hy))
                
            for j, ((rn, mode, diff), vals) in enumerate(top10):
                ry = hy + 34 + j * 32
                alt = C_PANEL if j % 2 == 0 else (28, 28, 40)
                pygame.draw.rect(c, alt, (50, ry - 6, 880, 30), border_radius=4)
                cells = [
                    str(j + 1), rn, mode, diff,
                    str(vals["score"]), f"{vals['acc']:.1f}%"
                ]
                for ci, cell in enumerate(cells):
                    col = C_GOLD if ci == 4 else C_WHITE
                    c.blit(self.f_xs.render(cell, True, col), (col_x[ci], ry))
                    
        self._btn(WIDTH // 2 - 88, HEIGHT - 55, 176, 42,
                "<- Back", C_DARKGRAY, C_WHITE, self.f_sm)
        
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
                    elif self.state in ("STATS", "SETTINGS", "LEADERBOARD"):
                        self.state = "MENU"
                    else:
                        self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._on_click(*event.pos, now)
                
    def _on_click(self, mx, my, now):
        if self.state == "MENU":
            mw, mh = 150, 40
            total_m = len(MODES) * mw + (len(MODES) - 1) * 10
            mx0 = WIDTH // 2 - total_m // 2
            for i, m in enumerate(MODES):
                bx, by = mx0 + i * (mw + 10), 228
                if bx <= mx <= bx + mw and by <= my <= by + mh:
                    self._mode_idx = i
                    self.mode = MODES[i]
                    return
                
            dw, dh = 148, 42
            total_d = len(self._diff_keys) * dw + (len(self._diff_keys) - 1) * 14
            dx0 = WIDTH // 2 - total_d // 2
            for i, dk in enumerate(self._diff_keys):
                bx, by = dx0 + i * (dw + 14), 344
                if bx <= mx <= bx + dw and by <= my <= by + dh:
                    self._diff_idx = i
                    self.difficulty = dk
                    return
                
            if WIDTH // 2 - 118 <= mx <= WIDTH // 2 + 118 and 420 <= my <= 474:
                self.start_game()
            elif WIDTH // 2 - 118 <= mx <= WIDTH // 2 - 7 and 484 <= my <= 526:
                self.state = "SETTINGS"
            elif WIDTH // 2 + 7 <= mx <= WIDTH // 2 + 118 and 484 <= my <= 526:
                self.state = "LEADERBOARD"
            elif WIDTH // 2 - 118 <= mx <= WIDTH // 2 + 118 and 536 <= my <= 576:
                if self.data_collector.load_data():
                    self._open_stats("MENU")
                    
        elif self.state == "SETTINGS":
            rows_keys = [
                ("duration", [15, 30, 60, 90]),
                ("max_targets", [1, 2, 3]),
                ("sound_on", [True, False]),
                ("crosshair", ["cross", "dot", "none"]),
                ("moving_pct", [0, 10, 15, 25, 40]),
                ("golden_pct", [0, 5, 10, 20]),
                ("bomb_pct", [0, 5, 10]),
                ("shrink", [True, False]),
            ]
            row_h = 52
            sy = 130
            for i, (key, opts) in enumerate(rows_keys):
                ry = sy + i * row_h
                if 80 <= mx <= 920 and ry <= my <= ry + row_h - 4:
                    self.settings.cycle(key, opts)
                    if key == "sound_on":
                        self.sounds.set_volume(1.0 if self.settings.sound_on else 0)
                    return
            by_back = sy + len(rows_keys) * row_h + 12
            if WIDTH // 2 - 80 <= mx <= WIDTH // 2 + 80 and by_back <= my <= by_back + 44:
                self.state = "MENU"
                
        elif self.state == "PLAYING":
            hit_target = None
            for t in self.targets[:]:
                if t.is_clicked(mx, my):
                    hit_target = t
                    break
                
            if hit_target is not None:
                t = hit_target
                click_ms = pygame.time.get_ticks()
                
                if isinstance(t, BombTarget):
                    self.score_manager.score = max(0, self.score_manager.score + t.POINTS)
                    self.score_manager.break_combo()
                    self.player.register_miss()
                    self.particles.burst(int(t.x), int(t.y), C_BOMB, 20)
                    self.sounds.play("bomb")
                    self._miss_fx.append((t.x, t.y, now))
                    self.targets.remove(t)
                    self._last_spawn = now
                    
                    self.data_collector.record_click(
                        round_n=self.round_n,
                        target_x=t.x, target_y=t.y, target_size=t._base_rad,
                        spawn_time=t.spawn_time / 1000, click_time=click_ms / 1000,
                        result="bomb",
                        score=self.score_manager.get_score(),
                        difficulty=self.difficulty,
                        session_id=self.session_id, mode=self.mode,
                        combo=0, target_type=t.TYPE)
                    
                    if self.mode == "Endurance":
                        self._lives -= 1
                        self.sounds.play("life")
                        self._trigger_shake(10, 18)
                        if self._lives <= 0:
                            self.end_game()
                            return
                    else:
                        self._trigger_shake(10, 18)
                        
                else:
                    if self.mode != "Practice":
                        gained = self.score_manager.add_score(t.POINTS)
                        self.player.register_hit()
                        if self.score_manager.combo > 1:
                            combo_col = (C_GOLD if self.score_manager.combo >= 4
                                        else C_WHITE)
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
                        result="hit",
                        score=self.score_manager.get_score(),
                        difficulty=self.difficulty,
                        session_id=self.session_id, mode=self.mode,
                        combo=self.score_manager.combo, target_type=t.TYPE)
                    
                    self.targets.remove(t)
                    self._last_spawn = now
                    
            else:
                if self.mode != "Practice":
                    self.player.register_miss()
                    self.score_manager.break_combo()
                    self._miss_fx.append((mx, my, now))
                    if self.mode == "Endurance":
                        self._lives -= 1
                        self._trigger_shake(8, 14)
                        self.sounds.play("life")
                        if self._lives <= 0:
                            self.end_game()
                    else:
                        self.sounds.play("miss")
                        
        elif self.state == "PAUSED":
            if WIDTH // 2 - 110 <= mx <= WIDTH // 2 + 110 and 370 <= my <= 418:
                self.end_game()
                
        elif self.state == "RESULTS":
            bw, bh = 178, 48
            gap = 14
            total_b = bw * 3 + gap * 2
            bx1 = WIDTH // 2 - total_b // 2
            bx2 = bx1 + bw + gap
            bx3 = bx2 + bw + gap
            by = 268
            if bx1 <= mx <= bx1 + bw and by <= my <= by + bh:
                self.start_game()
            elif bx2 <= mx <= bx2 + bw and by <= my <= by + bh:
                self._open_stats("RESULTS")
            elif bx3 <= mx <= bx3 + bw and by <= my <= by + bh:
                self.state = "MENU"
                
        elif self.state == "STATS":
            if WIDTH // 2 - 88 <= mx <= WIDTH // 2 + 88 and HEIGHT - 48 <= my <= HEIGHT - 8:
                self.state = self._prev_state
                
        elif self.state == "LEADERBOARD":
            if WIDTH // 2 - 88 <= mx <= WIDTH // 2 + 88 and HEIGHT - 55 <= my <= HEIGHT - 13:
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
        self._canvas.blit(surf, (WIDTH // 2 - surf.get_width() // 2, y))
        
    def _btn(self, x, y, w, h, label, bg, fg, font):
        pygame.draw.rect(self._canvas, bg, (x, y, w, h), border_radius=9)
        t = font.render(label, True, fg)
        self._canvas.blit(t, (x + w // 2 - t.get_width() // 2,
                               y + h // 2 - t.get_height() // 2))
        
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

