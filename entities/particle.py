# -*- coding: utf-8 -*-
"""粒子系统 — 用于 BOSS 撞碎障碍物时的碎片特效"""

import random
import pygame


class Particle:
    """单个粒子：有初速度、重力、alpha 渐隐"""

    def __init__(self, x, y, vx, vy, lifetime, color, size):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.color = color
        self.size = size

    def update(self):
        self.vy += 0.3  # 重力
        self.x += self.vx
        self.y += self.vy
        self.lifetime -= 1

    def dead(self):
        return self.lifetime <= 0

    def draw(self, surface, offset=(0, 0)):
        alpha = max(0, int(255 * self.lifetime / self.max_lifetime))
        color = (*self.color, alpha)
        px = int(self.x - offset[0])
        py = int(self.y - offset[1])
        s = self.size
        # 用带 alpha 的临时 surface 绘制
        rect_surf = pygame.Surface((s, s), pygame.SRCALPHA)
        rect_surf.fill(color)
        surface.blit(rect_surf, (px, py))


class ParticleSystem:
    """粒子群管理器"""

    # 泥土色系碎片颜色
    EARTH_COLORS = [
        (139, 90, 43),   # 棕色
        (160, 120, 60),  # 浅棕
        (100, 70, 40),   # 深棕
        (180, 150, 100), # 沙色
        (120, 100, 70),  # 灰棕
        (80, 60, 30),    # 暗棕
    ]

    def __init__(self):
        self.particles = []

    def emit(self, x, y, count=12):
        """在 (x, y) 处爆发 count 个碎片"""
        for _ in range(count):
            vx = random.uniform(-4, 4)
            vy = random.uniform(-5, -1)  # 向上飞
            lifetime = random.randint(15, 35)
            color = random.choice(self.EARTH_COLORS)
            size = random.randint(2, 4)
            self.particles.append(Particle(x, y, vx, vy, lifetime, color, size))

    def update(self):
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if not p.dead()]

    def draw(self, surface, offset=(0, 0)):
        for p in self.particles:
            p.draw(surface, offset)
