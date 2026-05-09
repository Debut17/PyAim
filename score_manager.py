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
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        
    def get_score(self) -> int:
        return self.score
    
    