"""Record the plotter coordinates of every key on your physical board.

Before running: tape the board down where it will live, then park the
carriage by hand at the LEFT-BACK corner (that spot is 0, 0).
Hold the pen just above the board (or use a capped pen) so it doesn't mark it.

Run:  python calibrate.py
Saves board_coords.json after every key, so you can quit and resume.
Delete board_coords.json to start over.
Run with --refine to nudge keys already saved (e.g. ones from make_coords.py).
"""
import json
import os
import string
import sys

from plotter import Plotter

KEYS = list(string.ascii_uppercase) + ["YES", "NO"]
FILE = "board_coords.json"
coords = json.load(open(FILE)) if os.path.exists(FILE) else {}

print(__doc__)
print("Commands: a/d = X- / X+,  w/s = Y+ / Y-,  step N = set step size in mm,")
print("          ok = save this spot and go to the next key,  home = back to 0,0,")
print("          skip = leave this key for later,  quit = stop\n")

p = Plotter()
step = 5.0
REFINE = "--refine" in sys.argv  # start each key at its saved spot and fine-tune it
for key in (list(coords) if REFINE else KEYS):
    if key in coords and not REFINE:
        continue
    if key in coords:
        p.goto(*coords[key])
    while True:
        cmd = input(f"[{key}] at ({p.x:.1f}, {p.y:.1f}) step {step:g}mm > ").strip().lower()
        if cmd == "d":
            p.goto(p.x + step, p.y)
        elif cmd == "a":
            p.goto(p.x - step, p.y)
        elif cmd == "w":
            p.goto(p.x, p.y + step)
        elif cmd == "s":
            p.goto(p.x, p.y - step)
        elif cmd.startswith("step"):
            try:
                step = float(cmd.split()[1])
            except (IndexError, ValueError):
                print("usage: step 2.5")
        elif cmd == "home":
            p.goto(0, 0)
        elif cmd == "ok":
            coords[key] = [round(p.x, 1), round(p.y, 1)]
            json.dump(coords, open(FILE, "w"), indent=1)
            break
        elif cmd == "skip":
            break
        elif cmd == "quit":
            p.goto(0, 0)
            p.close()
            raise SystemExit
        else:
            print("?")

p.goto(0, 0)
p.close()
print(f"Done. Saved {len(coords)} keys to {FILE}")