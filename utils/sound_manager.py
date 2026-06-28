# -*- coding: utf-8 -*-
"""音效管理器"""

import pygame
from config.settings import BGM_VOLUME, SFX_VOLUME


class SoundManager:
    def __init__(self):
        pygame.mixer.init()
        self.bgm_volume = BGM_VOLUME
        self.sfx_volume = SFX_VOLUME
        self.current_bgm = None
        self.sounds = {}

    def load_sound(self, name, path):
        self.sounds[name] = pygame.mixer.Sound(path)
        self.sounds[name].set_volume(self.sfx_volume)

    def play_bgm(self, path, loops=-1):
        if self.current_bgm != path:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self.bgm_volume)
            pygame.mixer.music.play(loops)
            self.current_bgm = path

    def stop_bgm(self):
        pygame.mixer.music.stop()
        self.current_bgm = None

    def play_sfx(self, name):
        if name in self.sounds:
            self.sounds[name].play()

    def set_bgm_volume(self, vol):
        self.bgm_volume = vol
        pygame.mixer.music.set_volume(vol)

    def set_sfx_volume(self, vol):
        self.sfx_volume = vol
        for s in self.sounds.values():
            s.set_volume(vol)
