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
        if self.total_clicks == 0:
            return 0.0
        return (self.hits / self.total_clicks) * 100.0
    
    def reset(self):
        self.total_clicks = 0
        self.hits = 0
        self.misses = 0
        
        