#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小红书竞品数据爬虫 - 真实爬取版
包含反爬策略：代理池、请求头轮换、延迟控制、Cookie管理
"""

import json
import time
import random
import re
import os
import hashlib
from datetime import datetime
from urllib.parse import quote, urlencode
from typing import List, Dict, Optional
import warnings
warnings.filterwarnings('ignore')

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
from snownlp import SnowNLP
import jieba.analyse

# ===================== 配置区域 =====================
class Config:
    # 竞品关键词（母婴品牌相关）
    KEYWORDS = [
        "飞鹤奶粉",
        "爱他美",
        "美赞臣",
        "惠氏",
        "a2奶粉",
    ]
    
    # 每个关键词爬取的笔记数量
    NOTES_PER_KEYWORD = 50
    
    # 输出目录
    OUTPUT_DIR = "output"
    
    # 请求间隔（秒）- 避免被封
    REQUEST_DELAY = (3, 8)  # 随机3-8秒
    
    # 最大重试次数
    MAX_RETRIES = 3
    
    # 代理设置（留空则不使用代理）
    # 格式: {"http": "http://ip:port", "https": "http://ip:port"}
    PROXIES = None
    
    # 是否使用代理池文件
    USE_PROXY_FILE = False
    PROXY_FILE = "proxies.txt"  # 每行一个代理，格式: ip:port
    
    # Cookie文件（登录后获取）
    COOKIE_FILE = "xhs_cookies.txt"
    
    # User-Agent池
    USER_AGENTS = [
        # Chrome
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # Firefox
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        # Safari
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        # Mobile
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    ]
    
    # 小红书签名算法密钥（需要定期更新）
    XHS_SIGN_KEY = "xhs_web_sign_key_2024"


# ===================== 代理池管理 =====================
class ProxyPool:
    """代理IP池管理"""
    
    def __init__(self, proxy_file: str = None):
        self.proxies = []
        self.current_index = 0
        if proxy_file and os.path.exists(proxy_file):
            self.load_from_file(proxy_file)
    
    def load_from_file(self, file_path: str):
        """从文件加载代理列表"""
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    self.proxies.append({
                        "http": f"http://{line}",
                        "https": f"http://{line}"
                    })
        print(f"已加载 {len(self.proxies)} 个代理IP")
    
    def get_proxy(self) -> Optional[Dict]:
        """获取下一个代理"""
        if not self.proxies:
            return None
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy
    
    def remove_bad_proxy(self, proxy: Dict):
        """移除失效代理"""
        if proxy in self.proxies:
            self.proxies.remove(proxy)
            print(f"移除失效代理，剩余 {len(self.proxies)} 个")


# ===================== Cookie管理 =====================
class CookieManager:
    """Cookie管理器"""
    
    def __init__(self, cookie_file: str = None):
        self.cookie_file = cookie_file
        self.cookies = {}
        self.load_cookies()
    
    def load_cookies(self):
        """从文件加载Cookie"""
        if self.cookie_file and os.path.exists(self.cookie_file):
            with open(self.cookie_file, 'r') as f:
                cookie_str = f.read().strip()
                if cookie_str:
                    # 解析Cookie字符串
                    for item in cookie_str.split(';'):
                        item = item.strip()
                        if '=' in item:
                            key, value = item.split('=', 1)
                            self.cookies[key.strip()] = value.strip()
                    print(f"已加载 {len(self.cookies)} 个Cookie")
    
    def save_cookies(self, cookie_str: str):
        """保存Cookie到文件"""
        if self.cookie_file:
            with open(self.cookie_file, 'w') as f:
                f.write(cookie_str)
    
    def get_cookie_header(self) -> str:
        """获取Cookie请求头"""
        return '; '.join([f"{k}={v}" for k, v in self.cookies.items()])
    
    def update_from_response(self, response):
        """从响应更新Cookie"""
        for cookie in response.cookies:
            self.cookies[cookie.name] = cookie.value


# ===================== 签名生成器 =====================
class SignGenerator:
    """小红书请求签名生成器"""
    
    @staticmethod
    def generate_x_s(api_path: str, params: dict = None) -> str:
        """
        生成X-S签名（简化版，实际需要逆向分析小红书JS）
        完整版需要使用execjs执行JS代码
        """
        timestamp = int(time.time() * 1000)
        data = f"{api_path}{json.dumps(params or {}, separators=(',', ':'))}{timestamp}"
        # 这里简化处理，实际需要逆向小红书的签名算法
        sign = hashlib.md5(data.encode()).hexdigest()
        return sign
    
    @staticmethod  
    def generate_x_t() -> str:
        """生成X-T时间戳"""
        return str(int(time.time() * 1000))


# ===================== 情感分析器 =====================
class SentimentAnalyzer:
    """基于SnowNLP的中文情感分析"""
    
    # 母婴领域正面词库
    POSITIVE_WORDS = [
        "好", "棒", "推荐", "满意", "喜欢", "不错", "值得", "安心", 
        "放心", "营养", "健康", "优质", "天然", "吸收好", "不上火",
        "不便秘", "长肉", "睡眠好", "口感好", "易溶解"
    ]
    
    # 母婴领域负面词库
    NEGATIVE_WORDS = [
        "差", "垃圾", "难喝", "结块", "上火", "便秘", "过敏", 
        "腹泻", "不好", "失望", "退货", "投诉", "假货", "不推荐",
        "溶解差", "有杂质", "味道怪"
    ]
    
    @staticmethod
    def analyze(text: str) -> Dict:
        """
        分析文本情感
        """
        try:
            s = SnowNLP(text)
            base_sentiment = s.sentiments
            
            # 结合领域词库调整情感分数
            positive_count = sum(1 for word in SentimentAnalyzer.POSITIVE_WORDS if word in text)
            negative_count = sum(1 for word in SentimentAnalyzer.NEGATIVE_WORDS if word in text)
            
            # 调整系数
            adjustment = (positive_count - negative_count) * 0.05
            adjusted_sentiment = max(0, min(1, base_sentiment + adjustment))
            
            # 情感分类
            if adjusted_sentiment > 0.6:
                label = "正面"
            elif adjusted_sentiment < 0.4:
                label = "负面"
            else:
                label = "中性"
            
            # 提取关键词
            keywords = jieba.analyse.extract_tags(text, topK=5)
            
            # 生成摘要
            try:
                summary = s.summary(3)
            except:
                summary = text[:100] + "..." if len(text) > 100 else text
            
            return {
                'sentiment': round(adjusted_sentiment, 4),
                'base_sentiment': round(base_sentiment, 4),
                'label': label,
                'keywords': keywords,
                'summary': summary,
                'positive_words_found': positive_count,
                'negative_words_found': negative_count
            }
        except Exception as e:
            return {
                'sentiment': 0.5,
                'label': '中性',
                'keywords': [],
                'summary': str(e),
                'error': True
            }


# ===================== 小红书爬虫 =====================
class XiaohongshuScraper:
    """小红书数据爬虫 - 真实爬取版"""
    
    def __init__(self, use_proxy: bool = False):
        self.session = self._create_session()
        self.results = []
        self.sentiment_analyzer = SentimentAnalyzer()
        self.sign_generator = SignGenerator()
        
        # 代理池
        self.proxy_pool = None
        if use_proxy or Config.USE_PROXY_FILE:
            self.proxy_pool = ProxyPool(Config.PROXY_FILE)
        
        # Cookie管理
        self.cookie_manager = CookieManager(Config.COOKIE_FILE)
        
        # 请求计数
        self.request_count = 0
        self.error_count = 0
        
        # API端点
        self.base_url = "https://www.xiaohongshu.com"
        self.api_base = "https://edith.xiaohongshu.com"
        
    def _create_session(self) -> requests.Session:
        """创建带重试机制的Session"""
        session = requests.Session()
        
        # 重试策略
        retry_strategy = Retry(
            total=Config.MAX_RETRIES,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _get_headers(self, referer: str = None) -> Dict:
        """生成随机请求头"""
        headers = {
            'User-Agent': random.choice(Config.USER_AGENTS),
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Origin': self.base_url,
            'Referer': referer or f'{self.base_url}/',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
        }
        
        # 添加Cookie
        cookie_header = self.cookie_manager.get_cookie_header()
        if cookie_header:
            headers['Cookie'] = cookie_header
        
        return headers
    
    def _delay(self):
        """随机延迟 + 指数退避"""
        base_delay = random.uniform(*Config.REQUEST_DELAY)
        # 添加随机抖动
        jitter = random.uniform(0.5, 1.5)
        delay = base_delay * jitter
        
        # 如果错误较多，增加延迟
        if self.error_count > 3:
            delay *= 2
            self.error_count = 0
        
        time.sleep(delay)
    
    def _make_request(self, url: str, params: Dict = None, method: str = 'GET') -> Optional[Dict]:
        """发起请求"""
        self._delay()
        
        headers = self._get_headers()
        proxy = self.proxy_pool.get_proxy() if self.proxy_pool else None
        
        try:
            if method == 'GET':
                response = self.session.get(
                    url, 
                    params=params, 
                    headers=headers,
                    proxies=proxy,
                    timeout=30
                )
            else:
                response = self.session.post(
                    url,
                    json=params,
                    headers=headers,
                    proxies=proxy,
                    timeout=30
                )
            
            self.request_count += 1
            
            # 更新Cookie
            self.cookie_manager.update_from_response(response)
            
            if response.status_code == 200:
                # 检查是否被重定向到验证页面
                if 'verify' in response.url or response.url != url:
                    print("⚠️ 触发验证，需要人工处理或更换IP")
                    self.error_count += 1
                    return None
                
                try:
                    return response.json()
                except:
                    # 可能返回了HTML页面
                    if '<!DOCTYPE html>' in response.text:
                        print("⚠️ 返回HTML页面，可能触发反爬")
                        self.error_count += 1
                    return None
            
            elif response.status_code == 403:
                print("⚠️ 403禁止访问，IP可能被封")
                if self.proxy_pool and proxy:
                    self.proxy_pool.remove_bad_proxy(proxy)
                self.error_count += 1
                return None
            
            elif response.status_code == 429:
                print("⚠️ 请求过于频繁，等待更长时间...")
                time.sleep(30)
                return None
            
            else:
                print(f"⚠️ 请求失败: HTTP {response.status_code}")
                return None
                
        except requests.exceptions.ProxyError:
            print("⚠️ 代理连接失败")
            if self.proxy_pool and proxy:
                self.proxy_pool.remove_bad_proxy(proxy)
            return None
            
        except requests.exceptions.Timeout:
            print("⚠️ 请求超时")
            return None
            
        except Exception as e:
            print(f"⚠️ 请求异常: {e}")
            return None
    
    def search_notes_api(self, keyword: str, page: int = 1, page_size: int = 20) -> List[Dict]:
        """
        使用API搜索笔记
        注意：小红书API需要签名，这里提供框架
        """
        notes = []
        
        # 搜索API（需要签名验证）
        api_path = "/api/sns/web/v1/search/notes"
        url = f"{self.api_base}{api_path}"
        
        params = {
            "keyword": keyword,
            "page": page,
            "page_size": page_size,
            "search_id": self._generate_search_id(),
            "sort": "general",  # general, time_descending, hot_descending
        }
        
        # 添加签名
        headers = self._get_headers(f"{self.base_url}/search/result?keyword={quote(keyword)}")
        headers['X-S'] = self.sign_generator.generate_x_s(api_path, params)
        headers['X-T'] = self.sign_generator.generate_x_t()
        
        data = self._make_request(url, params)
        
        if data and data.get('success'):
            items = data.get('data', {}).get('items', [])
            for item in items:
                note = self._parse_note_item(item, keyword)
                if note:
                    notes.append(note)
        
        return notes
    
    def search_notes_web(self, keyword: str, max_notes: int = 50) -> List[Dict]:
        """
        通过网页搜索（备选方案）
        使用网页端搜索，解析HTML
        """
        notes = []
        search_url = f"{self.base_url}/search/result"
        
        params = {
            "keyword": keyword,
            "source": "web_search_result_notes"
        }
        
        headers = self._get_headers()
        headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        
        try:
            response = self.session.get(
                search_url,
                params=params,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                # 解析页面中的初始数据
                notes = self._parse_search_page(response.text, keyword)
            else:
                print(f"搜索请求失败: {response.status_code}")
                
        except Exception as e:
            print(f"搜索异常: {e}")
        
        return notes
    
    def _parse_search_page(self, html: str, keyword: str) -> List[Dict]:
        """解析搜索页面HTML"""
        notes = []
        
        try:
            # 提取页面中的JSON数据
            pattern = r'window\.__INITIAL_STATE__\s*=\s*({.*?})</script>'
            match = re.search(pattern, html, re.DOTALL)
            
            if match:
                data = json.loads(match.group(1))
                items = data.get('search', {}).get('notes', [])
                
                for item in items:
                    note = self._parse_note_item(item, keyword)
                    if note:
                        notes.append(note)
        except Exception as e:
            print(f"解析页面失败: {e}")
        
        return notes
    
    def _parse_note_item(self, item: Dict, keyword: str) -> Optional[Dict]:
        """解析笔记数据"""
        try:
            note_card = item.get('noteCardView', item)
            note = {
                'id': note_card.get('noteId', ''),
                'keyword': keyword,
                'title': note_card.get('title', ''),
                'content': note_card.get('desc', ''),
                'author': note_card.get('user', {}).get('nickname', ''),
                'author_id': note_card.get('user', {}).get('userId', ''),
                'likes': note_card.get('interactInfo', {}).get('likedCount', 0),
                'comments': note_card.get('interactInfo', {}).get('commentCount', 0),
                'collects': note_card.get('interactInfo', {}).get('collectedCount', 0),
                'shares': note_card.get('interactInfo', {}).get('shareCount', 0),
                'publish_time': note_card.get('time', ''),
                'type': note_card.get('type', ''),
                'url': f"https://www.xiaohongshu.com/explore/{note_card.get('noteId', '')}",
                'images': [img.get('urlDefault') for img in note_card.get('imageList', [])],
                'video_url': note_card.get('video', {}).get('media', {}).get('stream', {}).get('h264', [{}])[0].get('masterUrl', ''),
            }
            return note
        except Exception as e:
            return None
    
    def _generate_search_id(self) -> str:
        """生成搜索ID"""
        return hashlib.md5(f"{time.time()}{random.random()}".encode()).hexdigest()
    
    def get_note_detail(self, note_id: str) -> Optional[Dict]:
        """获取笔记详情"""
        api_path = f"/api/sns/web/v1/feed"
        url = f"{self.api_base}{api_path}"
        
        params = {
            "source_note_id": note_id,
            "image_formats": ["jpg", "webp", "avif"],
            "extra": {"need_body_topic": 1}
        }
        
        data = self._make_request(url, params)
        
        if data and data.get('success'):
            return data.get('data', {}).get('items', [{}])[0]
        
        return None
    
    def search_with_fallback(self, keyword: str, max_notes: int = 50) -> List[Dict]:
        """
        搜索笔记（带降级策略）
        优先使用API，失败则降级到网页爬取
        """
        print(f"正在搜索: {keyword}")
        
        notes = []
        
        # 尝试API搜索
        try:
            api_notes = self.search_notes_api(keyword, page=1, page_size=min(max_notes, 20))
            if api_notes:
                notes.extend(api_notes)
                print(f"  API获取: {len(api_notes)}条")
        except Exception as e:
            print(f"  API搜索失败: {e}")
        
        # 如果API失败，尝试网页搜索
        if len(notes) < max_notes:
            try:
                web_notes = self.search_notes_web(keyword, max_notes - len(notes))
                if web_notes:
                    notes.extend(web_notes)
                    print(f"  网页获取: {len(web_notes)}条")
            except Exception as e:
                print(f"  网页搜索失败: {e}")
        
        # 如果都失败，使用模拟数据作为最终降级
        if not notes:
            print(f"  ⚠️ 全部失败，使用模拟数据")
            notes = self._generate_mock_data(keyword, min(max_notes, 10))
        
        # 对每条笔记进行情感分析
        for note in notes:
            sentiment_result = self.sentiment_analyzer.analyze(note.get('content', note.get('title', '')))
            note.update(sentiment_result)
            self.results.append(note)
        
        return notes
    
    def _generate_mock_data(self, keyword: str, count: int) -> List[Dict]:
        """生成模拟数据（最终降级方案）"""
        templates = [
            {
                'title': f'{keyword}使用心得分享',
                'content': f'最近给宝宝换了{keyword}，感觉还不错。宝宝喝了一个月，消化情况良好，没有出现便秘或者腹泻的情况。溶解度也可以，没有结块。价格方面稍微有点贵，但是为了宝宝的健康还是值得的。',
                'likes': random.randint(50, 500),
                'comments': random.randint(10, 100),
            },
            {
                'title': f'{keyword}真实测评',
                'content': f'买了{keyword}之后有点失望。宝宝喝了之后有点上火，可能是配方不太适合。而且粉质不够细腻，冲泡的时候容易结块。',
                'likes': random.randint(20, 200),
                'comments': random.randint(5, 50),
            },
        ]
        
        notes = []
        for i in range(count):
            template = templates[i % len(templates)]
            note = {
                'id': f'mock_{keyword}_{i}',
                'keyword': keyword,
                'title': template['title'],
                'content': template['content'],
                'author': f'用户{random.randint(10000, 99999)}',
                'likes': template['likes'] + random.randint(-20, 20),
                'comments': template['comments'] + random.randint(-5, 5),
                'publish_time': datetime.now().strftime('%Y-%m-%d'),
                'url': f'https://www.xiaohongshu.com/explore/{random.randint(100000000, 999999999)}',
                'is_mock': True
            }
            notes.append(note)
        
        return notes
    
    def run(self, keywords: List[str] = None, notes_per_keyword: int = None) -> List[Dict]:
        """运行爬虫"""
        keywords = keywords or Config.KEYWORDS
        notes_per_keyword = notes_per_keyword or Config.NOTES_PER_KEYWORD
        
        print("=" * 60)
        print("小红书竞品数据爬虫启动 [真实爬取版]")
        print(f"目标关键词: {len(keywords)}个")
        print(f"每个关键词爬取: {notes_per_keyword}条")
        print(f"代理池: {'已启用' if self.proxy_pool else '未启用'}")
        print("=" * 60)
        
        for keyword in keywords:
            try:
                notes = self.search_with_fallback(keyword, notes_per_keyword)
                print(f"✓ {keyword} 完成，累计: {len(self.results)}条")
            except Exception as e:
                print(f"✗ {keyword} 失败: {e}")
        
        print(f"\n总请求数: {self.request_count}")
        print(f"总错误数: {self.error_count}")
        
        return self.results
    
    def export_results(self, output_dir: str = None):
        """导出结果"""
        output_dir = output_dir or Config.OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 导出JSON
        json_path = os.path.join(output_dir, f'xhs_real_data_{timestamp}.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        print(f"✓ JSON导出: {json_path}")
        
        # 导出Excel
        df = pd.DataFrame(self.results)
        excel_path = os.path.join(output_dir, f'xhs_real_data_{timestamp}.xlsx')
        df.to_excel(excel_path, index=False, engine='openpyxl')
        print(f"✓ Excel导出: {excel_path}")
        
        # 生成分析报告
        self._generate_report(output_dir, timestamp)
        
        return json_path, excel_path
    
    def _generate_report(self, output_dir: str, timestamp: str):
        """生成分析报告"""
        report_path = os.path.join(output_dir, f'report_real_{timestamp}.md')
        
        df = pd.DataFrame(self.results)
        
        # 情感分布
        sentiment_dist = df['label'].value_counts()
        
        # 所有关键词汇总
        all_text = ' '.join([str(c) for c in df['content'].tolist() if c])
        top_keywords = jieba.analyse.extract_tags(all_text, topK=20)
        
        # 统计真实/模拟数据比例
        mock_count = df.get('is_mock', pd.Series([False]*len(df))).sum()
        real_count = len(df) - mock_count
        
        report = f"""# 小红书竞品数据分析报告 [真实爬取版]

## 1. 数据概览
- **爬取时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **总笔记数**: {len(self.results)}
- **真实数据**: {real_count}条 ({real_count/len(df)*100:.1f}%)
- **模拟数据**: {mock_count}条 ({mock_count/len(df)*100:.1f}%)
- **关键词数**: {df['keyword'].nunique()}
- **总请求数**: {self.request_count}

## 2. 各品牌数据统计

| 品牌 | 笔记数 | 总点赞 | 平均点赞 | 总评论 | 平均评论 | 平均情感分 |
|------|--------|--------|----------|--------|----------|------------|
"""
        
        for keyword in df['keyword'].unique():
            kw_data = df[df['keyword'] == keyword]
            row = f"| {keyword} | {len(kw_data)} | {kw_data['likes'].sum()} | {kw_data['likes'].mean():.1f} | {kw_data['comments'].sum()} | {kw_data['comments'].mean():.1f} | {kw_data['sentiment'].mean():.3f} |\n"
            report += row

        report += f"""
## 3. 情感分析分布

| 情感类型 | 数量 | 占比 |
|----------|------|------|
| 正面 | {sentiment_dist.get('正面', 0)} | {sentiment_dist.get('正面', 0)/len(df)*100:.1f}% |
| 中性 | {sentiment_dist.get('中性', 0)} | {sentiment_dist.get('中性', 0)/len(df)*100:.1f}% |
| 负面 | {sentiment_dist.get('负面', 0)} | {sentiment_dist.get('负面', 0)/len(df)*100:.1f}% |

## 4. 热门关键词

{', '.join([f'`{kw}`' for kw in top_keywords])}

## 5. 品牌口碑对比

"""
        
        for keyword in df['keyword'].unique():
            kw_data = df[df['keyword'] == keyword]
            avg_sentiment = kw_data['sentiment'].mean()
            positive_rate = len(kw_data[kw_data['label'] == '正面']) / len(kw_data) * 100
            
            if avg_sentiment > 0.55:
                verdict = "⭐⭐⭐ 口碑优秀"
            elif avg_sentiment > 0.5:
                verdict = "⭐⭐ 口碑良好"
            else:
                verdict = "⭐ 口碑一般"
            
            report += f"""### {keyword}
- 平均情感分: {avg_sentiment:.3f}
- 正面评价率: {positive_rate:.1f}%
- 综合评价: {verdict}

"""
        
        report += f"""
## 6. 爬取统计

- **总请求数**: {self.request_count}
- **错误次数**: {self.error_count}
- **成功率**: {(self.request_count - self.error_count) / max(self.request_count, 1) * 100:.1f}%

## 7. 反爬建议

1. **使用代理池**: 配置 `proxies.txt` 文件，每行一个代理IP
2. **配置Cookie**: 登录小红书后复制Cookie到 `xhs_cookies.txt`
3. **降低频率**: 增大 `REQUEST_DELAY` 参数
4. **分布式爬取**: 多IP、多账号轮流爬取

---
*报告由小红书竞品数据爬虫 [真实版] 自动生成*
"""
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"✓ 报告导出: {report_path}")


# ===================== 使用说明 =====================
def print_usage():
    """打印使用说明"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║           小红书竞品数据爬虫 - 使用说明                        ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  1. 基本使用（无代理）                                        ║
║     python3 xhs_scraper_real.py                              ║
║                                                              ║
║  2. 使用代理池                                                ║
║     - 创建 proxies.txt 文件，每行一个代理IP                   ║
║       格式: 192.168.1.1:8080                                 ║
║     - 设置 Config.USE_PROXY_FILE = True                      ║
║                                                              ║
║  3. 配置Cookie（提高成功率）                                  ║
║     - 登录小红书网页版                                        ║
║     - F12打开开发者工具 → Network → 任意请求 → Headers       ║
║     - 复制Cookie值到 xhs_cookies.txt                         ║
║                                                              ║
║  4. 修改爬取目标                                              ║
║     - 编辑 Config.KEYWORDS 列表                              ║
║     - 修改 Config.NOTES_PER_KEYWORD 数量                     ║
║                                                              ║
║  5. 反爬策略                                                  ║
║     - 自动随机User-Agent                                     ║
║     - 随机延迟 (3-8秒)                                       ║
║     - 代理IP轮换                                             ║
║     - Cookie持久化                                           ║
║     - 失败自动降级                                           ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")


# ===================== 主程序 =====================
def main():
    """主函数"""
    print_usage()
    
    # 创建爬虫实例（设置 use_proxy=True 启用代理）
    scraper = XiaohongshuScraper(use_proxy=False)
    
    # 运行爬虫
    results = scraper.run()
    
    # 导出结果
    if results:
        scraper.export_results()
        print("\n" + "=" * 60)
        print(f"爬取完成！共获取 {len(results)} 条数据")
        print("=" * 60)
    else:
        print("未获取到任何数据")


if __name__ == '__main__':
    main()
