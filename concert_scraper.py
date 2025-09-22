#!/usr/bin/env python3
"""
🎼 클래식 공연 정보 스크래퍼
롯데콘서트홀, 예술의전당 등의 공연 정보를 예쁘게 추출합니다.
"""

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.prompt import Prompt
from rich import print as rprint
import re
import time
from datetime import datetime
import json

console = Console()

class ConcertScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        })
        self.driver = None

    def setup_driver(self):
        """Selenium WebDriver 설정"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # 헤드리스 모드
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
    def get_page_content(self, url):
        """페이지 콘텐츠 가져오기 (Selenium + requests 조합)"""
        try:
            # 먼저 requests로 시도
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                return response.text
        except:
            pass
            
        # requests 실패시 Selenium 사용
        try:
            if not self.driver:
                self.setup_driver()
            
            self.driver.get(url)
            time.sleep(3)  # 페이지 로딩 대기
            return self.driver.page_source
        except Exception as e:
            console.print(f"[red]페이지 로딩 실패: {str(e)}")
            return None

    def extract_title(self, soup, text):
        """공연 제목 추출"""
        title_patterns = [
            r'정명훈\s*&\s*원\s*코리아\s*오케스트라\s*<[^>]+>',
            r'[^<>\n]{5,100}<[^<>\n]+>',
            r'[가-힣\s\w&,\.]{5,100}'
        ]
        
        # 텍스트에서 패턴 매칭
        for pattern in title_patterns:
            match = re.search(pattern, text)
            if match:
                title = match.group().strip()
                if len(title) > 5:
                    return title
        
        # HTML 태그에서 찾기
        title_selectors = ['h1', '.concert_title', '.performance_title', 'title']
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element and element.get_text().strip():
                title = element.get_text().strip()
                if len(title) > 5 and '공연정보' not in title:
                    return title
                    
        return "제목 없음"

    def extract_date_time(self, text):
        """날짜 및 시간 추출"""
        date_patterns = [
            r'\d{4}[-\.]\d{1,2}[-\.]\d{1,2}\s*\([월화수목금토일]\)\s*\d{1,2}:\d{2}',
            r'\d{4}년\s*\d{1,2}월\s*\d{1,2}일\s*\([월화수목금토일]\)\s*\d{1,2}:\d{2}',
            r'\d{4}[-\.]\d{1,2}[-\.]\d{1,2}',
            r'\d{4}년\s*\d{1,2}월\s*\d{1,2}일'
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
                # 주변 텍스트도 함께 추출
                pattern = rf'{venue}[^\n]{{0,30}}'
                match = re.search(pattern, text)
                if match:
                    return match.group().strip()
                    
        return ""

    def extract_performers(self, text):
        """출연진 정보 추출"""
        performers = []
        
        # 롯데콘서트홀 형식: "역할 | 이름"
        role_patterns = [
            (r'지휘\s*[|│]\s*([^\n,]+)', '지휘'),
            (r'소프라노\s*[|│]\s*([^\n,]+)', '소프라노'),
            (r'메조\s*소프라노\s*[|│]\s*([^\n,]+)', '메조소프라노'),
            (r'테너\s*[|│]\s*([^\n,]+)', '테너'),
            (r'바리톤\s*[|│]\s*([^\n,]+)', '바리톤'),
            (r'연주\s*[|│]\s*([^\n,]+)', '연주'),
            (r'합창\s*[|│]\s*([^\n,]+)', '합창'),
            (r'피아노\s*[|│]\s*([^\n,]+)', '피아노'),
            (r'바이올린\s*[|│]\s*([^\n,]+)', '바이올린')
        ]
        
        for pattern, role in role_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                name = match.group(1).strip()
                if name and len(name) > 1:
                    # 한글/영문 이름 분리
                    name_match = re.search(r'([\가-힣\s]+)\s*([A-Za-z\s\-]+)?', name)
                    if name_match:
                        kor_name = name_match.group(1).strip()
                        eng_name = name_match.group(2).strip() if name_match.group(2) else ""
                        
                        if eng_name:
                            full_name = f"{kor_name} ({eng_name})"
                        else:
                            full_name = kor_name
                            
                        performer_info = f"{full_name} - {role}"
                        if performer_info not in performers:
                            performers.append(performer_info)
        
        # 일반적인 출연진 패턴
        general_patterns = [
            r'출연\s*[:\s]*([^\n]+)',
            r'연주자\s*[:\s]*([^\n]+)'
        ]
        
        for pattern in general_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                names = match.group(1).split(',')
                for name in names:
                    name = name.strip()
                    if name and len(name) > 1 and name not in [p.split(' - ')[0] for p in performers]:
                        performers.append(name)
        
        return performers[:15]  # 최대 15명

    def extract_program(self, text):
        """프로그램 정보 추출"""
        programs = []
        
        # 베토벤 교향곡 제9번 특별 패턴
        beethoven_patterns = [
            r'베토벤\s*교향곡\s*제\s*9번[^\n]{0,50}',
            r'Beethoven\s*Symphony\s*No\.?\s*9[^\n]{0,50}',
            r'교향곡\s*제\s*9번[^\n]*(?:합창|Choral)',
            r'베토벤[^\n]{0,30}(?:d단조|D\s*minor)[^\n]{0,30}(?:op\.?\s*125|Op\.?\s*125)'
        ]
        
        for pattern in beethoven_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                program = match.group().strip()
                if program not in programs:
                    programs.append(program)
        
        # 일반적인 작곡가 패턴
        composers = [
            'Bach', 'Mozart', 'Beethoven', 'Brahms', 'Chopin', 'Schubert', 
            'Rachmaninoff', 'Tchaikovsky', 'Mahler', 'Debussy', 'Ravel',
            '바흐', '모차르트', '베토벤', '브람스', '쇼팽', '슈베르트', '차이콥스키'
        ]
        
        for composer in composers:
            pattern = rf'{composer}[^\n]{{5,100}}'
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                program = match.group().strip()
                if len(program) > 10 and len(program) < 150:
                    if not any(p in program.lower() for p in ['가격', 'price', '티켓', 'ticket']) and program not in programs:
                        programs.append(program)
        
        return programs[:10]  # 최대 10개

    def extract_price(self, text):
        """가격 정보 추출"""
        prices = []
        
        # 좌석별 가격 패턴
        seat_patterns = [
            r'[RSABCVIP]+석\s*[:\s]*[\d,]+원',
            r'[RSABCVIP]+\s*[:\s]*[\d,]+원',
            r'(?:전석|일반|학생)\s*[:\s]*[\d,]+원',
            r'시야방해[RSAB]*\s*[:\s]*[\d,]+원'
        ]
        
        for pattern in seat_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                price = match.group().strip()
                if price not in prices:
                    prices.append(price)
        
        # 일반 가격 패턴 (좌석별이 없을 때)
        if not prices:
            general_patterns = [r'[\d,]+원']
            for pattern in general_patterns:
                matches = re.finditer(pattern, text)
                for match in matches:
                    price_str = match.group().strip()
                    # 숫자만 추출해서 합리적인 범위인지 확인
                    price_num = int(re.sub(r'[^\d]', '', price_str))
                    if 1000 <= price_num <= 1000000:  # 1천원~100만원
                        if price_str not in prices:
                            prices.append(price_str)
        
        return prices[:8]  # 최대 8개 가격

    def scrape_concert_info(self, url):
        """공연 정보 스크래핑"""
        console.print(f"[cyan]🔍 스크래핑 중: {url}")
        
        html_content = self.get_page_content(url)
        if not html_content:
            return None
            
        soup = BeautifulSoup(html_content, 'html.parser')
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

    def display_concert_info(self, info):
        """공연 정보를 예쁘게 출력"""
        if not info:
            console.print("[red]❌ 공연 정보를 가져올 수 없습니다.")
            return
            
        # 제목
        title_text = Text(info['title'], style="bold magenta")
        title_panel = Panel(title_text, title="🎼 공연 제목", border_style="magenta")
        console.print(title_panel)
        console.print()
        
        # 정보 테이블
        table = Table(show_header=True, header_style="bold blue", border_style="blue")
        table.add_column("항목", style="cyan", width=15)
        table.add_column("내용", style="white")
        
        # 날짜 및 시간
        if info['date']:
            table.add_row("📅 날짜/시간", info['date'])
        
        # 공연장
        if info['venue']:
            table.add_row("🏛️ 공연장", info['venue'])
        
        # 출연진
        if info['performers']:
            performers_text = '\n'.join(info['performers'][:8])  # 최대 8명
            if len(info['performers']) > 8:
                performers_text += f"\n... 외 {len(info['performers']) - 8}명"
            table.add_row("👥 출연진", performers_text)
        
        # 프로그램
        if info['program']:
            program_text = '\n'.join(info['program'])
            table.add_row("🎵 프로그램", program_text)
        
        # 가격
        if info['price']:
            price_text = '\n'.join(info['price'])
            table.add_row("💰 가격", price_text)
        
        # URL
        table.add_row("🔗 URL", info['url'])
        
        # 스크래핑 시간
        table.add_row("⏰ 수집시간", info['scraped_at'])
        
        console.print(table)
        console.print()

    def save_to_json(self, info, filename=None):
        """JSON 파일로 저장"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"concert_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(info, f, ensure_ascii=False, indent=2)
            console.print(f"[green]💾 저장 완료: {filename}")
        except Exception as e:
            console.print(f"[red]❌ 저장 실패: {str(e)}")

    def close(self):
        """리소스 정리"""
        if self.driver:
            self.driver.quit()


def main():
    """메인 함수"""
    console.print(Panel.fit(
        "[bold magenta]🎼 클래식 공연 정보 스크래퍼[/bold magenta]\n"
        "[cyan]롯데콘서트홀, 예술의전당 등의 공연 정보를 추출합니다.[/cyan]",
        border_style="magenta"
    ))
    console.print()
    
    scraper = ConcertScraper()
    
    try:
        while True:
            # URL 입력
            url = Prompt.ask(
                "[cyan]🔗 공연 정보 URL을 입력하세요 (종료: quit)[/cyan]",
                default="https://www.lotteconcerthall.com/kor/Performance/ConcertDetails/260852"
            )
            
            if url.lower() in ['quit', 'exit', 'q']:
                break
            
            if not url.startswith('http'):
                console.print("[red]❌ 올바른 URL을 입력해주세요.")
                continue
            
            # 스크래핑 실행
            console.print()
            with console.status("[cyan]스크래핑 중...", spinner="dots"):
                concert_info = scraper.scrape_concert_info(url)
            
            # 결과 출력
            scraper.display_concert_info(concert_info)
            
            # 저장 여부 확인
            if concert_info:
                save = Prompt.ask("[cyan]JSON 파일로 저장하시겠습니까? (y/n)[/cyan]", default="n")
                if save.lower() in ['y', 'yes']:
                    scraper.save_to_json(concert_info)
            
            console.print("\n" + "="*60 + "\n")
            
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 프로그램을 종료합니다.")
    finally:
        scraper.close()


if __name__ == "__main__":
    main()