import sys, os
sys.path.insert(0, os.path.expanduser("~/growth-cli"))
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
load_dotenv(os.path.expanduser("~/growth-cli/.env"))
from main import get_naver_trends, get_gsc_data, get_threads_data, get_meta_data, get_ga4_data

mcp = FastMCP("hydra_growth_mcp")

@mcp.tool(name="hydra_get_threads_insights", annotations={"readOnlyHint": True})
def hydra_get_threads_insights() -> str:
    """Threads 7일 인사이트: 조회수, 좋아요, 댓글, 리포스트, TOP 게시물"""
    data = get_threads_data()
    if not data:
        return "Threads 데이터 없음. THREADS_ACCESS_TOKEN 확인 필요."
    def pct(c, p):
        if not p or abs((c-p)/p*100)>500: return "(신규)"
        v=(c-p)/p*100; return f"({'▲' if v>0 else '▼'}{abs(v):.0f}%)"
    lines=[f"Threads @{data['username']} | 팔로워:{data['followers']:,}",
           f"조회:{data['views']:,} {pct(data['views'],data['views_prev'])}",
           f"좋아요:{data['likes']:,} {pct(data['likes'],data['likes_prev'])}",
           f"댓글:{data['replies']:,} / 리포스트:{data['reposts']:,}"]
    if data.get("top_posts"):
        lines.append("TOP 게시물:")
        for i,p in enumerate(data["top_posts"],1):
            lines.append(f"  {i}위 조회:{p['views']:,} | {p['text'][:60]}")
    return "\n".join(lines)

@mcp.tool(name="hydra_get_naver_trends", annotations={"readOnlyHint": True})
def hydra_get_naver_trends(keywords: str = "") -> str:
    """네이버 DataLab 키워드 트렌드 (최근 3개월). keywords=쉼표구분 예: 기타,통기타"""
    if keywords: os.environ["NAVER_TREND_KEYWORDS"] = keywords
    results = get_naver_trends()
    if not results: return "네이버 트렌드 데이터 없음."
    lines = ["네이버 키워드 트렌드 (3개월)"]
    for r in results:
        sign = "+" if r["diff"]>0 else ""
        lines.append(f"{r['trend']} {r['keyword']} 검색량:{r['latest']} 전월대비:{sign}{r['diff']}")
    return "\n".join(lines)

@mcp.tool(name="hydra_get_seo_report", annotations={"readOnlyHint": True})
def hydra_get_seo_report() -> str:
    """Google Search Console SEO 현황 (7일): 클릭, 노출, 순위, TOP 키워드"""
    results = get_gsc_data()
    if not results: return "GSC 데이터 없음. Google 인증 확인 필요."
    lines = ["SEO 현황 (7일)"]
    for s in results:
        lines.append(f"사이트: {s['site']}")
        lines.append(f"클릭:{s['clicks']} 노출:{s['impressions']} 평균순위:{s['avg_position']:.1f}위")
        for kw in (s.get("top_keywords") or [])[:5]:
            lines.append(f"  {kw['query']} | 클릭:{kw['clicks']} 순위:{kw['position']:.1f}위")
    return "\n".join(lines)

@mcp.tool(name="hydra_get_meta_ads", annotations={"readOnlyHint": True})
def hydra_get_meta_ads() -> str:
    """Meta 광고 성과 (7일): 지출, 전환수, CPA, CTR"""
    data = get_meta_data()
    if not data: return "Meta 광고 데이터 없음."
    lines = [f"Meta 광고 (7일) | 지출:{data.get('spend',0):,.0f}원",
             f"전환:{data.get('conversions',0)} CPA:{data.get('cpa',0):,.0f}원 CTR:{data.get('ctr',0):.2f}%"]
    if data.get("prev_spend"):
        c=(data.get('spend',0)-data['prev_spend'])/data['prev_spend']*100
        lines.append(f"전주대비: {'▲' if c>0 else '▼'}{abs(c):.0f}%")
    return "\n".join(lines)

@mcp.tool(name="hydra_get_ga4_data", annotations={"readOnlyHint": True})
def hydra_get_ga4_data() -> str:
    """GA4 트래픽 (7일): 세션, 전환, 매출"""
    data = get_ga4_data()
    if not data: return "GA4 데이터 없음."
    lines = [f"GA4 (7일) | 세션:{data.get('sessions',0):,} 전환:{data.get('conversions',0):,} 매출:{data.get('revenue',0):,.0f}원"]
    if data.get("prev_conversions") and data["prev_conversions"]>0:
        c=(data.get('conversions',0)-data['prev_conversions'])/data['prev_conversions']*100
        lines.append(f"전환 전주대비: {'▲' if c>0 else '▼'}{abs(c):.0f}%")
    return "\n".join(lines)

@mcp.tool(name="hydra_full_report", annotations={"readOnlyHint": True})
def hydra_full_report() -> str:
    """전체 마케팅 통합 리포트: Threads + 네이버트렌드 + SEO + Meta + GA4"""
    sections = []
    t = get_threads_data()
    if t:
        sections.append(f"[Threads] @{t['username']} 조회:{t['views']:,} 좋아요:{t['likes']:,}")
        for p in (t.get("top_posts") or [])[:2]:
            sections.append(f"  TOP: {p['text'][:50]}")
    for r in (get_naver_trends() or [])[:3]:
        sections.append(f"[네이버] {r['keyword']} {r['latest']} {r['trend']}")
    for s in (get_gsc_data() or []):
        sections.append(f"[SEO] {s['site']} 클릭:{s['clicks']} 순위:{s['avg_position']:.1f}위")
    m = get_meta_data()
    if m: sections.append(f"[Meta] 지출:{m.get('spend',0):,.0f}원 CPA:{m.get('cpa',0):,.0f}원")
    g = get_ga4_data()
    if g: sections.append(f"[GA4] 세션:{g.get('sessions',0):,} 전환:{g.get('conversions',0):,}")
    return "Hydra Growth 통합 리포트\n" + "\n".join(sections) if sections else "데이터 없음. .env API 키 확인 필요."



@mcp.tool(name="hydra_demo_report", annotations={"readOnlyHint": True})
def hydra_demo_report() -> str:
    """데모용 통합 리포트. 실제 연결 없이도 마케팅 데이터 분석 시연 가능."""
    return """📊 Hydra Growth 데모 리포트 (샘플 데이터)

[Threads] @lavamusic_kr 조회:12,847 좋아요:342 (▲38%)
  TOP: 기타 처음 시작하는 사람들이 가장 많이 하는 실수 (조회8,201)
  TOP: 독학 3개월차 vs 레슨 3개월차 차이 (조회3,102)

[네이버트렌드] 기타 검색량:68.2 ▲ (+4.1)
[네이버트렌드] 통기타 검색량:41.5 ▲ (+2.8)
[네이버트렌드] 기타레슨 검색량:33.1 ▲ (+5.2)

[SEO] lavamusic.kr 클릭:247 순위:4.2위 (▲1.3)
  키워드: 기타독학 (3위) / 어쿠스틱기타추천 (5위) / 기타레슨비용 (7위)

[Meta광고] 지출:₩320,000 CPA:₩8,900 CTR:2.41%
  전주대비: 지출▲15% / 전환▲28% → ROAS 개선 중

[GA4] 세션:1,842 전환:36 매출:₩1,240,000
  전환 전주대비: ▲22%"""


@mcp.tool(name="hydra_demo_dashboard", annotations={"readOnlyHint": True})
def hydra_demo_dashboard() -> str:
    """마케팅 성과 시각화 대시보드 (데모). Chart.js 차트 + 액션 아이템을 HTML로 반환합니다."""
    return """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo',sans-serif;background:#0f0f0f;color:#e8e8e8;padding:24px}
h1{font-size:18px;font-weight:700;margin-bottom:4px}
.sub{color:#888;font-size:13px;margin-bottom:24px}
.kpi-row{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:24px}
.kpi{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:12px;padding:16px}
.kpi-label{font-size:11px;color:#666;margin-bottom:6px}
.kpi-value{font-size:22px;font-weight:700;color:#fff}
.kpi-change{font-size:12px;margin-top:4px}
.up{color:#4caf50}.down{color:#f44336}
.charts{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px}
.chart-box{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:12px;padding:16px}
.chart-title{font-size:13px;font-weight:600;color:#aaa;margin-bottom:12px}
.actions{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:12px;padding:20px}
.actions h2{font-size:14px;font-weight:700;margin-bottom:14px;color:#cc785c}
.action-item{display:flex;gap:12px;align-items:flex-start;margin-bottom:12px}
.priority{background:#cc785c;color:#fff;font-size:10px;font-weight:700;padding:2px 8px;border-radius:4px;white-space:nowrap;margin-top:2px}
.priority.p2{background:#3d5afe}
.priority.p3{background:#555}
.action-text{font-size:13px;line-height:1.5;color:#ccc}
.action-text strong{color:#fff}
</style>
</head>
<body>
<h1>📊 Hydra Growth 마케팅 대시보드</h1>
<div class="sub">이번 주 성과 요약 · 2025년 4월 3주차</div>

<div class="kpi-row">
  <div class="kpi">
    <div class="kpi-label">Threads 조회수</div>
    <div class="kpi-value">12,847</div>
    <div class="kpi-change up">▲ 38% 전주대비</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">SEO 평균 순위</div>
    <div class="kpi-value">4.2위</div>
    <div class="kpi-change up">▲ 1.3계단 상승</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">Meta CPA</div>
    <div class="kpi-value">₩8,900</div>
    <div class="kpi-change up">전환 ▲28%</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">GA4 매출</div>
    <div class="kpi-value">₩1.24M</div>
    <div class="kpi-change up">▲ 22% 전주대비</div>
  </div>
</div>

<div class="charts">
  <div class="chart-box">
    <div class="chart-title">🧵 Threads 게시물별 조회수</div>
    <canvas id="threadsChart" height="160"></canvas>
  </div>
  <div class="chart-box">
    <div class="chart-title">🔍 네이버 키워드 트렌드</div>
    <canvas id="naverChart" height="160"></canvas>
  </div>
</div>

<div class="actions">
  <h2>⚡ 이번 주 액션 아이템</h2>
  <div class="action-item">
    <span class="priority">P1</span>
    <div class="action-text"><strong>기타레슨 랜딩페이지 최적화</strong> — 네이버 "기타레슨" 검색량 +5.2 상승 중. 지금 랜딩페이지로 연결되는 키워드 내부링크 강화하면 이번 달 안에 전환 20% 이상 개선 가능.</div>
  </div>
  <div class="action-item">
    <span class="priority p2">P2</span>
    <div class="action-text"><strong>Threads 초보자 시리즈 2편 발행</strong> — "실수" 게시물 8,201회로 압도적 1위. 같은 포맷으로 "기타 독학 vs 레슨 비교" 시리즈 이어가면 알고리즘 탈 가능성 높음.</div>
  </div>
  <div class="action-item">
    <span class="priority p3">P3</span>
    <div class="action-text"><strong>Meta 광고 예산 10% 증액 검토</strong> — ROAS 개선 중이고 CPA ₩8,900은 업계 평균 대비 효율적. 성과 좋을 때 스케일업 타이밍.</div>
  </div>
</div>

<script>
new Chart(document.getElementById('threadsChart'),{
  type:'bar',
  data:{
    labels:['실수 게시물','독학 vs 레슨','기타 게시물들'],
    datasets:[{
      data:[8201,3102,1544],
      backgroundColor:['#cc785c','#e8956a','#555'],
      borderRadius:6
    }]
  },
  options:{plugins:{legend:{display:false}},scales:{x:{grid:{color:'#222'},ticks:{color:'#666',font:{size:10}}},y:{grid:{color:'#222'},ticks:{color:'#666',font:{size:10}}}}}
});
new Chart(document.getElementById('naverChart'),{
  type:'line',
  data:{
    labels:['1월','2월','3월','4월'],
    datasets:[
      {label:'기타',data:[60.1,62.3,64.1,68.2],borderColor:'#cc785c',tension:0.4,pointRadius:3},
      {label:'통기타',data:[36.2,37.8,38.7,41.5],borderColor:'#3d5afe',tension:0.4,pointRadius:3},
      {label:'기타레슨',data:[24.1,26.3,27.9,33.1],borderColor:'#4caf50',tension:0.4,pointRadius:3}
    ]
  },
  options:{plugins:{legend:{labels:{color:'#888',font:{size:10}}}},scales:{x:{grid:{color:'#222'},ticks:{color:'#666',font:{size:10}}},y:{grid:{color:'#222'},ticks:{color:'#666',font:{size:10}}}}}
});
</script>
</body>
</html>"""


@mcp.tool(name="hydra_export_csv", annotations={"readOnlyHint": False})
def hydra_export_csv() -> str:
    """마케팅 데이터를 CSV 파일로 내보냅니다. ~/growth-cli/reports/ 폴더에 날짜별로 저장됩니다."""
    import csv
    from datetime import datetime

    reports_dir = os.path.expanduser("~/growth-cli/reports")
    os.makedirs(reports_dir, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    filepath = os.path.join(reports_dir, f"hydra_report_{today}.csv")

    rows = []

    threads = get_threads_data()
    if threads:
        rows.append(["Threads", "조회수", threads.get("views", 0), ""])
        rows.append(["Threads", "좋아요", threads.get("likes", 0), ""])
        rows.append(["Threads", "댓글", threads.get("replies", 0), ""])
        rows.append(["Threads", "팔로워", threads.get("followers", 0), ""])
        for p in (threads.get("top_posts") or [])[:5]:
            rows.append(["Threads", "TOP게시물", p["views"], p["text"][:50]])

    trends = get_naver_trends()
    if trends:
        for t in trends:
            rows.append(["네이버트렌드", t["keyword"], t["latest"], f"전월대비{t['diff']:+}"])

    gsc = get_gsc_data()
    if gsc:
        for site in gsc:
            rows.append(["SEO", site.get("site",""), site.get("clicks",0), f"순위{site.get('avg_position',0):.1f}위"])
            for kw in (site.get("top_keywords") or [])[:5]:
                rows.append(["SEO_키워드", kw.get("query",""), kw.get("clicks",0), f"순위{kw.get('position',0):.1f}위"])

    meta = get_meta_data()
    if meta:
        rows.append(["Meta광고", "지출", meta.get("spend", 0), ""])
        rows.append(["Meta광고", "전환수", meta.get("conversions", 0), ""])
        rows.append(["Meta광고", "CPA", meta.get("cpa", 0), ""])
        rows.append(["Meta광고", "CTR", meta.get("ctr", 0), ""])

    ga4 = get_ga4_data()
    if ga4:
        rows.append(["GA4", "세션수", ga4.get("sessions", 0), ""])
        rows.append(["GA4", "전환수", ga4.get("conversions", 0), ""])
        rows.append(["GA4", "매출", ga4.get("revenue", 0), ""])

    if not rows:
        return "내보낼 데이터가 없어요. .env API 키를 확인해주세요."

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["채널", "지표", "값", "메모"])
        writer.writerows(rows)

    return f"✅ CSV 내보내기 완료!\n경로: {filepath}\n항목 수: {len(rows)}개"

if __name__ == "__main__":
    mcp.run(transport="stdio")
