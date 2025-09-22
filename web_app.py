#!/usr/bin/env python3
"""
🎼 클래식 공연 정보 스크래퍼 웹앱
Flask로 만든 웹 인터페이스
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
from concert_scraper import ConcertScraper
import json
import os
from datetime import datetime
import threading
import time

app = Flask(__name__)

# 전역 스크래퍼 인스턴스
scraper = ConcertScraper()

# 스크래핑 결과를 저장할 전역 변수
scraping_results = {}
scraping_status = {}

def scrape_async(task_id, url):
    """비동기 스크래핑 함수"""
    global scraping_results, scraping_status
    
    try:
        scraping_status[task_id] = "진행중"
        result = scraper.scrape_concert_info(url)
        scraping_results[task_id] = result
        scraping_status[task_id] = "완료"
    except Exception as e:
        scraping_results[task_id] = None
        scraping_status[task_id] = f"오류: {str(e)}"

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')

@app.route('/api/scrape', methods=['POST'])
def scrape_api():
    """스크래핑 API"""
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'URL이 필요합니다.'}), 400
    
    if not url.startswith('http'):
        return jsonify({'error': '올바른 URL을 입력해주세요.'}), 400
    
    # 작업 ID 생성
    task_id = f"task_{int(time.time() * 1000)}"
    
    # 비동기로 스크래핑 시작
    thread = threading.Thread(target=scrape_async, args=(task_id, url))
    thread.daemon = True
    thread.start()
    
    return jsonify({'task_id': task_id})

@app.route('/api/status/<task_id>')
def get_status(task_id):
    """스크래핑 상태 확인"""
    status = scraping_status.get(task_id, "알 수 없음")
    
    if status == "완료":
        result = scraping_results.get(task_id)
        return jsonify({
            'status': status,
            'result': result
        })
    else:
        return jsonify({
            'status': status
        })

@app.route('/api/save', methods=['POST'])
def save_result():
    """결과를 JSON 파일로 저장"""
    data = request.get_json()
    
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"concert_{timestamp}.json"
        filepath = os.path.join(os.getcwd(), filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        return jsonify({
            'success': True,
            'filename': filename
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.teardown_appcontext
def close_scraper(error):
    """앱 종료시 스크래퍼 정리"""
    if hasattr(scraper, 'close'):
        scraper.close()

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)