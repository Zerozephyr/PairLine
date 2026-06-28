# -*- coding: utf-8 -*-
"""方块类：泥土、草方块、背景块、平台、道具、传送门"""

import pygame


class Block(pygame.sprite.Sprite):
    def __init__(self, x, y, image_path, block_type="solid"):
        super().__init__()
        self.image = pygame.image.load(image_path).convert_alpha()
        self.rect = self.image.get_rect(topleft=(x, y))
        self.block_type = block_type

    def draw(self, surface, camera_offset=(0, 0)):
        surface.blit(self.image, (self.rect.x - camera_offset[0], self.rect.y - camera_offset[1]))


class MovingPlatform(Block):
    def __init__(self, x, y, image_path, move_range, axis="x", speed=1):
        super().__init__(x, y, image_path, "platform")
        self.start_pos = pygame.math.Vector2(x, y)
        self.move_range = move_range
        self.axis = axis
        self.speed = speed
        self.direction = 1

    def update(self):
        if self.axis == "x":
            self.rect.x += self.speed * self.direction
            if abs(self.rect.x - self.start_pos.x) >= self.move_range:
                self.direction *= -1
        else:
            self.rect.y += self.speed * self.direction
            if abs(self.rect.y - self.start_pos.y) >= self.move_range:
                self.direction *= -1


class Item(pygame.sprite.Sprite):
    def __init__(self, x, y, image_path):
        super().__init__()
        self.image = pygame.image.load(image_path).convert_alpha()
        self.rect = self.image.get_rect(topleft=(x, y))
        self.collected = False

    def draw(self, surface, camera_offset=(0, 0)):
        if not self.collected:
            surface.blit(self.image, (self.rect.x - camera_offset[0], self.rect.y - camera_offset[1]))


class Portal(pygame.sprite.Sprite):
    def __init__(self, x, y, image_path):
        super().__init__()
        self.image = pygame.image.load(image_path).convert_alpha()
        self.rect = self.image.get_rect(topleft=(x, y))
        self.players_inside = {True: False, False: False}

    def is_both_inside(self):
        return all(self.players_inside.values())

    def draw(self, surface, camera_offset=(0, 0)):
        surface.blit(self.image, (self.rect.x - camera_offset[0], self.rect.y - camera_offset[1]))
