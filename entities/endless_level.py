# -*- coding: utf-8 -*-
"""无尽模式地形生成器 — 4 种地形块随机拼合，持续向右延伸
所有模板均为连续地面，无悬崖缺口，通过地面障碍物增加变化"""

import random
import pygame
from config.settings import TILE_SIZE, ENDLESS_CHUNK_WIDTH
from config.path import DIRT_BLOCK, GRASS_BLOCK, BG_BLOCK, H_PLATFORM, KUN_ITEM
from entities.block import Block, MovingPlatform, Item
from entities.bat import Bat

# 每块宽度（像素）
CHUNK_W = ENDLESS_CHUNK_WIDTH * TILE_SIZE  # 320px


class EndlessLevel:
    def __init__(self):
        self.blocks = []
        self.items = []
        self.bats = []
        self.platforms = []
        self.portals = []  # 无尽模式无传送门
        self.spawn1 = (64, 96)
        self.spawn2 = (96, 96)
        self.map_width = CHUNK_W * 3  # 初始3块
        self.map_height = 10 * TILE_SIZE

        self._next_x = 6 * TILE_SIZE  # 紧接出生点地面（tx=0..5）之后
        self._templates = [self._chunk_flat, self._chunk_obstacles,
                           self._chunk_bats, self._chunk_tall]

        # 首个chunk固定为平坦地面，避免开局过于复杂
        self._chunk_flat(self._next_x)
        self._next_x += CHUNK_W
        # 后续2块随机生成
        for _ in range(2):
            self.generate_next_chunk()

        # 出生点下方铺地面
        for tx in range(0, 6):
            self._add_block("solid", tx, 7, GRASS_BLOCK)
        for tx in range(0, 6):
            self._add_block("solid", tx, 8, DIRT_BLOCK)
        for tx in range(0, 6):
            self._add_block("solid", tx, 9, DIRT_BLOCK)

    # ------------------------------------------------------------------
    # 地形块模板（全部连续地面，无悬崖）
    # ------------------------------------------------------------------
    def _chunk_flat(self, base_x):
        """平坦地面 + 散落小型障碍物 + kun + 少量蝙蝠"""
        tx_base = base_x // TILE_SIZE
        chunk_end = tx_base + ENDLESS_CHUNK_WIDTH
        # 连续地面
        for tx in range(tx_base, chunk_end):
            self._add_block("solid", tx, 7, GRASS_BLOCK)
            self._add_block("solid", tx, 8, DIRT_BLOCK)
            self._add_block("solid", tx, 9, DIRT_BLOCK)
        # 散落小型障碍物（1-3个，1~2宽 × 1~2高 dirt 堆）
        for _ in range(random.randint(1, 3)):
            ox = tx_base + random.randint(2, chunk_end - 4)
            ow = random.randint(1, 2)   # 宽度 1-2 格
            oh = random.randint(1, 2)   # 高度 1-2 格
            for dy in range(oh):
                for dx in range(ow):
                    self._add_block("solid", ox + dx, 6 - dy, DIRT_BLOCK)
        # kun 散落在地面
        for tx in range(tx_base + 2, chunk_end, 6):
            self._add_item(tx, 6)
        # 少量蝙蝠
        if random.random() < 0.35:
            bx = base_x + random.randint(80, 280)
            self._add_bat(bx, 96, patrol_range=40)

    def _chunk_obstacles(self, base_x):
        """连续地面 + 中央大型障碍物墙 + 上方平台"""
        tx_base = base_x // TILE_SIZE
        chunk_end = tx_base + ENDLESS_CHUNK_WIDTH
        # 连续地面（无缺口）
        for tx in range(tx_base, chunk_end):
            self._add_block("solid", tx, 7, GRASS_BLOCK)
            self._add_block("solid", tx, 8, DIRT_BLOCK)
            self._add_block("solid", tx, 9, DIRT_BLOCK)
        # 中央障碍物墙（3~4宽 × 2高 dirt）
        wall_start = tx_base + 8
        wall_w = random.randint(3, 4)
        for dy in range(2):
            for dx in range(wall_w):
                self._add_block("solid", wall_start + dx, 6 - dy, DIRT_BLOCK)
        # 障碍物上方平台
        self._add_platform(wall_start, 3, wall_w)
        # 平台上的 kun
        self._add_item(wall_start + wall_w // 2, 2)
        # 地面散落 kun
        for tx in range(tx_base + 1, wall_start, 4):
            self._add_item(tx, 6)
        # 蝙蝠
        if random.random() < 0.5:
            self._add_bat(base_x + 160, 96, patrol_range=48)

    def _chunk_bats(self, base_x):
        """地面 + 多个小障碍物 + 多只蝙蝠 + 平台"""
        tx_base = base_x // TILE_SIZE
        chunk_end = tx_base + ENDLESS_CHUNK_WIDTH
        for tx in range(tx_base, chunk_end):
            self._add_block("solid", tx, 7, GRASS_BLOCK)
            self._add_block("solid", tx, 8, DIRT_BLOCK)
            self._add_block("solid", tx, 9, DIRT_BLOCK)
        # 多个小型地面障碍物（间隔分布）
        for ox in [tx_base + 2, tx_base + 8, tx_base + 16]:
            h = random.randint(1, 2)
            for dy in range(h):
                self._add_block("solid", ox, 6 - dy, DIRT_BLOCK)
                self._add_block("solid", ox + 1, 6 - dy, DIRT_BLOCK)
        # 上方平台
        self._add_platform(tx_base + 3, 4, 2)
        self._add_platform(tx_base + 14, 4, 2)
        # 蝙蝠巡逻
        self._add_bat(base_x + 48, 96, patrol_range=64)
        self._add_bat(base_x + 180, 96, patrol_range=48)
        if random.random() < 0.5:
            self._add_bat(base_x + 240, 96, patrol_range=48)
        # kun
        self._add_item(tx_base + 4, 3)
        self._add_item(tx_base + 15, 3)
        # 地面散落 kun
        for tx in range(tx_base + 5, chunk_end, 5):
            if random.random() < 0.6:
                self._add_item(tx, 6)

    def _chunk_tall(self, base_x):
        """阶梯平台 + 地面障碍物 + kun 在高处"""
        tx_base = base_x // TILE_SIZE
        chunk_end = tx_base + ENDLESS_CHUNK_WIDTH
        for tx in range(tx_base, chunk_end):
            self._add_block("solid", tx, 7, GRASS_BLOCK)
            self._add_block("solid", tx, 8, DIRT_BLOCK)
            self._add_block("solid", tx, 9, DIRT_BLOCK)
        # 地面交错障碍物（1~2高 dirt 柱）
        for ox in [tx_base + 3, tx_base + 8, tx_base + 13]:
            h = random.randint(1, 2)
            for dy in range(h):
                self._add_block("solid", ox, 6 - dy, DIRT_BLOCK)
                self._add_block("solid", ox + 1, 6 - dy, DIRT_BLOCK)
        # 阶梯式平台
        self._add_platform(tx_base + 2, 5, 2)
        self._add_platform(tx_base + 5, 4, 2)
        self._add_platform(tx_base + 8, 3, 3)
        self._add_platform(tx_base + 14, 4, 2)
        # kun 在高层
        self._add_item(tx_base + 3, 4)
        self._add_item(tx_base + 9, 2)
        self._add_item(tx_base + 15, 3)

    # ------------------------------------------------------------------
    # 构建方法
    # ------------------------------------------------------------------
    def _add_block(self, block_type, tx, ty, img):
        x = tx * TILE_SIZE
        y = ty * TILE_SIZE
        block = Block(x, y, img, block_type=block_type)
        self.blocks.append(block)
        if block_type == "platform":
            self.platforms.append(block)

    def _add_platform(self, tx, ty, length):
        for i in range(length):
            self._add_block("platform", tx + i, ty, H_PLATFORM)

    def _add_item(self, tx, ty):
        x = tx * TILE_SIZE
        y = ty * TILE_SIZE
        item_rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
        # 检查是否与已有障碍物方块重叠，重叠则跳过
        for block in self.blocks:
            if block.block_type == "solid" and block.rect.colliderect(item_rect):
                return
        self.items.append(Item(x, y, KUN_ITEM))

    def _add_bat(self, x, y, patrol_range=48):
        self.bats.append(Bat(x, y, patrol_range=patrol_range))

    # ------------------------------------------------------------------
    # 地形生成 & 清理
    # ------------------------------------------------------------------
    def generate_next_chunk(self):
        """在 map 末尾随机生成一块地形"""
        template = random.choice(self._templates)
        template(self._next_x)
        self._next_x += CHUNK_W
        self.map_width = self._next_x

    def ensure_chunks_ahead(self, camera_right):
        """确保相机右侧有足够地形"""
        while self._next_x < camera_right + CHUNK_W * 2:
            self.generate_next_chunk()

    def prune_behind(self, cutoff_x):
        """移除左侧远落后于相机的方块/道具/蝙蝠（释放内存）"""
        margin = CHUNK_W * 2
        self.blocks = [b for b in self.blocks
                       if b.rect.right > cutoff_x - margin or b.block_type == "wall"]
        self.platforms = [b for b in self.platforms
                          if b.rect.right > cutoff_x - margin]
        self.items = [i for i in self.items
                      if i.rect.right > cutoff_x - margin]
        self.bats = [b for b in self.bats
                     if b.rect.right > cutoff_x - margin]

    def update(self):
        for b in self.bats:
            b.update()
        # 移动平台更新（目前无尽地形无移动平台，但保持兼容）
        for p in self.platforms:
            if hasattr(p, 'update'):
                p.update()

    def draw(self, surface, camera_offset):
        ox, oy = camera_offset
        for block in self.blocks:
            if block.block_type == "wall":
                continue
            surface.blit(block.image, (block.rect.x - ox, block.rect.y - oy))
        for item in self.items:
            if not item.collected:
                surface.blit(item.image, (item.rect.x - ox, item.rect.y - oy))
        for bat in self.bats:
            bat.draw(surface, camera_offset)

    def get_collected_count(self):
        return sum(1 for i in self.items if i.collected)

    def get_total_items(self):
        return len(self.items)
