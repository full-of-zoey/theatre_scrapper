# Firebase 설정 가이드

## 🔥 Firebase 사용 시 구조

```
Firebase (무료)
├── Firestore Database (NoSQL DB)
├── Firebase Storage (이미지 저장)
├── Firebase Hosting (웹 호스팅)
└── Firebase Auth (선택사항)
```

## 📋 설정 단계

### 1. Firebase 프로젝트 생성
1. [Firebase Console](https://console.firebase.google.com) 접속
2. "프로젝트 추가" 클릭
3. 프로젝트 이름: `fullofzoey`
4. Google Analytics 비활성화 (선택사항)

### 2. Firestore Database 설정
1. 좌측 메뉴 → Firestore Database
2. "데이터베이스 만들기"
3. 프로덕션 모드 선택
4. 지역: asia-northeast3 (서울)
5. 규칙 수정 (임시 - 추후 보안 강화 필요):
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      allow read: if true;
      allow write: if request.auth != null;
    }
  }
}
```

### 3. Firebase Storage 설정
1. 좌측 메뉴 → Storage
2. "시작하기" 클릭
3. 프로덕션 모드 선택
4. 지역: asia-northeast3 (서울)
5. 규칙 수정:
```javascript
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    match /{allPaths=**} {
      allow read: if true;
      allow write: if request.auth != null;
    }
  }
}
```

### 4. 서비스 계정 키 생성
1. 프로젝트 설정 → 서비스 계정
2. "새 비공개 키 생성"
3. JSON 파일 다운로드
4. 파일명을 `serviceAccountKey.json`으로 변경
5. 프로젝트 루트에 저장
6. `.gitignore`에 추가 (중요!)

### 5. Firebase Hosting 설정
1. Firebase CLI 설치:
```bash
npm install -g firebase-tools
```

2. 로그인:
```bash
firebase login
```

3. 프로젝트 초기화:
```bash
firebase init hosting
```

4. 설정:
   - 기존 프로젝트 선택
   - Public 디렉토리: `public`
   - Single-page app: No
   - GitHub 자동 배포: Yes (선택사항)

5. 배포:
```bash
firebase deploy --only hosting
```

### 6. 커스텀 도메인 연결
1. Firebase Console → Hosting
2. "도메인 연결" 클릭
3. `fullofzoey.club` 입력
4. DNS 설정 지시 따르기

## 🔧 Python 패키지 설치

```bash
pip install firebase-admin
```

requirements.txt 업데이트:
```
Flask==3.1.2
Flask-Cors==6.0.1
Pillow==11.3.0
requests==2.32.5
beautifulsoup4==4.13.5
firebase-admin==6.1.0
gunicorn==21.2.0
```

## 🚀 실행 방법

### 로컬 테스트
```bash
python firebase_version.py
```

### Firebase Hosting에 배포
정적 파일만 호스팅 가능하므로, Flask 앱은 다음 중 선택:
1. **Cloud Run** (Google Cloud - 무료 한도 있음)
2. **Cloud Functions** (Firebase - 서버리스)
3. **Render/Railway** (Flask 앱) + Firebase (DB/Storage)

## 📊 현재 구조 vs Firebase 구조

| 기능 | 현재 (SQLite + 로컬) | Firebase |
|-----|-------------------|----------|
| DB | SQLite (로컬 파일) | Firestore (클라우드) |
| 이미지 | uploads/ 폴더 | Firebase Storage |
| 인증 | 하드코딩 비밀번호 | Firebase Auth |
| 백업 | 수동 | 자동 |
| 확장성 | 제한적 | 무제한 |
| 비용 | 서버 비용 | 무료 한도 내 무료 |

## 🎯 추천 아키텍처

### 옵션 1: 풀 Firebase (추천)
- **Frontend**: Firebase Hosting (정적 파일)
- **Backend**: Cloud Functions (API)
- **Database**: Firestore
- **Storage**: Firebase Storage
- **Auth**: Firebase Auth

### 옵션 2: 하이브리드
- **Frontend**: Firebase Hosting
- **Backend**: Render.com (Flask)
- **Database**: Firestore
- **Storage**: Firebase Storage

### 옵션 3: 현재 구조 유지
- **All**: Render.com
- SQLite + 로컬 스토리지
- 단순하지만 제한적

## 🔐 보안 고려사항

1. **서비스 계정 키**: 절대 GitHub에 올리지 않기
2. **Firestore 규칙**: 프로덕션에서는 인증 필수
3. **Storage 규칙**: 업로드 크기 제한
4. **API 키**: 환경 변수로 관리

## 💡 Firebase 장점 요약

✅ **무료 한도가 넉넉함**
- Firestore: 1GB 저장, 일일 50,000 읽기
- Storage: 5GB 저장, 1GB/일 다운로드
- Hosting: 10GB 저장, 360MB/일 전송

✅ **자동 백업 & 실시간 동기화**
✅ **글로벌 CDN으로 빠른 이미지 로딩**
✅ **SSL 인증서 자동 관리**
✅ **Google 인프라의 안정성**

## 🤔 결정 도움

**Firebase를 선택하면 좋은 경우:**
- 확장 가능한 구조를 원할 때
- 이미지가 많이 업로드될 예정일 때
- 실시간 동기화가 필요할 때
- 여러 사용자가 동시 사용할 때

**현재 구조를 유지하면 좋은 경우:**
- 개인용으로만 사용할 때
- 단순함을 선호할 때
- Firebase 학습 시간이 없을 때