# -*- coding: utf-8 -*-
"""游戏内 HUD：血条、道具计数"""

import os
import pygame
from config.settings import LOGICAL_W, SCREEN_WIDTH, SCALE, WHITE
from config.path import HEART_FULL, HEART_EMPTY, KUN_ITEM, P1_HP, P2_HP, FONT_PATH, P1_DIR, P2_DIR


class HUD:
    def __init__(self):
        self.heart_full = pygame.image.load(HEART_FULL).convert_alpha()
        self.heart_empty = pygame.image.load(HEART_EMPTY).convert_alpha()
        self.p1_hp_bg = pygame.image.load(P1_HP).convert_alpha()
        self.p2_hp_bg = pygame.image.load(P2_HP).convert_alpha()
        raw_kun = pygame.image.load(KUN_ITEM).convert_alpha()
        w, h = raw_kun.get_width(), raw_kun.get_height()
        self.kun_img = pygame.transform.scale(raw_kun, (w // 2, h // 2))
        self.font = pygame.font.Font(FONT_PATH, 32)

        # 从角色 idle 帧截取头部作为血条头像
        p1_idle = pygame.image.load(os.path.join(P1_DIR, "p1_idle_01.png")).convert_alpha()
        p2_idle = pygame.image.load(os.path.join(P2_DIR, "p2_idle_01.png")).convert_alpha()
        # P1 精灵可见像素从 y=14 开始，取 16×10 头部区域
        self.p1_head = p1_idle.subsurface((0, 14, 16, 14))
        # P2 精灵可见像素从 y=14 开始，取 16×10 头部区域，翻转使其面向左侧
        p2_head_raw = p2_idle.subsurface((0, 14, 16, 14))
        self.p2_head = pygame.transform.flip(p2_head_raw, True, False)

    def draw_bg(self, canvas, p1_hp, p2_hp, collected, total):
        gap = 2
        # P1 血条背景 + 头像 + 爱心
        canvas.blit(self.p1_hp_bg, (2, 2))
        canvas.blit(self.p1_head, (4, 3))  # 头像在 HP 条左侧
        for i in range(3):
            x = 23 + i * (self.heart_full.get_width() + gap)
            y = 6
            if i < p1_hp:
                canvas.blit(self.heart_full, (x, y))
            else:
                canvas.blit(self.heart_empty, (x, y))

        # P2 血条背景 + 爱心 + 头像
        p2_bg_x = LOGICAL_W - self.p2_hp_bg.get_width() - 2
        canvas.blit(self.p2_hp_bg, (p2_bg_x, 2))
        # 头像在 HP 条右侧，与左侧头像对称
        canvas.blit(self.p2_head, (LOGICAL_W - 2 - 16 - 2, 3))
        for i in range(3):
            x = LOGICAL_W - 23 - (3 - i) * (self.heart_full.get_width() + gap)
            y = 6
            if i < p2_hp:
                canvas.blit(self.heart_full, (x, y))
            else:
                canvas.blit(self.heart_empty, (x, y))

        kun_x = LOGICAL_W // 2 - 20
        kun_y = 4
        canvas.blit(self.kun_img, (kun_x, kun_y))

    def draw_text(self, screen, p1_hp, p2_hp, collected, total):
        kun_x = LOGICAL_W // 2 - 20
        kun_y = 4
        text = self.font.render(f"{collected} / {total}", False, WHITE)
        screen.blit(text, ((kun_x + self.kun_img.get_width() + 2) * SCALE, kun_y * SCALE))
