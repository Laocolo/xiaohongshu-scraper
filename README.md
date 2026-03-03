# 小红书竞品数据爬虫

为猪八戒网项目：母婴品牌竞品数据爬取（含情感分析）

## 📁 文件结构

```
xiaohongshu_scraper/
├── xhs_scraper.py              # 基础版（模拟数据，用于演示）
├── xhs_scraper_real.py         # 真实爬取版（API+网页+降级）
├── xhs_scraper_selenium.py     # 浏览器自动化版（Playwright）
├── proxies.txt.example         # 代理配置模板
├── xhs_cookies.txt.example     # Cookie配置模板
└── output/                     # 输出目录
    ├── xhs_data_xxx.json       # JSON格式数据
    ├── xhs_data_xxx.xlsx       # Excel格式数据
    └── report_xxx.md           # 分析报告
```

## 🚀 快速开始

### 1. 基础版（模拟数据）
```bash
python3 xhs_scraper.py
```
- ✅ 无需配置
- ⚠️ 使用模拟数据
- 适合：功能演示、测试流程

### 2. 真实爬取版
```bash
# 方式1：直接运行（可能触发反爬）
python3 xhs_scraper_real.py

# 方式2：配置代理后运行（推荐）
cp proxies.txt.example proxies.txt
# 编辑 proxies.txt，添加代理IP
python3 xhs_scraper_real.py

# 方式3：配置Cookie后运行（推荐）
cp xhs_cookies.txt.example xhs_cookies.txt
# 编辑 xhs_cookies.txt，添加登录Cookie
python3 xhs_scraper_real.py
```

### 3. 浏览器自动化版（最稳定）
```bash
# 安装浏览器
python3 -m playwright install chromium

# 运行
python3 xhs_scraper_selenium.py
```
- ✅ 使用真实浏览器
- ✅ 自动绕过JS检测
- ✅ 支持登录状态保存
- ⚠️ 需要下载浏览器（约200MB）

## ⚙️ 配置说明

### 代理配置 (proxies.txt)
```
192.168.1.1:8080
10.0.0.1:3128
proxy.example.com:8888
```

### Cookie配置 (xhs_cookies.txt)
1. 打开 https://www.xiaohongshu.com 并登录
2. F12 → Network → 任意请求 → Headers
3. 复制 Cookie 值到文件

格式：
```
a1=xxxxx; webId=xxxxx; web_session=xxxxx
```

### 关键词配置
编辑 `Config.KEYWORDS` 列表：
```python
KEYWORDS = [
    "飞鹤奶粉",
    "爱他美",
    # 添加你的品牌...
]
```

## 🛡️ 反爬策略

| 策略 | 基础版 | 真实版 | Playwright版 |
|------|--------|--------|--------------|
| 随机User-Agent | ❌ | ✅ | ✅ |
| 随机延迟 | ❌ | ✅ | ✅ |
| 代理池 | ❌ | ✅ | ✅ |
| Cookie管理 | ❌ | ✅ | ✅ |
| 浏览器渲染 | ❌ | ❌ | ✅ |
| 登录状态 | ❌ | ❌ | ✅ |
| 反检测脚本 | ❌ | ❌ | ✅ |

## 📊 输出示例

### 数据字段
- `id`: 笔记ID
- `keyword`: 搜索关键词
- `title`: 标题
- `content`: 内容
- `author`: 作者
- `likes`: 点赞数
- `comments`: 评论数
- `sentiment`: 情感分数 (0-1)
- `label`: 情感标签 (正面/中性/负面)
- `keywords`: 关键词列表

### 分析报告
- 各品牌数据统计
- 情感分析分布
- 品牌口碑对比
- 热门关键词

## 💡 使用建议

### 500-5000元项目方案

**入门方案 (500元)**
- 使用基础版 + 手动补充真实数据
- 交付Excel报告

**标准方案 (1500元)**
- 使用真实版 + 代理池
- 配置Cookie
- 交付完整分析报告

**专业方案 (3000元)**
- 使用Playwright版
- 定制化关键词
- 持续监测（多次爬取）
- 详细情感分析报告
- 竞品对比分析

**企业方案 (5000元+)**
- 分布式爬取
- 实时监测
- 数据可视化大屏
- API接口

## ⚠️ 注意事项

1. **合法合规**
   - 仅用于市场调研
   - 不抓取用户隐私信息
   - 遵守小红书用户协议

2. **频率控制**
   - 默认延迟3-8秒
   - 大量爬取建议使用代理

3. **数据时效**
   - Cookie有效期有限
   - 建议定期更新

## 📞 技术支持

如需定制开发或技术支持，请联系项目开发者。

---
*为猪八戒网母婴品牌项目定制开发*
