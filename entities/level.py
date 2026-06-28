# -*- coding: utf-8 -*-
"""关卡地图加载与生成（采用 objects/layers/entities 结构）"""

import json
import os
import pygame
from config.settings import TILE_SIZE
from config.path import DIRT_BLOCK, GRASS_BLOCK, BG_BLOCK, H_PLATFORM, V_PLATFORM, KUN_ITEM, PORTAL, DATA_DIR
from entities.block import Block, MovingPlatform, Item, Portal
from entities.bat import Bat


class Level:
    def __init__(self):
        self.blocks = []
        self.items = []
        self.portals = []
        self.platforms = []
        self.bats = []
        self.spawn1 = (2 * TILE_SIZE, 8 * TILE_SIZE)
        self.spawn2 = (5 * TILE_SIZE, 8 * TILE_SIZE)
        self.map_width = 0
        # 默认 10 行高 = 160 像素（×SCALE=4 后 = 640 像素 = 窗口高度）
        self.map_height = 10 * TILE_SIZE

    def add_block(self, x, y, img=DIRT_BLOCK, block_type="solid"):
        b = Block(x, y, img, block_type)
        self.blocks.append(b)
        if block_type == "platform":
            self.platforms.append(b)
        return b

    def add_moving_platform(self, x, y, img, move_range, axis="x", speed=1):
        mp = MovingPlatform(x, y, img, move_range, axis, speed)
        self.blocks.append(mp)
        self.platforms.append(mp)
        return mp

    def add_bat(self, x, y, patrol_range=48, speed=1.5):
        b = Bat(x, y, patrol_range, speed)
        self.bats.append(b)
        return b

    def update(self):
        for p in self.platforms:
            p.update()
        for b in self.bats:
            b.update()

    def draw(self, surface, camera_offset):
        for block in self.blocks:
            if block.block_type == "wall":
                continue
            block.draw(surface, camera_offset)
        for item in self.items:
            item.draw(surface, camera_offset)
        for portal in self.portals:
            portal.draw(surface, camera_offset)
        for bat in self.bats:
            bat.draw(surface, camera_offset)

    def get_collected_count(self):
        return sum(1 for item in self.items if item.collected)

    def get_total_items(self):
        return len(self.items)

    def is_all_portal(self):
        return all(p.is_both_inside() for p in self.portals)


def _pos(p):
    return p[0] * TILE_SIZE, p[1] * TILE_SIZE


def _build_ground_layer(lv, layer):
    """layers.ground: {x:[x0,x1], y:[y0,y1]} 范围内的方格全部用 DIRT_BLOCK"""
    if "x" not in layer or "y" not in layer:
        return
    x0, x1 = layer["x"]
    y0, y1 = layer["y"]
    for x in range(x0, x1):
        for y in range(y0, y1):
            lv.add_block(x * TILE_SIZE, y * TILE_SIZE, DIRT_BLOCK, "solid")


def _build_objects(lv, objects):
    # 草方块装饰（地表散点）
    for pos in objects.get("ground", []):
        x, y = _pos(pos)
        lv.add_block(x, y, GRASS_BLOCK, "solid")
    # 水平平台：[[x, y, length?], ...]
    for plat in objects.get("platform", []):
        x, y = plat[0], plat[1]
        length = plat[2] if len(plat) > 2 else 1
        for i in range(length):
            lv.add_block((x + i) * TILE_SIZE, y * TILE_SIZE, H_PLATFORM, "platform")
    # 竖直平台
    for plat in objects.get("vplatform", []):
        x, y = plat[0], plat[1]
        length = plat[2] if len(plat) > 2 else 1
        for i in range(length):
            lv.add_block(x * TILE_SIZE, (y + i) * TILE_SIZE, V_PLATFORM, "platform")
    # 背景块（被凿空的山洞，不阻挡）
    for pos in objects.get("bg", []):
        x, y = _pos(pos)
        lv.add_block(x, y, BG_BLOCK, "bg")
    # 移动平台：[[x, y, length, axis, move_range, speed?], ...]
    for mp in objects.get("moving_platform", []):
        x, y = mp[0], mp[1]
        length = mp[2] if len(mp) > 2 else 1
        axis = mp[3] if len(mp) > 3 else "x"
        move_range = mp[4] if len(mp) > 4 else 48
        speed = mp[5] if len(mp) > 5 else 1
        for i in range(length):
            lv.add_moving_platform((x + i) * TILE_SIZE, y * TILE_SIZE,
                                   H_PLATFORM, move_range, axis, speed)


def _build_entities(lv, entities):
    for pos in entities.get("kun", []):
        x, y = _pos(pos)
        lv.items.append(Item(x, y, KUN_ITEM))
    for pos in entities.get("portal", []):
        x, y = _pos(pos)
        lv.portals.append(Portal(x, y, PORTAL))
    # 蝙蝠：[[x, y, patrol_range?, speed?], ...]
    for bat_data in entities.get("bats", []):
        x, y = _pos(bat_data[:2])
        patrol_range = bat_data[2] if len(bat_data) > 2 else 48
        speed = bat_data[3] if len(bat_data) > 3 else 1.5
        lv.add_bat(x, y, patrol_range, speed)


def _apply_grass_tops(lv):
    """将所有顶部暴露的 solid 方块自动替换为草方块"""
    # 收集所有 solid 方块位置
    solid_positions = set()
    for block in lv.blocks:
        if block.block_type == "solid":
            solid_positions.add((block.rect.x, block.rect.y))
    # 顶部暴露 → 换成草方块
    for block in lv.blocks:
        if block.block_type == "solid":
            above = (block.rect.x, block.rect.y - TILE_SIZE)
            if above not in solid_positions:
                block.image = pygame.image.load(GRASS_BLOCK).convert_alpha()


def load_level_from_json(name):
    """从 config/data/*.json 读取关卡，结构：{id, length, level:{objects,layers,entities}}"""
    path = os.path.join(DATA_DIR, name)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    lv = Level()
    length = data.get("length", 60)
    lv.map_width = length * TILE_SIZE

    if "spawn1" in data:
        lv.spawn1 = _pos(data["spawn1"])
    if "spawn2" in data:
        lv.spawn2 = _pos(data["spawn2"])

    body = data.get("level", {})
    _build_ground_layer(lv, body.get("layers", {}).get("ground", {}))
    _build_objects(lv, body.get("objects", {}))
    _build_entities(lv, body.get("entities", {}))
    # 自动将顶部暴露的 solid 方块替换为草方块
    _apply_grass_tops(lv)

    # 若未在 entities.portal 显式声明，则在关卡末端自动放一个传送门
    if not lv.portals:
        portal_x = (length - 2) * TILE_SIZE
        portal_y = 9 * TILE_SIZE
        lv.portals.append(Portal(portal_x, portal_y, PORTAL))

    # 左右边界空气墙（不可见的碰撞体，防止角色走出地图）
    for row_y in range(0, lv.map_height // TILE_SIZE + 1):
        lv.add_block(0, row_y * TILE_SIZE, DIRT_BLOCK, "wall")
        lv.add_block(lv.map_width - TILE_SIZE, row_y * TILE_SIZE, DIRT_BLOCK, "wall")

    return lv