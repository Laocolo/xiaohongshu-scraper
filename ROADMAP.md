# 小红书竞品数据爬虫

[![GitHub](https://img.shields.io/github/license/Laocolo/xiaohongshu-scraper)](https://github.com/Laocolo/xiaohongshu-scraper)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)

小红书竞品数据爬虫 - 母婴品牌数据采集与情感分析

适用于猪八戒网项目：为母婴品牌爬取小红书竞品数据（含情感分析）

## 🚀 快速开始

```bash
# 1. 克隆项目
git clone https://github.com/Laocolo/xiaohongshu-scraper.git
cd xiaohongshu-scraper

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 Cookie
cp xhs_cookies.txt.example xhs_cookies.txt
# 编辑 xhs_cookies.txt，粘贴你的小红书 Cookie

# 4. 运行
python xhs_scraper_real.py
```

## 📁 项目结构

```
xiaohongshu-scraper/
├── xhs_scraper.py              # 基础版（模拟数据）
├── xhs_scraper_real.py         # 真实爬取版 ⭐推荐
├── xhs_scraper_search.py       # 搜索引擎版
├── xhs_scraper_selenium.py     # Playwright浏览器版
├── requirements.txt            # 依赖列表
├── proxies.txt.example         # 代理配置模板
├── xhs_cookies.txt.example     # Cookie配置模板
├── README.md                   # 英文文档
├── 本地运行指南.md              # 中文指南
└── output/                     # 输出目录
```

## 📊 输出示例

| 品牌 | 笔记数 | 平均点赞 | 平均评论 | 平均情感分 | 口碑 |
|------|--------|----------|----------|------------|------|
| 飞鹤奶粉 | 50 | 349.1 | 122.2 | 0.800 | ⭐⭐⭐ |
| 爱他美 | 50 | 416.7 | 82.0 | 0.800 | ⭐⭐⭐ |
| 美赞臣 | 50 | 406.8 | 90.8 | 0.800 | ⭐⭐⭐ |

## 🛡️ 反爬策略

- ✅ 随机 User-Agent
- ✅ 随机延迟 (3-8秒)
- ✅ Cookie 管理
- ✅ 代理池支持
- ✅ 失败自动降级

## 📝 开发计划

- [ ] 添加更多情感分析模型
- [ ] 支持图片/视频内容分析
- [ ] 添加数据可视化大屏
- [ ] 支持定时任务自动爬取
- [ ] 添加 Web UI 界面

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

---

**项目地址：** https://github.com/Laocolo/xiaohongshu-scraper
