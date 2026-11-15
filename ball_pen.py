import tkinter as tk
from tkinter import messagebox
import math
import time

# Optional libraries used only for MP4 recording.
try:
    import cv2
    import numpy as np
    from PIL import ImageGrab
    RECORDING_AVAILABLE = True
except ImportError:
    RECORDING_AVAILABLE = False

# ---------------- SETTINGS ----------------
W, H = 1280, 720
CONTROL_H = 65
FPS = 30
DURATION = 30

INK = (28, 63, 170)
INK2 = (109, 140, 240)
BG = "#eef2f7"

TH = 0.95
PX0, PX1, PY = 740, 1190, 620
LC = (205, 300)
LR = 190

def rgb(color):
    return "#%02x%02x%02x" % color

def clamp(v, a, b):
    return max(a, min(b, v))

def seg(t, a, b):
    return clamp((t - a) / (b - a), 0, 1)

def ease(t):
    return t * t * (3 - 2 * t)

def path_pt(u):
    return (
        PX0 + (PX1 - PX0) * u,
        PY + 26 * math.sin(u * 14) + 10 * math.sin(u * 31)
    )

def rotated_point(x, y, ox, oy, angle):
    cs, sn = math.cos(angle), math.sin(angle)
    return (ox + x * cs - y * sn, oy + x * sn + y * cs)

class BallPenAnimation:
    def __init__(self, root):
        self.root = root
        root.title("How a Ball Pen Works")
        root.resizable(False, False)

        self.canvas = tk.Canvas(
            root, width=W, height=H + CONTROL_H,
            bg=BG, highlightthickness=0
        )
        self.canvas.pack()

        self.paused = False
        self.recording = False
        self.video = None
        self.start_time = time.perf_counter()
        self.elapsed_offset = 0.0
        self.last_frame_time = 0.0

        self.draw(0)
        self.draw_controls()
        self.update()

        root.protocol("WM_DELETE_WINDOW", self.close)

    def text(self, s, x, y, color="#1d2733", size=18,
             bold=False, center=False):
        self.canvas.create_text(
            x, y, text=s, fill=color,
            font=("Arial", size, "bold" if bold else "normal"),
            anchor="center" if center else "nw"
        )

    def rounded_rect(self, x1, y1, x2, y2, fill,
                     outline="", radius=8, width=1):
        # Smooth rounded rectangle using a polygon with curved corners.
        r = min(radius, (x2 - x1) / 2, (y2 - y1) / 2)
        points = [
            x1+r, y1, x2-r, y1, x2, y1, x2, y1+r,
            x2, y2-r, x2, y2, x2-r, y2,
            x1+r, y2, x1, y2, x1, y2-r,
            x1, y1+r, x1, y1
        ]
        self.canvas.create_polygon(
            points, fill=fill, outline=outline, width=width,
            smooth=True
        )

    def pen_rect(self, x, y, w, h, radius, color, tipx, tipy):
        points = [
            rotated_point(a, b, tipx, tipy, TH)
            for a, b in [(x, y), (x+w, y), (x+w, y+h), (x, y+h)]
        ]
        flat = [v for point in points for v in point]
        self.canvas.create_polygon(flat, fill=rgb(color), outline=rgb(color))
        if radius:
            for px, py in points:
                self.canvas.create_oval(
                    px-radius, py-radius, px+radius, py+radius,
                    fill=rgb(color), outline=rgb(color)
                )

    def draw_pen(self, t, tipx, tipy, lvl, flow, writing):
        # Outer transparent barrel
        self.pen_rect(-520, -19, 448, 38, 12,
                      (205, 224, 242), tipx, tipy)

        points = [
            rotated_point(x, y, tipx, tipy, TH)
            for x, y in [(-520, -19), (-72, -19), (-72, 19), (-520, 19)]
        ]
        self.canvas.create_polygon(
            [v for p in points for v in p],
            fill="", outline="#6b7f95", width=2
        )

        self.pen_rect(-548, -21, 30, 42, 8,
                      (52, 73, 94), tipx, tipy)
        self.pen_rect(-470, -29, 130, 8, 4,
                      (52, 73, 94), tipx, tipy)
        self.pen_rect(-500, -8, 428, 16, 8,
                      (255, 255, 255), tipx, tipy)

        x0 = -72 - lvl * 428
        self.pen_rect(x0, -7, -72-x0, 14, 0, INK, tipx, tipy)
        self.pen_rect(x0-6, -7, 6, 14, 0,
                      (139, 151, 163), tipx, tipy)

        if writing:
            for i in range(16):
                p = (i / 16 + flow) % 1
                x = x0 + p * (-72 - x0)
                y = math.sin(i * 2.7) * 4
                px, py = rotated_point(x, y, tipx, tipy, TH)
                self.canvas.create_oval(
                    px-2, py-2, px+2, py+2,
                    fill=rgb(INK2), outline=""
                )

        metal = [
            rotated_point(x, y, tipx, tipy, TH)
            for x, y in [(-74, -19), (-74, 19), (-4, 5), (-4, -5)]
        ]
        self.canvas.create_polygon(
            [v for p in metal for v in p],
            fill="#8f9aa6", outline="#8f9aa6"
        )

        bx, by = rotated_point(0, 0, tipx, tipy, TH)
        self.canvas.create_oval(
            bx-5, by-5, bx+5, by+5,
            fill="#c4ccd4", outline="#707b86"
        )

    def draw_magnifier(self, t, phi, flow, writing):
        cx, cy = LC

        self.canvas.create_oval(
            cx-LR, cy-LR, cx+LR, cy+LR,
            fill="#f9fbfd", outline=""
        )
        self.canvas.create_rectangle(
            cx-LR, cy+112, cx+LR, cy+232,
            fill="#fffdf3", outline=""
        )

        for i in range(14):
            x = ((i*53 - phi*46) % 400 + 400) % 400 - 200
            y = 126 + (i % 4) * 14
            self.canvas.create_line(
                cx+x, cy+y, cx+x+14, cy+y,
                fill="#d9d2bd", width=2
            )

        if t > 9.2:
            self.canvas.create_rectangle(
                cx-LR, cy+107, cx, cy+112,
                fill=rgb(INK), outline=""
            )

        chamber = [
            (cx-54, cy-190), (cx+54, cy-190),
            (cx+54, cy+50), (cx+36, cy+96),
            (cx-36, cy+96), (cx-54, cy+50)
        ]
        self.canvas.create_polygon(
            [v for p in chamber for v in p],
            fill=rgb(INK), outline=rgb(INK)
        )

        if writing:
            for i in range(12):
                x = ((i*47) % 84) - 42
                y = ((i*61 + flow*160) % 215) - 190
                self.canvas.create_oval(
                    cx+x-3, cy+y-3, cx+x+3, cy+y+3,
                    fill=rgb(INK2), outline=""
                )

        for s in [-1, 1]:
            self.canvas.create_line(
                cx+s*70, cy-200, cx+s*62, cy+60,
                cx+s*33, cy+103,
                fill="#8d98a5", width=18, smooth=True
            )

        self.canvas.create_oval(
            cx-46, cy+20, cx+46, cy+112,
            fill="#5d6975", outline="#5d6975"
        )
        self.canvas.create_oval(
            cx-40, cy+26, cx+30, cy+96,
            fill="#a9b4c0", outline="#a9b4c0"
        )
        self.canvas.create_oval(
            cx-29, cy+36, cx-1, cy+64,
            fill="white", outline="white"
        )

        if t > 9:
            self.canvas.create_arc(
                cx-48, cy+18, cx+48, cy+114,
                start=200, extent=105, style="arc",
                outline=rgb(INK), width=4
            )

        for k in range(5):
            a = phi + k * 1.2566
            x = cx + 30 * math.cos(a)
            y = cy + 66 + 30 * math.sin(a)
            self.canvas.create_oval(
                x-4, y-4, x+4, y+4,
                fill="#44505c", outline=""
            )

        self.canvas.create_arc(
            cx-62, cy+4, cx+62, cy+128,
            start=20, extent=65, style="arc",
            outline="#d6336c", width=3
        )

        self.text("Ink", cx, cy-130, "white", 20, True, True)
        self.text("Steel ball", cx+72, cy+34, size=17, bold=True)
        self.text("Metal socket", cx-160, cy-95, size=15, bold=True)
        self.text("ball spins", cx+74, cy+6, "#d6336c", 15, True)
        self.canvas.create_line(
            cx-20, cy+132, cx-104, cy+132,
            fill="#d6336c", width=3
        )
        self.text(
            "paper drags the ball", cx-102, cy+152,
            "#d6336c", 13, True
        )
        self.canvas.create_oval(
            cx-LR, cy-LR, cx+LR, cy+LR,
            fill="", outline="#44566c", width=6
        )

    def draw(self, t):
        c = self.canvas
        c.delete("scene")
        c.delete("all")
        c.configure(bg=BG)

        lift = 1 - ease(seg(t, 6, 9)) + ease(seg(t, 25, 28))
        u = seg(t, 9, 25)
        writing = 9 < t < 25
        drawn_to = 0 if t < 9 else (u if t < 25 else 1)

        px, py = path_pt(u)
        tipx, tipy = px + lift*60, py - lift*110
        phi, flow = u*38, u*6
        lvl = 0.92 if t < 0.3 else 0.92 - 0.14*drawn_to
        magnifier_alpha = seg(t, 6.5, 8) * (1-seg(t, 25, 26.5))

        self.rounded_rect(530, 500, 1250, 710, "#d2dae2", radius=10)
        self.rounded_rect(520, 490, 1240, 700, "#fffef9", radius=10)

        for y in range(530, 700, 36):
            c.create_line(520, y, 1240, y, fill="#d7e3f2", width=2)

        if drawn_to > 0:
            pts = [path_pt(drawn_to*i/260) for i in range(261)]
            c.create_line(
                [v for p in pts for v in p],
                fill=rgb(INK), width=4, smooth=True
            )
            wet = 1-seg(t, 25, 29)
            if wet > 0 and t < 29:
                c.create_line(
                    [v for p in pts for v in p],
                    fill="#82a5eb", width=2, smooth=True
                )

        self.draw_pen(t, tipx, tipy, lvl, flow, writing)

        if magnifier_alpha > 0.01:
            self.draw_magnifier(t, phi, flow, writing)

        self.text("How a ball pen works", 30, 30, "#1d2733", 30, True)

        cap = "1 - The parts of a ball pen"
        if 6 <= t < 9:
            cap = "2 - Touch the pen to paper"
        elif 9 <= t < 13:
            cap = "3 - Move the pen: friction makes the ball roll"
        elif 13 <= t < 17:
            cap = "The spinning ball picks up ink from the chamber"
        elif 17 <= t < 21:
            cap = "Gravity and capillary action keep fresh ink flowing"
        elif 21 <= t < 25:
            cap = "The rolling ball presses ink onto the paper"
        elif t >= 25:
            cap = "4 - Lift the pen: ink soaks into the paper and dries"
        self.text(cap, 30, 75, "#34495e", 22)

    def draw_controls(self):
        c = self.canvas
        c.create_rectangle(
            0, H, W, H+CONTROL_H,
            fill="#0d0f14", outline=""
        )

        self.rounded_rect(
            380, H+12, 590, H+54, "#282d37", radius=7
        )
        self.text(
            "Stop Recording" if self.recording else "Record Video",
            485, H+33, "white", 17, True, True
        )

        self.rounded_rect(
            610, H+12, 740, H+54, "#282d37", radius=7
        )
        self.text(
            "Play" if self.paused else "Pause",
            675, H+33, "white", 17, True, True
        )

        status = (
            "Paused" if self.paused else
            "Recording..." if self.recording else
            "Playing (loops)"
        )
        self.text(status, 770, H+33, "#e6e6e6", 16)

    def elapsed(self):
        if self.paused:
            return self.elapsed_offset
        return self.elapsed_offset + time.perf_counter() - self.start_time

    def start_recording(self):
        if not RECORDING_AVAILABLE:
            messagebox.showerror(
                "Recording libraries missing",
                "Animation works without extra libraries.\n\n"
                "To record MP4, install them with:\n"
                "python -m pip install opencv-python numpy pillow"
            )
            return

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.video = cv2.VideoWriter(
            "ball-pen-simulation.mp4", fourcc, FPS, (W, H)
        )
        if not self.video.isOpened():
            self.video = None
            messagebox.showerror(
                "Recording error", "Could not create the MP4 file."
            )
            return

        self.recording = True
        self.paused = False
        self.elapsed_offset = 0.0
        self.start_time = time.perf_counter()

    def stop_recording(self):
        self.recording = False
        if self.video is not None:
            self.video.release()
            self.video = None
            messagebox.showinfo(
                "Video saved",
                "Saved as ball-pen-simulation.mp4 in the project folder."
            )

    def on_click(self, event):
        x, y = event.x, event.y
        if 380 <= x <= 590 and H+12 <= y <= H+54:
            if self.recording:
                self.stop_recording()
            else:
                self.start_recording()
        elif 610 <= x <= 740 and H+12 <= y <= H+54:
            if self.paused:
                self.paused = False
                self.start_time = time.perf_counter()
            else:
                self.paused = True
                self.elapsed_offset = self.elapsed()

    def update(self):
        now = time.perf_counter()
        elapsed = self.elapsed()
        t = min(elapsed, DURATION) if self.recording else elapsed % DURATION

        self.draw(t)
        self.draw_controls()

        if self.recording and self.video is not None:
            try:
                x = self.root.winfo_rootx()
                y = self.root.winfo_rooty()
                shot = ImageGrab.grab(bbox=(x, y, x+W, y+H))
                frame = cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2BGR)
                self.video.write(frame)
            except Exception as exc:
                self.stop_recording()
                messagebox.showerror("Recording error", str(exc))

            if elapsed >= DURATION:
                self.stop_recording()

        self.root.after(int(1000/FPS), self.update)

    def close(self):
        if self.video is not None:
            self.video.release()
            self.video = None
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = BallPenAnimation(root)
    app.canvas.bind("<Button-1>", app.on_click)
    root.mainloop()
