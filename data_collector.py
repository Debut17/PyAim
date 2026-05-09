import csv
import os

from constants import DATA_FILE


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

