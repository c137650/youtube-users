# YouTube Users - 个人记忆图谱

> 基于YouTube观看历史，构建个人知识图谱

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 项目简介

本项目可以从YouTube观看历史中提取数据，构建可交互的个人记忆图谱，帮助用户：
- 分析自己的观看习惯
- 可视化兴趣分布
- 探索知识关联

---

## 项目结构

```
youtube-users/
│
├── README.md              ← 项目说明
├── roadmap.md             ← 技术路线图
├── .gitignore             ← Git忽略配置
├── config.json            ← 配置模板
│
├── process_takeout.py     ← 主处理脚本
├── youtube_api_proxy.py   ← API测试脚本
│
├── docs/                  ← 文档目录
│   ├── takeout-guide-cn.md   ← 数据导出指南（中文）
│   └── takeout-guide-en.md   ← Data Export Guide (English)
│
└── outcome/               ← 输出目录（自动创建）
    └── n/
        ├── video_details_TIMESTAMP.json
        ├── video_dict_TIMESTAMP.json
        └── metadata.json
```

---

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/c137650/youtube-users.git
cd youtube-users
```

### 2. 导出YouTube数据

按照 `docs/takeout-guide-cn.md` 的步骤导出您的观看记录。

### 3. 配置（如需API补充）

1. 申请 [YouTube Data API v3](https://console.cloud.google.com/) 密钥
2. 在`config.json` 中填入您的密钥：
   ```json
   {
       "api": {
           "key": "您的API密钥",
           "proxy": {
               "http": "http://proxy-dku.oit.duke.edu:3128",
               "https": "http://proxy-dku.oit.duke.edu:3128"
           }
       },
       "paths": {
           "takeout_dir": "您的Takeout文件夹路径"
       }
   }
   ```
   > ⚠️ 注意：请勿将包含真实密钥的 `config.json` 推送到GitHub

### 4. 运行处理脚本

```bash
pip install google-api-python-client pandas
python process_takeout.py
```

### 5. 查看结果

结果保存在 `outcome/{序号}/` 目录下。

---

## 功能特性

| 功能 | 说明 |
|------|------|
| HTML解析 | 从Takeout导出文件中提取视频URL |
| API补充 | 获取视频标签、分类、频道信息 |
| 自动编号 | 每次运行自动创建新文件夹 |
| 多语言支持 | 中文/英文文档 |

---

## 技术栈

| 用途 | 技术 |
|------|------|
| 数据解析 | 正则表达式 |
| API调用 | google-api-python-client |
| 分类 | 标签权重 + 关键词匹配 |
| 图谱可视化 | D3.js / ECharts（规划中） |

---

## 贡献指南

欢迎提交 Issue 和 Pull Request！

---

## 许可证

MIT License

---

## 团队

| 模块 | 状态 |
|------|------|
| 数据导出/解析 | ✅ |
| API调用 | ✅ |
| 分类算法 | ⏳ |
| 图谱前端 | ⏳ |

---

*Made with ❤️ for YouTube users*
