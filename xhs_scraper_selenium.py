#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小红书竞品数据爬虫 - Selenium/Playwright版
使用浏览器自动化绕过反爬
"""

import json
import time
import random
import os
import re
import asyncio
from datetime import datetime
from typing import List, Dict, Optional

import pandas as pd
from snownlp import SnowNLP
import jieba.analyse

# ===================== 配置 =====================
class Config:
    KEYWORDS = ["飞鹤奶粉", "爱他美", "美赞臣", "惠氏", "a2奶粉"]
    NOTES_PER_KEYWORD = 30
    OUTPUT_DIR = "output"
    REQUEST_DELAY = (3, 6)
    
    # 浏览器配置
    HEADLESS = True  # 无头模式
    USER_DATA_DIR = "./browser_data"  # 浏览器数据目录（保存登录状态）


# ===================== 情感分析 =====================
def analyze_sentiment(text: str) -> Dict:
    """情感分析"""
    try:
        s = SnowNLP(text)
        sentiment = s.sentiments
        
        if sentiment > 0.6:
            label = "正面"
        elif sentiment < 0.4:
            label = "负面"
        else:
            label = "中性"
        
        keywords = jieba.analyse.extract_tags(text, topK=5)
        
        return {
            'sentiment': round(sentiment, 4),
            'label': label,
            'keywords': keywords
        }
    except:
        return {'sentiment': 0.5, 'label': '中性', 'keywords': []}


# ===================== Playwright爬虫 =====================
class XHSPlaywrightScraper:
    """使用Playwright的小红书爬虫"""
    
    def __init__(self):
        self.results = []
        self.browser = None
        self.context = None
        self.page = None
    
    async def init_browser(self):
        """初始化浏览器"""
        from playwright.async_api import async_playwright
        
        self.playwright = await async_playwright().start()
        
        # 使用持久化上下文（保存登录状态）
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=Config.USER_DATA_DIR,
            headless=Config.HEADLESS,
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN',
            timezone_id='Asia/Shanghai',
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--no-sandbox',
            ]
        )
        
        self.page = await self.context.new_page()
        
        # 注入反检测脚本
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        print("✓ 浏览器初始化完成")
    
    async def login_check(self):
        """检查登录状态"""
        await self.page.goto('https://www.xiaohongshu.com', wait_until='networkidle')
        await asyncio.sleep(2)
        
        # 检查是否需要登录
        login_btn = await self.page.query_selector('.login-btn')
        if login_btn:
            print("⚠️ 未登录，请手动登录...")
            print("登录完成后按回车继续...")
            input()
        
        print("✓ 登录状态正常")
    
    async def search(self, keyword: str, max_notes: int = 30) -> List[Dict]:
        """搜索笔记"""
        notes = []
        
        # 构建搜索URL
        search_url = f"https://www.xiaohongshu.com/search/result?keyword={keyword}&source=web_search_result_notes"
        
        await self.page.goto(search_url, wait_until='networkidle')
        await asyncio.sleep(random.uniform(2, 4))
        
        # 滚动加载更多
        for _ in range(3):
            await self.page.evaluate('window.scrollBy(0, 1000)')
            await asyncio.sleep(random.uniform(1, 2))
        
        # 解析页面数据
        content = await self.page.content()
        notes = self._parse_page_data(content, keyword)
        
        return notes[:max_notes]
    
    def _parse_page_data(self, html: str, keyword: str) -> List[Dict]:
        """解析页面数据"""
        notes = []
        
        try:
            # 提取初始状态数据
            pattern = r'window\.__INITIAL_STATE__\s*=\s*({.*?})</script>'
            match = re.search(pattern, html, re.DOTALL)
            
            if match:
                data = json.loads(match.group(1))
                items = data.get('search', {}).get('notes', [])
                
                for item in items:
                    card = item.get('noteCardView', item)
                    
                    note = {
                        'id': card.get('noteId', ''),
                        'keyword': keyword,
                        'title': card.get('title', ''),
                        'content': card.get('desc', ''),
                        'author': card.get('user', {}).get('nickname', ''),
                        'likes': card.get('interactInfo', {}).get('likedCount', 0),
                        'comments': card.get('interactInfo', {}).get('commentCount', 0),
                        'url': f"https://www.xiaohongshu.com/explore/{card.get('noteId', '')}",
                        'is_real': True
                    }
                    
                    # 情感分析
                    sentiment = analyze_sentiment(note['content'] or note['title'])
                    note.update(sentiment)
                    
                    notes.append(note)
                    self.results.append(note)
                    
        except Exception as e:
            print(f"解析失败: {e}")
        
        return notes
    
    async def run(self):
        """运行爬虫"""
        await self.init_browser()
        await self.login_check()
        
        print("=" * 60)
        print("小红书爬虫 [Playwright版] 启动")
        print(f"关键词: {len(Config.KEYWORDS)}个")
        print("=" * 60)
        
        for keyword in Config.KEYWORDS:
            try:
                print(f"搜索: {keyword}")
                notes = await self.search(keyword, Config.NOTES_PER_KEYWORD)
                print(f"✓ {keyword}: {len(notes)}条, 累计: {len(self.results)}条")
                
                # 随机延迟
                await asyncio.sleep(random.uniform(*Config.REQUEST_DELAY))
                
            except Exception as e:
                print(f"✗ {keyword} 失败: {e}")
        
        await self.close()
        return self.results
    
    async def close(self):
        """关闭浏览器"""
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
    
    def export_results(self):
        """导出结果"""
        os.makedirs(Config.OUTPUT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSON
        json_path = os.path.join(Config.OUTPUT_DIR, f'xhs_pw_data_{timestamp}.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        # Excel
        df = pd.DataFrame(self.results)
        excel_path = os.path.join(Config.OUTPUT_DIR, f'xhs_pw_data_{timestamp}.xlsx')
        df.to_excel(excel_path, index=False)
        
        print(f"✓ 导出完成: {json_path}")
        print(f"✓ 导出完成: {excel_path}")


# ===================== Selenium爬虫（备选） =====================
class XHSSeleniumScraper:
    """使用Selenium的小红书爬虫（需要chromedriver）"""
    
    def __init__(self):
        self.results = []
        self.driver = None
    
    def init_driver(self):
        """初始化Selenium"""
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        
        # 随机User-Agent
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        options.add_argument(f'user-agent={random.choice(user_agents)}')
        
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        
        # 执行反检测脚本
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
        })
        
        print("✓ Selenium初始化完成")
    
    def run(self):
        """运行爬虫"""
        try:
            self.init_driver()
            
            for keyword in Config.KEYWORDS:
                print(f"搜索: {keyword}")
                # 实现搜索逻辑...
                time.sleep(random.uniform(*Config.REQUEST_DELAY))
                
        finally:
            if self.driver:
                self.driver.quit()


# ===================== 主程序 =====================
async def main():
    """主函数"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║        小红书爬虫 - Playwright浏览器自动化版                   ║
╠══════════════════════════════════════════════════════════════╣
║  特点:                                                       ║
║  - 使用真实浏览器，绕过JS检测                                 ║
║  - 支持登录状态保存                                          ║
║  - 自动滚动加载更多内容                                       ║
║  - 反检测脚本注入                                            ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    scraper = XHSPlaywrightScraper()
    
    try:
        results = await scraper.run()
        
        if results:
            scraper.export_results()
            print(f"\n✓ 爬取完成！共 {len(results)} 条数据")
        else:
            print("\n✗ 未获取到数据")
            
    except Exception as e:
        print(f"\n✗ 爬取出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(main())
