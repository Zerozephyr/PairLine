# -*- coding: utf-8 -*-
"""视差滚动背景系统（4层）"""

import math
import pygame
from config.settings import LOGICAL_W, LOGICAL_H


CLOUD_SWAY_AMPLITUDE = 10.0
CLOUD_SWAY_SPEED = 1.5

def _fit_to_h(img, target_h):
    """等比缩放到目标高度"""
    w, h = img.get_size()
    if h == target_h:
        return img
    new_w = round(w * target_h / h)
    return pygame.transform.scale(img, (new_w, target_h))


class ParallaxBackground:
    def __init__(self, sky_path, cloud_path, far_mountain_path, near_mountain_path):
        sky = pygame.image.load(sky_path).convert()
        cloud = pygame.image.load(cloud_path).convert_alpha()
        far_mountain = pygame.image.load(far_mountain_path).convert_alpha()
        near_mountain = pygame.image.load(near_mountain_path).convert_alpha()

        self.sky = _fit_to_h(sky, LOGICAL_H)
        self.cloud = _fit_to_h(cloud, LOGICAL_H)
        self.far_mountain = _fit_to_h(far_mountain, LOGICAL_H)
        self.near_mountain = _fit_to_h(near_mountain, LOGICAL_H)

        self.speeds = {"cloud": 0.1, "far": 0.3, "near": 0.6}
        self.offsets = {"cloud": 0, "far": 0, "near": 0}

    def update(self, camera_x):
        sway = math.sin(pygame.time.get_ticks() / 1000.0 * CLOUD_SWAY_SPEED) * CLOUD_SWAY_AMPLITUDE
        self.offsets["cloud"] = -camera_x * self.speeds["cloud"] + sway
        self.offsets["far"] = -camera_x * self.speeds["far"]
        self.offsets["near"] = -camera_x * self.speeds["near"]

    def _draw_layer(self, surface, img, offset_x, y_pos=0):
        w = img.get_width()
        start_x = offset_x % w - w
        while start_x < LOGICAL_W:
            surface.blit(img, (start_x, y_pos))
            start_x += w

    def draw(self, surface):
        surface.blit(self.sky, (0, 0))
        self._draw_layer(surface, self.cloud, self.offsets["cloud"], 0)
        self._draw_layer(surface, self.far_mountain, self.offsets["far"], 0)
        self._draw_layer(surface, self.near_mountain, self.offsets["near"], 0)
