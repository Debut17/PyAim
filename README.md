# PyAim

## Project Description

- **Project by:** Panuwitch Sowkasem (Student ID: 6810545867)
- **Game Genre:** Aim Trainer / Reflex

PyAim is a 2D aim-training game built with Python and Pygame. Targets appear at random positions on screen and the player must click them before they disappear. Every click is recorded to a CSV file and a full statistical analysis screen is available inside the game — no separate script needed.

---

## Installation

Clone this repository:

```sh
git clone https://github.com/Debut17/PyAim.git
cd PyAim
```

Create and activate a Python virtual environment, then install dependencies.

**Windows:**

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**Mac:**

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Running Guide

After activating the virtual environment, run the game with:

**Windows:**

```bat
python main.py
```

**Mac:**

```sh
python3 main.py
```

---

## Tutorial / Usage

### Main Menu

- Click a **Mode** button to select your game mode
- Click a **Difficulty** button (Easy / Normal / Hard) to set target size and speed
- Click **PLAY** to start
- Click **Analysis** to view your performance graphs (available after at least one session)
- Click **Leaderboard** to see top rounds from all past sessions
- Click **Settings** to adjust game options

### In-Game Controls

| Action | Input |
|---|---|
| Click a target | Left mouse button |
| Pause / Resume | P key |
| End game early | ESC |

### How Scoring Works

- Hit a target → gain points equal to `target points × combo multiplier`
- Combo multiplier increases by 1 for each consecutive hit (max ×5)
- Any miss resets the combo to ×1

### After the Game

- Results screen shows your score, accuracy, hits, misses, average reaction time, and max combo
- Click **Analysis** to open the 7-graph performance screen
- A stats PNG is automatically saved to the project folder after every session

---

## Game Features

### Game Modes

| Mode | Description |
|---|---|
| Classic | 30-second timed game — hit as many targets as possible |
| Precision | 20 targets total — every miss counts against accuracy |
| Speed | 15 seconds, smaller targets, faster spawn rate |
| Endurance | No timer — you have 3 lives, lose one on every miss |
| Practice | No score, no timer — free warm-up with no pressure |

### Difficulty Levels

| Difficulty | Target Radius | Lifetime | Spawn Delay |
|---|---|---|---|
| Easy | 45 px | 3.0 s | 1.2 s |
| Normal | 30 px | 2.0 s | 0.9 s |
| Hard | 18 px | 1.2 s | 0.6 s |

### Target Types

| Type | Colour | Points | Behaviour |
|---|---|---|---|
| Normal | Red | ×1 | Static |
| Moving | Blue | ×2 | Bounces around the screen |
| Golden | Gold | ×3 | Smaller, worth more |
| Bomb | Dark red | −2 | Avoid — clicking costs points and a life (Endurance) |

### Settings (configurable in-game)

- Game duration: 15 / 30 / 60 / 90 seconds
- Max targets on screen: 1 / 2 / 3
- Sound: On / Off
- Crosshair style: Cross / Dot / None
- Moving target chance, Golden target chance, Bomb target chance
- Shrinking targets: On / Off

### Statistical Analysis (7 Graphs)

1. **Reaction Time Histogram** — distribution of hit response times with mean and ±std dev
2. **Score per Round Bar Chart** — compare performance across sessions
3. **Hit vs Miss Pie Chart** — overall accuracy proportion
4. **Score Progression Line Graph** — how score built up during the last session
5. **X-Zone Bar Chart** — hit count by screen area (Left / Centre / Right)
6. **Y-Zone Bar Chart** — hit count by screen area (Top / Middle / Bottom)
7. **Click Heatmap** — 2D density map of all hit positions with miss markers

Summary panel shows: total records, avg reaction, std dev, targets per minute, best score, accuracy.

### Other Features

- Combo multiplier up to ×5 with floating score popup
- Particle burst effect on every hit
- Screen shake on miss and bomb click
- Procedural sound effects (no audio files required)
- Animated dot-grid background
- Personal best saved per mode + difficulty combination
- Leaderboard showing top 10 rounds from all recorded data
- Stats PNG auto-exported after every session

---

## Known Bugs

- Sound effects require NumPy to work. If NumPy is not installed, the game runs silently with no error.
- On some systems the matplotlib chart takes 3–5 seconds to build on the first Analysis screen visit. This is normal behaviour — a "Building charts..." message is shown while it loads.

---

## Unfinished Works

All planned features from the proposal have been implemented. The following items are possible future improvements but were not in scope for this submission:

- Online leaderboard (current leaderboard is local CSV only)
- Replay system to watch back a previous session
- Controller / gamepad support

---

## External Sources

1. Pygame — [https://www.pygame.org](https://www.pygame.org) — LGPL License
2. Matplotlib — [https://matplotlib.org](https://matplotlib.org) — BSD License
3. NumPy — [https://numpy.org](https://numpy.org) — BSD 3-Clause License

No external images, music, or third-party game code were used. All visuals are drawn with pygame drawing functions and all sounds are generated programmatically with NumPy.
