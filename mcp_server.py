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

if __name__ == "__main__":
    mcp.run(transport="stdio")
