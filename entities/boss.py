# -*- coding: utf-8 -*-
"""龙 BOSS — 无尽模式中从左侧追击玩家，撞碎障碍物"""

import pygame
from config.settings import BOSS_INITIAL_SPEED, BOSS_SPEED_INCREMENT, TILE_SIZE
from config.path import get_dragon_frames
from utils.animation import Animation


class Boss(pygame.sprite.Sprite):
    def __init__(self, x, ground_y):
        super().__init__()
        frames = get_dragon_frames()
        if not frames:
            # 后备：如果没有龙帧，用一个红色方块代替
            self.image = pygame.Surface((32, 32))
            self.image.fill((200, 50, 50))
            self.anim = None
        else:
            self.anim = Animation(frames, frame_duration=10, loop=True)
            self.image = self.anim.get_current_frame()

        # 碰撞盒取图像下半部分，底部对齐地面
        img_h = self.image.get_height()
        self.rect = pygame.Rect(x, ground_y - img_h // 2,
                                self.image.get_width(), img_h // 2)
        self.facing_right = True
        self.base_speed = BOSS_INITIAL_SPEED
        self.speed = BOSS_INITIAL_SPEED
        self.alive_frames = 0  # 存活帧数，决定速度增长
        self._sfx_callback = None

    def set_sfx_callback(self, cb):
        self._sfx_callback = cb

    def update(self, blocks, particles, target_x=None):
        """每帧移动 + 碰撞检测。target_x 不为 None 时锁定到该位置"""
        self.alive_frames += 1
        self.speed = self.base_speed + self.alive_frames * BOSS_SPEED_INCREMENT

        # 动画
        if self.anim:
            self.anim.update()
            self.image = self.anim.get_current_frame()
            if not self.facing_right:
                self.image = pygame.transform.flip(self.image, True, False)

        # 位置：锁定目标位置，或自主向右移动
        if target_x is not None:
            self.rect.x = target_x
        else:
            self.rect.x += int(self.speed)

        # 碰撞检测：撞到方块 → 方块消失 + 粒子
        for block in list(blocks):
            if block.block_type in ("bg", "wall"):
                continue
            if self.rect.colliderect(block.rect):
                # 粒子爆发（方块中心）
                cx = block.rect.centerx
                cy = block.rect.centery
                particles.emit(cx, cy, count=10)
                # 播放音效
                if self._sfx_callback:
                    self._sfx_callback("soil_break")
                # 移除方块
                blocks.remove(block)

    def draw(self, surface, camera_offset=(0, 0)):
        offset_y = self.image.get_height() // 2
        pos = (self.rect.x - camera_offset[0],
               self.rect.y - offset_y - camera_offset[1])
        surface.blit(self.image, pos)
