# -*- coding: utf-8 -*-
"""计分面板、血量UI、数值渲染"""

import pygame
from config.settings import WHITE, RED, GREEN


class ScorePanel:
    def __init__(self, font_path, size=24):
        self.font = pygame.font.Font(font_path, size)
        self.score = 0
        self.hp = 100
        self.max_hp = 100

    def set_score(self, score):
        self.score = score

    def set_hp(self, hp, max_hp=None):
        self.hp = hp
        if max_hp is not None:
            self.max_hp = max_hp

    def draw(self, surface):
        score_text = self.font.render(f"Score: {self.score}", True, WHITE)
        surface.blit(score_text, (10, 10))
        hp_text = self.font.render(f"HP: {self.hp}/{self.max_hp}", True, WHITE)
        surface.blit(hp_text, (10, 40))
        bar_width = 200
        bar_height = 16
        fill = int(bar_width * (self.hp / self.max_hp))
        pygame.draw.rect(surface, RED, (10, 70, bar_width, bar_height))
        pygame.draw.rect(surface, GREEN, (10, 70, fill, bar_height))
        pygame.draw.rect(surface, WHITE, (10, 70, bar_width, bar_height), 2)
