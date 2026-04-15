# YouTube Memory Graph - 个人记忆图谱

> 基于YouTube观看历史，构建可交互的个人知识图谱

---

## 项目简介

本项目可以从YouTube观看历史中提取数据，自动匹配用户兴趣标签，构建可交互的个人记忆图谱，帮助用户：
- 📊 分析自己的观看习惯
- 🏷️ 可视化兴趣分布
- 🔗 探索知识关联
- 🎮 互动式图谱浏览

---

## 项目结构

```
hackathon_data_crawler/
├── README.md              ← 项目说明
├── roadmap.md             ← 技术路线图
├── main.py                ← 🎯 主程序（解析 + 标签匹配）
├── user_tags.json         ← 用户标签分类体系
├── config.json            ← 配置文件
├── .gitignore
├── LICENSE
│
├── docs/                  ← 文档目录
│   ├── takeout-guide-cn.md   ← 数据导出指南（中文）
│   └── takeout-guide-en.md   ← Data Export Guide
│
├── frontend/              ← 🌟 前端图谱
│   ├── index.html         ← 主页面
│   ├── app.js             ← 核心逻辑（Canvas + D3-force）
│   ├── styles.css         ← 样式
│   ├── package.json       ← Node 依赖
│   ├── vite.config.ts     ← Vite 配置
│   └── src/                ← React 源码（可选）
│       ├── main.tsx
│       ├── App.tsx
│       ├── components/
│       │   ├── BubbleChart.tsx
│       │   └── KnowledgeGraph.tsx
│       └── utils/
│           └── data.ts
│
├── Takeout/               ← 放置导出的数据（可选）
│
└── outcome/               ← 输出目录
    └── n/
        └── video_labels_xxx.json     ← 标签分类结果 ⭐
```

---

## 快速开始

### 1. 数据处理

```bash
# 克隆项目
git clone https://github.com/c137650/youtube-users.git
cd youtube-users

# 安装 Python 依赖
pip install google-api-python-client pandas

# 导出 YouTube 数据（见 docs/takeout-guide-cn.md）

# 配置 API 密钥（见 docs/takeout-guide-cn.md）
# 编辑 config.json 中的 api.key

# 一键运行
python main.py
```

### 2. 查看前端图谱

#### 方式 A：直接打开（推荐）
```bash
cd frontend
# 安装依赖
npm install
# 启动开发服务器
npx vite --port 3888
# 浏览器访问 http://localhost:3888/
```

#### 方式 B：双击打开
```bash
# 直接双击打开 index.html
# 注意：需要网络加载 D3.js
```

---

## 功能特性

### 数据处理

| 功能 | 说明 |
|------|------|
| 🎬 HTML解析 | 从Takeout导出文件中提取视频URL + 观看时间 |
| 🔍 API补充 | 获取视频标签、分类、频道信息（需配置API） |
| 🏷️ 标签分类 | 基于梗图式人格标签的正则匹配 |
| 📅 时间保留 | 所有输出保留原始观看日期 |
| 📁 自动编号 | 每次运行自动创建新文件夹 |
| 📄 多格式输出 | JSON格式便于后续处理 |

### 前端图谱

| 功能 | 说明 |
|------|------|
| 🎈 气泡图 | 每个气泡代表一个标签，大小反映视频数量 |
| 🔍 悬停预览 | 鼠标悬停显示标签信息 |
| 📊 点击跳转 | 点击气泡进入该标签的知识图谱 |
| 🔗 知识图谱 | 同标签视频用连线连接 |
| ✋ 拖拽交互 | 节点可自由拖拽（不触发跳转） |
| 📅 时间颜色 | 观看时间越近颜色越深 |
| 🎨 随机配色 | 每个标签随机独特颜色 |
| 📱 全屏浏览 | 图谱占满整个视口 |

---

## 标签分类系统

项目使用**梗图式用户标签**进行分类：

### 核心人格标签
| 标签 | Emoji | 说明 |
|------|-------|------|
| 深夜实验室科学家 | 🧪 | 技术宅/程序员/AI爱好者 |
| 快乐肥宅 | 🎮 | 游戏动漫二次元狂热者 |
| 自律战士 | 🏋️ | 健身/运动/拳击狂热者 |
| 卷王之王 | 📚 | 学习狂魔/考试战士 |
| 音乐鉴赏家 | 🎵 | 音乐发烧友 |
| 影视达人 | 🎬 | 电影/剧集/综艺爱好者 |
| 生活家 | 🍳 | 烹饪/手工/DIY达人 |
| 云旅游者 | 🌍 | 旅行/探店爱好者 |

### 梗标签
| 标签 | Emoji | 说明 |
|------|-------|------|
| AI狂信徒 | 🤖 | 对AI极度痴迷 |
| 失眠患者 | 🌙 | 深夜睡不着刷视频 |
| 摸鱼带师 | 🐟 | 上班摸鱼偷看 |
| 无限循环患者 | 🔄 | 反复看同一视频 |
| 知识焦虑症 | 📦 | 疯狂收藏但从不看 |

> 详见 `user_tags.json`，可自行添加/修改标签

---

## 数据格式

### 输入：`video_labels_xxx.json`

```json
{
  "Python机器学习教程": [
    "深夜实验室科学家, AI狂信徒",
    "https://www.youtube.com/watch?v=abc123",
    "2024年3月15日"
  ]
}
```

格式：`{视频标题: [标签字符串, URL, 观看时间]}`

---

## 前端交互说明

| 视图 | 操作 | 效果 |
|------|------|------|
| **气泡图** | 悬停气泡 | 气泡放大 + 显示标签信息 |
| **气泡图** | 点击气泡 | 切换到该标签的知识图谱 |
| **知识图谱** | 悬停节点 | 显示视频名称、标签、时间 |
| **知识图谱** | 点击节点 | 在新标签页打开 YouTube 视频 |
| **知识图谱** | 拖拽节点 | 自由移动节点位置（不触发跳转） |
| **知识图谱** | 点击返回按钮 / ESC | 返回气泡图 |

---

## 技术栈

### 后端
| 用途 | 技术 |
|------|------|
| 数据解析 | Python 正则表达式 |
| API调用 | google-api-python-client |
| 标签匹配 | 正则 + 关键词权重 |

### 前端
| 用途 | 技术 |
|------|------|
| 图谱渲染 | HTML5 Canvas |
| 力导向 | D3.js (d3-force) |
| 样式 | CSS3 |
| 构建工具 | Vite（可选）|

---

## 贡献指南

欢迎提交 Issue 和 Pull Request！

---

## 许可证

MIT License

---

*Made with ❤️ for YouTube users*
