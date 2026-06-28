# -*- coding: utf-8 -*-
"""小怪蝙蝠类：左右巡逻、动画播放、碰撞伤害"""

import pygame
from utils.animation import Animation
from config.path import get_bat_frames


class Bat(pygame.sprite.Sprite):
    def __init__(self, x, y, patrol_range=48, speed=1.5):
        super().__init__()
        frames = get_bat_frames()
        self.anim = Animation(frames, frame_duration=8, loop=True)
        self.image = self.anim.get_current_frame()
        self.rect = self.image.get_rect(topleft=(x, y))
        # 碰撞盒缩小一圈，让视觉上更宽容
        self.hitbox = self.rect.inflate(-4, -4)

        # 巡逻
        self.start_x = x
        self.patrol_range = patrol_range
        self.speed = speed
        self.facing_right = True

    def update(self):
        self.anim.update()
        self.image = self.anim.get_current_frame()
        if not self.facing_right:
            self.image = pygame.transform.flip(self.image, True, False)

        # 左右巡逻
        self.rect.x += int(self.speed * (1 if self.facing_right else -1))
        self.hitbox.center = self.rect.center

        # 到达巡逻边界时折返
        if self.rect.x >= self.start_x + self.patrol_range:
            self.facing_right = False
        elif self.rect.x <= self.start_x - self.patrol_range:
            self.facing_right = True

    def draw(self, surface, camera_offset=(0, 0)):
        pos = (self.rect.x - camera_offset[0], self.rect.y - camera_offset[1])
        surface.blit(self.image, pos)
