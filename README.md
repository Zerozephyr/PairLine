# PairLine — 双人绳索协作平台跳跃游戏

> 大二下 Python 课程项目 | Pygame 开发 | 支持本地同屏 & 远程联机

PairLine 是一款**双人绳索协作**平台跳跃游戏。两名玩家被一根弹性绳索连接，必须默契配合——收集 Kun 道具、躲避蝙蝠障碍、合力抵达传送门通关。游戏包含 **本地同屏双人**、**远程联机** 和 **无尽跑酷+BOSS追击** 三种模式。

---

## 🎮 游戏截图

![游戏截图1](screenshot1.png)

![游戏截图2](screenshot2.png)

---

## 🕹️ 操作方式

| 动作 | 玩家 1（P1） | 玩家 2（P2） |
|------|:-----------:|:-----------:|
| 移动 | `A` `D` | `←` `→` |
| 跳跃 | `W` | `↑` |
| 抓取 | `S` | `↓` |

- 按住抓取键可**固定在原地**，搭档借绳索摆荡跨越沟壑
- 按 `M` 键切换背景音乐开关
- 按 `ESC` 暂停 / 返回

---

## ✨ 核心玩法

| 机制 | 说明 |
|------|------|
| **绳索约束** | 两人之间始终连接一根弹性绳索，超出最大长度时产生回拉力和位置修正 |
| **抓取摆荡** | 抓取时化身锚点，搭档可以借力荡过更远距离 |
| **收集 & 传送** | 拾取关卡中所有 Kun 道具，两人同时站在传送门上即可通关 |
| **生命系统** | 每人 3 点 HP，碰到蝙蝠或摔落会受伤，受伤后有短暂闪烁无敌；两人同时死亡则游戏结束 |
| **远程联机** | 通过 Socket.IO 中继服务器实现双人远程协作，房主创建房间，客机输入 4 位码加入 |

---

## 🎯 游戏模式

- **普通关卡**（2 关）：收集 Kun → 到达传送门 → 通关。第一关通关解锁第二关，第二关通关解锁无尽模式
- **无尽模式**：自动向右滚屏，跑够 300 距离后触发 BOSS 预警（屏幕震动 + 龙吼），BOSS 从左侧追击，碰到即死
- **远程联机**：基于 Flask-SocketIO + Eventlet 中继服务器，房主/客机分别控制 P1/P2 远程协作

---

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Windows / macOS / Linux

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动游戏

```bash
python main.py
```

### 启动联机服务器（可选）

```bash
cd server
pip install -r requirements.txt
python server.py --host 0.0.0.0 --port 5121
```

服务器默认监听 `5121` 端口（HTTP）。

### 生产环境部署（推荐）

以下以 Linux 服务器 + PM2 + Nginx 为例。

#### 1. 上传服务端文件

```bash
scp -r server/ root@your-server:/opt/pairline/server/
```

#### 2. 安装依赖

```bash
ssh root@your-server
cd /opt/pairline/server
pip install -r requirements.txt
```

#### 3. PM2 进程守护

```bash
# 安装 PM2
npm install -g pm2

# 启动
pm2 start server.py --name pairline-server --interpreter python3 -- --host 0.0.0.0 --port 5121

# 设置开机自启
pm2 save
pm2 startup
```

常用 PM2 命令：

```bash
pm2 status              # 查看状态
pm2 logs pairline-server     # 查看日志
pm2 restart pairline-server  # 重启服务
pm2 stop pairline-server     # 停止服务
```

#### 4. Nginx 反向代理 HTTPS（可选）

```nginx
server {
    listen 5122 ssl;
    server_name your-domain.com;

    ssl_certificate     /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:5121;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Socket.IO 需要
    location /socket.io/ {
        proxy_pass http://127.0.0.1:5121;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### 5. 客户端配置

修改 `config/settings.py` 中的 `SERVER_URL` 指向你的服务器地址：

```python
SERVER_URL = "http://your-server-ip:5122"   # HTTP
# 或
SERVER_URL = "https://your-domain:5122"      # HTTPS (Nginx)
```

---



## 📁 项目结构

```
PairLine/
├── main.py                         # 入口、游戏主循环、场景调度
├── requirements.txt                # 客户端依赖
├── config/
│   ├── settings.py                 # 全局常量（帧率、物理、按键、网络地址）
│   ├── path.py                     # 资源路径管理
│   └── data/
│       ├── level_1.json            # 第一关地图
│       └── level_2.json            # 第二关地图
├── entities/
│   ├── player.py                   # 玩家动画状态机、移动/跳跃/抓取
│   ├── rope.py                     # 绳索弹性约束物理
│   ├── camera.py                   # 平滑跟随相机
│   ├── background.py               # 4 层视差滚动背景
│   ├── level.py                    # 关卡地图加载（JSON → Tile）
│   ├── endless_level.py            # 无尽模式程序化地形生成
│   ├── block.py                    # 方块、移动平台、道具、传送门
│   ├── bat.py                      # 蝙蝠怪物 AI
│   ├── boss.py                     # BOSS 龙（入场 + 追击）
│   ├── particle.py                 # 粒子特效系统
│   └── physic.py                   # 通用物理工具
├── UI/
│   ├── menu.py                     # 主菜单 / 关卡选择 / 暂停 / 结算 / 联机
│   ├── hud.py                      # 游戏内 HUD（血条、道具计数）
│   ├── score_panel.py              # 计分面板
│   └── endless_hud.py              # 无尽模式专属 HUD
├── network/
│   ├── client.py                   # Socket.IO 客户端（后台线程处理 I/O）
│   └── protocol.py                 # 消息类型常量与序列化
├── server/
│   ├── server.py                   # Flask-SocketIO 中继服务器
│   └── requirements.txt            # 服务端依赖
├── utils/
│   ├── animation.py                # 逐帧动画加载与播放
│   └── sound_manager.py            # BGM + SFX 音效管理
└── static/
    ├── font/                       # 文泉驿位图字体
    ├── img/
    │   ├── Background/             # 视差背景图层
    │   ├── Block/                  # 方块 / 平台 / 道具 / 传送门
    │   ├── Player/                 # P1 / P2 帧动画（8 状态 × 多帧）
    │   ├── Master/                 # 蝙蝠 / 龙 帧动画
    │   └── UI/                     # 血条、箭头等 UI 元素
    └── sound/                      # BGM（主菜单/普通/无尽）+ SFX
```

---

## 🏗️ 技术架构

### 客户端

- **渲染**：Pygame 2.6，逻辑画布 256×160 像素 → 4× 缩放输出
- **物理**：自研绳索弹性约束系统（距离检测 → 回拉力 → 位置修正）
- **动画**：8 状态动画状态机（idle / run / jump / fall / hurt / death / grab / swing）
- **联机**：`python-socketio` 客户端，后台线程处理 WebSocket I/O，主线程通过线程安全队列消费消息

### 服务端

- **框架**：Flask + Flask-SocketIO + Eventlet
- **协议**：纯中继模式，服务器不解包游戏数据，仅按房间广播转发
- **房间管理**：4 位数字房间码，HTTP API 创建/加入/查询，10 分钟无活动自动清理

### 网络消息协议

| 消息类型 | 方向 | 说明 |
|----------|------|------|
| `player_state` | P2P | 玩家位置/状态同步（20Hz） |
| `game_event` | P2P | 游戏事件（伤害/通关/死亡） |
| `game_over_action` | Host→Guest | 房主结算选择（下一关/重新开始） |
| `ping` | P2P | 延迟测量（2Hz） |

---

## 🗺️ 关卡编辑

关卡为 JSON 格式，存放在 `config/data/`。坐标单位为**瓦片**（1 瓦片 = 16 像素）。

```json
{
  "id": 1,
  "length": 30,
  "spawn1": [1, 7],
  "spawn2": [3, 7],
  "level": {
    "objects": {
      "ground":   [[x, y], ...],
      "platform":  [[x, y, len], ...],
      "vplatform": [[x, y, len], ...],
      "bg":        [[x, y], ...]
    },
    "layers": {
      "ground": { "x": [0, 30], "y": [8, 10] }
    },
    "entities": {
      "kun":    [[x, y], ...],
      "portal": [[x, y], ...],
      "bat":    [[x, y, speed], ...]
    }
  }
}
```

---

## 📐 物理参数

| 参数 | 值 | 可调 |
|------|-----|------|
| 窗口分辨率 | 1024 × 640 | `SCREEN_WIDTH/HEIGHT` |
| 逻辑画布 | 256 × 160（4× 缩放） | `SCALE` |
| 帧率 | 60 FPS | `FPS` |
| 重力 | 0.8 | `GRAVITY` |
| 跳跃力度 | -9 | `JUMP_STRENGTH` |
| 移动速度 | 2.5 | `MOVE_SPEED` |
| 绳索最大长度 | 60 px | `ROPE_LENGTH` |
| 绳索刚度 | 0.5 | `ROPE_STIFFNESS` |
| 瓦片大小 | 16 × 16 | `TILE_SIZE` |

> 修改 `config/settings.py` 即可调整。

---

## 📋 功能清单

- ✅ 本地同屏双人模式
- ✅ 远程联机（创建/加入房间、实时同步、延迟测量）
- ✅ 绳索弹性物理约束
- ✅ 8 状态动画状态机
- ✅ 4 层视差滚动背景
- ✅ JSON 驱动关卡编辑器
- ✅ 道具收集 & 传送门通关
- ✅ 蝙蝠怪物 AI
- ✅ 无尽跑酷 + BOSS 追击模式
- ✅ 主菜单 / 关卡选择 / 暂停 / 结算界面
- ✅ 背景音乐 + 音效（切换/静音）
- ✅ PyInstaller 单文件打包

---

## 📄 许可证

本项目为课程作业项目，仅供学习交流使用。
