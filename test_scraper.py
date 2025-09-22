#!/usr/bin/env python3
"""
🎼 클래식 공연 정보 스크래퍼 테스트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from concert_scraper import ConcertScraper
from rich.console import Console

console = Console()

def test_scraper():
    """스크래퍼 테스트"""
    scraper = ConcertScraper()
    
    # 테스트 URL들
    test_urls = [
        "https://www.lotteconcerthall.com/kor/Performance/ConcertDetails/260852",
        "https://www.lotteconcerthall.com/kor/Performance/ConcertDetails/260699"
    ]
    
    try:
        for i, url in enumerate(test_urls, 1):
            console.print(f"\n[bold blue]{'='*60}")
            console.print(f"[bold blue]테스트 #{i}")
            console.print(f"[bold blue]{'='*60}")
            
            # 스크래핑 실행
            with console.status("[cyan]스크래핑 중...", spinner="dots"):
                concert_info = scraper.scrape_concert_info(url)
            
            # 결과 출력
            scraper.display_concert_info(concert_info)
            
            if i < len(test_urls):
                console.print("\n[yellow]다음 테스트로 진행...")
                
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 테스트를 중단합니다.")
    finally:
        scraper.close()

if __name__ == "__main__":
    console.print("[bold magenta]🧪 클래식 공연 정보 스크래퍼 테스트 시작...[/bold magenta]\n")
    test_scraper()
    console.print("\n[bold green]✅ 테스트 완료!")