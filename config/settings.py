# -*- coding: utf-8 -*-
"""全局常量：帧率、窗口尺寸、物理参数、音效音量等"""

import pygame

# 窗口
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 640
FPS = 60

# 渲染全局缩放倍数
SCALE = 4
LOGICAL_W = SCREEN_WIDTH // SCALE
LOGICAL_H = SCREEN_HEIGHT // SCALE

# 瓦片
TILE_SIZE = 16

# 物理
GRAVITY = 0.8
FRICTION = 0.85
JUMP_STRENGTH = -9
MOVE_SPEED = 2.5
MAX_FALL_SPEED = 12

# 绳索
ROPE_LENGTH = 60
ROPE_STIFFNESS = 0.5
ROPE_DAMPING = 0.85

# 音量
BGM_VOLUME = 0.5
SFX_VOLUME = 0.7

# 颜色
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
TRANSPARENT = (0, 0, 0, 0)

# 网络联机
SERVER_URL = "http://YourIP:5122"
SYNC_INTERVAL = 3       # 每隔几帧发送一次 player_state（60/3 = 20Hz）
PING_INTERVAL = 30      # 每隔几帧发送一次 ping（60/30 = 2Hz）

# 无尽模式
ENDLESS_SCROLL_SPEED = 1.2      # 初始自动滚屏速度 (px/帧)
ENDLESS_SPEED_INCREMENT = 0     # 滚屏速度恒定，不随时间加快
ENDLESS_CHUNK_WIDTH = 20        # 每个地形块宽度(tiles)
ENDLESS_CHASE_DISTANCE = 120    # 落后相机多少像素即死
BOSS_INITIAL_SPEED = 1.2        # BOSS 初始速度（需 > ENDLESS_SCROLL_SPEED）
BOSS_SPEED_INCREMENT = 0        # BOSS 速度恒定，不随时间加快
BOSS_DAMAGE = 1                 # BOSS 碰触玩家伤害

# 按键配置
P1_KEYS = {
    "left": pygame.K_a,
    "right": pygame.K_d,
    "jump": pygame.K_w,
    "grab": pygame.K_s,
}

P2_KEYS = {
    "left": pygame.K_LEFT,
    "right": pygame.K_RIGHT,
    "jump": pygame.K_UP,
    "grab": pygame.K_DOWN,
}
