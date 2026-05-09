import io
import statistics

import pygame

from constants import WIDTH, HEIGHT, HUD_H


class StatsRenderer:
    BG = "#0C0C12"
    PANEL = "#16161F"
    GRN = "#50DC8C"
    RED = "#FF4F64"
    BLU = "#50A0FF"
    GLD = "#FFC83C"
    WHT = "#F0F0F5"
    GRY = "#787887"
    
    X_ZONES = {"Left": (0, 333), "Centre": (333, 667), "Right": (667, 1000)}
    Y_ZONES = {
        "Top": (HUD_H, HUD_H + 214),
        "Middle": (HUD_H + 214, HUD_H + 428),
        "Bottom": (HUD_H + 428, HEIGHT),
    }
    
    @staticmethod
    def _f(v):
        try:
            return float(v)
        except Exception:
            return None
        
    def _x_zone(self, x) -> str:
        x = self._f(x) or 0
        for n, (lo, hi) in self.X_ZONES.items():
            if lo <= x < hi:
                return n
        return "Right"
    
    def _y_zone(self, y) -> str:
        y = self._f(y) or 0
        for n, (lo, hi) in self.Y_ZONES.items():
            if lo <= y < hi:
                return n
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
        
        rt_ms = [v for v in (self._f(r["reaction_time"]) for r in hits) if v is not None]
        
        rounds: dict[int, int] = {}
        for r in data:
            rn = int(self._f(r.get("round")) or 0)
            sc = int(self._f(r.get("score"))  or 0)
            rounds[rn] = max(rounds.get(rn, 0), sc)
            
        avg_rt = (sum(rt_ms) / len(rt_ms)) if rt_ms else None
        std_rt = statistics.stdev(rt_ms)    if len(rt_ms) > 1 else None
        acc = (len(hits) / len(data) * 100) if data else 0
        best_sc = max(rounds.values(), default=0)
        
        try:
            times = sorted(self._f(r.get("click_time")) or 0 for r in hits)
            span = (times[-1] - times[0]) / 60 if len(times) > 1 else 1
            tpm = len(hits) / span if span > 0 else 0
        except Exception:
            tpm = 0
            
        plt.rcParams.update({
            "figure.facecolor": self.BG,
            "axes.facecolor": self.PANEL,
            "axes.edgecolor": "#2A2A3A",
            "axes.labelcolor": self.GRY,
            "xtick.color": self.GRY,
            "ytick.color": self.GRY,
            "text.color": self.WHT,
            "grid.color": "#2A2A3A",
            "grid.linewidth": 0.6,
            "font.family": "DejaVu Sans",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.titlesize": 9,
            "axes.labelsize": 7.5,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
        })
        
        fig = plt.figure(figsize=(16, 10))
        fig.suptitle("PyAim — Performance Analysis",
                    fontsize=15, fontweight="bold", color=self.WHT, y=0.985)
        
        outer = gs_mod.GridSpec(
            1, 2, figure=fig, width_ratios=[3, 1],
            left=0.05, right=0.97, top=0.95, bottom=0.07, wspace=0.06)
        lgs = gs_mod.GridSpecFromSubplotSpec(
            3, 3, subplot_spec=outer[0], hspace=0.54, wspace=0.42)
        rgs = gs_mod.GridSpecFromSubplotSpec(
            2, 1, subplot_spec=outer[1], hspace=0.30)
        
        def ax(r, c):
            return fig.add_subplot(lgs[r, c])
        
        a1 = ax(0, 0)
        if rt_ms:
            a1.hist(rt_ms, bins=20, color=self.GRN,
                    edgecolor=self.BG, linewidth=0.3, alpha=0.9)
            a1.axvline(avg_rt, color=self.GLD, linestyle="--",
                    linewidth=1.4, label=f"Mean {avg_rt:.0f} ms")
            if std_rt:
                a1.axvspan(avg_rt - std_rt, avg_rt + std_rt,
                        alpha=0.10, color=self.GLD,
                        label=f"±SD {std_rt:.0f}")
            a1.legend(fontsize=7, framealpha=0)
        else:
            a1.text(0.5, 0.5, "No hit data yet", ha="center", va="center",
                    transform=a1.transAxes, color=self.GRY, fontsize=8)
        a1.set_title("Reaction Time (ms)")
        a1.set_xlabel("ms")
        a1.set_ylabel("Frequency")
        a1.grid(axis="y")
        
        a2 = ax(0, 1)
        if rounds:
            rns = sorted(rounds.keys())
            cols = [self.GRN if i == len(rns) - 1 else self.BLU
                    for i in range(len(rns))]
            a2.bar([str(r) for r in rns], [rounds[r] for r in rns],
                color=cols, edgecolor=self.BG, linewidth=0.3)
            a2.grid(axis="y")
        else:
            a2.text(0.5, 0.5, "No data yet", ha="center", va="center",
                    transform=a2.transAxes, color=self.GRY, fontsize=8)
        a2.set_title("Score per Round")
        a2.set_xlabel("Round")
        a2.set_ylabel("Score")
        
        a3 = ax(0, 2)
        hc, mc = len(hits), len(misses)
        if hc + mc:
            _, texts, autos = a3.pie(
                [hc, mc], labels=["Hit", "Miss"],
                autopct="%1.1f%%", colors=[self.GRN, self.RED],
                wedgeprops={"linewidth": 2, "edgecolor": self.BG},
                startangle=90,
                textprops={"color": self.WHT, "fontsize": 8})
            for au in autos:
                au.set_color(self.BG)
                au.set_fontweight("bold")
                au.set_fontsize(7)
        else:
            a3.text(0.5, 0.5, "No data yet", ha="center", va="center",
                    transform=a3.transAxes, color=self.GRY, fontsize=8)
        a3.set_title("Hit vs Miss")
        
        a4 = ax(1, 0)
        if data:
            scores = [self._f(r.get("score")) or 0 for r in data]
            a4.plot(scores, color=self.GRN, linewidth=1.8)
            a4.fill_between(range(len(scores)), scores,
                            alpha=0.14, color=self.GRN)
            a4.grid(axis="y")
        else:
            a4.text(0.5, 0.5, "No data yet", ha="center", va="center",
                    transform=a4.transAxes, color=self.GRY, fontsize=8)
        a4.set_title("Score Progression")
        a4.set_xlabel("Click #")
        a4.set_ylabel("Score")
        
        a5a = ax(1, 1)
        xc = {z: 0 for z in self.X_ZONES}
        for r in hits:
            xc[self._x_zone(r.get("target_x"))] += 1
        a5a.bar(list(xc.keys()), list(xc.values()),
                color=[self.BLU, self.GRN, self.RED],
                edgecolor=self.BG, linewidth=0.3)
        a5a.grid(axis="y")
        a5a.set_title("Hits by X Zone")
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
        a5b.set_title("Hits by Y Zone")
        a5b.set_xlabel("Zone (Top / Middle / Bottom)")
        a5b.set_ylabel("Hit Count")
        
        a6 = fig.add_subplot(lgs[2, :])
        hx = [v for v in (self._f(r.get("target_x")) for r in hits) if v is not None]
        hy = [v for v in (self._f(r.get("target_y")) for r in hits) if v is not None]
        if len(hx) > 1:
            heatmap, _, _ = np.histogram2d(
                hx, hy, bins=[20, 13],
                range=[[0, WIDTH], [HUD_H, HEIGHT]])
            im = a6.imshow(
                heatmap.T, origin="lower",
                extent=[0, WIDTH, HUD_H, HEIGHT],
                cmap="YlOrRd", aspect="auto", alpha=0.9)
            fig.colorbar(im, ax=a6, fraction=0.015, pad=0.01,
                        label="Hit Density").ax.yaxis.label.set_color(self.GRY)
            mx_v = [v for v in (self._f(r.get("target_x")) for r in misses) if v]
            my_v = [v for v in (self._f(r.get("target_y")) for r in misses) if v]
            if mx_v:
                a6.scatter(mx_v, my_v, c=self.RED, s=6, alpha=0.35,
                        label="Misses", marker="x")
            a6.legend(fontsize=7, framealpha=0)
        else:
            a6.text(0.5, 0.5, "Not enough data for heatmap",
                    ha="center", va="center",
                    transform=a6.transAxes, color=self.GRY, fontsize=9)
        a6.set_title("Click Heatmap")
        a6.set_xlabel("X (pixels)")
        a6.set_ylabel("Y (pixels)")
        a6.set_xlim(0, WIDTH)
        a6.set_ylim(HUD_H, HEIGHT)
        a6.invert_yaxis()
        
        ax_sum = fig.add_subplot(rgs[0])
        ax_sum.axis("off")
        rows = [
            ("Total records", f"{len(data)}"),
            ("Rounds", f"{len(rounds)}"),
            ("Best score", f"{best_sc}"),
            ("Accuracy", f"{acc:.1f} %"),
            ("Avg reaction", f"{avg_rt:.0f} ms" if avg_rt else "—"),
            ("Std dev reaction", f"{std_rt:.0f} ms" if std_rt else "—"),
            ("Targets / min", f"{tpm:.1f}"),
            ("Total hits", f"{hc}"),
            ("Total misses", f"{mc}"),
        ]
        tbl = ax_sum.table(
            cellText=[[l, v] for l, v in rows],
            cellColours=[[self.PANEL, self.PANEL]] * len(rows),
            cellLoc="left", loc="center", bbox=[0, 0, 1, 1])
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(8)
        for (row, col), cell in tbl.get_celld().items():
            cell.set_edgecolor("#2A2A3A")
            cell.set_linewidth(0.4)
            cell.set_facecolor(self.PANEL)
            cell.set_text_props(
                color=self.GLD if col == 1 else self.GRY,
                fontweight="bold" if col == 1 else "normal")
        ax_sum.set_title("Summary Stats", fontsize=9, color=self.WHT, pad=6)
        
        ax_type = fig.add_subplot(rgs[1])
        type_counts: dict[str, int] = {}
        for r in data:
            tt = r.get("target_type", "normal") or "normal"
            type_counts[tt] = type_counts.get(tt, 0) + 1
        if type_counts:
            tc_colors = {
                "normal": self.GRN, "moving": self.BLU,
                "golden": self.GLD, "bomb": self.RED,
            }
            ax_type.barh(
                list(type_counts.keys()),
                list(type_counts.values()),
                color=[tc_colors.get(k, self.GRY) for k in type_counts])
            ax_type.grid(axis="x")
        else:
            ax_type.text(0.5, 0.5, "No type data", ha="center", va="center",
                        transform=ax_type.transAxes, color=self.GRY, fontsize=8)
        ax_type.set_title("Target Types", fontsize=9, color=self.WHT, pad=6)
        ax_type.set_xlabel("Count")
        
        if export_path:
            fig.savefig(export_path, dpi=130, bbox_inches="tight",
                        facecolor=self.BG, edgecolor="none")
            
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=105, bbox_inches="tight",
                    facecolor=self.BG, edgecolor="none")
        plt.close(fig)
        buf.seek(0)
        return pygame.image.load(buf, "s.png").convert()
    
    