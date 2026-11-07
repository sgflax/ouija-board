import serial, time
# s = serial.Serial("/dev/cu.usbmodem201912341", 115200, timeout=2)
# time.sleep(2)
# for cmd in ["G21", "G91", "G1 X20 F3000", "G1 X-20 F3000"]:
#     s.write((cmd + "\n").encode()); time.sleep(1.5)
#     print(cmd, "->", s.read_all().decode().strip())

s = serial.Serial("/dev/cu.usbmodem201912341", 115200, timeout=2)
time.sleep(2)

def send(cmd):
    s.write((cmd + "\n").encode()); time.sleep(1.2)
    print(cmd, "->", s.read_all().decode().strip())

send("G21")
send("G92 X0 Y0")   # call the current spot (0, 0)
send("G90")         # absolute moves from now on
for cmd in ["G1 X30 F3000", "G1 X30 Y30", "G1 X0 Y30", "G1 X0 Y0"]:
    send(cmd)

"""Small, safe wrapper for the iDraw plotter over USB serial.

Ritual every session: park the carriage by hand at the LEFT-BACK corner,
then run the script. That spot becomes (0, 0).

All moves are clamped to MAX_X / MAX_Y so a typo can't drive the carriage
into the frame. Measure your real travel and raise these numbers.
"""
import time
import serial

PORT = "/dev/cu.usbmodem201912341"
BAUD = 115200
MAX_X = 210.0   # mm
MAX_Y = 300.0   # mm
SPEED = 3000    # mm/min


class Plotter:
    def __init__(self, port=PORT):
        self.s = serial.Serial(port, BAUD, timeout=2)
        time.sleep(2)
        self.x = self.y = 0.0
        for cmd in ("G21", "G92 X0 Y0", "G90"):  # mm, this spot = (0, 0), absolute
            self.send(cmd)

    def send(self, cmd):
        self.s.write((cmd + "\n").encode())
        time.sleep(0.2)
        return self.s.read_all().decode().strip()

    def goto(self, x, y, speed=SPEED):
        x = min(max(x, 0.0), MAX_X)  # clamp to the safe box
        y = min(max(y, 0.0), MAX_Y)
        self.send(f"G1 X{x:.2f} Y{y:.2f} F{speed}")
        dist = ((x - self.x) ** 2 + (y - self.y) ** 2) ** 0.5
        time.sleep(dist / speed * 60 + 0.3)  # wait until the move has finished
        self.x, self.y = x, y

    def close(self):
        self.s.close()


if __name__ == "__main__":
    # Self-test: trace the safe box. Park at the left-back corner first!
    p = Plotter()
    for pt in [(MAX_X, 0), (MAX_X, MAX_Y), (0, MAX_Y), (0, 0)]:
        p.goto(*pt)
    p.close()