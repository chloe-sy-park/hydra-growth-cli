# 📊 Hydra Growth CLI

> 네이버 · 구글 · 메타 광고 데이터를 한 줄 명령어로 분석하고,
> AI가 지금 당장 뭘 해야 할지 알려주는 마케터용 CLI 도구

## 미리보기

```bash
python main.py demo
```

## 왜 만들었나요?

광고 성과를 보려면 매번 네이버, 구글, 메타에 따로 로그인해야 했어요.
데이터를 모아도 "그래서 지금 뭘 해야 하지?"가 막막했고요.

**Hydra Growth CLI는 이 두 가지를 해결해요:**
- 모든 채널 데이터를 명령어 하나로 통합
- AI가 지금 당장 해야 할 액션을 우선순위로 제안

## 설치 방법

### 1. 저장소 클론
```bash
git clone https://github.com/본인계정/hydra-growth-cli.git
cd hydra-growth-cli
```

### 2. 가상환경 + 패키지 설치
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. API 키 설정
```bash
cp .env.example .env
```
`.env` 파일에 본인 키 입력: