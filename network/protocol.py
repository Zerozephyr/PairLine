# -*- coding: utf-8 -*-
"""网络协议 — 消息类型常量和序列化工具"""

import json
import time

# ---- 消息类型 ----
MSG_PLAYER_STATE   = "player_state"
MSG_LEVEL_SELECT   = "level_select"
MSG_GAME_START     = "game_start"
MSG_PLAYER_JOINED  = "player_joined"
MSG_PLAYER_LEFT    = "player_left"
MSG_GAME_EVENT     = "game_event"
MSG_GAME_OVER_ACTION = "game_over_action"
MSG_PING           = "ping"
MSG_ERROR          = "error"

# ---- 游戏内事件 ----
EVT_ITEM_COLLECTED = "item_collected"
EVT_PORTAL_UPDATE  = "portal_update"
EVT_DAMAGE         = "damage"
EVT_DEATH          = "death"
EVT_GAME_OVER      = "game_over"


def encode(msg_type, data, seq=0):
    """构造可序列化的消息字典（不含信封，Socket.IO 自带事件名）"""
    return {
        "type": msg_type,
        "data": data,
        "seq": seq,
        "timestamp": time.time(),
    }


def decode(raw):
    """解析 JSON 消息（Socket.IO 已做 JSON 解析，此函数用于统一处理）"""
    if isinstance(raw, dict):
        return raw
    return json.loads(raw)
