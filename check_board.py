"""Visit a few keys so you can check the coordinates against the real board.
Park the carriage at the LEFT-BACK corner first. Hold the pen just above the board."""
import json
import time

from plotter import Plotter

coords = json.load(open("board_coords.json"))
p = Plotter()
for key in ["YES", "A", "B", "Z", "T", "J", "YES", "NO"]:
    print("->", key, coords[key])
    p.goto(*coords[key])
    time.sleep(2.5)
p.goto(0, 0)
p.close()
