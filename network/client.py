# -*- coding: utf-8 -*-
"""网络客户端：Socket.IO + HTTP，后台线程自动处理 I/O

与服务器 Flask-SocketIO 协议对接。所有 Pygame 调用仅在主线程进行；
网络回调仅将消息推入线程安全队列。
"""

import queue
import threading
import time
import logging

import requests
import socketio

from config.settings import SERVER_URL
from network.protocol import (
    MSG_PLAYER_STATE, MSG_LEVEL_SELECT, MSG_GAME_START,
    MSG_PLAYER_JOINED, MSG_PLAYER_LEFT, MSG_GAME_EVENT, MSG_PING,
)

logger = logging.getLogger("pairline-net")

# ---- 静默 SSL 自签证书警告 ----
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class NetworkClient:
    """远程联机客户端。

    使用方式：
        net = NetworkClient()
        code, role = net.create_room()          # 创建房间
        # 或者
        role = net.join_room("1234")            # 加入房间
        net.connect_ws(code, role)              # 建立 WebSocket
        ...
        msgs = net.poll()                       # 主线程每帧调用
        net.send("player_state", {...})         # 主线程发送
        net.stop()                              # 断开
    """

    def __init__(self):
        self._sio = socketio.Client(ssl_verify=False, logger=False, engineio_logger=False)
        self.incoming = queue.Queue()
        self.room_code = None
        self.role = None           # "host" | "guest"
        self.connected = threading.Event()
        self.peer_joined = threading.Event()
        self.peer_left = threading.Event()
        self._last_remote_state = None
        self.latency_ms = 0
        self._ping_seq = 0

        # 注册 Socket.IO 事件回调（这些回调在后台网络线程执行）
        self._sio.on("player_state", namespace="/game")(self._on_player_state)
        self._sio.on("player_joined", namespace="/game")(self._on_player_joined)
        self._sio.on("player_left", namespace="/game")(self._on_player_left)
        self._sio.on("level_select", namespace="/game")(self._on_level_select)
        self._sio.on("game_start", namespace="/game")(self._on_game_start)
        self._sio.on("game_event", namespace="/game")(self._on_game_event)
        self._sio.on("ping", namespace="/game")(self._on_ping)
        self._sio.on("error", namespace="/game")(self._on_error)
        self._sio.on("game_over_action", namespace="/game")(self._on_game_over_action)

    # ------------------------------------------------------------------
    # HTTP API（同步阻塞，仅在菜单场景调用）
    # ------------------------------------------------------------------
    def create_room(self):
        """创建房间 → (room_code, 'host')。失败抛异常。"""
        try:
            r = requests.post(f"{SERVER_URL}/api/rooms", verify=False, timeout=10)
            data = r.json()
            if r.status_code != 200 or "error" in data:
                raise RuntimeError(data.get("error", "创建失败"))
            self.room_code = data["room_code"]
            self.role = "host"
            return self.room_code, "host"
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"无法连接服务器: {e}")

    def join_room(self, code):
        """加入房间 → 'guest'。失败抛异常。"""
        try:
            r = requests.post(f"{SERVER_URL}/api/rooms/{code}/join", verify=False, timeout=10)
            data = r.json()
            if r.status_code != 200 or "error" in data:
                raise RuntimeError(data.get("error", "加入失败"))
            self.room_code = code
            self.role = "guest"
            return "guest"
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"无法连接服务器: {e}")

    # ------------------------------------------------------------------
    # WebSocket 连接
    # ------------------------------------------------------------------
    def connect_ws(self, code, role):
        """建立 WebSocket 连接（阻塞直到连接完成或超时）。

        在后台线程中连接，避免阻塞 Pygame 主循环。
        """
        self.room_code = code
        self.role = role

        def _connect():
            try:
                url = f"{SERVER_URL}?room={code}&role={role}"
                self._sio.connect(url, namespaces=["/game"], wait_timeout=10)
                self.connected.set()
            except Exception as e:
                logger.error(f"WebSocket 连接失败: {e}")
                self.incoming.put({"type": "error", "data": {"message": str(e)}})

        t = threading.Thread(target=_connect, daemon=True)
        t.start()

    def wait_connected(self, timeout=10):
        """等待 WebSocket 连接完成"""
        return self.connected.wait(timeout)

    # ------------------------------------------------------------------
    # 发送（主线程调用，非阻塞）
    # ------------------------------------------------------------------
    def send(self, msg_type, data):
        """发送消息到服务器（非阻塞）"""
        if not self.connected.is_set():
            return
        try:
            self._sio.emit(msg_type, data, namespace="/game")
        except Exception as e:
            logger.error(f"发送失败: {e}")

    # ------------------------------------------------------------------
    # 轮询（主线程每帧调用）
    # ------------------------------------------------------------------
    def poll(self):
        """非阻塞排空接收队列，返回消息列表"""
        msgs = []
        while True:
            try:
                msgs.append(self.incoming.get_nowait())
            except queue.Empty:
                break
        return msgs

    def get_remote_state(self):
        """获取最新远程玩家状态（线程安全）"""
        return self._last_remote_state

    # ------------------------------------------------------------------
    # 停止
    # ------------------------------------------------------------------
    def stop(self):
        """断开连接并清理"""
        self.connected.clear()
        try:
            self._sio.disconnect()
        except Exception:
            pass

    # ==================================================================
    # Socket.IO 事件回调（后台线程）
    # ==================================================================
    def _on_player_state(self, data):
        self._last_remote_state = data
        self.incoming.put({"type": MSG_PLAYER_STATE, "data": data})

    def _on_player_joined(self, data):
        self.peer_joined.set()
        self.incoming.put({"type": MSG_PLAYER_JOINED, "data": data})

    def _on_player_left(self, data):
        self.peer_left.set()
        self.peer_joined.clear()
        self.incoming.put({"type": MSG_PLAYER_LEFT, "data": data})

    def _on_level_select(self, data):
        self.incoming.put({"type": MSG_LEVEL_SELECT, "data": data})

    def _on_game_start(self, data):
        self.incoming.put({"type": MSG_GAME_START, "data": data})

    def _on_game_event(self, data):
        self.incoming.put({"type": MSG_GAME_EVENT, "data": data})

    def _on_ping(self, data):
        # 收到 ping → 回复 pong（延迟测量用）
        try:
            self._sio.emit("ping", {
                "pong": True,
                "sent_at": data.get("sent_at", 0),
                "seq": data.get("seq", 0),
            }, namespace="/game")
        except Exception:
            pass
        # 如果是对方回的 pong，计算延迟
        if data.get("pong"):
            sent_at = data.get("sent_at", 0)
            if sent_at:
                self.latency_ms = (time.time() - sent_at) * 1000

    def _on_error(self, data):
        self.incoming.put({"type": "error", "data": data})

    def _on_game_over_action(self, data):
        self.incoming.put({"type": "game_over_action", "data": data})
