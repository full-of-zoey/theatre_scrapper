# 배포 가이드 - Full of Zoey

## 📝 배포 준비 체크리스트

### 1. GitHub 저장소 생성
1. GitHub.com에서 새 저장소 생성 (예: `fullofzoey`)
2. 로컬에서 원격 저장소 연결:
```bash
git remote add origin https://github.com/yourusername/fullofzoey.git
git add .
git commit -m "Initial commit"
git push -u origin main
```

### 2. 비밀번호 보안 설정
⚠️ **중요**: 프로덕션 배포 전 비밀번호 변경 필수!
- `templates/culture_log_minimal.html` 930번째 줄 수정
- 환경 변수로 관리하는 것을 권장

## 🚀 배포 옵션

### 옵션 1: Render.com (추천 - 무료)

#### 장점
- 무료 플랜 제공
- 자동 HTTPS
- GitHub 연동 자동 배포
- 1GB 영구 스토리지 (이미지 저장용)

#### 배포 단계
1. [Render.com](https://render.com) 가입
2. Dashboard → New → Web Service
3. GitHub 저장소 연결
4. 설정:
   - **Name**: fullofzoey
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn culture_log_app:app`
5. 환경 변수 추가:
   - `FLASK_ENV`: production
   - `PYTHON_VERSION`: 3.9

#### 도메인 연결
1. Render Dashboard → Settings → Custom Domain
2. `fullofzoey.club` 추가
3. DNS 설정 (도메인 등록업체에서):
   - Type: CNAME
   - Name: @ 또는 www
   - Value: [your-app].onrender.com

### 옵션 2: Railway.app (대안)

#### 장점
- 더 빠른 콜드 스타트
- 월 $5 크레딧 무료
- PostgreSQL 무료 제공

#### 배포 단계
1. [Railway.app](https://railway.app) 가입
2. New Project → Deploy from GitHub repo
3. 환경 변수 설정
4. 도메인 설정

### 옵션 3: Vercel (정적 사이트용)

Flask 앱을 Vercel에서 실행하려면 추가 설정 필요:
1. `vercel.json` 파일 생성
2. Serverless 함수로 변환

## 🖼️ 이미지 스토리지 솔루션

### 현재 문제점
- 로컬 파일 시스템 사용 중
- 서버 재시작 시 업로드 파일 손실 가능
- Render 무료 플랜: 서버 15분 미사용 시 슬립

### 해결 방안

#### 1. Cloudinary (추천)
```python
# pip install cloudinary
import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name="your_cloud_name",
    api_key="your_api_key",
    api_secret="your_api_secret"
)

# 업로드 예시
result = cloudinary.uploader.upload(file)
image_url = result['secure_url']
```

#### 2. AWS S3
- 월 5GB 무료
- 설정이 복잡하지만 확장성 좋음

#### 3. Render Disk (현재 설정)
- `render.yaml`에 이미 설정됨
- 1GB 영구 스토리지
- 추가 비용 없음

## 🔐 보안 체크리스트

- [ ] 비밀번호 환경 변수로 이동
- [ ] SECRET_KEY 설정
- [ ] CORS 설정 확인
- [ ] Debug 모드 비활성화
- [ ] 민감한 정보 .gitignore에 추가

## 📊 모니터링

### 무료 모니터링 도구
1. **UptimeRobot**: 사이트 가동 시간 모니터링
2. **Google Analytics**: 사용자 분석
3. **Sentry**: 에러 추적 (무료 플랜)

## 🆘 트러블슈팅

### 일반적인 문제

1. **모듈 import 에러**
   - `requirements.txt` 확인
   - Python 버전 확인

2. **데이터베이스 에러**
   - SQLite 파일 권한 확인
   - 초기화 함수 실행 확인

3. **이미지 업로드 실패**
   - 디렉토리 권한 확인
   - 디스크 공간 확인

## 📱 모바일 최적화

현재 반응형 디자인이 적용되어 있지만 추가 개선 가능:
- PWA (Progressive Web App) 변환
- 오프라인 지원 추가

## 🔄 백업 전략

1. **데이터베이스 자동 백업**
   - GitHub Actions로 일일 백업
   - Google Drive 연동

2. **이미지 백업**
   - Cloudinary 사용 시 자동 백업
   - 로컬 백업 스크립트 작성

## 📈 성능 최적화

1. **캐싱 추가**
   - Flask-Caching 설치
   - Redis 연동 (선택사항)

2. **이미지 최적화**
   - 업로드 시 자동 압축
   - WebP 포맷 지원

3. **CDN 사용**
   - Cloudflare 무료 플랜
   - 정적 파일 캐싱

## 💡 추가 기능 아이디어

- 소셜 로그인 (OAuth)
- 데이터 내보내기/가져오기
- 통계 대시보드
- 공유 기능
- 태그 시스템
- 댓글 기능

## 📞 지원

문제가 있으시면 GitHub Issues에 등록해주세요!