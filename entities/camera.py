# -*- coding: utf-8 -*-
"""相机跟随类（场景滚动、视口偏移）"""

import pygame
from config.settings import LOGICAL_W, LOGICAL_H


class Camera:
    def __init__(self, map_width, map_height):
        self.rect = pygame.Rect(0, 0, LOGICAL_W, LOGICAL_H)
        self.map_width = map_width
        self.map_height = map_height
        self.smooth_speed = 0.1

    def update(self, target1, target2):
        mid_x = (target1.centerx + target2.centerx) // 2
        mid_y = (target1.centery + target2.centery) // 2

        target_x = mid_x - LOGICAL_W // 2
        target_y = mid_y - LOGICAL_H // 2

        self.rect.x += int((target_x - self.rect.x) * self.smooth_speed)
        self.rect.y += int((target_y - self.rect.y) * self.smooth_speed)

        self.rect.x = max(0, min(self.rect.x, max(0, self.map_width - LOGICAL_W)))
        self.rect.y = max(0, min(self.rect.y, max(0, self.map_height - LOGICAL_H)))

    def offset(self):
        return (self.rect.x, self.rect.y)
