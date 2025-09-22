#!/usr/bin/env python3
"""
🎭 My Culture Log - 개인 문화생활 기록 플랫폼 MVP
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from simple_scraper import SimpleConcertScraper
import sqlite3
import json
import os
import uuid
from datetime import datetime
from PIL import Image
import threading
import time

app = Flask(__name__)
CORS(app)

# 디렉토리 설정
UPLOAD_FOLDER = 'uploads'
THUMBNAILS_FOLDER = 'thumbnails'
DATABASE = 'culture_log.db'

# 폴더 생성
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(THUMBNAILS_FOLDER, exist_ok=True)
os.makedirs('static', exist_ok=True)

# 전역 변수
scraper = SimpleConcertScraper()
scraping_results = {}
scraping_status = {}

def init_db():
    """데이터베이스 초기화"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # 문화생활 기록 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS culture_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            venue TEXT,
            performers TEXT,
            program TEXT,
            price TEXT,
            rating INTEGER,
            review TEXT,
            photos TEXT,
            source_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    print(f"✅ 데이터베이스 초기화 완료: {DATABASE}")

def create_thumbnail(image_path, thumbnail_path, size=(300, 400)):
    """이미지 썸네일 생성"""
    try:
        with Image.open(image_path) as img:
            # RGBA를 RGB로 변환 (투명도 제거)
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            img.thumbnail(size, Image.Resampling.LANCZOS)
            img.save(thumbnail_path, 'JPEG', quality=85)
        return True
    except Exception as e:
        print(f"썸네일 생성 실패: {e}")
        return False

def scrape_async(task_id, url):
    """비동기 스크래핑"""
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
    return render_template('culture_log_minimal.html')

@app.route('/api/scrape', methods=['POST'])
def scrape_performance():
    """공연 정보 스크래핑"""
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'URL이 필요합니다.'}), 400
    
    task_id = f"task_{int(time.time() * 1000)}"
    thread = threading.Thread(target=scrape_async, args=(task_id, url))
    thread.daemon = True
    thread.start()
    
    return jsonify({'task_id': task_id})

@app.route('/api/scrape-status/<task_id>')
def scrape_status(task_id):
    """스크래핑 상태 확인"""
    status = scraping_status.get(task_id, "알 수 없음")
    
    if status == "완료":
        result = scraping_results.get(task_id)
        return jsonify({'status': status, 'result': result})
    else:
        return jsonify({'status': status})

@app.route('/api/upload-photos', methods=['POST'])
def upload_photos():
    """사진 업로드"""
    try:
        files = request.files.getlist('photos')
        uploaded_files = []
        
        for file in files:
            if file and file.filename:
                # 고유 파일명 생성
                file_ext = file.filename.rsplit('.', 1)[1].lower()
                if file_ext not in ['jpg', 'jpeg', 'png', 'gif']:
                    continue
                    
                filename = f"{uuid.uuid4()}.{file_ext}"
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                
                # 원본 저장
                file.save(filepath)
                
                # 썸네일 생성
                thumbnail_path = os.path.join(THUMBNAILS_FOLDER, filename)
                create_thumbnail(filepath, thumbnail_path)
                
                uploaded_files.append({
                    'filename': filename,
                    'original_name': file.filename
                })
        
        return jsonify({
            'success': True,
            'files': uploaded_files
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """문화생활 기록 목록 조회"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # 페이지네이션
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        offset = (page - 1) * per_page
        
        # 필터
        category = request.args.get('category')
        search = request.args.get('search')
        
        query = "SELECT * FROM culture_logs"
        params = []
        
        conditions = []
        if category:
            conditions.append("category = ?")
            params.append(category)
        
        if search:
            conditions.append("(title LIKE ? OR venue LIKE ? OR performers LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY date DESC, created_at DESC LIMIT ? OFFSET ?"
        params.extend([per_page, offset])
        
        cursor.execute(query, params)
        logs = cursor.fetchall()
        
        # 전체 개수 조회
        count_query = "SELECT COUNT(*) FROM culture_logs"
        if conditions:
            count_query += " WHERE " + " AND ".join(conditions[:-2] if search else conditions)
            cursor.execute(count_query, params[:-2])
        else:
            cursor.execute(count_query)
        
        total = cursor.fetchone()[0]
        
        # 결과 포맷팅
        result = []
        for log in logs:
            photos = json.loads(log[10]) if log[10] else []
            result.append({
                'id': log[0],
                'title': log[1],
                'category': log[2],
                'date': log[3],
                'venue': log[4],
                'performers': log[5],
                'program': log[6],
                'price': log[7],
                'rating': log[8],
                'review': log[9],
                'photos': photos,
                'source_url': log[11],
                'created_at': log[12]
            })
        
        conn.close()
        
        return jsonify({
            'logs': result,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs', methods=['POST'])
def create_log():
    """새 문화생활 기록 생성"""
    try:
        data = request.get_json()
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO culture_logs 
            (title, category, date, venue, performers, program, price, rating, review, photos, source_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('title'),
            data.get('category'),
            data.get('date'),
            data.get('venue'),
            json.dumps(data.get('performers', []), ensure_ascii=False),
            json.dumps(data.get('program', []), ensure_ascii=False),
            json.dumps(data.get('price', []), ensure_ascii=False),
            data.get('rating'),
            data.get('review'),
            json.dumps(data.get('photos', []), ensure_ascii=False),
            data.get('source_url')
        ))
        
        log_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'id': log_id})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stats')
def get_stats():
    """통계 데이터"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # 기본 통계
        cursor.execute("SELECT COUNT(*) FROM culture_logs")
        total_logs = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(rating) FROM culture_logs WHERE rating IS NOT NULL")
        avg_rating = cursor.fetchone()[0] or 0
        
        # 카테고리별 통계
        cursor.execute("""
            SELECT category, COUNT(*) 
            FROM culture_logs 
            GROUP BY category 
            ORDER BY COUNT(*) DESC
        """)
        category_stats = dict(cursor.fetchall())
        
        # 월별 통계 (올해)
        cursor.execute("""
            SELECT strftime('%m', date) as month, COUNT(*) 
            FROM culture_logs 
            WHERE strftime('%Y', date) = strftime('%Y', 'now')
            GROUP BY month 
            ORDER BY month
        """)
        monthly_stats = dict(cursor.fetchall())
        
        # 평점 분포
        cursor.execute("""
            SELECT rating, COUNT(*) 
            FROM culture_logs 
            WHERE rating IS NOT NULL
            GROUP BY rating 
            ORDER BY rating
        """)
        rating_distribution = dict(cursor.fetchall())
        
        conn.close()
        
        return jsonify({
            'total_logs': total_logs,
            'avg_rating': round(avg_rating, 1),
            'category_stats': category_stats,
            'monthly_stats': monthly_stats,
            'rating_distribution': rating_distribution
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """업로드된 파일 서빙"""
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/thumbnails/<filename>')
def thumbnail_file(filename):
    """썸네일 파일 서빙"""
    return send_from_directory(THUMBNAILS_FOLDER, filename)

@app.route('/api/logs/<int:log_id>', methods=['DELETE'])
def delete_log(log_id):
    """문화생활 기록 삭제"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        # 먼저 사진 파일들 삭제
        cursor.execute("SELECT photos FROM culture_logs WHERE id = ?", (log_id,))
        result = cursor.fetchone()

        if result and result[0]:
            photos = json.loads(result[0])
            for photo in photos:
                filename = photo.get('filename')
                if filename:
                    try:
                        os.remove(os.path.join(UPLOAD_FOLDER, filename))
                        os.remove(os.path.join(THUMBNAILS_FOLDER, filename))
                    except:
                        pass

        # 레코드 삭제
        cursor.execute("DELETE FROM culture_logs WHERE id = ?", (log_id,))
        conn.commit()
        conn.close()

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reset-database', methods=['POST'])
def reset_database():
    """데이터베이스 완전 초기화 (개발용)"""
    try:
        # 모든 업로드된 파일 삭제
        import shutil
        if os.path.exists(UPLOAD_FOLDER):
            shutil.rmtree(UPLOAD_FOLDER)
        if os.path.exists(THUMBNAILS_FOLDER):
            shutil.rmtree(THUMBNAILS_FOLDER)

        # 폴더 재생성
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(THUMBNAILS_FOLDER, exist_ok=True)

        # 데이터베이스 삭제 및 재생성
        if os.path.exists(DATABASE):
            os.remove(DATABASE)

        init_db()

        return jsonify({'success': True, 'message': '데이터베이스가 완전히 초기화되었습니다.'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    init_db()
    # 프로덕션에서는 debug=False로 설정
    import os
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    port = int(os.environ.get('PORT', 5002))
    app.run(debug=debug_mode, host='0.0.0.0', port=port)