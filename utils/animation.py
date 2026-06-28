# -*- coding: utf-8 -*-
"""动画加载与播放工具"""

import pygame


class Animation:
    def __init__(self, frame_paths, frame_duration=5, loop=True):
        self.frames = [pygame.image.load(p).convert_alpha() for p in frame_paths]
        self.frame_duration = frame_duration
        self.loop = loop
        self.frame_index = 0
        self.timer = 0
        self.finished = False

    def update(self):
        if self.finished and not self.loop:
            return
        self.timer += 1
        if self.timer >= self.frame_duration:
            self.timer = 0
            self.frame_index += 1
            if self.frame_index >= len(self.frames):
                if self.loop:
                    self.frame_index = 0
                else:
                    self.frame_index = len(self.frames) - 1
                    self.finished = True

    def get_current_frame(self):
        return self.frames[self.frame_index]

    def reset(self):
        self.frame_index = 0
        self.timer = 0
        self.finished = False
