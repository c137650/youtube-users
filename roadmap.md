# Hackathon: 个人记忆图谱

## 项目背景

制作一个可拖拽和交互的**个人记忆图谱**，基于用户YouTube观看历史。

---

## 一、数据获取方案

### 1.1 主数据：用户自行导出（Takeout）

**步骤**：
1. 打开 https://takeout.google.com
2. 登录Google账号
3. 勾选 **YouTube → 历史记录 → 观看历史**
4. 导出下载（HTML格式）

**输出文件**：`观看记录.html`

**优点**：
- 不需要API配额
- 完整的历史记录
- 用户自己控制数据

### 1.2 补充数据：YouTube API

虽然主数据使用导出的方式，但API可用于**补充信息**（如视频分类、标签、频道详情等）。

---

## 二、YouTube API 能力说明

### 2.1 API配置

```
代理地址: http://proxy-dku.oit.duke.edu
端口: 3128
API Key: AIzaSyCfqxUG56YJYfg3RzXPbGAqiNWUXPTuecI
```

### 2.2 可以获取的内容 ✅

| 功能 | API方法 | 返回字段 | 说明 |
|------|---------|----------|------|
| **视频详情** | `videos.list` | snippet, contentDetails, statistics | 标题、描述、发布时间、频道名 |
| **标签** | `videos.list` | snippet.tags | 视频标签（关键！） |
| **分类** | `videos.list` | snippet.categoryId | YouTube官方分类ID |
| **频道信息** | `channels.list` | snippet, statistics | 频道名、订阅数、观看数 |
| **搜索功能** | `search.list` | snippet | 按关键词搜索视频 |

### 2.3 无法获取的内容 ❌

| 功能 | 原因 | 替代方案 |
|------|------|----------|
| **用户观看历史** | 需要OAuth授权 | 使用Takeout导出 ✅ |
| **用户订阅列表** | 需要OAuth授权 | - |
| **字幕内容** | 需单独API | 使用`youtube-transcript-api`库 |
| **私密视频** | 无权限 | 跳过 |
| **用户评论** | 需要OAuth | - |

### 2.4 API配额

| 限制 | 数值 |
|------|------|
| 免费配额/天 | 10,000单位 |
| `videos.list()` | 1单位/视频 |
| `channels.list()` | 1单位/频道 |
| 最大批量请求 | 50视频/请求 |

**估算**：获取1000个视频 = 1000单位/天

### 2.5 可获取的官方分类（47类）

| ID | 分类 | ID | 分类 |
|----|------|----|------|
| 1 | Film & Animation | 22 | People & Blogs |
| 2 | Autos & Vehicles | 23 | Comedy |
| 10 | Music | 24 | Entertainment |
| 15 | Pets & Animals | 25 | News & Politics |
| 17 | Sports | 26 | Howto & Style |
| 18 | Science & Technology | 27 | Science & Technology |
| 19 | Travel & Events | 28 | Education |
| 20 | Gaming | 29 | Nonprofits & Activism |
| 21 | Vlogs | ... | ... |

---

## 三、视频分类体系

### 3.1 YouTube官方分类（基于category_id）

```
ID 27: Science & Technology
ID 28: Education  
ID 10: Music
ID 20: Gaming
ID 17: Sports
ID 24: Entertainment
...
```

### 3.2 自定义分类（基于标签+描述）

```
教育(28)
  ├── 编程 → python, tutorial, coding, programming
  ├── 数学 → math, calculus, statistics, machine learning
  ├── 语言 → english, chinese, learning
  └── 科学 → physics, chemistry, biology

科技(27)
  ├── AI/ML → machine learning, neural network, AI, deep learning
  ├── 硬件 → hardware, laptop, phone, computer
  └── 软件 → software, app, tool, tutorial

娱乐
  ├── 音乐 → music, song, concert, lyrics
  ├── 游戏 → gaming, gameplay, walkthrough, esports
  ├── Vlog → vlog, daily, life, diary
  └── 搞笑 → funny, comedy, meme, hilarious

体育(17)
  ├── 篮球 → basketball, NBA, basketball
  ├── 足球 → soccer, football, premier league
  └── 综合 → boxing, MMA, fitness, workout
```

---

## 四、数据处理流程

```
Takeout导出
    ↓
观看记录.html
    ↓
解析video_id + 观看时间
    ↓
视频详情（可选项）
    ↓
字幕获取（可选项）
    ↓
分类处理（官方分类 + 自定义标签）
    ↓
构建知识图谱
```

---

## 五、脚本说明

### 5.1 核心脚本

| 脚本 | 功能 | 状态 |
|------|------|------|
| `youtube_api_proxy.py` | YouTube API调用 | ✅ 已测试 |
| `extract_video_ids.py` | 从Takeout HTML解析video_id | ⏳ 待实现 |
| `batch_fetch.py` | 批量获取视频信息 | ⏳ 待实现 |
| `transcript_fetch.py` | 获取视频字幕 | ⏳ 待实现 |

### 5.2 数据格式

**观看记录解析后**：
```python
{
    'video_id': 'dQw4w9WgXcQ',
    'watched_at': '2024-03-15T14:30:00Z',
    'title': '...',  # 可选
    'channel': '...'  # 可选
}
```

**API补充后**：
```python
{
    'video_id': 'dQw4w9WgXcQ',
    'watched_at': '2024-03-15T14:30:00Z',
    'title': 'Video Title',
    'description': 'Video description...',
    'tags': ['tag1', 'tag2'],
    'category_id': '27',
    'channel_title': 'Channel Name',
    'published_at': '2020-01-01T00:00:00Z',
}
```

---

## 六、下一步

- [x] ~~导出YouTube数据（Takeout）~~ ✅ 舰长已有
- [ ] 编写 `extract_video_ids.py` 解析HTML
- [ ] 实现分类算法（官方分类 + 标签分类）
- [ ] 可选：使用API补充视频详情
- [ ] 可选：获取字幕文本
- [ ] 存储到数据库
- [ ] 前端图谱展示

---

## 七、团队分工

| 模块 | 负责人 |
|------|--------|
| Takeout数据解析 | 舰长 |
| 分类算法 | 待定 |
| 图谱前端 | 待定 |
| 布洛妮娅辅助 | API调用、脚本编写 |

---

## 八、技术栈参考

| 用途 | 技术 |
|------|------|
| 数据解析 | BeautifulSoup,正则表达式 |
| API调用 | google-api-python-client |
| 字幕获取 | youtube-transcript-api |
| 分类 | 标签权重 + 关键词匹配 |
| 图谱可视化 | D3.js / ECharts / Pyvis |
| 数据存储 | SQLite / PostgreSQL |

---

*文档版本：v0.5 | 更新时间：2026-04-14*
*GitHub: https://github.com/c137650/youtube-users*
