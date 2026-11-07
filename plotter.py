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
    p = Plotter()
    for pt in [(MAX_X, 0), (MAX_X, MAX_Y), (0, MAX_Y), (0, 0)]:
        p.goto(*pt)
    p.close()