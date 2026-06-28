# -*- coding: utf-8 -*-
"""玩家角色类：动画状态机、移动、跳跃、抓取、受击逻辑"""

import pygame
from config.settings import GRAVITY, FRICTION, JUMP_STRENGTH, MOVE_SPEED, MAX_FALL_SPEED, TILE_SIZE
from utils.animation import Animation
from config.path import get_player_frames


class Player(pygame.sprite.Sprite):
    STATES = ["idle", "run", "jump", "hurt", "death", "grab"]

    def __init__(self, x, y, p_dir, keys, arrow_img, hp_img, is_p1=True, is_remote=False):
        super().__init__()
        self.p_dir = p_dir
        self.keys = keys
        self.is_p1 = is_p1
        self.is_remote = is_remote   # True → 由网络远程控制，不读键盘
        self.facing_right = True

        # 加载动画
        self.animations = {}
        anim_specs = [
            ("idle", "idle", 30, True),
            ("run", "run", 10, True),
            ("jump", "jump", 14, True),
            ("hurt", "hurt", 12, True),
            ("grab", "grab", 6, False),
            ("death", "death", 18, False),
        ]
        for state, name, frame_duration, loop in anim_specs:
            frames = get_player_frames(self.p_dir, name)
            self.animations[state] = Animation(frames, frame_duration=frame_duration, loop=loop)

        self.state = "idle"

        self.image = self.animations[self.state].get_current_frame()
        # 碰撞盒仅取图片下半部分（16×16），上半为动作留空区
        self.rect = pygame.Rect(x, y + self.image.get_height() // 2,
                                self.image.get_width(), self.image.get_height() // 2)
        self.mask = pygame.mask.from_surface(self.image)
        self._cached_state = self.state
        self._cached_frame_index = self.animations[self.state].frame_index
        self._cached_facing = self.facing_right

        # 物理
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.on_ground = False
        self.grabbing = False        # 按住抓取键
        self.grab_attached = False   # 真正吸附在方块上
        self.grab_block = None
        self.jumps_left = 2          # 二段跳剩余次数
        self._jump_pressed_prev = False
        self.dead = False
        self.invincible = 0

        # 属性
        self.max_hp = 3
        self.max_hp = 3
        self.hp = self.max_hp
        self.arrow_img = pygame.image.load(arrow_img).convert_alpha() if arrow_img else None
        self.hp_img = pygame.image.load(hp_img).convert_alpha() if hp_img else None

    def handle_input(self):
        if self.is_remote or self.dead:
            return
        keys = pygame.key.get_pressed()

        # 抓取键按下
        if keys[self.keys["grab"]]:
            if not self.grabbing:
                self.start_grab()
        else:
            if self.grabbing:
                self.release_grab()

        # 已吸附在方块上：冻结位置，不响应移动/跳跃
        if self.grabbing and self.grab_attached:
            self.vel_x = 0
            self.vel_y = 0
            self.state = "grab"
            return

        # 空抓或未吸附：允许正常移动，动画保持 grab
        if self.grabbing:
            self.state = "grab"

        # 左右移动
        move = 0
        if keys[self.keys["left"]]:
            move = -MOVE_SPEED
            self.facing_right = False
        if keys[self.keys["right"]]:
            move = MOVE_SPEED
            self.facing_right = True

        self.vel_x = move

        # 跳跃（边沿触发，支持二段跳）
        jump_pressed = keys[self.keys["jump"]]
        jump_edge = jump_pressed and not self._jump_pressed_prev
        if jump_edge:
            if self.on_ground:
                self.jumps_left = 2
                self.vel_y = JUMP_STRENGTH
                self.on_ground = False
                self.jumps_left -= 1
                self.change_state("jump")
            elif self.jumps_left > 0:
                self.vel_y = JUMP_STRENGTH
                self.jumps_left -= 1
                self.change_state("jump")
        self._jump_pressed_prev = jump_pressed

    def apply_remote_state(self, data):
        """应用网络接收的远程玩家状态（lerp 插值平滑）"""
        LERP = 0.35
        self.rect.x += (data["x"] - self.rect.x) * LERP
        self.rect.y += (data["y"] - self.rect.y) * LERP
        self.vel_x = data.get("vel_x", 0)
        self.vel_y = data.get("vel_y", 0)
        self.facing_right = data.get("facing_right", self.facing_right)
        self.on_ground = data.get("on_ground", self.on_ground)
        self.grabbing = data.get("grabbing", self.grabbing)
        self.grab_attached = data.get("grab_attached", self.grab_attached)
        new_state = data.get("state", self.state)
        if new_state != self.state:
            self.change_state(new_state)
        new_hp = data.get("hp", self.hp)
        if new_hp < self.hp:
            self.take_damage(self.hp - new_hp)
        self.dead = data.get("dead", self.dead)

    def start_grab(self):
        self.grabbing = True
        self.change_state("grab")

    def release_grab(self):
        self.grabbing = False
        self.grab_attached = False
        self.grab_block = None
        self.animations["grab"].reset()
        if self.on_ground:
            self.change_state("idle")
        else:
            self.change_state("jump")

    def change_state(self, new_state):
        if new_state == self.state:
            return
        self.state = new_state
        self.animations[self.state].reset()

    def update(self, blocks, items, portals, all_players, sfx_callback=None):
        if self.invincible > 0:
            self.invincible -= 1

        prev_state = self.state
        prev_grabbing = self.grabbing

        self.handle_input()

        # 音效回调
        if sfx_callback:
            if prev_state != "jump" and self.state == "jump":
                sfx_callback("jump")
            if not prev_grabbing and self.grabbing:
                sfx_callback("grab1")
            if prev_grabbing and not self.grabbing:
                sfx_callback("grab2")

        if self.dead:
            self.animations[self.state].update()
            self._update_image()
            return

        # 已吸附：完全冻结
        if self.grabbing and self.grab_attached:
            self.animations[self.state].update()
            self._update_image()
            return

        # 重力
        self.vel_y += GRAVITY
        if self.vel_y > MAX_FALL_SPEED:
            self.vel_y = MAX_FALL_SPEED

        # 水平移动
        self.rect.x += int(self.vel_x)
        self._handle_collision(blocks, "x")

        # 垂直移动
        self.on_ground = False
        self.rect.y += int(self.vel_y)
        self._handle_collision(blocks, "y")

        # 落地时重置二段跳
        if self.on_ground:
            self.jumps_left = 2

        # 抓取吸附检测（碰撞解析后判断是否有方块紧贴左/右/下）
        if self.grabbing:
            self.grab_attached = self._check_grab_attachment(blocks)
            if self.grab_attached:
                self.vel_x = 0
                self.vel_y = 0

        # 状态判定（空抓时不覆盖 grab 状态）
        if not self.on_ground and self.state not in ("jump", "hurt", "grab"):
            self.change_state("jump")
        elif self.on_ground and self.state == "jump":
            self.change_state("idle")
        elif self.on_ground and abs(self.vel_x) > 0.5 and self.state in ("idle", "run"):
            self.change_state("run")
        elif self.on_ground and abs(self.vel_x) < 0.5 and self.state == "run":
            self.change_state("idle")

        self.animations[self.state].update()
        self._update_image()

        # 受伤动画结束后切回正常状态
        if self.state == "hurt" and self.invincible <= 0:
            if self.on_ground:
                self.change_state("idle")
            else:
                self.change_state("jump")

        # 道具检测
        for item in items:
            if self.rect.colliderect(item.rect):
                item.collected = True

        # 传送门检测
        for portal in portals:
            portal.players_inside[self.is_p1] = self.rect.colliderect(portal.rect)

    def _handle_collision(self, blocks, axis):
        for block in blocks:
            if block.block_type == "bg":
                continue
            if self.rect.colliderect(block.rect):
                if axis == "x":
                    if self.vel_x > 0:
                        self.rect.right = block.rect.left
                    elif self.vel_x < 0:
                        self.rect.left = block.rect.right
                    self.vel_x = 0
                elif axis == "y":
                    if self.vel_y > 0:
                        self.rect.bottom = block.rect.top
                        self.on_ground = True
                        self.vel_y = 0
                    elif self.vel_y < 0:
                        self.rect.top = block.rect.bottom
                        self.vel_y = 0
            # 处理恰好站在方块上（接触但未重叠）的情况，防止 on_ground 抖动
            elif axis == "y" and self.vel_y >= 0:
                if (self.rect.bottom == block.rect.top and
                    self.rect.right > block.rect.left and
                    self.rect.left < block.rect.right):
                    self.on_ground = True
                    self.vel_y = 0

    def resolve_block_pushout(self, blocks):
        """被绳子拉拽后调用：将玩家推出任何重叠方块"""
        for block in blocks:
            if block.block_type in ("bg", "wall"):
                continue
            if not self.rect.colliderect(block.rect):
                continue
            # 计算四个方向的重叠量，选最小方向推出
            push_left = self.rect.right - block.rect.left
            push_right = block.rect.right - self.rect.left
            push_top = self.rect.bottom - block.rect.top
            push_bottom = block.rect.bottom - self.rect.top
            min_push = min(push_left, push_right, push_top, push_bottom)
            if min_push == push_top:
                self.rect.bottom = block.rect.top
                self.vel_y = 0
            elif min_push == push_bottom:
                self.rect.top = block.rect.bottom
                self.vel_y = 0
            elif min_push == push_left:
                self.rect.right = block.rect.left
                self.vel_x = 0
            else:
                self.rect.left = block.rect.right
                self.vel_x = 0

    def _check_grab_attachment(self, blocks):
        """检查玩家左/右/下三个面是否紧贴可抓取方块"""
        for block in blocks:
            if block.block_type not in ("solid", "platform"):
                continue
            # 下方：玩家站在方块上
            if (self.rect.bottom == block.rect.top and
                    self.rect.right > block.rect.left and
                    self.rect.left < block.rect.right):
                return True
            # 左侧：玩家左面紧贴方块右面
            if (self.rect.left == block.rect.right and
                    self.rect.bottom > block.rect.top and
                    self.rect.top < block.rect.bottom):
                return True
            # 右侧：玩家右面紧贴方块左面
            if (self.rect.right == block.rect.left and
                    self.rect.bottom > block.rect.top and
                    self.rect.top < block.rect.bottom):
                return True
        return False

    def _update_image(self):
        frame = self.animations[self.state].get_current_frame()
        if not self.facing_right:
            frame = pygame.transform.flip(frame, True, False)
        self.image = frame
        self.mask = pygame.mask.from_surface(self.image)

    def take_damage(self, amount=1):
        if self.invincible > 0 or self.dead:
            return
        self.hp -= amount
        self.invincible = 60
        if self.hp <= 0:
            self.hp = 0
            self.dead = True
            self.change_state("death")
        else:
            self.change_state("hurt")

    def draw(self, surface, camera_offset=(0, 0)):
        # 闪烁无敌
        if self.invincible > 0 and self.invincible % 4 < 2:
            return
        # 碰撞盒为图片下半部分，绘制时向上偏移以显示完整角色
        offset_y = self.image.get_height() // 2
        pos = (self.rect.x - camera_offset[0], self.rect.y - offset_y - camera_offset[1])
        surface.blit(self.image, pos)
        # 头顶箭头（紧贴角色实际头顶，水平居中）
        # 角色精灵翻转后视觉中心会偏移，面向左时补偿 2px
        arrow_x_adjust = 0 if self.facing_right else 2
        arrow_pos = (self.rect.centerx - camera_offset[0] - self.arrow_img.get_width() // 2 + arrow_x_adjust,
                     self.rect.top - camera_offset[1] - self.arrow_img.get_height() - 4)
        surface.blit(self.arrow_img, arrow_pos)
