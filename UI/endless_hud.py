# -*- coding: utf-8 -*-
"""无尽模式 HUD — 距离、分数、速度等级、血量"""

import pygame
from config.settings import SCREEN_WIDTH, SCREEN_HEIGHT, SCALE, YELLOW, WHITE, RED, CYAN
from config.path import FONT_PATH


class EndlessHUD:
    def __init__(self):
        self.font = pygame.font.Font(FONT_PATH, 28)
        self.font_big = pygame.font.Font(FONT_PATH, 36)
        self.font_small = pygame.font.Font(FONT_PATH, 22)

    def draw(self, screen, distance, score, kun_count, hp1, hp2, speed_level):
        # 顶部半透明底条
        bar = pygame.Surface((SCREEN_WIDTH, 48), pygame.SRCALPHA)
        bar.fill((0, 0, 0, 120))
        screen.blit(bar, (0, 0))

        # 距离（左上）
        dist_label = self.font.render("距离", False, (180, 180, 180))
        screen.blit(dist_label, (12, 4))
        dist_text = self.font_big.render(f"{int(distance / 10)}m", False, WHITE)
        screen.blit(dist_text, (12, 20))

        # 分数（中上）
        score_text = self.font_big.render(f"得分 {score}", False, YELLOW)
        screen.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, 10))

        # 速度等级（右上）
        speed_text = self.font.render(f"速度 Lv.{speed_level}", False, CYAN)
        screen.blit(speed_text, (SCREEN_WIDTH - speed_text.get_width() - 12, 14))

        # kun 收集（速度下方）
        kun_text = self.font_small.render(f"kun ×{kun_count}", False, YELLOW)
        screen.blit(kun_text, (12, 52))

        # 血量（底部）
        hp1_text = self.font_small.render(f"P1 HP: {hp1}/3", False, WHITE)
        screen.blit(hp1_text, (12, SCREEN_HEIGHT - 28))
        hp2_text = self.font_small.render(f"P2 HP: {hp2}/3", False, WHITE)
        screen.blit(hp2_text, (SCREEN_WIDTH - hp2_text.get_width() - 12, SCREEN_HEIGHT - 28))
