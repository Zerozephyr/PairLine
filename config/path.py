# -*- coding: utf-8 -*-
"""统一路径管理：图片/字体/音效/json配置路径，避免硬编码"""

import os
import sys

# 支持 PyInstaller 打包后的路径解析
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STATIC_DIR = os.path.join(BASE_DIR, "static")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
DATA_DIR = os.path.join(CONFIG_DIR, "data")

# 图片
IMG_DIR = os.path.join(STATIC_DIR, "img")

# 方块
BLOCK_DIR = os.path.join(IMG_DIR, "Block")
DIRT_BLOCK = os.path.join(BLOCK_DIR, "dirt_block.png")
GRASS_BLOCK = os.path.join(BLOCK_DIR, "grass_block.png")
BG_BLOCK = os.path.join(BLOCK_DIR, "background_block.png")
H_PLATFORM = os.path.join(BLOCK_DIR, "horizontal_platform.png")
V_PLATFORM = os.path.join(BLOCK_DIR, "vertical_platform.png")
KUN_ITEM = os.path.join(BLOCK_DIR, "kun.png")
PORTAL = os.path.join(BLOCK_DIR, "portal.png")

# 背景
BG_DIR = os.path.join(IMG_DIR, "Background")
SKY_IMG = os.path.join(BG_DIR, "sky.png")
CLOUD_IMG = os.path.join(BG_DIR, "cloud.png")
FAR_MOUNTAIN_IMG = os.path.join(BG_DIR, "far_mountain.png")
NEAR_MOUNTAIN_IMG = os.path.join(BG_DIR, "near_mountain.png")
HOME_BG_GIF = os.path.join(BG_DIR, "home_background.gif")

# 玩家
PLAYER_DIR = os.path.join(IMG_DIR, "Player")
P1_DIR = os.path.join(PLAYER_DIR, "p1")
P2_DIR = os.path.join(PLAYER_DIR, "p2")

def get_player_frames(p_dir, action):
    """获取某角色某动作的所有帧路径，按数字排序"""
    frames = []
    prefix = os.path.basename(p_dir)
    for f in sorted(os.listdir(p_dir)):
        if f.startswith(f"{prefix}_{action}_") and f.endswith(".png"):
            frames.append(os.path.join(p_dir, f))
    return frames

# 怪物
MASTER_DIR = os.path.join(IMG_DIR, "Master")
BAT_DIR = os.path.join(MASTER_DIR, "bat")

def get_bat_frames():
    """获取蝙蝠飞行动画所有帧路径"""
    frames = []
    for f in sorted(os.listdir(BAT_DIR)):
        if f.startswith("bat_fly_") and f.endswith(".png"):
            frames.append(os.path.join(BAT_DIR, f))
    return frames

# 龙 BOSS
DRAGON_DIR = os.path.join(MASTER_DIR, "dragon")

def get_dragon_frames():
    """获取龙 BOSS 行走动画所有帧路径"""
    frames = []
    for f in sorted(os.listdir(DRAGON_DIR)):
        if f.startswith("dragon_walk_") and f.endswith(".png"):
            frames.append(os.path.join(DRAGON_DIR, f))
    return frames



# UI
UI_DIR = os.path.join(IMG_DIR, "UI")
P1_ARROW = os.path.join(UI_DIR, "p1_arrow.png")
P2_ARROW = os.path.join(UI_DIR, "p2_arrow.png")
SELECT_ARROW = os.path.join(UI_DIR, "select_arrow.png")
HEART_FULL = os.path.join(UI_DIR, "heart_full.png")
HEART_EMPTY = os.path.join(UI_DIR, "heart_empty.png")
P1_HP = os.path.join(UI_DIR, "p1_hp.png")
P2_HP = os.path.join(UI_DIR, "p2_hp.png")

# 图标
ICON_PATH = os.path.join(BASE_DIR, "PairLine.ico")

# 字体
FONT_DIR = os.path.join(STATIC_DIR, "font")
FONT_PATH = os.path.join(FONT_DIR, "WenQuanYi Bitmap Song 16px.ttf")

# 音效
SOUND_DIR = os.path.join(STATIC_DIR, "sound")
HOME_BGM = os.path.join(SOUND_DIR, "home_BGM.MP3")
NORMAL_BGM = os.path.join(SOUND_DIR, "normal_level_BGM.MP3")
ENDLESS_BGM = os.path.join(SOUND_DIR, "endless_level_BGM.MP3")
JUMP_SOUND = os.path.join(SOUND_DIR, "jump.MP3")
GRAB1_SOUND = os.path.join(SOUND_DIR, "grab1.MP3")
GRAB2_SOUND = os.path.join(SOUND_DIR, "grab2.MP3")
SOIL_BREAK_SOUND = os.path.join(SOUND_DIR, "soil_break.mp3")
DRAGON_ROAR_SOUND = os.path.join(SOUND_DIR, "dragon_roar.wav")

# JSON
def data_file(name):
    return os.path.join(DATA_DIR, name)
