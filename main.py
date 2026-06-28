# -*- coding: utf-8 -*-
"""程序入口、游戏主循环、场景调度"""

import sys
import time
import random
import pygame
from config.settings import (SCREEN_WIDTH, SCREEN_HEIGHT, LOGICAL_W, LOGICAL_H,
                              FPS, P1_KEYS, P2_KEYS, SERVER_URL, SYNC_INTERVAL, PING_INTERVAL,
                              ENDLESS_SCROLL_SPEED, ENDLESS_SPEED_INCREMENT, ENDLESS_CHASE_DISTANCE,
                              BOSS_INITIAL_SPEED, BOSS_DAMAGE, TILE_SIZE, RED, WHITE, YELLOW)
from config.path import (P1_DIR, P2_DIR, P1_ARROW, P2_ARROW, FONT_PATH,
                         HOME_BGM, NORMAL_BGM, ENDLESS_BGM, SOIL_BREAK_SOUND,
                         JUMP_SOUND, GRAB1_SOUND, GRAB2_SOUND, DRAGON_ROAR_SOUND,
                         SKY_IMG, CLOUD_IMG, FAR_MOUNTAIN_IMG, NEAR_MOUNTAIN_IMG,
                         ICON_PATH)
from entities.player import Player
from entities.rope import Rope
from entities.camera import Camera
from entities.background import ParallaxBackground
from entities.level import load_level_from_json
from entities.endless_level import EndlessLevel
from entities.boss import Boss
from entities.particle import ParticleSystem
from UI.menu import MainMenu, LevelSelectMenu, PauseMenu, GameOverMenu, OnlineMenu, MultiplayerLevelSelectMenu
from UI.hud import HUD

from utils.sound_manager import SoundManager


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("PairLine")
        try:
            pygame.display.set_icon(pygame.image.load(ICON_PATH))
        except Exception:
            pass  # 图标加载失败不阻塞游戏启动

        # 自动切换为英文输入法，避免中文输入导致 WASD 失效
        self._switch_to_english_ime()

        # 逻辑像素画布，最终整体 SCALE 倍输出到主屏
        self.canvas = pygame.Surface((LOGICAL_W, LOGICAL_H))
        self.clock = pygame.time.Clock()
        self.sound = SoundManager()
        self.sound.load_sound("jump", JUMP_SOUND)
        self.sound.load_sound("grab1", GRAB1_SOUND)
        self.sound.load_sound("grab2", GRAB2_SOUND)
        self.bg = ParallaxBackground(SKY_IMG, CLOUD_IMG, FAR_MOUNTAIN_IMG, NEAR_MOUNTAIN_IMG)
        self.main_menu = MainMenu()
        self.level_menu = LevelSelectMenu()
        self.pause_menu = PauseMenu()
        self.game_over_menu = GameOverMenu()
        self.online_menu = OnlineMenu()
        self.hud = HUD()
        self.state = "main_menu"
        self.player1 = None
        self.player2 = None
        self.rope = None
        self.camera = None
        self.level = None
        self.current_level_name = None
        # 关卡文件名 → 中文名的映射
        self._level_name_map = {"level_1.json": "第一关", "level_2.json": "第二关"}
        # 关卡顺序（用于"下一关"）
        self._level_order = ["level_1.json", "level_2.json"]
        self._pending_next_level = None

        # 联机相关
        self.online = False          # 是否在线联机中
        self.network = None          # NetworkClient 实例
        self.is_host = False         # 当前客户端是否为房主(P1)
        self.my_player = None        # 本地控制的玩家引用
        self.remote_player = None    # 远程控制的玩家引用
        self.multi_level_menu = None # MultiplayerLevelSelectMenu 实例
        self.frame_count = 0         # 帧计数器（用于网络同步频率控制）
        self._disconnected = False   # 联机断线标记

        # 无尽模式
        self.endless_level = None
        self.boss = None
        self.particles = None
        self.endless_distance = 0.0
        self.endless_score = 0
        self.endless_speed = ENDLESS_SCROLL_SPEED
        self.endless_phase = 0       # 0=跑酷, 1=预警, 2=BOSS追击
        self._warning_timer = 0
        self._boss_entered = False  # Boss 是否已走入屏幕
        self.bgm_enabled = True    # 背景音乐开关

    def start_level(self, level_name, online=False, is_host=False):
        self.level = load_level_from_json(level_name)
        self.current_level_name = level_name
        self._game_over_is_endless = False
        self.camera = Camera(self.level.map_width, self.level.map_height)

        if online:
            self.online = True
            self.is_host = is_host
            # 房主控制 P1，客机控制 P2；对方由网络远程驱动
            if is_host:
                self.player1 = Player(self.level.spawn1[0], self.level.spawn1[1],
                                      P1_DIR, P1_KEYS, P1_ARROW, None, is_p1=True, is_remote=False)
                self.player2 = Player(self.level.spawn2[0], self.level.spawn2[1],
                                      P2_DIR, P2_KEYS, P2_ARROW, None, is_p1=False, is_remote=True)
                self.my_player = self.player1
                self.remote_player = self.player2
            else:
                self.player1 = Player(self.level.spawn1[0], self.level.spawn1[1],
                                      P1_DIR, P1_KEYS, P1_ARROW, None, is_p1=True, is_remote=True)
                self.player2 = Player(self.level.spawn2[0], self.level.spawn2[1],
                                      P2_DIR, P2_KEYS, P2_ARROW, None, is_p1=False, is_remote=False)
                self.my_player = self.player2
                self.remote_player = self.player1
        else:
            self.online = False
            self.is_host = False
            self.my_player = None
            self.remote_player = None
            self.player1 = Player(self.level.spawn1[0], self.level.spawn1[1],
                                  P1_DIR, P1_KEYS, P1_ARROW, None, is_p1=True)
            self.player2 = Player(self.level.spawn2[0], self.level.spawn2[1],
                                  P2_DIR, P2_KEYS, P2_ARROW, None, is_p1=False)

        self.rope = Rope(self.player1, self.player2)
        self.state = "playing"
        self._disconnected = False
        self.sound.play_bgm(NORMAL_BGM)

    def back_to_menu(self):
        self.sound.stop_bgm()
        self.state = "main_menu"
        self.sound.play_bgm(HOME_BGM)

    # ------------------------------------------------------------------
    # 无尽模式
    # ------------------------------------------------------------------
    def _start_endless(self):
        self.endless_level = EndlessLevel()
        self.current_level_name = None
        self.camera = Camera(self.endless_level.map_width, self.endless_level.map_height)
        self.player1 = Player(self.endless_level.spawn1[0], self.endless_level.spawn1[1],
                              P1_DIR, P1_KEYS, P1_ARROW, None, is_p1=True)
        self.player2 = Player(self.endless_level.spawn2[0], self.endless_level.spawn2[1],
                              P2_DIR, P2_KEYS, P2_ARROW, None, is_p1=False)
        self.rope = Rope(self.player1, self.player2)
        self.boss = None                # 先不创建，等预警阶段结束后再出现
        self.particles = ParticleSystem()
        self.endless_distance = 0.0
        self.endless_score = 0
        self.endless_speed = ENDLESS_SCROLL_SPEED
        self.endless_phase = 0          # 0=自由跑酷
        self._warning_timer = 0
        self._boss_entered = False
        self._game_over_is_endless = True
        self.sound.load_sound("soil_break", SOIL_BREAK_SOUND)
        self.sound.load_sound("dragon_roar", DRAGON_ROAR_SOUND)
        self.sound.play_bgm(ENDLESS_BGM)
        self.state = "endless"

    # ------------------------------------------------------------------
    # 联机辅助方法
    # ------------------------------------------------------------------
    def _start_multiplayer_level_select(self):
        """从 OnlineMenu 过渡到双人关卡选择"""
        self.network = self.online_menu.network
        role = self.online_menu._role
        self.multi_level_menu = MultiplayerLevelSelectMenu(self.network, role)
        # 同步关卡解锁状态
        self.multi_level_menu.level_unlocked = dict(self.level_menu.level_unlocked)
        self.multi_level_menu.level_kun_records = dict(self.level_menu.level_kun_records)
        self.state = "multiplayer_level_select"

    def _start_online_game(self):
        """双人关卡选择完成 → 开始联机游戏"""
        level_file = self.multi_level_menu._game_start_level
        self.multi_level_menu._game_start_level = None
        self.start_level(level_file, online=True, is_host=(self.multi_level_menu.role == "host"))

    def _poll_network_messages(self):
        """处理联机游戏中的网络消息"""
        if self.network is None:
            return
        for msg in self.network.poll():
            self._handle_network_message(msg)

    def _handle_network_message(self, msg):
        """分发单条网络消息"""
        t = msg.get("type", "")
        data = msg.get("data", {})

        if t == "player_state":
            # 应用远程玩家状态
            if self.remote_player:
                self.remote_player.apply_remote_state(data)

        elif t == "player_left":
            self._on_disconnect()

        elif t == "game_event":
            event = data.get("event", "")
            if event == "damage":
                target = self.player1 if data.get("target") == "p1" else self.player2
                target.take_damage(data.get("amount", 1))
            elif event == "game_over":
                # 如果本地已先检测到通关，不覆盖（远程消息缺少 has_next 等信息）
                if self.state == "game_over":
                    return
                self.game_over_menu.setup(
                    win=data.get("win", False), endless=False,
                    score=data.get("score", 0),
                    total_items=data.get("total", 0),
                    online_guest=(not self.is_host))
                self._game_over_is_endless = False
                self.state = "game_over"

        elif t == "game_over_action":
            # 客机收到房主的游戏结束选择
            action = data.get("action", "")
            level_file = data.get("level", "")
            if action == "restart":
                if self.current_level_name:
                    self.start_level(self.current_level_name, online=True, is_host=self.is_host)
            elif action == "next_level":
                if level_file:
                    self.start_level(level_file, online=True, is_host=self.is_host)
            elif action == "level_select":
                self.state = "level_select"
            elif action == "back":
                self.back_to_menu()

        elif t == "ping":
            # 对方回应的 pong → 在 NetworkClient 中已计算延迟
            pass

    def _send_player_state(self):
        """发送本地玩家状态给服务器"""
        if not self.my_player or not self.network:
            return
        p = self.my_player
        self.network.send("player_state", {
            "x": p.rect.x, "y": p.rect.y,
            "vel_x": p.vel_x, "vel_y": p.vel_y,
            "state": p.state,
            "facing_right": p.facing_right,
            "hp": p.hp,
            "on_ground": p.on_ground,
            "grabbing": p.grabbing,
            "grab_attached": p.grab_attached,
            "dead": p.dead,
        })

    def _on_disconnect(self):
        """远程玩家断开连接"""
        self._disconnected = True
        if self.network:
            self.network.stop()
            self.network = None
        self.online = False

    def _disconnect_online(self):
        """手动断开联机"""
        if self.network:
            self.network.stop()
            self.network = None
        self.online = False
        self.multi_level_menu = None

    def _switch_to_english_ime(self):
        """通过 Windows API 强制切换为英文键盘布局"""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            # 加载美式英文键盘布局
            hkl = user32.LoadKeyboardLayoutW("00000409", 0x00000001)
            if hkl == 0:
                return
            # 向当前线程的焦点窗口发送切换输入法的消息
            hwnd = user32.GetForegroundWindow()
            WM_INPUTLANGCHANGEREQUEST = 0x0050
            INPUTLANGCHANGE_SYSCHARSET = 0x0001
            user32.PostMessageW(hwnd, WM_INPUTLANGCHANGEREQUEST,
                                INPUTLANGCHANGE_SYSCHARSET, hkl)
        except Exception:
            pass  # 非 Windows 平台忽略

    def run(self):
        self.sound.play_bgm(HOME_BGM)
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if self.network:
                        self.network.stop()
                    pygame.quit()
                    sys.exit()
                self._handle_event(event)
            self._update()
            self._draw()
            pygame.display.flip()
            self.clock.tick(FPS)

    def _handle_event(self, event):
        # 全局：M 键切换背景音乐开关
        if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
            self.bgm_enabled = not self.bgm_enabled
            if self.bgm_enabled:
                self.sound.set_bgm_volume(0.5)
            else:
                self.sound.set_bgm_volume(0.0)

        if self.state == "main_menu":
            r = self.main_menu.handle_event(event)
            if r == "本地同屏双人":
                self.state = "level_select"
            elif r == "远程联机模式":
                self.state = "online"
        elif self.state == "online":
            r = self.online_menu.handle_event(event)
            if r == "BACK":
                self.state = "main_menu"
        elif self.state == "multiplayer_level_select":
            if self.multi_level_menu:
                r = self.multi_level_menu.handle_event(event)
                if r == "BACK":
                    self._disconnect_online()
                    self.state = "main_menu"
        elif self.state == "level_select":
            r = self.level_menu.handle_event(event)
            if r == "第一关":
                self.start_level("level_1.json")
            elif r == "第二关":
                self.start_level("level_2.json")
            elif r == "无尽模式":
                self._start_endless()
            elif r == "BACK":
                self.state = "main_menu"
        elif self.state in ("playing", "endless"):
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.pause_menu.active = True
                self._prev_state = self.state
                self.state = "paused"
        elif self.state == "paused":
            r = self.pause_menu.handle_event(event)
            if r == "继续游戏":
                self.state = self._prev_state if hasattr(self, '_prev_state') else "playing"
            elif r == "重新开始":
                if self._prev_state == "endless":
                    self._start_endless()
                elif self.current_level_name:
                    self.start_level(self.current_level_name, online=self.online, is_host=self.is_host)
                else:
                    self.start_level("level_1.json", online=self.online, is_host=self.is_host)
            elif r == "返回主菜单":
                self.back_to_menu()
        elif self.state == "game_over":
            r = self.game_over_menu.handle_event(event)
            if r == "restart":
                if self._game_over_is_endless:
                    self._start_endless()
                elif self.current_level_name:
                    self.start_level(self.current_level_name, online=self.online, is_host=self.is_host)
                else:
                    self.start_level("level_1.json", online=self.online, is_host=self.is_host)
                self._send_game_over_action("restart")
            elif r == "next_level":
                if hasattr(self, '_pending_next_level'):
                    self.start_level(self._pending_next_level, online=self.online, is_host=self.is_host)
                    self._send_game_over_action("next_level", self._pending_next_level)
            elif r == "level_select":
                self.state = "level_select"
                self._send_game_over_action("level_select")
            elif r == "back":
                self.back_to_menu()
                self._send_game_over_action("back")

    def _send_game_over_action(self, action, level_file=""):
        """房主将游戏结束选择同步给客机"""
        if self.online and self.network and self.is_host:
            self.network.send("game_over_action", {
                "action": action,
                "level": level_file,
            })

    def _update(self):
        self.frame_count += 1

        # ---- 菜单联机状态网络轮询 ----
        if self.state == "online":
            r = self.online_menu.poll_network()
            if r == "CONNECTED":
                self._start_multiplayer_level_select()
                return
        elif self.state == "multiplayer_level_select":
            if self.multi_level_menu:
                r = self.multi_level_menu.poll_network()
                if r == "start":
                    self._start_online_game()
                    return
                elif r == "disconnect":
                    self._on_disconnect()
                    return

        # ---- 联机游戏：处理网络消息 + 发送本地状态 ----
        if self.online and self.state in ("playing", "game_over") and self.network:
            self._poll_network_messages()
            if self._disconnected:
                return
            if self.state == "playing":
                if self.frame_count % SYNC_INTERVAL == 0:
                    self._send_player_state()
                if self.frame_count % PING_INTERVAL == 0:
                    self.network.send("ping", {"sent_at": time.time()})

        # ---- 无尽模式 ----
        if self.state == "endless":
            self._update_endless()
            return

        # ---- 非游戏状态不更新物理 ----
        if self.state != "playing":
            return

        self.level.update()
        blocks = [b for b in self.level.blocks if b.block_type != "bg"]
        sfx_cb = lambda name: self.sound.play_sfx(name)
        self.player1.update(blocks, self.level.items, self.level.portals, [self.player1, self.player2], sfx_cb)
        self.player2.update(blocks, self.level.items, self.level.portals, [self.player1, self.player2], sfx_cb)
        self.rope.update(blocks)
        self.camera.update(self.player1.rect, self.player2.rect)
        self.bg.update(self.camera.rect.x)

        # 蝙蝠碰撞检测（仅本地玩家触发伤害发送网络事件）
        for bat in self.level.bats:
            for p in (self.player1, self.player2):
                if p.rect.colliderect(bat.hitbox):
                    if not p.is_remote:
                        p.take_damage(1)
                        if self.online and self.network:
                            self.network.send("game_event", {
                                "event": "damage",
                                "target": "p1" if p.is_p1 else "p2",
                                "amount": 1,
                            })

        for p in (self.player1, self.player2):
            if not p.dead and p.rect.y > self.level.map_height:
                p.take_damage(99)

        if self.level.portals and self.level.is_all_portal():
            # 更新 kun 记录并解锁下一关（通关即解锁，无需 kun 门槛）
            lvl_name = self._level_name_map.get(self.current_level_name)
            if lvl_name:
                kun_count = self.level.get_collected_count()
                prev = self.level_menu.level_kun_records.get(lvl_name, 0)
                if kun_count > prev:
                    self.level_menu.level_kun_records[lvl_name] = kun_count
                # 第一关通关 → 解锁第二关
                if lvl_name == "第一关":
                    self.level_menu.level_unlocked["第二关"] = True
                # 第二关通关 → 解锁无尽模式
                elif lvl_name == "第二关":
                    self.level_menu.level_unlocked["无尽模式"] = True
            # 检查下一关
            has_next = False
            if self.current_level_name in self._level_order:
                idx = self._level_order.index(self.current_level_name)
                if idx + 1 < len(self._level_order):
                    next_file = self._level_order[idx + 1]
                    next_name = self._level_name_map.get(next_file, "")
                    if self.level_menu.level_unlocked.get(next_name, False):
                        has_next = True
                        self._pending_next_level = next_file
            self.game_over_menu.setup(
                win=True, endless=False,
                score=self.level.get_collected_count(),
                total_items=self.level.get_total_items(),
                has_next=has_next,
                online_guest=(self.online and not self.is_host))
            self.state = "game_over"
            self._game_over_is_endless = False
            # 联机时通知对方游戏结束
            if self.online and self.network:
                self.network.send("game_event", {
                    "event": "game_over",
                    "win": True,
                    "score": self.level.get_collected_count(),
                    "total": self.level.get_total_items(),
                })
        elif self.player1.dead and self.player2.dead:
            self.game_over_menu.setup(
                win=False, endless=False,
                score=self.level.get_collected_count(),
                total_items=self.level.get_total_items(),
                online_guest=(self.online and not self.is_host))
            self.state = "game_over"
            self._game_over_is_endless = False
            if self.online and self.network:
                self.network.send("game_event", {
                    "event": "game_over",
                    "win": False,
                })

    def _update_endless(self):
        """无尽模式每帧更新"""
        self.endless_distance += self.endless_speed
        self.endless_speed += ENDLESS_SPEED_INCREMENT

        # 地形生成 & 清理
        camera_right = self.camera.rect.right
        self.endless_level.ensure_chunks_ahead(camera_right + 320)
        self.endless_level.prune_behind(self.camera.rect.left)

        # 自动向右滚屏
        self.camera.rect.x += int(self.endless_speed)

        # 更新实体
        self.endless_level.update()
        blocks = [b for b in self.endless_level.blocks if b.block_type != "bg"]
        sfx_cb = lambda name: self.sound.play_sfx(name)
        self.player1.update(blocks, self.endless_level.items, [], [self.player1, self.player2], sfx_cb)
        self.player2.update(blocks, self.endless_level.items, [], [self.player1, self.player2], sfx_cb)
        self.rope.update(blocks)
        self.bg.update(self.camera.rect.x)

        # ---- 阶段管理 ----
        GROUND_Y = 7 * TILE_SIZE  # 地面行 y 坐标

        if self.endless_phase == 0:
            # 自由跑酷阶段：跑够 300 距离后进入预警
            if self.endless_distance > 300:
                self.endless_phase = 1
                self._warning_timer = 120  # 2 秒 @ 60fps
                self._shake_baseline_y = self.camera.rect.y  # 保存震动前 camera 基准 y
                self.sound.play_sfx("dragon_roar")  # 播放龙吼音效

        elif self.endless_phase == 1:
            # 预警阶段：屏幕震动 + 倒计时
            self._warning_timer -= 1
            # 屏幕震动（随机偏移相机，不累积位移）
            if self._warning_timer % 6 < 3:
                self.camera.rect.x += random.randint(-3, 3)
                self.camera.rect.y = self._shake_baseline_y + random.randint(-2, 2)
            else:
                self.camera.rect.y = self._shake_baseline_y
            if self._warning_timer <= 0:
                # 预警结束，Boss 从左侧远处走入屏幕
                self.endless_phase = 2
                self._boss_entered = False
                self.boss = Boss(self.camera.rect.left - 64, GROUND_Y)
                self.boss.set_sfx_callback(lambda name: self.sound.play_sfx(name))
                # 入场阶段临时加速，确保能追上滚屏
                self.boss.base_speed = 3.0

        elif self.endless_phase == 2:
            # BOSS 追击阶段
            if not self._boss_entered:
                # 走入阶段：Boss 自主向右快速移动，直到进入屏幕可见范围
                self.boss.update(blocks, self.particles)
                if self.boss.rect.right >= self.camera.rect.left + 16:
                    self._boss_entered = True
                    # 恢复正常速度，锁定在屏幕左侧边界
                    self.boss.base_speed = BOSS_INITIAL_SPEED
            else:
                # 锁定阶段：Boss 贴住屏幕左侧边界
                self.boss.update(blocks, self.particles,
                                 target_x=self.camera.rect.left + 16)
            self.particles.update()

        # 蝙蝠碰撞
        for bat in self.endless_level.bats:
            for p in (self.player1, self.player2):
                if p.rect.colliderect(bat.hitbox):
                    p.take_damage(1)

        # BOSS 碰撞玩家（仅在追击阶段）
        if self.endless_phase == 2 and self.boss:
            for p in (self.player1, self.player2):
                if not p.dead and p.rect.colliderect(self.boss.rect):
                    p.take_damage(BOSS_DAMAGE)

        # 玩家掉出底部
        for p in (self.player1, self.player2):
            if not p.dead and p.rect.y > self.endless_level.map_height:
                p.take_damage(99)

        # 玩家落后于相机左侧 → 即死
        for p in (self.player1, self.player2):
            if not p.dead and p.rect.right < self.camera.rect.left - ENDLESS_CHASE_DISTANCE:
                p.take_damage(99)

        # 分数 = 距离分 + kun 分
        self.endless_score = int(self.endless_distance / 10) + self.endless_level.get_collected_count() * 10

        # 游戏结束判断
        if self.player1.dead and self.player2.dead:
            self.game_over_menu.setup(
                win=False, endless=True,
                score=self.endless_score,
                total_items=self.endless_level.get_collected_count())
            self._game_over_is_endless = True
            self.state = "game_over"

    def _draw(self):
        if self.state == "main_menu":
            self.main_menu.draw_bg(self.canvas)
        elif self.state == "online":
            self.online_menu.draw_bg(self.canvas)
        elif self.state == "level_select":
            self.level_menu.draw_bg(self.canvas)
        elif self.state == "multiplayer_level_select":
            if self.multi_level_menu:
                self.multi_level_menu.draw_bg(self.canvas)
        elif self.state == "endless":
            self._draw_endless()
        elif self.state in ("playing", "paused", "game_over"):
            # 无尽模式的 game_over 使用无尽场景作为背景
            if self._game_over_is_endless and self.state == "game_over":
                self._draw_endless()
            else:
                self._draw_game()
            if self.state == "paused":
                self.pause_menu.draw_bg(self.canvas)
            elif self.state == "game_over":
                self.game_over_menu.draw_bg(self.canvas)
        pygame.transform.scale(self.canvas, self.screen.get_size(), self.screen)
        if self.state == "endless":
            self._draw_endless_hud()
        elif self.state in ("playing", "paused", "game_over"):
            if self._game_over_is_endless:
                # 无尽模式 game_over 也用普通 HUD
                self.hud.draw_text(self.screen,
                                  self.player1.hp, self.player2.hp,
                                  self.endless_level.get_collected_count(),
                                  self.endless_level.get_total_items())
            else:
                self._draw_hud_text()
            if self.online and self._disconnected:
                self._draw_disconnect_overlay()
        if self.state == "main_menu":
            self.main_menu.draw_text(self.screen)
        elif self.state == "online":
            self.online_menu.draw_text(self.screen)
        elif self.state == "level_select":
            self.level_menu.draw_text(self.screen)
        elif self.state == "multiplayer_level_select":
            if self.multi_level_menu:
                self.multi_level_menu.draw_text(self.screen)
        elif self.state == "paused":
            self.pause_menu.draw_text(self.screen)
        elif self.state == "game_over":
            self.game_over_menu.draw_text(self.screen)

    def _draw_disconnect_overlay(self):
        """联机断线遮罩"""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        font = pygame.font.Font(FONT_PATH, 48)
        text = font.render("连接断开", False, (255, 80, 80))
        self.screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2,
                                SCREEN_HEIGHT // 2 - text.get_height() // 2))

    def _draw_game(self):
        self.canvas.fill((0, 0, 0))  # 清空画布，消除残留像素
        self.bg.draw(self.canvas)
        # 天空原图顶部有断断续续的黑像素，用天蓝色覆盖掉
        self.canvas.fill((141, 216, 247), pygame.Rect(0, 0, LOGICAL_W, 1))
        offset = self.camera.offset()
        self.level.draw(self.canvas, offset)
        self.rope.draw(self.canvas, offset)
        self.player1.draw(self.canvas, offset)
        self.player2.draw(self.canvas, offset)
        self.hud.draw_bg(self.canvas,
                         self.player1.hp, self.player2.hp,
                         self.level.get_collected_count(),
                         self.level.get_total_items())


    def _draw_hud_text(self):
        self.hud.draw_text(self.screen,
                           self.player1.hp, self.player2.hp,
                           self.level.get_collected_count(),
                           self.level.get_total_items())

    def _draw_endless(self):
        """无尽模式渲染"""
        self.canvas.fill((0, 0, 0))
        self.bg.draw(self.canvas)
        self.canvas.fill((141, 216, 247), pygame.Rect(0, 0, LOGICAL_W, 1))
        offset = self.camera.offset()
        self.endless_level.draw(self.canvas, offset)
        self.rope.draw(self.canvas, offset)
        self.player1.draw(self.canvas, offset)
        self.player2.draw(self.canvas, offset)
        if self.boss:
            self.boss.draw(self.canvas, offset)
        self.particles.draw(self.canvas, offset)
        # 使用普通关卡同款血条和状态栏
        self.hud.draw_bg(self.canvas,
                         self.player1.hp, self.player2.hp,
                         self.endless_level.get_collected_count(),
                         self.endless_level.get_total_items())

    def _draw_endless_hud(self):
        """无尽模式 HUD（屏幕空间）"""
        # 普通关卡的血条文字（kun 计数等）
        self.hud.draw_text(self.screen,
                          self.player1.hp, self.player2.hp,
                          self.endless_level.get_collected_count(),
                          self.endless_level.get_total_items())
        # 无尽专属信息：屏幕居中靠上，分行显示（避开血条和kun计数）
        font = pygame.font.Font(FONT_PATH, 24)
        font.set_bold(True)
        center_x = SCREEN_WIDTH // 2
        base_y = 52
        line_gap = 24

        lines = [
            (f"距离: {int(self.endless_distance / 10)}m", WHITE),
            (f"得分: {self.endless_score}", YELLOW),
        ]
        for i, (text, color) in enumerate(lines):
            surf = font.render(text, False, color)
            self.screen.blit(surf,
                (center_x - surf.get_width() // 2, base_y + i * line_gap))

        # 预警阶段：屏幕中央闪烁提示
        if self.endless_phase == 1:
            warn_font = pygame.font.Font(FONT_PATH, 56)
            if (self._warning_timer // 15) % 2 == 0:
                warn_text = warn_font.render("BOSS 即将来袭！", False, RED)
                self.screen.blit(warn_text,
                    (SCREEN_WIDTH // 2 - warn_text.get_width() // 2,
                     SCREEN_HEIGHT // 2 - warn_text.get_height() // 2 - 40))


if __name__ == "__main__":
    Game().run()
