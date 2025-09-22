#!/usr/bin/env python3
"""
🎼 간단한 클래식 공연 정보 스크래퍼 (Selenium 없이)
"""

import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime

class SimpleConcertScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })

    def get_page_content(self, url):
        """페이지 콘텐츠 가져오기"""
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"페이지 로딩 실패: {str(e)}")
            return None

    def extract_title(self, soup, text):
        """공연 제목 추출"""
        # 롯데콘서트홀 특정 패턴
        title_patterns = [
            r'정명훈\s*&\s*원\s*코리아\s*오케스트라\s*<[^>]+>',
            r'[가-힣\w\s&,.]+<[가-힣\w\s]+>',
            r'[가-힣\w\s&,.]{10,100}'
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, text)
            if match:
                title = match.group().strip()
                if len(title) > 5 and not any(skip in title.lower() for skip in ['공연정보', 'lotte', 'sac', '예매']):
                    return title
        
        # HTML 태그에서 찾기
        title_selectors = ['h1', 'title', '.concert_title', '.performance_title']
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get_text().strip()
                if len(title) > 5 and not any(skip in title.lower() for skip in ['공연정보', 'lotte', 'sac', '예매']):
                    return title
                    
        return "제목 추출 실패"

    def extract_date_time(self, text):
        """날짜 및 시간 추출"""
        date_patterns = [
            r'2025[-\.]\d{1,2}[-\.]\d{1,2}\s*\([월화수목금토일]\)\s*\d{1,2}:\d{2}',
            r'2025년\s*\d{1,2}월\s*\d{1,2}일\s*\([월화수목금토일]\)\s*\d{1,2}:\d{2}',
            r'2025[-\.]\d{1,2}[-\.]\d{1,2}',
            r'2025년\s*\d{1,2}월\s*\d{1,2}일'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group().strip()
                
        return ""

    def extract_venue(self, text):
        """공연장 추출"""
        venues = [
            '롯데콘서트홀', '예술의전당', 'SAC', '세종문화회관', '통영국제음악당',
            'LG아트센터', '금호아트홀', '블루스퀘어', 'IBK챔버홀', '리사이틀홀'
        ]
        
        for venue in venues:
            if venue in text:
                return venue
                    
        return ""

    def extract_performers(self, text):
        """출연진 정보 추출"""
        performers = []
        
        # 롯데콘서트홀 형식: "역할 | 이름"
        role_patterns = [
            (r'지휘\s*[|│]\s*([가-힣\s]+(?:\([A-Za-z\s\-]+\))?)', '지휘'),
            (r'소프라노\s*[|│]\s*([가-힣\s]+(?:\([A-Za-z\s\-]+\))?)', '소프라노'),
            (r'메조\s*소프라노\s*[|│]\s*([가-힣\s]+(?:\([A-Za-z\s\-]+\))?)', '메조소프라노'),
            (r'테너\s*[|│]\s*([가-힣\s]+(?:\([A-Za-z\s\-]+\))?)', '테너'),
            (r'바리톤\s*[|│]\s*([가-힣\s]+(?:\([A-Za-z\s\-]+\))?)', '바리톤'),
            (r'연주\s*[|│]\s*([가-힣\s\w]+(?:\([A-Za-z\s\-]+\))?)', '연주'),
            (r'합창\s*[|│]\s*([가-힣\s\w,]+)', '합창'),
        ]
        
        for pattern, role in role_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                name = match.group(1).strip()
                if name and len(name) > 1:
                    performer_info = f"{name} - {role}"
                    if performer_info not in performers:
                        performers.append(performer_info)
        
        return performers[:12]  # 최대 12명

    def extract_program(self, text):
        """프로그램 정보 추출"""
        programs = []
        
        # 베토벤 교향곡 제9번 특별 패턴
        beethoven_patterns = [
            r'베토벤\s*교향곡\s*제\s*9번[^\n]{0,50}',
            r'Beethoven\s*Symphony\s*No\.?\s*9[^\n]{0,50}',
            r'교향곡\s*제\s*9번[^\n]*(?:합창|Choral)',
        ]
        
        for pattern in beethoven_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                program = match.group().strip()
                if program not in programs:
                    programs.append(program)
        
        # 일반적인 작곡가 패턴
        composers = [
            'Rachmaninoff', 'Beethoven', 'Mozart', 'Bach', 'Brahms', 'Chopin', 
            '라흐마니노프', '베토벤', '모차르트', '바흐', '브람스', '쇼팽'
        ]
        
        for composer in composers:
            pattern = rf'{composer}[^\n]{{10,80}}'
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                program = match.group().strip()
                if len(program) > 10 and len(program) < 120:
                    if not any(skip in program.lower() for skip in ['가격', 'price', '티켓']) and program not in programs:
                        programs.append(program)
        
        return programs[:8]  # 최대 8개

    def extract_price(self, text):
        """가격 정보 추출"""
        prices = []
        
        # 좌석별 가격 패턴
        seat_patterns = [
            r'[RSABCVIP]+석\s*[:\s]*[\d,]+원',
            r'[RSABCVIP]+\s*[:\s]*[\d,]+원',
            r'시야방해[RSAB]*\s*[:\s]*[\d,]+원'
        ]
        
        for pattern in seat_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                price = match.group().strip()
                if price not in prices:
                    prices.append(price)
        
        return prices[:6]  # 최대 6개 가격

    def scrape_concert_info(self, url):
        """공연 정보 스크래핑"""
        print(f"🔍 스크래핑 중: {url}")
        
        html_content = self.get_page_content(url)
        if not html_content:
            return None
            
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 스크립트와 스타일 태그 제거
        for script in soup(["script", "style"]):
            script.decompose()
            
        text_content = soup.get_text()
        
        # 정보 추출
        concert_info = {
            'url': url,
            'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'title': self.extract_title(soup, text_content),
            'date': self.extract_date_time(text_content),
            'venue': self.extract_venue(text_content),
            'performers': self.extract_performers(text_content),
            'program': self.extract_program(text_content),
            'price': self.extract_price(text_content)
        }
        
        return concert_info

    def close(self):
        """리소스 정리 (Selenium 없으므로 필요 없음)"""
        pass