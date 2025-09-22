#!/usr/bin/env python3
"""
Firebase 버전 - My Culture Log
Firebase Firestore + Storage 사용
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore, storage
import json
import os
import uuid
from datetime import datetime
from PIL import Image
import io
import base64

app = Flask(__name__)
CORS(app)

# Firebase 초기화
# 1. Firebase Console에서 서비스 계정 키 다운로드
# 2. 아래 경로에 JSON 파일 저장
cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred, {
    'storageBucket': 'your-project-id.appspot.com'  # Firebase Console에서 확인
})

# Firestore 클라이언트
db = firestore.client()
bucket = storage.bucket()

def resize_image(image_data, max_size=(800, 800)):
    """이미지 리사이즈"""
    img = Image.open(io.BytesIO(image_data))
    img.thumbnail(max_size, Image.Resampling.LANCZOS)

    output = io.BytesIO()
    img.save(output, format='JPEG', quality=85)
    return output.getvalue()

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('culture_log_firebase.html')

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """문화생활 기록 목록 조회"""
    try:
        # 페이지네이션
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))

        # 필터
        category = request.args.get('category')
        search = request.args.get('search')

        # Firestore 쿼리
        logs_ref = db.collection('culture_logs')

        if category:
            logs_ref = logs_ref.where('category', '==', category)

        # 정렬 및 제한
        logs_ref = logs_ref.order_by('date', direction=firestore.Query.DESCENDING)
        logs_ref = logs_ref.limit(per_page).offset((page - 1) * per_page)

        docs = logs_ref.stream()
        logs = []

        for doc in docs:
            log_data = doc.to_dict()
            log_data['id'] = doc.id
            logs.append(log_data)

        # 전체 개수 (페이지네이션용)
        total_ref = db.collection('culture_logs')
        if category:
            total_ref = total_ref.where('category', '==', category)
        total = len(list(total_ref.stream()))

        return jsonify({
            'logs': logs,
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

        # Firestore에 문서 추가
        doc_ref = db.collection('culture_logs').document()
        doc_ref.set({
            'title': data.get('title'),
            'category': data.get('category'),
            'date': data.get('date'),
            'venue': data.get('venue'),
            'performers': data.get('performers', []),
            'program': data.get('program', []),
            'price': data.get('price', []),
            'rating': data.get('rating'),
            'review': data.get('review'),
            'photos': data.get('photos', []),
            'source_url': data.get('source_url'),
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP
        })

        return jsonify({'success': True, 'id': doc_ref.id})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload-photos', methods=['POST'])
def upload_photos():
    """Firebase Storage에 사진 업로드"""
    try:
        files = request.files.getlist('photos')
        uploaded_files = []

        for file in files:
            if file and file.filename:
                # 파일 읽기
                file_data = file.read()

                # 리사이즈
                resized_data = resize_image(file_data)

                # 고유 파일명 생성
                file_ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"{uuid.uuid4()}.{file_ext}"

                # Firebase Storage에 업로드
                blob = bucket.blob(f"photos/{filename}")
                blob.upload_from_string(resized_data, content_type=f"image/{file_ext}")

                # 공개 URL 생성
                blob.make_public()

                uploaded_files.append({
                    'filename': filename,
                    'original_name': file.filename,
                    'url': blob.public_url
                })

        return jsonify({
            'success': True,
            'files': uploaded_files
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/logs/<log_id>', methods=['DELETE'])
def delete_log(log_id):
    """문화생활 기록 삭제"""
    try:
        # 문서 가져오기
        doc_ref = db.collection('culture_logs').document(log_id)
        doc = doc_ref.get()

        if doc.exists:
            # 이미지 삭제
            data = doc.to_dict()
            if data.get('photos'):
                for photo in data['photos']:
                    try:
                        blob = bucket.blob(f"photos/{photo.get('filename')}")
                        blob.delete()
                    except:
                        pass

            # 문서 삭제
            doc_ref.delete()

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stats')
def get_stats():
    """통계 데이터"""
    try:
        logs_ref = db.collection('culture_logs')
        all_logs = list(logs_ref.stream())

        # 기본 통계
        total_logs = len(all_logs)

        # 평균 평점
        ratings = [doc.to_dict().get('rating', 0) for doc in all_logs if doc.to_dict().get('rating')]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0

        # 카테고리별 통계
        category_stats = {}
        for doc in all_logs:
            cat = doc.to_dict().get('category')
            if cat:
                category_stats[cat] = category_stats.get(cat, 0) + 1

        # 월별 통계 (올해)
        current_year = datetime.now().year
        monthly_stats = {}
        for doc in all_logs:
            date_str = doc.to_dict().get('date')
            if date_str:
                date = datetime.strptime(date_str, '%Y-%m-%d')
                if date.year == current_year:
                    month = str(date.month).zfill(2)
                    monthly_stats[month] = monthly_stats.get(month, 0) + 1

        return jsonify({
            'total_logs': total_logs,
            'avg_rating': round(avg_rating, 1),
            'category_stats': category_stats,
            'monthly_stats': monthly_stats
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5002))
    app.run(debug=True, host='0.0.0.0', port=port)