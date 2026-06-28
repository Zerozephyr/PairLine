# -*- coding: utf-8 -*-
"""主菜单、关卡选择、暂停、游戏结束界面

文字绕过 canvas 缩放，直接渲染到 1024×640 屏幕，字号 64（=16×SCALE），
避免 4× nearest 放大造成小字号文字笔画过粗模糊。
背景填充仍在 canvas 上完成。

所有按钮均支持键盘（↑↓←→ Enter Esc）和鼠标点击。
"""

import pygame
from PIL import Image
from config.settings import LOGICAL_W, LOGICAL_H, SCREEN_WIDTH, SCREEN_HEIGHT, SCALE, WHITE, BLACK, YELLOW, CYAN, GREEN, RED
from config.path import FONT_PATH, SELECT_ARROW, KUN_ITEM, HOME_BG_GIF

FONT_SIZE_TITLE = 64
FONT_SIZE_BODY = 48
FONT_SIZE_HINT = 32


def _s2s(x):
    """画布坐标 → 屏幕坐标"""
    return x * SCALE


def _load(path):
    return pygame.image.load(path).convert_alpha()


# ---------------------------------------------------------------------------
# 主菜单（GIF 背景 + 底部左右排布按钮）
# ---------------------------------------------------------------------------
def _load_gif_frames(path, target_size):
    """用 Pillow 提取 GIF 所有帧，缩放到 target_size，返回 [(surface, duration_ms), ...]"""
    pil = Image.open(path)
    frames = []
    for i in range(pil.n_frames):
        pil.seek(i)
        rgba = pil.convert("RGBA").resize(target_size, Image.NEAREST)
        data = rgba.tobytes()
        surf = pygame.image.fromstring(data, target_size, "RGBA")
        dur = pil.info.get("duration", 100)  # 毫秒
        frames.append((surf, dur))
    return frames


class MainMenu:
    def __init__(self):
        self.font = pygame.font.Font(FONT_PATH, FONT_SIZE_BODY)
        self.options = ["本地同屏双人", "远程联机模式"]
        self.selected = 0
        self.arrow = _load(SELECT_ARROW)
        self.option_rects = []

        # 加载 GIF 背景帧（256×160 逻辑画布）
        self._gif_frames = _load_gif_frames(HOME_BG_GIF, (LOGICAL_W, LOGICAL_H))
        self._gif_idx = 0
        self._gif_accum = 0       # 当前帧已累积毫秒
        self._last_tick = 0       # 上次 draw 时刻(ms)，首次 draw 时初始化

        # 按钮布局常量（屏幕像素）
        self._btn_w = 260
        self._btn_h = 64
        self._btn_gap = 40
        self._btn_y = SCREEN_HEIGHT - self._btn_h - 8  # 贴底，留 8px 边距

    def _get_button_rect(self, index):
        total_w = len(self.options) * self._btn_w + (len(self.options) - 1) * self._btn_gap
        start_x = (SCREEN_WIDTH - total_w) // 2
        x = start_x + index * (self._btn_w + self._btn_gap)
        return pygame.Rect(x, self._btn_y, self._btn_w, self._btn_h)

    # ------------------------------------------------------------------
    # 输入
    # ------------------------------------------------------------------
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_UP):
                self.selected = (self.selected - 1) % len(self.options)
            elif event.key in (pygame.K_RIGHT, pygame.K_DOWN):
                self.selected = (self.selected + 1) % len(self.options)
            elif event.key == pygame.K_RETURN:
                return self.options[self.selected]
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for rect, ret in self.option_rects:
                if rect.collidepoint(mx, my):
                    self.selected = self.options.index(ret) if ret in self.options else self.selected
                    return ret
        return None

    # ------------------------------------------------------------------
    # 绘制
    # ------------------------------------------------------------------
    def draw_bg(self, canvas):
        # 按 GIF 原始帧间隔逐帧轮播
        now = pygame.time.get_ticks()
        if self._last_tick == 0:
            self._last_tick = now
        dt = now - self._last_tick
        self._last_tick = now
        self._gif_accum += dt
        # 跳过已过期的帧（处理 lag 导致的堆积）
        while self._gif_accum >= self._gif_frames[self._gif_idx][1]:
            self._gif_accum -= self._gif_frames[self._gif_idx][1]
            self._gif_idx = (self._gif_idx + 1) % len(self._gif_frames)
        surf, _ = self._gif_frames[self._gif_idx]
        canvas.blit(surf, (0, 0))

    def draw_text(self, screen):
        self.option_rects = []

        for i, opt in enumerate(self.options):
            is_selected = (i == self.selected)
            btn_rect = self._get_button_rect(i)

            # 按钮底色（半透明暗色背景）
            btn_surf = pygame.Surface((btn_rect.width, btn_rect.height), pygame.SRCALPHA)
            if is_selected:
                btn_surf.fill((255, 255, 255, 30))  # 白色半透明
                border_color = YELLOW
                border_w = 3
            else:
                btn_surf.fill((0, 0, 0, 100))  # 黑色半透明
                border_color = (120, 120, 120)
                border_w = 2
            screen.blit(btn_surf, (btn_rect.x, btn_rect.y))
            pygame.draw.rect(screen, border_color, btn_rect, border_w, border_radius=8)

            # 按钮文字
            color = YELLOW if is_selected else WHITE
            text = self.font.render(opt, False, color)
            tx = btn_rect.centerx - text.get_width() // 2
            ty = btn_rect.centery - text.get_height() // 2
            screen.blit(text, (tx, ty))

            self.option_rects.append((btn_rect, opt))

            # 选中指示箭头（按钮上方居中，向下指）
            if is_selected:
                arrow_down = pygame.transform.rotate(self.arrow, -90)
                arrow_w = arrow_down.get_width() * SCALE
                arrow_h = arrow_down.get_height() * SCALE
                arrow_scaled = pygame.transform.scale(arrow_down, (arrow_w, arrow_h))
                ax = btn_rect.centerx - arrow_w // 2
                ay = btn_rect.top - arrow_h - 4
                screen.blit(arrow_scaled, (ax, ay))


# ---------------------------------------------------------------------------
# 关卡选择（卡片式布局）
# ---------------------------------------------------------------------------
class LevelSelectMenu:
    def __init__(self):
        self.font_title = pygame.font.Font(FONT_PATH, 64)
        self.font = pygame.font.Font(FONT_PATH, FONT_SIZE_BODY)
        self.font_small = pygame.font.Font(FONT_PATH, FONT_SIZE_HINT)
        # kun 道具图标（放大 3× = 48×48）
        raw_kun = pygame.image.load(KUN_ITEM).convert_alpha()
        self.kun_icon = pygame.transform.scale(raw_kun, (48, 48))
        self.levels = ["第一关", "第二关", "无尽模式"]
        self.selected = 0
        self.option_rects = []
        # 关卡状态（外部设置）
        self.level_unlocked = {"第一关": True, "第二关": False, "无尽模式": False}
        self.level_files = {"第一关": "level_1.json", "第二关": "level_2.json", "无尽模式": None}
        self.level_kun_records = {"第一关": 0, "第二关": 0, "无尽模式": 0}
        self.level_total_kun = {"第一关": 7, "第二关": 8, "无尽模式": "∞"}

        # 卡片布局常量（屏幕像素）
        self.card_w = 200
        self.card_h = 260
        self.card_gap = 60
        self._card_rects = []

    # ------------------------------------------------------------------
    # 布局计算
    # ------------------------------------------------------------------
    def _get_card_rect(self, index):
        """返回第 index 张卡片的屏幕坐标矩形"""
        total_w = len(self.levels) * self.card_w + (len(self.levels) - 1) * self.card_gap
        start_x = (SCREEN_WIDTH - total_w) // 2
        x = start_x + index * (self.card_w + self.card_gap)
        y = 150
        return pygame.Rect(x, y, self.card_w, self.card_h)

    # ------------------------------------------------------------------
    # 输入处理
    # ------------------------------------------------------------------
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_UP):
                self.selected = (self.selected - 1) % len(self.levels)
            elif event.key in (pygame.K_RIGHT, pygame.K_DOWN):
                self.selected = (self.selected + 1) % len(self.levels)
            elif event.key == pygame.K_RETURN:
                lvl = self.levels[self.selected]
                if self.level_unlocked.get(lvl, False):
                    return lvl
            elif event.key == pygame.K_ESCAPE:
                return "BACK"
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for i, rect in enumerate(self._card_rects):
                if rect.collidepoint(mx, my):
                    lvl = self.levels[i]
                    if self.level_unlocked.get(lvl, False):
                        return lvl
            for rect, ret in self.option_rects:
                if rect.collidepoint(mx, my):
                    return ret
        return None

    # ------------------------------------------------------------------
    # 绘制
    # ------------------------------------------------------------------
    def draw_bg(self, canvas):
        canvas.fill(BLACK)

    def _draw_lock_icon(self, screen, x, y, size=28):
        """在 (x, y) 绘制锁图标（左上角定位），size 为锁体宽度"""
        # 锁梁（顶部半圆弧 — 0→π 是上半圆）
        shackle_rect = pygame.Rect(x + size // 4, y, size // 2, size // 2)
        pygame.draw.arc(screen, (220, 220, 220), shackle_rect, 0, 3.1416, 3)
        # 锁体
        body_top = y + size // 3
        body_rect = pygame.Rect(x, body_top, size, size * 2 // 3)
        pygame.draw.rect(screen, (200, 200, 200), body_rect, border_radius=4)
        pygame.draw.rect(screen, (130, 130, 130), body_rect, 2, border_radius=4)
        # 钥匙孔
        kx, ky = x + size // 2, body_top + size // 3 + 2
        pygame.draw.circle(screen, (70, 70, 70), (kx, ky), size // 6)
        pygame.draw.rect(screen, (70, 70, 70), (kx - 1, ky, 2, size // 4))

    def draw_text(self, screen):
        self.option_rects = []
        self._card_rects = []

        # ---- 标题 ----
        title = self.font_title.render("选择关卡", False, CYAN)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 70))

        # ---- 关卡卡片 ----
        for i, lvl in enumerate(self.levels):
            unlocked = self.level_unlocked.get(lvl, False)
            is_selected = (i == self.selected)
            card_rect = self._get_card_rect(i)
            self._card_rects.append(card_rect)

            # 卡片底色
            if not unlocked:
                fill_color = (25, 25, 38)
                border_color = (55, 55, 65)
            elif is_selected:
                fill_color = (42, 50, 78)
                border_color = YELLOW
            else:
                fill_color = (32, 36, 54)
                border_color = (100, 120, 160)

            pygame.draw.rect(screen, fill_color, card_rect, border_radius=10)
            border_w = 4 if is_selected else 2
            pygame.draw.rect(screen, border_color, card_rect, border_w, border_radius=10)

            # 关卡名称（卡片顶部）
            name_color = WHITE if unlocked else (100, 100, 100)
            name_text = self.font_small.render(lvl, False, name_color)
            name_x = card_rect.centerx - name_text.get_width() // 2
            name_y = card_rect.top + 16
            screen.blit(name_text, (name_x, name_y))

            # kun 图标（卡片中央）
            if unlocked:
                kun_img = self.kun_icon
            else:
                # 未解锁时把图标变灰
                kun_img = self.kun_icon.copy()
                kun_img.fill((60, 60, 60, 200), special_flags=pygame.BLEND_RGBA_MULT)
            icon_x = card_rect.centerx - kun_img.get_width() // 2
            icon_y = card_rect.centery - kun_img.get_height() // 2 - 8
            screen.blit(kun_img, (icon_x, icon_y))

            # 收集数量：× 0/7
            kun_count = self.level_kun_records.get(lvl, 0)
            kun_total = self.level_total_kun.get(lvl, 0)
            kun_color = WHITE if unlocked else (100, 100, 100)
            kun_text = self.font_small.render(
                f"× {kun_count}/{kun_total}", False, kun_color
            )
            kun_x = card_rect.centerx - kun_text.get_width() // 2
            kun_y = icon_y + kun_img.get_height() + 10
            screen.blit(kun_text, (kun_x, kun_y))

            # 未解锁 → 右上角锁图标
            if not unlocked:
                lock_size = 28
                self._draw_lock_icon(
                    screen,
                    card_rect.right - lock_size - 12,
                    card_rect.top + 12,
                    lock_size,
                )

        # ---- 底部提示 ----
        hint = self.font.render("ESC 返回", False, (150, 150, 150))
        hx = SCREEN_WIDTH // 2 - hint.get_width() // 2
        hy = SCREEN_HEIGHT - _s2s(22)
        screen.blit(hint, (hx, hy))
        self.option_rects.append((hint.get_rect(topleft=(hx, hy)), "BACK"))


# ---------------------------------------------------------------------------
# 暂停菜单
# ---------------------------------------------------------------------------
class PauseMenu:
    def __init__(self):
        self.font_large = pygame.font.Font(FONT_PATH, FONT_SIZE_TITLE)
        self.font = pygame.font.Font(FONT_PATH, FONT_SIZE_BODY)
        self.options = ["继续游戏", "重新开始", "返回主菜单"]
        self.selected = 0
        self.active = False
        self.arrow = _load(SELECT_ARROW)
        self.option_rects = []

    def handle_event(self, event):
        if not self.active:
            return None
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected = (self.selected - 1) % len(self.options)
            elif event.key == pygame.K_DOWN:
                self.selected = (self.selected + 1) % len(self.options)
            elif event.key == pygame.K_RETURN:
                return self.options[self.selected]
            elif event.key == pygame.K_ESCAPE:
                self.active = False
                return "继续游戏"
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for rect, ret in self.option_rects:
                if rect.collidepoint(mx, my):
                    return ret
        return None

    def draw_bg(self, canvas):
        if not self.active:
            return
        overlay = pygame.Surface((LOGICAL_W, LOGICAL_H))
        overlay.set_alpha(180)
        overlay.fill(BLACK)
        canvas.blit(overlay, (0, 0))

    def draw_text(self, screen):
        if not self.active:
            return
        self.option_rects = []

        screen_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        screen_overlay.set_alpha(180)
        screen_overlay.fill(BLACK)
        screen.blit(screen_overlay, (0, 0))

        title = self.font_large.render("暂停", False, WHITE)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, _s2s(30)))

        for i, opt in enumerate(self.options):
            color = YELLOW if i == self.selected else WHITE
            text = self.font.render(opt, False, color)
            x = SCREEN_WIDTH // 2 - text.get_width() // 2
            y = _s2s(75) + i * _s2s(20)
            screen.blit(text, (x, y))
            self.option_rects.append((text.get_rect(topleft=(x, y)), opt))
            if i == self.selected:
                arrow_y = y + (text.get_height() - self.arrow.get_height() * SCALE) // 2
                screen.blit(pygame.transform.scale(self.arrow, (self.arrow.get_width() * SCALE, self.arrow.get_height() * SCALE)),
                            (x - _s2s(12), arrow_y))


# ---------------------------------------------------------------------------
# 游戏结束界面（胜利/失败均显示按钮选项）
# ---------------------------------------------------------------------------
class GameOverMenu:
    def __init__(self):
        self.font_large = pygame.font.Font(FONT_PATH, FONT_SIZE_TITLE)
        self.font = pygame.font.Font(FONT_PATH, FONT_SIZE_BODY)
        self.font_hint = pygame.font.Font(FONT_PATH, FONT_SIZE_HINT)
        self.arrow = _load(SELECT_ARROW)
        self.active = False
        self.win = False
        self.score = 0
        self.total_items = 0
        self.endless = False
        self.selected = 0
        self.options = []        # [(label, action), ...]
        self.option_rects = []
        self.online_guest = False  # 联机客机标记

    def setup(self, win, endless, score, total_items, has_next=False, online_guest=False):
        """每次弹出前调用，设置具体选项"""
        self.active = True
        self.win = win
        self.endless = endless
        self.score = score
        self.total_items = total_items
        self.selected = 0
        self.online_guest = online_guest

        if online_guest:
            self.options = []  # 客机无选项，等待房主
        elif endless:
            self.options = [("重新开始", "restart"), ("返回主菜单", "back")]
        elif win:
            self.options = []
            if has_next:
                self.options.append(("下一关", "next_level"))
            self.options.append(("关卡选择", "level_select"))
        else:
            self.options = [("重新开始", "restart"), ("关卡选择", "level_select")]

    def handle_event(self, event):
        """处理键盘和鼠标输入，返回动作字符串或 None"""
        if not self.active:
            return None
        # 联机客机：仅允许 ESC 断开
        if self.online_guest:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return "back"
            return None
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_LEFT):
                self.selected = (self.selected - 1) % len(self.options)
            elif event.key in (pygame.K_DOWN, pygame.K_RIGHT):
                self.selected = (self.selected + 1) % len(self.options)
            elif event.key == pygame.K_RETURN:
                return self.options[self.selected][1]
            elif event.key == pygame.K_r:
                # 快捷键：R 始终对应重新开始（如果选项中有的话）
                for label, action in self.options:
                    if action == "restart":
                        return "restart"
            elif event.key == pygame.K_ESCAPE:
                for label, action in self.options:
                    if action in ("level_select", "back"):
                        return action
                return "back"
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for rect, ret in self.option_rects:
                if rect.collidepoint(mx, my):
                    # 同步 selected 到点击项
                    for i, (lbl, act) in enumerate(self.options):
                        if act == ret:
                            self.selected = i
                    return ret
        return None

    def draw_bg(self, canvas):
        if not self.active:
            return
        overlay = pygame.Surface((LOGICAL_W, LOGICAL_H))
        overlay.set_alpha(200)
        overlay.fill(BLACK)
        canvas.blit(overlay, (0, 0))

    def draw_text(self, screen):
        if not self.active:
            return
        self.option_rects = []

        screen_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        screen_overlay.set_alpha(200)
        screen_overlay.fill(BLACK)
        screen.blit(screen_overlay, (0, 0))

        # 标题
        title_text = "通关成功！" if self.win else "游戏结束"
        color = (0, 255, 0) if self.win else (255, 0, 0)
        title = self.font_large.render(title_text, False, color)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, _s2s(30)))

        # 分数
        if self.endless:
            score_text = self.font.render(
                f"最终得分: {self.score}  收集kun: {self.total_items}", False, WHITE)
        else:
            score_text = self.font.render(
                f"收集道具: {self.score} / {self.total_items}", False, WHITE)
        screen.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, _s2s(75)))

        # 联机客机：显示等待提示
        if self.online_guest:
            wait_text = self.font.render("等待房主选择...", False, (200, 200, 200))
            screen.blit(wait_text, (SCREEN_WIDTH // 2 - wait_text.get_width() // 2, _s2s(105)))
            hint = self.font_hint.render("ESC 断开连接", False, (150, 150, 150))
            screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - _s2s(22)))
            self.option_rects.append((hint.get_rect(topleft=(hint.get_rect().x, SCREEN_HEIGHT - _s2s(22))), "back"))
            return

        # 按钮
        btn_w, btn_h = 260, 56
        btn_gap = 16
        start_y = _s2s(100)

        for i, (label, action) in enumerate(self.options):
            is_sel = (i == self.selected)
            btn_rect = pygame.Rect(
                SCREEN_WIDTH // 2 - btn_w // 2,
                start_y + i * (btn_h + btn_gap),
                btn_w, btn_h)

            # 按钮底色
            btn_surf = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
            if is_sel:
                btn_surf.fill((255, 255, 255, 30))
                border = YELLOW
                border_w = 3
            else:
                btn_surf.fill((0, 0, 0, 100))
                border = (120, 120, 120)
                border_w = 2
            screen.blit(btn_surf, (btn_rect.x, btn_rect.y))
            pygame.draw.rect(screen, border, btn_rect, border_w, border_radius=8)

            # 按钮文字
            text_color = YELLOW if is_sel else WHITE
            text = self.font.render(label, False, text_color)
            tx = btn_rect.centerx - text.get_width() // 2
            ty = btn_rect.centery - text.get_height() // 2
            screen.blit(text, (tx, ty))

            self.option_rects.append((btn_rect, action))

            # 选中箭头
            if is_sel:
                arrow_scaled = pygame.transform.scale(
                    self.arrow,
                    (self.arrow.get_width() * SCALE, self.arrow.get_height() * SCALE))
                ax = btn_rect.left - arrow_scaled.get_width() - 8
                ay = btn_rect.centery - arrow_scaled.get_height() // 2
                screen.blit(arrow_scaled, (ax, ay))


# ---------------------------------------------------------------------------
# 远程联机模式（创建/加入房间）
# ---------------------------------------------------------------------------
class OnlineMenu:
    """远程联机界面 — 子状态机驱动

    子状态:
        mode_select       → 选择"创建房间"或"加入房间"
        join_input        → 输入 4 位房间码
        creating          → 等待 HTTP 创建房间
        room_code_display → 显示房间码，等待好友
        joining           → 等待 HTTP 加入房间
        waiting           → 好友已加入，短暂过渡
        error             → 显示错误信息
    """

    def __init__(self):
        self.font_large = pygame.font.Font(FONT_PATH, FONT_SIZE_TITLE)
        self.font = pygame.font.Font(FONT_PATH, FONT_SIZE_BODY)
        self.font_hint = pygame.font.Font(FONT_PATH, FONT_SIZE_HINT)
        self.font_big = pygame.font.Font(FONT_PATH, 72)  # 房间码大字体
        self.option_rects = []

        # 子状态
        self.sub_state = "mode_select"
        self._modes = ["创建房间", "加入房间"]
        self._mode_sel = 0

        # 房间码输入
        self.input_digits = []
        self._blink_timer = 0

        # 网络
        self.network = None
        self._room_code = None
        self._role = None
        self._error_msg = ""
        self._connect_started = False

        # 按钮布局
        self._btn_w = 260
        self._btn_h = 64
        self._btn_gap = 40
        self._btn_y = SCREEN_HEIGHT - self._btn_h - 8

    def _get_button_rect(self, index):
        total_w = len(self._modes) * self._btn_w + (len(self._modes) - 1) * self._btn_gap
        start_x = (SCREEN_WIDTH - total_w) // 2
        x = start_x + index * (self._btn_w + self._btn_gap)
        return pygame.Rect(x, self._btn_y, self._btn_w, self._btn_h)

    # ------------------------------------------------------------------
    # 输入
    # ------------------------------------------------------------------
    def handle_event(self, event):
        if self.sub_state == "mode_select":
            return self._handle_mode_select(event)
        elif self.sub_state == "join_input":
            return self._handle_join_input(event)
        elif self.sub_state == "room_code_display":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if self.network:
                    self.network.stop()
                    self.network = None
                self._reset()
                return "BACK"
        elif self.sub_state == "error":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self._reset()
                    return "BACK"
                elif event.key == pygame.K_RETURN:
                    self._reset()
        return None

    def _handle_mode_select(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_UP):
                self._mode_sel = (self._mode_sel - 1) % len(self._modes)
            elif event.key in (pygame.K_RIGHT, pygame.K_DOWN):
                self._mode_sel = (self._mode_sel + 1) % len(self._modes)
            elif event.key == pygame.K_RETURN:
                if self._mode_sel == 0:
                    self._start_create_room()
                else:
                    self.sub_state = "join_input"
                    self.input_digits = []
            elif event.key == pygame.K_ESCAPE:
                return "BACK"
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for i in range(len(self._modes)):
                rect = self._get_button_rect(i)
                if rect.collidepoint(mx, my):
                    if i == 0:
                        self._start_create_room()
                    else:
                        self.sub_state = "join_input"
                        self.input_digits = []
        return None

    def _handle_join_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.sub_state = "mode_select"
                self.input_digits = []
            elif event.key == pygame.K_BACKSPACE:
                if self.input_digits:
                    self.input_digits.pop()
            elif event.key == pygame.K_RETURN:
                if len(self.input_digits) == 4:
                    code = "".join(self.input_digits)
                    self._start_join_room(code)
            elif event.key in (pygame.K_0, pygame.K_1, pygame.K_2, pygame.K_3,
                               pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7,
                               pygame.K_8, pygame.K_9,
                               pygame.K_KP0, pygame.K_KP1, pygame.K_KP2,
                               pygame.K_KP3, pygame.K_KP4, pygame.K_KP5,
                               pygame.K_KP6, pygame.K_KP7, pygame.K_KP8,
                               pygame.K_KP9):
                if len(self.input_digits) < 4:
                    if event.key >= pygame.K_KP0:
                        digit = str(event.key - pygame.K_KP0)
                    else:
                        digit = str(event.key - pygame.K_0)
                    self.input_digits.append(digit)
        return None

    def _start_create_room(self):
        self.sub_state = "creating"
        self._error_msg = ""
        self._connect_started = False
        try:
            from network.client import NetworkClient
            self.network = NetworkClient()
            code, role = self.network.create_room()
            self._room_code = code
            self._role = role
            self.network.connect_ws(code, role)
            self._connect_started = True
            self.sub_state = "room_code_display"
        except Exception as e:
            self._error_msg = str(e)
            self.sub_state = "error"
            if self.network:
                self.network = None

    def _start_join_room(self, code):
        self.sub_state = "joining"
        self._error_msg = ""
        self._connect_started = False
        try:
            from network.client import NetworkClient
            self.network = NetworkClient()
            role = self.network.join_room(code)
            self._room_code = code
            self._role = role
            self.network.connect_ws(code, role)
            self._connect_started = True
            self.sub_state = "waiting"
        except Exception as e:
            self._error_msg = str(e)
            self.sub_state = "error"
            if self.network:
                self.network = None

    def _reset(self):
        self.sub_state = "mode_select"
        self._mode_sel = 0
        self.input_digits = []
        self._error_msg = ""
        self._connect_started = False
        if self.network:
            self.network.stop()
            self.network = None

    def poll_network(self):
        """主循环每帧调用 — 检查网络事件"""
        if self.network is None:
            return None

        # WebSocket 连接等待
        if self._connect_started and not self.network.connected.is_set():
            self.network.wait_connected(timeout=0.01)
            return None

        if not self.network.connected.is_set():
            return None

        # 处理接收消息
        for msg in self.network.poll():
            t = msg.get("type", "")
            if t == "player_joined":
                # 忽略自己触发的加入事件
                if msg.get("data", {}).get("role") == self._role:
                    continue
                if self.sub_state in ("room_code_display", "waiting"):
                    self.sub_state = "waiting"
                    # 短暂延迟后返回 CONNECTED（在主循环中计数）
                    self._connected_frames = 60  # 1 秒 @ 60fps
            elif t == "player_left":
                self._error_msg = "好友已断开连接"
                self.sub_state = "error"

        # waiting 倒计时
        if self.sub_state == "waiting":
            self._connected_frames -= 1
            if self._connected_frames <= 0:
                return "CONNECTED"
        return None

    # ------------------------------------------------------------------
    # 绘制
    # ------------------------------------------------------------------
    def draw_bg(self, canvas):
        canvas.fill(BLACK)

    def draw_text(self, screen):
        self.option_rects = []

        if self.sub_state == "mode_select":
            self._draw_mode_select(screen)
        elif self.sub_state == "join_input":
            self._draw_join_input(screen)
        elif self.sub_state == "creating":
            self._draw_status(screen, "正在创建房间...")
        elif self.sub_state == "joining":
            self._draw_status(screen, "正在加入房间...")
        elif self.sub_state == "room_code_display":
            self._draw_room_code(screen)
        elif self.sub_state == "waiting":
            self._draw_status(screen, "好友已加入！即将进入关卡选择...")
        elif self.sub_state == "error":
            self._draw_error(screen)

    def _draw_mode_select(self, screen):
        title = self.font_large.render("远程联机模式", False, CYAN)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, _s2s(30)))

        for i, opt in enumerate(self._modes):
            is_sel = (i == self._mode_sel)
            btn_rect = self._get_button_rect(i)

            btn_surf = pygame.Surface((btn_rect.width, btn_rect.height), pygame.SRCALPHA)
            if is_sel:
                btn_surf.fill((255, 255, 255, 30))
                border = YELLOW
                border_w = 3
            else:
                btn_surf.fill((0, 0, 0, 100))
                border = (120, 120, 120)
                border_w = 2
            screen.blit(btn_surf, (btn_rect.x, btn_rect.y))
            pygame.draw.rect(screen, border, btn_rect, border_w, border_radius=8)

            color = YELLOW if is_sel else WHITE
            text = self.font.render(opt, False, color)
            tx = btn_rect.centerx - text.get_width() // 2
            ty = btn_rect.centery - text.get_height() // 2
            screen.blit(text, (tx, ty))

        hint = self.font_hint.render("ESC 返回", False, (150, 150, 150))
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2,
                           SCREEN_HEIGHT - _s2s(24)))

    def _draw_join_input(self, screen):
        title = self.font_large.render("加入房间", False, CYAN)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, _s2s(30)))

        prompt = self.font.render("请输入4位房间号:", False, WHITE)
        screen.blit(prompt, (SCREEN_WIDTH // 2 - prompt.get_width() // 2, _s2s(60)))

        # 输入框
        box_w, box_h = 260, 80
        box_x = SCREEN_WIDTH // 2 - box_w // 2
        box_y = _s2s(80)
        pygame.draw.rect(screen, (50, 50, 70), (box_x, box_y, box_w, box_h),
                         border_radius=8)
        pygame.draw.rect(screen, YELLOW, (box_x, box_y, box_w, box_h), 2,
                         border_radius=8)

        # 数字显示
        digits_str = "".join(self.input_digits).ljust(4, "_")
        digit_text = self.font_big.render(digits_str, False, WHITE)
        dx = box_x + box_w // 2 - digit_text.get_width() // 2
        dy = box_y + box_h // 2 - digit_text.get_height() // 2
        screen.blit(digit_text, (dx, dy))

        hint = self.font_hint.render("Enter 确认  ESC 返回  Backspace 删除",
                                     False, (150, 150, 150))
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2,
                           box_y + box_h + 30))

    def _draw_status(self, screen, msg):
        title = self.font_large.render("远程联机模式", False, CYAN)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, _s2s(30)))

        text = self.font.render(msg, False, WHITE)
        screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, _s2s(80)))

    def _draw_room_code(self, screen):
        title = self.font_large.render("房间已创建", False, GREEN)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, _s2s(20)))

        hint1 = self.font.render("将房间号告诉好友:", False, WHITE)
        screen.blit(hint1, (SCREEN_WIDTH // 2 - hint1.get_width() // 2, _s2s(58)))

        # 房间码大框
        box_w, box_h = 300, 100
        box_x = SCREEN_WIDTH // 2 - box_w // 2
        box_y = _s2s(80)
        pygame.draw.rect(screen, (20, 30, 50), (box_x, box_y, box_w, box_h),
                         border_radius=12)
        pygame.draw.rect(screen, GREEN, (box_x, box_y, box_w, box_h), 3,
                         border_radius=12)

        code_text = self.font_big.render(self._room_code or "----", False, GREEN)
        cx = box_x + box_w // 2 - code_text.get_width() // 2
        cy = box_y + box_h // 2 - code_text.get_height() // 2
        screen.blit(code_text, (cx, cy))

        hint2 = self.font_hint.render("等待好友加入...  ESC 取消",
                                      False, (150, 150, 150))
        screen.blit(hint2, (SCREEN_WIDTH // 2 - hint2.get_width() // 2,
                            box_y + box_h + 30))

    def _draw_error(self, screen):
        title = self.font_large.render("出错了", False, RED)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, _s2s(30)))

        err_text = self.font.render(self._error_msg, False, WHITE)
        screen.blit(err_text, (SCREEN_WIDTH // 2 - err_text.get_width() // 2, _s2s(80)))

        hint = self.font_hint.render("Enter 重试  ESC 返回", False, (150, 150, 150))
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, _s2s(120)))


# ---------------------------------------------------------------------------
# 多人联机关卡选择（房主选择，客机等待）
# ---------------------------------------------------------------------------
class MultiplayerLevelSelectMenu:
    """联机模式关卡选择 — 仅房主可操作，客机显示等待提示

    - 房主用键盘选择关卡并回车确认
    - 客机看到房主的光标移动但不能操作
    - 房主确认后双方同步开始游戏
    """

    def __init__(self, network, role):
        self.font_title = pygame.font.Font(FONT_PATH, 64)
        self.font = pygame.font.Font(FONT_PATH, FONT_SIZE_BODY)
        self.font_small = pygame.font.Font(FONT_PATH, FONT_SIZE_HINT)
        self.font_hint = pygame.font.Font(FONT_PATH, FONT_SIZE_HINT)
        raw_kun = pygame.image.load(KUN_ITEM).convert_alpha()
        self.kun_icon = pygame.transform.scale(raw_kun, (48, 48))
        self.levels = ["第一关", "第二关"]
        self.level_files = {"第一关": "level_1.json", "第二关": "level_2.json"}
        self.level_unlocked = {"第一关": True, "第二关": False}
        self.level_kun_records = {"第一关": 0, "第二关": 0}
        self.level_total_kun = {"第一关": 7, "第二关": 8}

        self.network = network
        self.role = role                # "host" (房主) 或 "guest" (客机)
        self.host_selected = 0          # 房主当前选中的关卡索引
        self.option_rects = []
        self._is_host = (role == "host")

        # 卡片布局
        self.card_w = 200
        self.card_h = 260
        self.card_gap = 60
        self._card_rects = []

        # 游戏开始
        self._game_start_level = None

    def _get_card_rect(self, index):
        total_w = len(self.levels) * self.card_w + (len(self.levels) - 1) * self.card_gap
        start_x = (SCREEN_WIDTH - total_w) // 2
        x = start_x + index * (self.card_w + self.card_gap)
        y = 150
        return pygame.Rect(x, y, self.card_w, self.card_h)

    # ------------------------------------------------------------------
    # 输入
    # ------------------------------------------------------------------
    def handle_event(self, event):
        if not self._is_host:
            # 客机只能 ESC 退出
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return "BACK"
            return None
        # 房主操作
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_UP):
                self.host_selected = (self.host_selected - 1) % len(self.levels)
                self._send_selection()
            elif event.key in (pygame.K_RIGHT, pygame.K_DOWN):
                self.host_selected = (self.host_selected + 1) % len(self.levels)
                self._send_selection()
            elif event.key == pygame.K_RETURN:
                lvl = self.levels[self.host_selected]
                if self.level_unlocked.get(lvl, False):
                    self._send_game_start(lvl)
            elif event.key == pygame.K_ESCAPE:
                return "BACK"
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for i, rect in enumerate(self._card_rects):
                if rect.collidepoint(mx, my):
                    lvl = self.levels[i]
                    if self.level_unlocked.get(lvl, False):
                        self.host_selected = i
                        self._send_selection()
                        self._send_game_start(lvl)
        return None

    def _send_selection(self):
        """房主发送当前选中关卡"""
        lvl_name = self.levels[self.host_selected]
        self.network.send("level_select", {
            "level": self.level_files[lvl_name],
            "level_name": lvl_name,
            "selected_index": self.host_selected,
        })

    def _send_game_start(self, lvl_name):
        """房主发送游戏开始"""
        self.network.send("game_start", {
            "level": self.level_files[lvl_name],
            "level_name": lvl_name,
        })
        self._game_start_level = self.level_files[lvl_name]

    # ------------------------------------------------------------------
    # 网络轮询
    # ------------------------------------------------------------------
    def poll_network(self):
        """处理网络消息"""
        if self.network is None or not self.network.connected.is_set():
            return None

        for msg in self.network.poll():
            t = msg.get("type", "")
            data = msg.get("data", {})

            if t == "level_select":
                # 更新房主的选中位置（客机用来同步显示）
                idx = data.get("selected_index", -1)
                if 0 <= idx < len(self.levels):
                    self.host_selected = idx

            elif t == "game_start":
                self._game_start_level = data.get("level", "")
                return "start"

            elif t == "player_left":
                return "disconnect"

        # 房主确认后返回 start
        # 注意：不在此处重置 _game_start_level，
        # 因为 main.py 的 _start_online_game() 需要读取它，
        # 重置由 _start_online_game() 负责（line 174）。
        if self._game_start_level:
            return "start"
        return None

    # ------------------------------------------------------------------
    # 绘制
    # ------------------------------------------------------------------
    def draw_bg(self, canvas):
        canvas.fill(BLACK)

    def _draw_lock_icon(self, screen, x, y, size=28):
        shackle_rect = pygame.Rect(x + size // 4, y, size // 2, size // 2)
        pygame.draw.arc(screen, (220, 220, 220), shackle_rect, 0, 3.1416, 3)
        body_top = y + size // 3
        body_rect = pygame.Rect(x, body_top, size, size * 2 // 3)
        pygame.draw.rect(screen, (200, 200, 200), body_rect, border_radius=4)
        pygame.draw.rect(screen, (130, 130, 130), body_rect, 2, border_radius=4)
        kx, ky = x + size // 2, body_top + size // 3 + 2
        pygame.draw.circle(screen, (70, 70, 70), (kx, ky), size // 6)
        pygame.draw.rect(screen, (70, 70, 70), (kx - 1, ky, 2, size // 4))

    def draw_text(self, screen):
        self.option_rects = []
        self._card_rects = []

        # 标题
        title = self.font_title.render("选择关卡", False, CYAN)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 30))

        # 角色 + 状态提示
        if self._is_host:
            role_text = self.font_small.render("你: 房主 P1 (黄) — 选择关卡后按 Enter", False, WHITE)
        else:
            role_text = self.font_small.render("你: 客机 P2 (青) — 等待房主选择关卡...", False,
                                               (180, 180, 180))
        screen.blit(role_text, (SCREEN_WIDTH // 2 - role_text.get_width() // 2, 100))

        if not self._is_host:
            status = "等待房主选择关卡..."
            status_color = (150, 150, 150)
            status_text = self.font_small.render(status, False, status_color)
            screen.blit(status_text, (SCREEN_WIDTH // 2 - status_text.get_width() // 2, 125))

        # 卡片
        for i, lvl in enumerate(self.levels):
            unlocked = self.level_unlocked.get(lvl, False)
            card_rect = self._get_card_rect(i)
            self._card_rects.append(card_rect)

            # 底色
            if not unlocked:
                fill_color = (25, 25, 38)
            else:
                fill_color = (32, 36, 54)

            pygame.draw.rect(screen, fill_color, card_rect, border_radius=10)

            # 房主光标边框（黄）
            if i == self.host_selected:
                border_color = YELLOW
                border_w = 4
                pygame.draw.rect(screen, border_color, card_rect, border_w, border_radius=10)
                # 房主标签
                lbl = self.font_small.render("P1" if self._is_host else "房主", False, YELLOW)
                lbl_x = card_rect.centerx - lbl.get_width() // 2
                lbl_y = card_rect.top + 4
                screen.blit(lbl, (lbl_x, lbl_y))
            else:
                border_color = (55, 55, 65) if not unlocked else (100, 120, 160)
                pygame.draw.rect(screen, border_color, card_rect, 2, border_radius=10)

            # 关卡名称
            name_color = WHITE if unlocked else (100, 100, 100)
            name_text = self.font_small.render(lvl, False, name_color)
            name_x = card_rect.centerx - name_text.get_width() // 2
            name_y = card_rect.top + 28
            screen.blit(name_text, (name_x, name_y))

            # kun 图标
            if unlocked:
                kun_img = self.kun_icon
            else:
                kun_img = self.kun_icon.copy()
                kun_img.fill((60, 60, 60, 200), special_flags=pygame.BLEND_RGBA_MULT)
            icon_x = card_rect.centerx - kun_img.get_width() // 2
            icon_y = card_rect.centery - kun_img.get_height() // 2 - 8
            screen.blit(kun_img, (icon_x, icon_y))

            # 收集数量
            kun_count = self.level_kun_records.get(lvl, 0)
            kun_total = self.level_total_kun.get(lvl, 0)
            kun_color = WHITE if unlocked else (100, 100, 100)
            kun_text = self.font_small.render(
                f"× {kun_count}/{kun_total}", False, kun_color
            )
            kun_x = card_rect.centerx - kun_text.get_width() // 2
            kun_y = icon_y + kun_img.get_height() + 10
            screen.blit(kun_text, (kun_x, kun_y))

            # 未解锁锁图标
            if not unlocked:
                lock_size = 28
                self._draw_lock_icon(
                    screen,
                    card_rect.right - lock_size - 12,
                    card_rect.top + 12,
                    lock_size,
                )

        # 底部返回提示
        hint = self.font_hint.render("ESC 返回主菜单", False, (150, 150, 150))
        hx = SCREEN_WIDTH // 2 - hint.get_width() // 2
        hy = SCREEN_HEIGHT - _s2s(22)
        screen.blit(hint, (hx, hy))
        self.option_rects.append((hint.get_rect(topleft=(hx, hy)), "BACK"))
