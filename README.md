# 📊 Hydra Growth CLI + MCP

> 네이버 · 구글 · 메타 · Threads 마케팅 데이터를 **Claude / ChatGPT에서 자연어로 바로 조회**하는 MCP 서버 + CLI 도구

---

## ✨ 이런 게 가능해져요

Claude Desktop에 연결하면 이렇게 쓸 수 있어요:

```
나: "이번 주 마케팅 성과 요약해줘"

Claude: 이번 주 주요 지표를 확인했어요.

Threads @계정ID — 조회 3,216회, 좋아요 37개
최고 성과 게시물: "오늘의 스레드는+..."

네이버 키워드 트렌드 — 키워드1(-3.1), 키워드2(-2.8) 하락세
→ 비수기 진입 중. 콘텐츠 방향 전환 고려 필요.

도메인주소.kr — 클릭 5회, 평균 순위 6.1위
→ 1페이지 진입 직전. 상위 키워드 집중 공략 추천.
```

CLI로도 그대로 쓸 수 있어요:

```bash
python main.py status
```

---

## 🔌 MCP 서버 연결 방법 (Claude Desktop)

마케팅 데이터를 Claude에서 바로 물어볼 수 있게 연결하는 방법이에요.

### 1. 저장소 클론 + 설치

```bash
git clone https://github.com/chloe-sy-park/hydra-growth-cli.git
cd hydra-growth-cli
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. API 키 설정

```bash
cp .env.example .env
```

`.env` 파일에 보유한 API 키 입력 (없는 건 비워도 됨):

```env
# Threads
THREADS_ACCESS_TOKEN=

# 네이버 DataLab
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=
NAVER_TREND_KEYWORDS=키워드1,키워드2   # 추적할 키워드

# Google (Search Console + GA4)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REFRESH_TOKEN=
GSC_SITE_URLS=https://yoursite.com/
GA4_PROPERTY_ID=

# Meta 광고
META_ACCESS_TOKEN=
META_AD_ACCOUNT_ID=
```

### 3. Claude Desktop 설정에 추가

`~/Library/Application Support/Claude/claude_desktop_config.json` 파일을 열어서 `mcpServers` 섹션 추가:

```json
{
  "mcpServers": {
    "hydra-growth": {
      "command": "/절대경로/hydra-growth-cli/venv/bin/python3",
      "args": ["/절대경로/hydra-growth-cli/mcp_server.py"]
    }
  }
}
```

경로 확인 방법:
```bash
cd hydra-growth-cli && pwd
# 출력된 경로를 위에 붙여넣기
```

### 4. Claude Desktop 재시작

재시작 후 Claude에게 바로 물어보면 돼요:
- "이번 주 마케팅 성과 요약해줘"
- "네이버에서 기타 검색량 트렌드 어때?"
- "지금 SEO 순위 어디야?"
- "Meta 광고 이번 주 CPA 얼마야?"

---

## 🛠 CLI로 쓰는 방법

```bash
source venv/bin/activate
python main.py status      # 전체 현황 한눈에
python main.py demo        # 샘플 데이터로 미리보기
```

---

## 연결 가능한 채널

| 채널 | 데이터 |
|------|--------|
| 🧵 Threads | 조회수, 좋아요, 댓글, 리포스트, TOP 게시물 |
| 🔍 네이버 DataLab | 키워드 검색량 트렌드 (월별) |
| 📈 Google Search Console | 클릭, 노출, 순위, TOP 키워드 |
| 📊 Meta 광고 | 지출, 전환수, CPA, CTR |
| 📉 Google Analytics 4 | 세션, 전환, 매출 |

---

## API 키 발급 방법

<details>
<summary>Threads API</summary>

1. [Meta for Developers](https://developers.facebook.com) → 앱 생성
2. Threads API 추가 → Access Token 발급
3. 만료 전 갱신 필요 (60일)

</details>

<details>
<summary>네이버 DataLab API</summary>

1. [네이버 개발자 센터](https://developers.naver.com) → 애플리케이션 등록
2. 검색어 트렌드 API 사용 신청
3. Client ID / Secret 복사

</details>

<details>
<summary>Google (GSC + GA4)</summary>

1. [Google Cloud Console](https://console.cloud.google.com) → 프로젝트 생성
2. Search Console API + Analytics Data API 활성화
3. OAuth 2.0 클라이언트 ID 생성
4. `python get_token.py` 실행 → Refresh Token 발급

</details>

<details>
<summary>Meta 광고</summary>

1. [Meta Business Suite](https://business.facebook.com) → 광고 계정 연결
2. [Graph API Explorer](https://developers.facebook.com/tools/explorer) → Access Token 발급
3. `ads_read` 권한 포함 필요

</details>

---

## 라이선스

MIT
