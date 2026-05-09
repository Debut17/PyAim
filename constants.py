WIDTH = 1000
HEIGHT = 700
HUD_H = 70
FPS = 60
DATA_FILE = "pyaim_data.csv"
SETTINGS_FILE = "pyaim_settings.json"
BEST_FILE = "pyaim_best.json"

DIFFICULTIES = {
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

C_BG = (12, 12, 18)
C_PANEL = (22, 22, 32)
C_ACCENT = (80, 220, 140)
C_RED = (255, 80, 100)
C_BLUE = ( 80, 160, 255)
C_WHITE = (240, 240, 245)
C_GRAY = (120, 120, 135)
C_DARKGRAY = (45, 45, 58)
C_GOLD = (255, 200, 60)
C_BOMB = (180, 40, 60)
C_TARGET = (255, 70, 90)
C_TARGET_RIM = (255, 140, 150)
C_MOVING = (80, 180, 255)
C_MOVING_RIM = (160, 210, 255)

