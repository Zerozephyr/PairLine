# -*- coding: utf-8 -*-
"""软绳物理系统：多节点模拟下垂 + 距离约束 + 颜色反馈"""

import pygame
import math
from config.settings import ROPE_LENGTH, ROPE_STIFFNESS, ROPE_DAMPING


class Rope:
    """
    软绳物理系统，连接两个玩家，带重力下垂效果

    实现原理：
    1. 绳子由多个节点组成，节点之间有距离约束
    2. 中间节点受重力影响自然下垂
    3. 两端固定在玩家中心，平滑跟随玩家移动
    4. 玩家之间通过弹性力相互牵制
    """

    def __init__(self, player1, player2):
        self.p1 = player1
        self.p2 = player2

        # 绳子物理参数
        self.rest_length = ROPE_LENGTH          # 自然长度（像素）
        self.stiffness = ROPE_STIFFNESS         # 弹性系数（越小越软）
        self.damping = ROPE_DAMPING             # 阻尼系数（越大能量损失越快）
        self.gravity = 0.2                      # 节点重力加速度

        # 长度限制
        self.max_length = ROPE_LENGTH * 1.2     # 最大拉伸长度
        self.min_length = 40                    # 最小压缩长度

        # 绳子分段数（越多越平滑，计算量越大）
        self.segments = 10

        # 节点位置 / 速度列表
        self.nodes = []
        self.node_vels = []
        self._init_nodes()

    # ------------------------------------------------------------------
    # 初始化
    # ------------------------------------------------------------------
    def _init_nodes(self):
        """在玩家连线间均匀分布节点，并添加初始下垂效果"""
        pos1 = pygame.math.Vector2(self.p1.rect.centerx, self.p1.rect.centery)
        pos2 = pygame.math.Vector2(self.p2.rect.centerx, self.p2.rect.centery)

        self.nodes = []
        self.node_vels = []

        for i in range(self.segments + 1):
            t = i / self.segments
            base_pos = pos1 + (pos2 - pos1) * t
            # 正弦曲线初始下垂
            sag = math.sin(t * math.pi) * 20
            base_pos.y += sag
            self.nodes.append(base_pos)
            self.node_vels.append(pygame.math.Vector2(0, 0))

    # ------------------------------------------------------------------
    # 每帧更新
    # ------------------------------------------------------------------
    def update(self, blocks=None):
        if self.p1.dead or self.p2.dead:
            return

        target_pos1 = pygame.math.Vector2(self.p1.rect.centerx, self.p1.rect.centery)
        target_pos2 = pygame.math.Vector2(self.p2.rect.centerx, self.p2.rect.centery)

        # 端点直接跟随玩家
        self.nodes[0] = target_pos1
        self.nodes[-1] = target_pos2
        self.node_vels[0] = pygame.math.Vector2(0, 0)
        self.node_vels[-1] = pygame.math.Vector2(0, 0)

        segment_length = self.rest_length / self.segments

        # ---- 对中间节点施加重力和阻尼 ----
        for i in range(1, len(self.nodes) - 1):
            self.node_vels[i].y += self.gravity
            self.node_vels[i] *= self.damping
            self.nodes[i] += self.node_vels[i]

        # ---- 迭代距离约束（地面约束穿插其中，防止抽搐） ----
        for _ in range(5):
            for i in range(len(self.nodes) - 1):
                node1 = self.nodes[i]
                node2 = self.nodes[i + 1]
                diff = node2 - node1
                dist = diff.length()
                if dist > 0:
                    correction = (dist - segment_length) / dist * 0.5
                    offset = diff * correction
                    if i > 0:
                        self.nodes[i] += offset
                    if i + 1 < len(self.nodes) - 1:
                        self.nodes[i + 1] -= offset
            # 每轮约束后立即修正地面穿透，避免下一轮约束把节点又拉入地面
            if blocks:
                self._apply_ground_constraint(blocks)

        # ---- 玩家间作用力 ----
        self._apply_player_forces(blocks)

    # ------------------------------------------------------------------
    # 地面约束
    # ------------------------------------------------------------------
    def _apply_ground_constraint(self, blocks):
        """防止绳子中间节点穿透到方块内部"""
        for i in range(1, len(self.nodes) - 1):
            node = self.nodes[i]
            for block in blocks:
                if block.block_type in ("bg", "wall"):
                    continue
                # 仅在节点真正进入方块内部时才推开
                if (block.rect.left < node.x < block.rect.right and
                        block.rect.top <= node.y <= block.rect.bottom):
                    self.nodes[i].y = block.rect.top - 1
                    self.node_vels[i].y = 0

    # ------------------------------------------------------------------
    # 玩家间弹力
    # ------------------------------------------------------------------
    def _apply_player_forces(self, blocks=None):
        """
        绳子仅提供拉力（无推力）：只在拉伸超过阈值时将玩家拉近。

        策略：
        1. 拉伸过度时用位置修正拉近玩家
        2. 拉近后执行碰撞修正，防止穿入方块
        3. 轻度速度阻尼，避免拉拽过猛
        """
        pos1 = pygame.math.Vector2(self.p1.rect.centerx, self.p1.rect.centery)
        pos2 = pygame.math.Vector2(self.p2.rect.centerx, self.p2.rect.centery)
        diff = pos2 - pos1
        distance = diff.length()

        if distance < 0.001:
            return

        direction = diff.normalize()

        # ---- 位置修正（仅拉力） ----
        threshold = self.max_length * 0.85
        if distance > threshold:
            over_distance = distance - threshold
            pull_amount = over_distance * 0.2
            correction_vec = direction * pull_amount
            if not self.p1.grabbing:
                self.p1.rect.x += int(correction_vec.x)
                self.p1.rect.y += int(correction_vec.y)
                if blocks:
                    self.p1.resolve_block_pushout(blocks)
            if not self.p2.grabbing:
                self.p2.rect.x -= int(correction_vec.x)
                self.p2.rect.y -= int(correction_vec.y)
                if blocks:
                    self.p2.resolve_block_pushout(blocks)

        # ---- 速度影响（轻柔弹性反馈） ----
        extension = distance - self.rest_length
        if extension > 0:
            stretch_ratio = min(extension / (self.max_length * 0.5), 1.0)

            # 阻尼力：减少玩家远离彼此的速度
            if direction.x > 0:
                if self.p1.vel_x < 0:
                    self.p1.vel_x += abs(self.p1.vel_x) * 0.05 * stretch_ratio
                if self.p2.vel_x > 0:
                    self.p2.vel_x -= abs(self.p2.vel_x) * 0.05 * stretch_ratio
            else:
                if self.p1.vel_x > 0:
                    self.p1.vel_x -= abs(self.p1.vel_x) * 0.05 * stretch_ratio
                if self.p2.vel_x < 0:
                    self.p2.vel_x += abs(self.p2.vel_x) * 0.05 * stretch_ratio

    # ------------------------------------------------------------------
    # 绘制
    # ------------------------------------------------------------------
    def draw(self, surface, camera_offset=(0, 0)):
        """绘制多节点绳索，深黄 / 深棕交替，模拟绞绳效果"""
        if len(self.nodes) < 2:
            return

        cx, cy = camera_offset

        # 世界坐标 → 屏幕坐标
        points = []
        for node in self.nodes:
            screen_x = int(node.x - cx)
            screen_y = int(node.y - cy)
            points.append((screen_x, screen_y))

        # 逐段绘制，交替深黄 / 深棕
        dark_yellow = (180, 150, 40)
        dark_brown = (100, 65, 25)

        for i in range(len(points) - 1):
            color = dark_yellow if i % 2 == 0 else dark_brown
            pygame.draw.line(surface, color, points[i], points[i + 1], 2)
