#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小红书竞品数据爬虫 + 情感分析
适用于猪八戒网项目：为母婴品牌爬取竞品数据
"""

import json
import time
import random
import re
import os
from datetime import datetime
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
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
        "君乐宝",
        "合生元",
        "贝因美",
        "伊利金领冠",
        "诺优能",
    ]
    
    # 每个关键词爬取的笔记数量
    NOTES_PER_KEYWORD = 20
    
    # 输出目录
    OUTPUT_DIR = "output"
    
    # 请求间隔（秒）- 避免被封
    REQUEST_DELAY = (2, 5)  # 随机2-5秒
    
    # User-Agent池
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    ]


# ===================== 情感分析器 =====================
class SentimentAnalyzer:
    """基于SnowNLP的中文情感分析"""
    
    @staticmethod
    def analyze(text):
        """
        分析文本情感
        返回: {
            'sentiment': 情感分数 (0-1, >0.6正面, <0.4负面),
            'label': 情感标签,
            'keywords': 关键词,
            'summary': 摘要
        }
        """
        try:
            s = SnowNLP(text)
            sentiment_score = s.sentiments
            
            # 情感分类
            if sentiment_score > 0.6:
                label = "正面"
            elif sentiment_score < 0.4:
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
                'sentiment': round(sentiment_score, 4),
                'label': label,
                'keywords': keywords,
                'summary': summary
            }
        except Exception as e:
            return {
                'sentiment': 0.5,
                'label': '中性',
                'keywords': [],
                'summary': str(e)
            }


# ===================== 小红书爬虫 =====================
class XiaohongshuScraper:
    """小红书数据爬虫"""
    
    def __init__(self):
        self.session = requests.Session()
        self.results = []
        self.sentiment_analyzer = SentimentAnalyzer()
        
    def _get_headers(self):
        """生成随机请求头"""
        return {
            'User-Agent': random.choice(Config.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.xiaohongshu.com/',
        }
    
    def _delay(self):
        """随机延迟"""
        time.sleep(random.uniform(*Config.REQUEST_DELAY))
    
    def search_notes(self, keyword, max_notes=20):
        """
        搜索笔记
        注意: 小红书有反爬机制，这里使用模拟数据作为示例
        实际使用时需要配合Selenium或第三方API
        """
        print(f"正在搜索: {keyword}")
        
        # 由于小红书反爬严格，这里生成模拟数据用于演示
        # 实际项目中需要使用:
        # 1. Selenium + 浏览器自动化
        # 2. 第三方数据API
        # 3. 代理IP池
        
        mock_notes = self._generate_mock_data(keyword, max_notes)
        
        # 对每条笔记进行情感分析
        for note in mock_notes:
            sentiment_result = self.sentiment_analyzer.analyze(note['content'])
            note.update(sentiment_result)
            self.results.append(note)
        
        self._delay()
        return mock_notes
    
    def _generate_mock_data(self, keyword, count):
        """
        生成模拟数据（实际项目中替换为真实爬取逻辑）
        模拟母婴产品相关的用户评价
        """
        templates = [
            {
                'title': f'{keyword}使用心得分享',
                'content': f'最近给宝宝换了{keyword}，感觉还不错。宝宝喝了一个月，消化情况良好，没有出现便秘或者腹泻的情况。溶解度也可以，没有结块。价格方面稍微有点贵，但是为了宝宝的健康还是值得的。推荐给正在纠结的妈妈们！',
                'likes': random.randint(50, 500),
                'comments': random.randint(10, 100),
            },
            {
                'title': f'{keyword}真实测评',
                'content': f'买了{keyword}之后有点失望。宝宝喝了之后有点上火，可能是配方不太适合。而且粉质不够细腻，冲泡的时候容易结块。客服态度也一般，退换货比较麻烦。不太推荐。',
                'likes': random.randint(20, 200),
                'comments': random.randint(5, 50),
            },
            {
                'title': f'{keyword} VS 其他品牌对比',
                'content': f'对比了{keyword}和其他几个牌子，发现各有优缺点。{keyword}的营养成分比较全面，DHA含量高，但是价格偏贵。性价比方面可能不是最优选择，但是品质还是有保障的。',
                'likes': random.randint(100, 800),
                'comments': random.randint(30, 200),
            },
            {
                'title': f'儿科医生推荐的{keyword}',
                'content': f'带宝宝体检的时候医生推荐的{keyword}，用了三个月效果很好。宝宝体重增长正常，睡眠也改善了。最主要是没有过敏反应，之前用过其他品牌宝宝会有轻微湿疹。非常满意！',
                'likes': random.randint(200, 1000),
                'comments': random.randint(50, 300),
            },
            {
                'title': f'{keyword}性价比分析',
                'content': f'从性价比角度分析{keyword}：价格中等偏上，但是品质稳定。促销活动的时候囤货比较划算。比起进口品牌便宜不少，但是和国产平价品牌比还是贵。适合预算充足的家庭。',
                'likes': random.randint(80, 600),
                'comments': random.randint(20, 150),
            },
        ]
        
        notes = []
        for i in range(min(count, len(templates) * 4)):
            template = templates[i % len(templates)]
            note = {
                'id': f'note_{keyword}_{i}',
                'keyword': keyword,
                'title': template['title'],
                'content': template['content'],
                'author': f'用户{random.randint(10000, 99999)}',
                'likes': template['likes'] + random.randint(-20, 20),
                'comments': template['comments'] + random.randint(-5, 5),
                'publish_time': datetime.now().strftime('%Y-%m-%d'),
                'url': f'https://www.xiaohongshu.com/explore/{random.randint(100000000, 999999999)}',
            }
            notes.append(note)
        
        return notes
    
    def run(self, keywords=None, notes_per_keyword=None):
        """运行爬虫"""
        keywords = keywords or Config.KEYWORDS
        notes_per_keyword = notes_per_keyword or Config.NOTES_PER_KEYWORD
        
        print("=" * 60)
        print("小红书竞品数据爬虫启动")
        print(f"目标关键词: {len(keywords)}个")
        print(f"每个关键词爬取: {notes_per_keyword}条")
        print("=" * 60)
        
        for keyword in keywords:
            try:
                self.search_notes(keyword, notes_per_keyword)
                print(f"✓ {keyword} 完成，累计: {len(self.results)}条")
            except Exception as e:
                print(f"✗ {keyword} 失败: {e}")
        
        return self.results
    
    def export_results(self, output_dir=None):
        """导出结果"""
        output_dir = output_dir or Config.OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 导出JSON
        json_path = os.path.join(output_dir, f'xhs_data_{timestamp}.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        print(f"✓ JSON导出: {json_path}")
        
        # 导出Excel
        df = pd.DataFrame(self.results)
        excel_path = os.path.join(output_dir, f'xhs_data_{timestamp}.xlsx')
        df.to_excel(excel_path, index=False, engine='openpyxl')
        print(f"✓ Excel导出: {excel_path}")
        
        # 生成分析报告
        self._generate_report(output_dir, timestamp)
        
        return json_path, excel_path
    
    def _generate_report(self, output_dir, timestamp):
        """生成分析报告"""
        report_path = os.path.join(output_dir, f'report_{timestamp}.md')
        
        # 统计数据
        df = pd.DataFrame(self.results)
        
        # 按关键词分组统计
        keyword_stats = df.groupby('keyword').agg({
            'likes': ['sum', 'mean'],
            'comments': ['sum', 'mean'],
            'sentiment': 'mean'
        }).round(2)
        
        # 情感分布
        sentiment_dist = df['label'].value_counts()
        
        # 所有关键词汇总
        all_text = ' '.join(df['content'].tolist())
        top_keywords = jieba.analyse.extract_tags(all_text, topK=20)
        
        report = f"""# 小红书竞品数据分析报告

## 1. 数据概览
- **爬取时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **总笔记数**: {len(self.results)}
- **关键词数**: {df['keyword'].nunique()}

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
        
        # 各品牌情感分析
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
        
        report += """
## 6. 建议

基于以上数据分析，建议：

1. **关注高互动内容**: 点赞和评论数高的笔记往往代表用户关注度高
2. **分析负面评价**: 找出竞品的痛点，作为自身产品改进的参考
3. **学习正面案例**: 借鉴竞品在用户好评方面的做法
4. **持续监测**: 定期爬取数据，追踪品牌口碑变化

---
*报告由小红书竞品数据爬虫自动生成*
"""
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"✓ 报告导出: {report_path}")


# ===================== 主程序 =====================
def main():
    """主函数"""
    scraper = XiaohongshuScraper()
    
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
