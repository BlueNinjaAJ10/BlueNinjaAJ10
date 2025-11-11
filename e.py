import sys
import random
import math
import tkinter as tk
from dataclasses import dataclass
import time

#!/usr/bin/env python3
"""
Simple 2D particle simulation with elastic collisions using tkinter.
Save as e.py and run: python e.py [num_particles]

Controls:
 - Space: pause/resume
 - r: reset with same particle count
 - Up/Down: increase/decrease simulation speed
"""


WIDTH, HEIGHT = 800, 600
DEFAULT_N = 1
MIN_RADIUS, MAX_RADIUS = 18, 18
GRAVITY = 200.0  # set small positive like 200 for gravity (px/s^2)
FRICTION = 1.0  # air friction applied to velocities per step


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    r: float
    m: float
    color: str

    def draw(self, canvas):
        canvas.coords(self._id, self.x - self.r, self.y - self.r, self.x + self.r, self.y + self.r)

    def create(self, canvas):
        self._id = canvas.create_oval(self.x - self.r, self.y - self.r, self.x + self.r, self.y + self.r, fill=self.color, outline="")


class Simulation:
    def __init__(self, root, n=DEFAULT_N):
        self.root = root
        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="black")
        self.canvas.pack()
        self.particles = []
        self.running = True
        self.speed = 1.0  # simulation speed multiplier
        self.dt = 0.016  # seconds per frame (approx 60 FPS)
        self._init_particles(n)
        self._bind_keys()
        self.last_time = None
        self._loop()

    def _init_particles(self, n):
        self.canvas.delete("all")
        self.particles = []
        attempts = 0
        while len(self.particles) < n and attempts < n * 200:
            attempts += 1
            r = random.uniform(MIN_RADIUS, MAX_RADIUS)
            x = random.uniform(r, WIDTH - r)
            y = random.uniform(r, HEIGHT - r)
            vx = random.uniform(-150, 150)
            vy = random.uniform(-150, 150)
            color = "#" + "".join(random.choice("89ABCDEF") for _ in range(6))
            p = Particle(x, y, vx, vy, r, r * r, color)
            if not any(self._overlap(p, other) for other in self.particles):
                p.create(self.canvas)
                self.particles.append(p)
        # if not enough placed, just proceed with what we have

    def _overlap(self, a, b):
        dx = a.x - b.x
        dy = a.y - b.y
        return dx * dx + dy * dy < (a.r + b.r) ** 2

    def _bind_keys(self):
        self.root.bind("<space>", lambda e: self._toggle())
        self.root.bind("r", lambda e: self._reset())
        self.root.bind("<Up>", lambda e: self._change_speed(1.1))
        self.root.bind("<Down>", lambda e: self._change_speed(0.9))

    def _toggle(self):
        self.running = not self.running

    def _reset(self):
        n = len(self.particles)
        self._init_particles(n)

    def _change_speed(self, factor):
        self.speed *= factor
        self.speed = max(0.1, min(10.0, self.speed))

    def _loop(self):
        if self.running:
            self._step(self.dt * self.speed)
        self.root.after(int(self.dt * 1000), self._loop)

    def _step(self, dt):
        # integrate velocities/positions
        for p in self.particles:
            p.vy += GRAVITY * dt
            p.vx *= FRICTION
            p.vy *= FRICTION
            p.x += p.vx * dt
            p.y += p.vy * dt
            self._handle_wall_collision(p)
        # handle pairwise collisions
        self._resolve_collisions()
        # redraw
        for p in self.particles:
            p.draw(self.canvas)

    def _handle_wall_collision(self, p):
        if p.x - p.r < 0:
            p.x = p.r
            p.vx = abs(p.vx)
        if p.x + p.r > WIDTH:
            p.x = WIDTH - p.r
            p.vx = -abs(p.vx)
        if p.y - p.r < 0:
            p.y = p.r
            p.vy = abs(p.vy)
        if p.y + p.r > HEIGHT:
            p.y = HEIGHT - p.r
            p.vy = -abs(p.vy)

    def _resolve_collisions(self):
        n = len(self.particles)
        for i in range(n):
            a = self.particles[i]
            for j in range(i + 1, n):
                b = self.particles[j]
                dx = b.x - a.x
                dy = b.y - a.y
                dist2 = dx * dx + dy * dy
                radii = a.r + b.r
                if dist2 <= radii * radii and dist2 > 0:
                    dist = math.sqrt(dist2)
                    # normalize collision vector
                    nx = dx / dist
                    ny = dy / dist
                    # minimum translation distance to avoid overlap
                    overlap = radii - dist
                    # push particles apart proportional to mass
                    total_mass = a.m + b.m
                    a.x -= nx * (overlap * (b.m / total_mass))
                    a.y -= ny * (overlap * (b.m / total_mass))
                    b.x += nx * (overlap * (a.m / total_mass))
                    b.y += ny * (overlap * (a.m / total_mass))
                    # relative velocity
                    rvx = b.vx - a.vx
                    rvy = b.vy - a.vy
                    # velocity along normal
                    vel_along_normal = rvx * nx + rvy * ny
                    if vel_along_normal > 0:
                        continue  # they are separating
                    # restitution (elastic collision)
                    e = 0.95
                    j = -(1 + e) * vel_along_normal
                    j /= (1 / a.m) + (1 / b.m)
                    impulse_x = j * nx
                    impulse_y = j * ny
                    a.vx -= impulse_x / a.m
                    a.vy -= impulse_y / a.m
                    b.vx += impulse_x / b.m
                    b.vy += impulse_y / b.m


if __name__ == "__main__":
    n = DEFAULT_N
    if len(sys.argv) > 1:
        try:
            n = max(1, int(sys.argv[1]))
        except Exception:
            pass
    root = tk.Tk()
    root.title(f"Particle Simulation — {n} particles")
    sim = Simulation(root, n=n)
    # Interactive mouse controls:
    # - Left-click + drag on a particle to pick up and throw it
    # - Left-click on empty space to spawn a particle and drag to position it
    # - Right-click + drag to spawn a particle with initial velocity based on drag
    drag = {"p": None, "last": None, "start": None, "button": None}

    def spawn_particle(x, y, vx=0.0, vy=0.0, r=None):
        r = r if r is not None else random.uniform(MIN_RADIUS, MAX_RADIUS)
        color = "#" + "".join(random.choice("89ABCDEF") for _ in range(6))
        p = Particle(x, y, vx, vy, r, r * r, color)
        p.create(sim.canvas)
        sim.particles.append(p)
        return p

    def find_particle_at(x, y):
        for p in reversed(sim.particles):  # topmost first
            dx = p.x - x
            dy = p.y - y
            if dx * dx + dy * dy <= p.r * p.r:
                return p
        return None

    def on_button_press(event):
        b = event.num
        x, y = event.x, event.y
        drag["button"] = b
        if b == 1:
            p = find_particle_at(x, y)
            if p:
                drag["p"] = p
                drag["last"] = (x, y, time.time())
            else:
                # create and start dragging a new particle
                p = spawn_particle(x, y, 0.0, 0.0)
                drag["p"] = p
                drag["last"] = (x, y, time.time())
            sim.canvas.config(cursor="fleur")
        elif b == 3:
            drag["start"] = (x, y, time.time())

    def on_motion(event):
        if drag["p"] and drag["last"]:
            x, y = event.x, event.y
            last_x, last_y, last_t = drag["last"]
            now = time.time()
            dt = max(1e-4, now - last_t)
            dx = x - last_x
            dy = y - last_y
            p = drag["p"]
            # move particle to mouse and set velocity based on motion
            p.x = x
            p.y = y
            p.vx = dx / dt
            p.vy = dy / dt
            drag["last"] = (x, y, now)

    def on_button_release(event):
        b = event.num
        x, y = event.x, event.y
        if b == 1 and drag["p"]:
            # release — keep velocity computed during drag
            drag["p"] = None
            drag["last"] = None
            sim.canvas.config(cursor="")
        elif b == 3 and drag["start"]:
            sx, sy, st = drag["start"]
            now = time.time()
            dt = max(1e-4, now - st)
            vx = (x - sx) / dt * 0.02  # scale down so velocities aren't huge
            vy = (y - sy) / dt * 0.02
            spawn_particle(sx, sy, vx, vy)
            drag["start"] = None

    # wheel to change global speed
    def on_mouse_wheel(event):
        # Windows uses event.delta, Linux uses Button-4/5; keep simple for Windows/mac
        delta = getattr(event, "delta", 0)
        if delta == 0:
            return
        factor = 1.1 if delta > 0 else 0.9
        sim._change_speed(factor)

    sim.canvas.bind("<ButtonPress-1>", on_button_press)
    sim.canvas.bind("<B1-Motion>", on_motion)
    sim.canvas.bind("<ButtonRelease-1>", on_button_release)
    sim.canvas.bind("<ButtonPress-3>", on_button_press)
    sim.canvas.bind("<ButtonRelease-3>", on_button_release)
    # wheel (Windows/mac)
    sim.canvas.bind("<MouseWheel>", on_mouse_wheel)

    root.mainloop()