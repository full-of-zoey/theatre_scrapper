# Full of Zoey - 문화생활 기록 플랫폼

개인의 문화생활(공연, 전시, 영화 등)을 기록하고 관리하는 웹 애플리케이션입니다.

## 주요 기능

- 📝 문화생활 기록 작성 (제목, 카테고리, 날짜, 장소, 평점, 후기)
- 🖼️ 다중 이미지 업로드
- 🎭 카테고리별 맞춤 정보 (출연자/작가)
- 🔍 검색 및 필터링
- 📄 페이지네이션 (10개 단위)
- 🔗 공연 정보 URL 스크래핑 (SAC, 롯데콘서트홀 등)
- 🔒 편집 모드 (비밀번호 보호)

## 기술 스택

- **Backend**: Python Flask
- **Frontend**: Alpine.js
- **Database**: SQLite
- **Styling**: Vanilla CSS (미니멀 디자인)

## 로컬 실행 방법

### 1. 저장소 클론
```bash
git clone https://github.com/yourusername/fullofzoey.git
cd fullofzoey
```

### 2. 가상환경 설정 (선택사항)
```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate  # Windows
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

### 4. 애플리케이션 실행
```bash
python culture_log_app.py
```

브라우저에서 `http://localhost:5002` 접속

## 배포 방법

### Render.com 사용 (무료)

1. [Render.com](https://render.com) 가입
2. GitHub 저장소 연결
3. 새 Web Service 생성:
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn culture_log_app:app`
4. 환경 변수 설정:
   - `PYTHON_VERSION`: 3.9

### 도메인 연결 (fullofzoey.club)

1. 도메인 등록업체에서 DNS 설정
2. Render의 Custom Domain 메뉴에서 도메인 추가
3. DNS 레코드 설정:
   - Type: CNAME
   - Name: @ 또는 www
   - Value: [your-app].onrender.com

## 환경 설정

### 비밀번호 변경

`templates/culture_log_minimal.html` 파일의 930번째 줄 수정:
```javascript
if (this.loginPassword === 'your-password-here') {
```

### 이미지 저장소 (프로덕션)

프로덕션 환경에서는 클라우드 스토리지 사용을 권장합니다:

#### Cloudinary 설정 예시
1. [Cloudinary](https://cloudinary.com) 가입
2. API 키 획득
3. 환경 변수 설정
4. `culture_log_app.py`에서 업로드 로직 수정

## 데이터 백업

SQLite 데이터베이스 백업:
```bash
cp culture_log.db culture_log_backup_$(date +%Y%m%d).db
```

## 기여 방법

1. Fork 저장소
2. 새 브랜치 생성 (`git checkout -b feature/amazing-feature`)
3. 변경사항 커밋 (`git commit -m 'Add amazing feature'`)
4. 브랜치 푸시 (`git push origin feature/amazing-feature`)
5. Pull Request 생성

## 라이선스

MIT License

## 문의

문제가 있거나 제안사항이 있으시면 Issue를 등록해주세요.