"""
Minimal interactive 2D black hole simulation.

Controls:
 - Left click: add a particle at mouse with approximate tangential velocity for orbit
 - Right click: add particle with small random velocity
 - Up / Down: increase / decrease BH mass
 - Space: pause / resume
 - C: clear particles
 - R: spawn a random cloud
 - Esc / Close window: quit
Notes:
 - Units are arbitrary and scaled for visualization. Schwarzschild radius r_s = 2 * M (G=c=1).
"""

import math
import random
import sys
try:
    import pygame
except Exception:
    print("pygame is required to run this simulation. Install with: pip install pygame")
    sys.exit(1)

# Constants and configuration
WIDTH, HEIGHT = 1000, 700
BG_COLOR = (10, 12, 20)
PARTICLE_COLOR = (200, 220, 255)
TRAIL_COLOR = (120, 160, 255)
FPS = 60

G = 10.0  # gravitational constant in simulation units

# Particle class
class Particle:
    def __init__(self, x, y, vx=0.0, vy=0.0, color=PARTICLE_COLOR):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.trail = []

    def pos(self):
        return (self.x, self.y)

# Simulation class
class BlackHoleSim:
    def __init__(self, width=WIDTH, height=HEIGHT):
        pygame.init()
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Black Hole Simulation")
        self.clock = pygame.time.Clock()
        self.width = width
        self.height = height

        # Black hole parameters (adjustable)
        self.M = 40.0  # mass
        # With G=c=1, Schwarzschild radius r_s = 2*M
        self.scale = 1.0  # world units == pixels (for now 1:1)

        self.particles = []
        self.running = True
        self.paused = False
        # timing: use base_dt and a speed multiplier to allow speeding up / down
        self.base_dt = 1.0 / FPS
        self.speed_mult = 1.0
        self.dt = self.base_dt * self.speed_mult
        self.trail_length = 30

        # interactivity state
        self.dragging = False
        self.drag_start = None
        self.drag_button = None
        self.show_trails = True

    def schwarzschild_radius(self):
        # r_s = 2GM / c^2 ; with G=c=1 => 2*M
        return 2.0 * self.M

    def center(self):
        return (self.width / 2.0, self.height / 2.0)

    def world_offset(self):
        # Black hole at center
        return self.center()

    def add_particle(self, x, y, vx=0.0, vy=0.0):
        p = Particle(x, y, vx, vy)
        self.particles.append(p)

    def spawn_random_cloud(self, n=120, radius_min=120, radius_max=320):
        cx, cy = self.center()
        for _ in range(n):
            r = random.uniform(radius_min, radius_max)
            theta = random.uniform(0, 2 * math.pi)
            x = cx + r * math.cos(theta)
            y = cy + r * math.sin(theta)
            # approximate circular velocity
            v_circ = math.sqrt(G * self.M / max(r, 1e-3))
            # perpendicular direction
            vx = -v_circ * math.sin(theta) * random.uniform(0.8, 1.2)
            vy = v_circ * math.cos(theta) * random.uniform(0.8, 1.2)
            # small random perturbation
            vx += random.uniform(-0.05, 0.05) * v_circ
            vy += random.uniform(-0.05, 0.05) * v_circ
            self.add_particle(x, y, vx, vy)

    def compute_acceleration(self, px, py):
        cx, cy = self.center()
        dx = px - cx
        dy = py - cy
        r = math.hypot(dx, dy)
        if r == 0:
            return 0.0, 0.0
        # Newtonian gravity with softening to avoid extreme spikes
        soft = 6.0  # softening length in pixels
        denom = (r * r + soft * soft) ** 1.5
        a_mag = -G * self.M / denom * (r if r != 0 else 1.0)
        ax = a_mag * dx
        ay = a_mag * dy
        # Note: a_mag is negative because of the sign; multiply by dx gives inward acceleration
        # But above formula yields small numbers; simpler radial formula:
        # Use radial unit vector and standard formula:
        ax = -G * self.M * dx / denom
        ay = -G * self.M * dy / denom
        return ax, ay

    def step(self):
        # Integrate particles (symplectic Euler)
        remove = []
        r_s = self.schwarzschild_radius()
        cx, cy = self.center()
        for p in self.particles:
            ax, ay = self.compute_acceleration(p.x, p.y)
            # velocity update
            p.vx += ax * self.dt
            p.vy += ay * self.dt
            # position update
            p.x += p.vx * self.dt
            p.y += p.vy * self.dt
            # trail
            p.trail.append((p.x, p.y))
            if len(p.trail) > self.trail_length:
                p.trail.pop(0)
            # Check capture: distance to center <= r_s
            if math.hypot(p.x - cx, p.y - cy) <= r_s:
                remove.append(p)
        for p in remove:
            self.particles.remove(p)

    def draw_hud(self):
        font = pygame.font.SysFont("consolas", 16)
        lines = [
            f"Mass M: {self.M:.1f}   r_s=2M: {self.schwarzschild_radius():.1f} px",
            f"Particles: {len(self.particles)}   dt: {self.dt:.5f}  Speed x{self.speed_mult:.2f}",
            f"Particles: {len(self.particles)}   dt: {self.dt:.5f}",
            "Controls:",
            " LClick: spawn orbit / click-drag: fling | RClick: spawn random / drag: fling",
            " Up/Down: change mass (Shift modifies faster)  |  Space: pause  |  N: step once",
            " [: slow x2   ]: speed x2   |  T: toggle trails  |  C: clear  |  R: random cloud  |  Esc: quit"
        ]
        x, y = 8, 8
        for line in lines:
            surf = font.render(line, True, (220, 220, 220))
            self.screen.blit(surf, (x, y))
            y += 18

    def draw(self):
        self.screen.fill(BG_COLOR)
        cx, cy = self.center()
        r_s = self.schwarzschild_radius()

        # Draw faint accretion disk: simple ring
        disk_inner = int(max(0, r_s * 1.8))
        disk_outer = int(max(disk_inner + 6, r_s * 3.2))
        # radial gradient-ish rings
        for i in range(8):
            color = (30 + i * 8, 20 + i * 6, 40 + i * 6)
            pygame.draw.circle(self.screen, color, (int(cx), int(cy)), disk_outer - i * 3, 1)

        # Event horizon (filled)
        pygame.draw.circle(self.screen, (0, 0, 0), (int(cx), int(cy)), int(max(2, r_s)))
        # horizon border glow
        pygame.draw.circle(self.screen, (120, 20, 20), (int(cx), int(cy)), int(max(2, r_s)) + 3, 2)

        # Draw particles and trails
        for p in self.particles:
            if self.show_trails and len(p.trail) > 1:
                pts = [(int(px), int(py)) for (px, py) in p.trail]
                pygame.draw.lines(self.screen, TRAIL_COLOR, False, pts, 1)
            pygame.draw.circle(self.screen, p.color, (int(p.x), int(p.y)), 2)

        # HUD
        self.draw_hud()

        pygame.display.flip()

    def run(self):
        # initial cloud
        self.spawn_random_cloud(n=80)
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    mods = pygame.key.get_mods()
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_SPACE:
                        self.paused = not self.paused
                    elif event.key == pygame.K_c:
                        self.particles.clear()
                    elif event.key == pygame.K_r:
                        self.spawn_random_cloud(n=60)
                    elif event.key == pygame.K_UP:
                        if mods & pygame.KMOD_SHIFT:
                            self.M *= 1.5
                        else:
                            self.M *= 1.1
                    elif event.key == pygame.K_DOWN:
                        if mods & pygame.KMOD_SHIFT:
                            self.M = max(1.0, self.M / 1.5)
                        else:
                            self.M = max(1.0, self.M * 0.9)
                    elif event.key == pygame.K_RIGHTBRACKET:  # ] speed up
                        self.speed_mult *= 2.0
                        self.dt = self.base_dt * self.speed_mult
                    elif event.key == pygame.K_LEFTBRACKET:   # [ slow down
                        self.speed_mult = max(0.125, self.speed_mult / 2.0)
                        self.dt = self.base_dt * self.speed_mult
                    elif event.key == pygame.K_n:  # single-step when paused
                        if self.paused:
                            self.step()
                    elif event.key == pygame.K_t:  # toggle trails
                        self.show_trails = not self.show_trails
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos
                    self.dragging = True
                    self.drag_start = (mx, my)
                    self.drag_button = event.button
                elif event.type == pygame.MOUSEBUTTONUP:
                    mx, my = event.pos
                    if not self.dragging or self.drag_start is None:
                        continue
                    sx, sy = self.drag_start
                    dx = mx - sx
                    dy = my - sy
                    dist = math.hypot(dx, dy)
                    # treat as drag fling if movement is significant
                    if dist > 6:
                        # fling scale - tweak to taste
                        fling_scale = 0.06
                        vx = dx * fling_scale
                        vy = dy * fling_scale
                        self.add_particle(sx, sy, vx, vy)
                    else:
                        # treat as click - original behaviors
                        if self.drag_button == 1:  # left click: spawn orbital particle
                            cx, cy = self.center()
                            dx_c = sx - cx
                            dy_c = sy - cy
                            r = math.hypot(dx_c, dy_c)
                            if r >= 5:
                                v_circ = math.sqrt(G * self.M / max(r, 1e-3))
                                vx = -v_circ * dy_c / r
                                vy = v_circ * dx_c / r
                                vx *= random.uniform(0.95, 1.05)
                                vy *= random.uniform(0.95, 1.05)
                                self.add_particle(sx, sy, vx, vy)
                        elif self.drag_button == 3:  # right click random velocity
                            vx = random.uniform(-0.6, 0.6)
                            vy = random.uniform(-0.6, 0.6)
                            self.add_particle(sx, sy, vx, vy)
                    # reset dragging state
                    self.dragging = False
                    self.drag_start = None
                    self.drag_button = None

            # update dt in case speed_mult changed elsewhere
            self.dt = self.base_dt * self.speed_mult

            if not self.paused:
                # use fixed dt already tuned to FPS
                self.step()

            self.draw()
            self.clock.tick(FPS)

        pygame.quit()

# Entry point
if __name__ == "__main__":
    sim = BlackHoleSim()
    sim.run()