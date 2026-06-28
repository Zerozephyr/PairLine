# -*- coding: utf-8 -*-
"""PairLine 远程联机中继服务器

Flask + Flask-SocketIO + Eventlet
- HTTP API: 创建/加入/查询房间
- WebSocket: 房间内消息纯中继，不含游戏逻辑
"""

import os
import sys
import time
import random
import logging
from threading import Thread

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
from flask_cors import CORS

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
HOST = "0.0.0.0"
PORT = 5121  # 内部 HTTP 端口，nginx 反向代理 5122(HTTPS) → 5121(HTTP)
ROOM_CLEANUP_SEC = 600  # 10 分钟无活动自动清理

# 从命令行解析 --host / --port
i = 1
while i < len(sys.argv):
    if sys.argv[i] == "--host" and i + 1 < len(sys.argv):
        HOST = sys.argv[i + 1]; i += 2
    elif sys.argv[i] == "--port" and i + 1 < len(sys.argv):
        PORT = int(sys.argv[i + 1]); i += 2
    else:
        i += 1

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("pairline-server")

# ---------------------------------------------------------------------------
# Flask 应用
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = "pairline-server-secret"
CORS(app)
socketio = SocketIO(app, async_mode="eventlet", cors_allowed_origins="*")

# ---------------------------------------------------------------------------
# 房间管理
# ---------------------------------------------------------------------------
rooms_db = {}  # code -> dict


def _generate_room_code():
    """生成不重复的 4 位数字房间码"""
    for _ in range(100):
        code = str(random.randint(1000, 9999))
        if code not in rooms_db:
            return code
    # 极端情况：所有 9000 个码都被占用
    for code in range(1000, 10000):
        code = str(code)
        if code not in rooms_db:
            return code
    return None


def _cleanup_stale_rooms():
    """移除超时未活动的房间"""
    now = time.time()
    stale = [c for c, r in rooms_db.items() if now - r["last_activity"] > ROOM_CLEANUP_SEC]
    for c in stale:
        logger.info(f"清理过期房间: {c}")
        del rooms_db[c]


def _cleanup_loop():
    """后台线程：每 30 秒清理一次过期房间"""
    while True:
        time.sleep(30)
        _cleanup_stale_rooms()


# ---------------------------------------------------------------------------
# HTTP API
# ---------------------------------------------------------------------------
@app.route("/api/rooms", methods=["POST"])
def api_create_room():
    """创建房间 → {room_code, role: 'host'}"""
    _cleanup_stale_rooms()
    code = _generate_room_code()
    if code is None:
        return jsonify({"error": "服务器房间已满，请稍后再试"}), 503
    rooms_db[code] = {
        "code": code,
        "host_sid": None,
        "guest_sid": None,
        "state": "waiting",        # waiting | level_select | playing
        "host_level": None,
        "guest_level": None,
        "created_at": time.time(),
        "last_activity": time.time(),
    }
    logger.info(f"房间创建: {code}")
    return jsonify({"room_code": code, "role": "host"})


@app.route("/api/rooms/<code>/join", methods=["POST"])
def api_join_room(code):
    """加入房间 → {role: 'guest'} 或错误"""
    _cleanup_stale_rooms()
    room = rooms_db.get(code)
    if room is None:
        return jsonify({"error": "房间不存在或已过期"}), 404
    if room["guest_sid"] is not None:
        return jsonify({"error": "房间已满（已有两名玩家）"}), 409
    return jsonify({"role": "guest"})


@app.route("/api/rooms/<code>", methods=["GET"])
def api_room_status(code):
    """查询房间状态"""
    room = rooms_db.get(code)
    if room is None:
        return jsonify({"exists": False})
    return jsonify({
        "exists": True,
        "state": room["state"],
        "players": (1 if room["host_sid"] is not None else 0)
                   + (1 if room["guest_sid"] is not None else 0),
    })


# ---------------------------------------------------------------------------
# WebSocket 事件（Socket.IO namespace /game）
# ---------------------------------------------------------------------------
@socketio.on("connect", namespace="/game")
def on_connect():
    """客户端连接：从查询参数中解析 room + role"""
    sid = request.sid
    room_code = request.args.get("room", "")
    role = request.args.get("role", "")

    room = rooms_db.get(room_code)
    if room is None:
        logger.warning(f"拒绝连接 sid={sid}: 房间 {room_code} 不存在")
        emit("error", {"message": "房间不存在"}, to=sid)
        return False

    room["last_activity"] = time.time()

    if role == "host":
        room["host_sid"] = sid
    elif role == "guest":
        room["guest_sid"] = sid
    else:
        logger.warning(f"拒绝连接 sid={sid}: 无效角色 {role}")
        emit("error", {"message": "无效角色"}, to=sid)
        return False

    # 加入 Socket.IO 房间（物理房间，用于广播）
    join_room(room_code)
    logger.info(f"玩家连接: room={room_code} role={role} sid={sid}")

    # 通知房间内已有玩家：新玩家加入
    other_role = "guest" if role == "host" else "host"
    emit("player_joined", {"role": role}, room=room_code)

    # 如果房间已有另一玩家，也通知新连上的客户端
    other_sid = room["guest_sid"] if role == "host" else room["host_sid"]
    if other_sid is not None:
        emit("player_joined", {"role": other_role}, to=sid)

    return True


@socketio.on("disconnect", namespace="/game")
def on_disconnect():
    sid = request.sid
    # 找到该 sid 所属的房间
    for code, room in list(rooms_db.items()):
        role = None
        if room["host_sid"] == sid:
            role = "host"
            room["host_sid"] = None
        elif room["guest_sid"] == sid:
            role = "guest"
            room["guest_sid"] = None
        else:
            continue

        room["last_activity"] = time.time()
        leave_room(code)
        logger.info(f"玩家断开: room={code} role={role} sid={sid}")

        # 通知房间内另一玩家
        emit("player_left", {"role": role}, room=code)

        # 如果两人都离开了，标记清理
        if room["host_sid"] is None and room["guest_sid"] is None:
            room["state"] = "abandoned"
        break


# ---- 纯中继消息（不解包，直接转发给房间内其他客户端） ----

RELAY_EVENTS = [
    "player_state",
    "level_select",
    "game_event",
    "game_over_action",
    "ping",
]


def _make_relay_handler(evt_name):
    def handler(data):
        sid = request.sid
        # 找到 sid 所属房间并广播给其他人
        for code, room in rooms_db.items():
            if room["host_sid"] == sid or room["guest_sid"] == sid:
                room["last_activity"] = time.time()
                # 附加发送者角色
                role = "host" if room["host_sid"] == sid else "guest"
                data["_from"] = role
                emit(evt_name, data, room=code, include_self=False)
                return
    handler.__name__ = f"on_{evt_name}"
    return handler


for evt in RELAY_EVENTS:
    socketio.on(evt, namespace="/game")(_make_relay_handler(evt))


# ---- 特殊消息：game_start（服务器检测匹配后广播） ----

@socketio.on("game_start", namespace="/game")
def on_game_start(data):
    """game_start 由任意客户端发送，广播给房间内所有人（含发送者）"""
    sid = request.sid
    for code, room in rooms_db.items():
        if room["host_sid"] == sid or room["guest_sid"] == sid:
            room["last_activity"] = time.time()
            room["state"] = "playing"
            data["_from"] = "host" if room["host_sid"] == sid else "guest"
            emit("game_start", data, room=code)
            return


# ---------------------------------------------------------------------------
# 启动
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logger.info("PairLine 联机服务器启动中...")
    logger.info(f"监听地址: {HOST}:{PORT}")

    # 启动后台清理线程
    t = Thread(target=_cleanup_loop, daemon=True)
    t.start()

    logger.info(f"以 HTTP 模式启动（SSL 应由反向代理处理）")
    socketio.run(app, host=HOST, port=PORT)
