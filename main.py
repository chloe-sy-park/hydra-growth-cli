import typer
import anthropic
import requests
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
import config
from helpers import canonicalize_page, resolve_date

app = typer.Typer()
console = Console()

def get_naver_data():
    """네이버 검색광고 데이터 가져오기"""
    import hmac
    import hashlib
    import base64
    import time

    def get_signature(timestamp, method, path):
        message = f"{timestamp}.{method}.{path}"
        signature = hmac.new(
            config.NAVER_SECRET_KEY.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        )
        return base64.b64encode(signature.digest()).decode('utf-8')

    timestamp = str(int(time.time() * 1000))
    path = "/ncc/campaigns"
    method = "GET"

    headers = {
        "X-Timestamp": timestamp,
        "X-API-KEY": config.NAVER_API_KEY,
        "X-Customer": str(config.NAVER_CUSTOMER_ID),
        "X-Signature": get_signature(timestamp, method, path),
        "Content-Type": "application/json"
    }

    # 최근 7일 날짜
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    prev_end = (datetime.now() - timedelta(days=8)).strftime('%Y-%m-%d')
    prev_start = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')

    def fetch_stats(since, until):
        path_stat = "/stats"
        timestamp_s = str(int(time.time() * 1000))
        headers_s = {
            "X-Timestamp": timestamp_s,
            "X-API-KEY": config.NAVER_API_KEY,
            "X-Customer": str(config.NAVER_CUSTOMER_ID),
            "X-Signature": get_signature(timestamp_s, "GET", path_stat),
            "Content-Type": "application/json"
        }
        params = {
            "datePreset": "custom",
            "startDate": since,
            "endDate": until,
            "timeUnit": "allDays",
            "fields": "clkCnt,impCnt,salesAmt,crpCost",
            "stat": "campaign"
        }
        r = requests.get(
            "https://api.naver.com/stats",
            headers=headers_s,
            params=params
        )
        return r.json()

    current = fetch_stats(start_date, end_date)
    previous = fetch_stats(prev_start, prev_end)

    def parse(data):
        if not data or 'data' not in data:
            return None
        rows = data['data']
        if not rows:
            return None
        total_cost = sum(float(r.get('crpCost', 0)) for r in rows)
        total_conv = sum(int(r.get('salesAmt', 0)) for r in rows)
        total_clicks = sum(int(r.get('clkCnt', 0)) for r in rows)
        total_imp = sum(int(r.get('impCnt', 0)) for r in rows)
        cpa = total_cost / total_conv if total_conv > 0 else 0
        ctr = (total_clicks / total_imp * 100) if total_imp > 0 else 0
        return {
            'spend': total_cost,
            'conversions': total_conv,
            'cpa': cpa,
            'ctr': ctr
        }

    curr_parsed = parse(current)
    prev_parsed = parse(previous)

    if not curr_parsed:
        return None

    if prev_parsed:
        curr_parsed['prev_cpa'] = prev_parsed['cpa']
        curr_parsed['prev_conversions'] = prev_parsed['conversions']

    return curr_parsed



def get_threads_data():
    """Threads 인사이트: 추세 + 콘텐츠별 성과"""
    try:
        import os as _os
        token = _os.getenv("THREADS_ACCESS_TOKEN")
        if not token:
            return None
        base = "https://graph.threads.net/v1.0"
        me = requests.get(f"{base}/me", params={"fields":"id,username,name","access_token":token}, timeout=10).json()
        user_id = me.get("id")
        if not user_id:
            return None

        # 14일 인사이트 → 이번 주 vs 저번 주
        now = datetime.now()
        ins = requests.get(f"{base}/{user_id}/threads_insights", params={
            "metric": "views,likes,replies,reposts,quotes,followers_count",
            "period": "day",
            "since": int((now - timedelta(days=14)).timestamp()),
            "until": int(now.timestamp()),
            "access_token": token
        }, timeout=10).json()

        this_week, last_week = {}, {}
        for item in ins.get("data", []):
            name = item["name"]
            if "values" in item:
                vals = item["values"]
                half = len(vals) // 2
                last_week[name] = sum(v.get("value",0) for v in vals[:half])
                this_week[name]  = sum(v.get("value",0) for v in vals[half:])
            elif "total_value" in item:
                this_week[name] = item["total_value"].get("value", 0)

        # 최근 게시물 + 개별 인사이트
        tl = requests.get(f"{base}/me/threads", params={
            "fields":"id,text,timestamp","limit":10,"access_token":token
        }, timeout=10).json()

        posts = []
        for post in tl.get("data", [])[:8]:
            pid = post.get("id")
            pi = requests.get(f"{base}/{pid}/insights", params={
                "metric":"views,likes,replies,reposts,quotes","access_token":token
            }, timeout=10).json()
            pm = {}
            for m in pi.get("data", []):
                if "total_value" in m:
                    pm[m["name"]] = m["total_value"].get("value", 0)
                elif "values" in m:
                    pm[m["name"]] = sum(v.get("value",0) for v in m["values"])
            posts.append({
                "text": (post.get("text") or "")[:60],
                "timestamp": post.get("timestamp",""),
                "views":   pm.get("views",0),
                "likes":   pm.get("likes",0),
                "replies": pm.get("replies",0),
            })
        posts.sort(key=lambda x: x["views"], reverse=True)

        return {
            "username": me.get("username",""),
            "name":     me.get("name",""),
            "followers":   this_week.get("followers_count",0),
            "views":       this_week.get("views",0),
            "views_prev":  last_week.get("views",0),
            "likes":       this_week.get("likes",0),
            "likes_prev":  last_week.get("likes",0),
            "replies":     this_week.get("replies",0),
            "reposts":     this_week.get("reposts",0),
            "top_posts":   posts[:3],
        }
    except Exception:
        return None



def get_naver_trends():
    """네이버 DataLab 검색어 트렌드"""
    try:
        if not config.NAVER_CLIENT_ID or not config.NAVER_CLIENT_SECRET:
            return None
        import os as _os
        kw_env = _os.getenv("NAVER_TREND_KEYWORDS", "기타,통기타,라바뮤직")
        keywords = [k.strip() for k in kw_env.split(",") if k.strip()][:5]
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        payload = {
            "startDate": start_date, "endDate": end_date, "timeUnit": "month",
            "keywordGroups": [{"groupName": kw, "keywords": [kw]} for kw in keywords],
        }
        headers = {
            "X-Naver-Client-Id": config.NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": config.NAVER_CLIENT_SECRET,
            "Content-Type": "application/json",
        }
        r = requests.post("https://openapi.naver.com/v1/datalab/search", headers=headers, json=payload, timeout=10)
        if r.status_code != 200:
            return None
        results = []
        for item in r.json().get("results", []):
            ratios = [d["ratio"] for d in item.get("data", []) if "ratio" in d]
            if len(ratios) >= 2:
                diff = ratios[-1] - ratios[-2]
                results.append({
                    "keyword": item["title"],
                    "latest": round(ratios[-1], 1),
                    "trend": "▲" if diff > 1 else ("▼" if diff < -1 else "→"),
                    "diff": round(diff, 1),
                })
        return results or None
    except Exception:
        return None

def get_gsc_data():
    """Google Search Console 오가닉 검색 데이터"""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    creds = Credentials(
        token=None,
        refresh_token=config.GOOGLE_REFRESH_TOKEN,
        client_id=config.GOOGLE_CLIENT_ID,
        client_secret=config.GOOGLE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=[
            "https://www.googleapis.com/auth/analytics.readonly",
            "https://www.googleapis.com/auth/webmasters.readonly"
        ]
    )
    creds.refresh(Request())

    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

    results = []

    for site_url in config.GSC_SITE_URLS:
        if not site_url:
            continue

        # 전체 성과
        payload = {
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": ["query"],
            "rowLimit": 10,
            "orderBy": [{"fieldName": "clicks", "sortOrder": "DESCENDING"}]
        }

        r = requests.post(
            f"https://www.googleapis.com/webmasters/v3/sites/{requests.utils.quote(site_url, safe='')}/searchAnalytics/query",
            headers={
                "Authorization": f"Bearer {creds.token}",
                "Content-Type": "application/json"
            },
            json=payload
        )

        data = r.json()

        if 'rows' not in data:
            continue

        total_clicks = sum(row['clicks'] for row in data['rows'])
        total_impressions = sum(row['impressions'] for row in data['rows'])
        avg_position = sum(row['position'] for row in data['rows']) / len(data['rows'])
        top_keywords = [
            {
                'keyword': row['keys'][0],
                'clicks': row['clicks'],
                'impressions': row['impressions'],
                'position': round(row['position'], 1)
            }
            for row in data['rows'][:5]
        ]

        results.append({
            'site': site_url,
            'clicks': total_clicks,
            'impressions': total_impressions,
            'avg_position': round(avg_position, 1),
            'top_keywords': top_keywords
        })

    return results if results else None

def get_meta_data():
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    start_date_prev = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
    end_date_prev = (datetime.now() - timedelta(days=8)).strftime('%Y-%m-%d')

    def fetch(since, until):
        url = f"https://graph.facebook.com/v18.0/{config.META_AD_ACCOUNT_ID}/insights"
        params = {
            'access_token': config.META_ACCESS_TOKEN,
            'fields': 'spend,actions,clicks,impressions',
            'time_range': f'{{"since":"{since}","until":"{until}"}}',
            'level': 'account'
        }
        r = requests.get(url, params=params).json()
        if 'error' in r or not r.get('data'):
            return None
        item = r['data'][0]
        spend = float(item.get('spend', 0))
        clicks = int(item.get('clicks', 0))
        impressions = int(item.get('impressions', 0))
        conversions = sum(
            int(float(a['value'])) for a in item.get('actions', [])
            if a['action_type'] in ['purchase', 'lead', 'complete_registration']
        )
        cpa = spend / conversions if conversions > 0 else 0
        ctr = (clicks / impressions * 100) if impressions > 0 else 0
        roas = 0
        return {'spend': spend, 'conversions': conversions, 'cpa': cpa, 'ctr': ctr, 'roas': roas}

    current = fetch(start_date, end_date)
    previous = fetch(start_date_prev, end_date_prev)
    if current and previous:
        current['prev_cpa'] = previous['cpa']
        current['prev_conversions'] = previous['conversions']
    return current

def get_ga4_data():
    """GA4 데이터 가져오기"""
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Metric, Dimension
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    creds = Credentials(
        token=None,
        refresh_token=config.GOOGLE_REFRESH_TOKEN,
        client_id=config.GOOGLE_CLIENT_ID,
        client_secret=config.GOOGLE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/analytics.readonly"]
    )
    creds.refresh(Request())

    client = BetaAnalyticsDataClient(credentials=creds)

    request = RunReportRequest(
        property=f"properties/{config.GA4_PROPERTY_ID}",
        date_ranges=[
            DateRange(start_date="7daysAgo", end_date="yesterday"),
            DateRange(start_date="14daysAgo", end_date="8daysAgo"),
        ],
        metrics=[
            Metric(name="sessions"),
            Metric(name="conversions"),
            Metric(name="totalRevenue"),
        ],
    )

    response = client.run_report(request)

    current = response.rows[0].metric_values if response.rows else None
    previous = response.rows[1].metric_values if len(response.rows) > 1 else None

    if not current:
        return None

    sessions = int(float(current[0].value))
    conversions = int(float(current[1].value))
    revenue = float(current[2].value)
    prev_conversions = int(float(previous[1].value)) if previous else 0

    return {
        "name": "GA4",
        "sessions": sessions,
        "conversions": conversions,
        "revenue": revenue,
        "prev_conversions": prev_conversions,
    }

# ============================================================
# Hydra Phase A: 파라미터화된 detailed 버전 (cross-source 조인용)
# 기존 get_gsc_data / get_ga4_data 는 backward compat을 위해 유지
# ============================================================

def get_gsc_data_detailed(
    site_url: str = None,
    start_date: str = "7daysAgo",
    end_date: str = "yesterday",
    dimensions=None,
    row_limit: int = 1000,
    search_type: str = "web",
):
    """
    GSC 파라미터화 버전. dimensions에 'page' 포함 시 page_key 자동 부여.
    site_url 미지정 시 config.GSC_SITE_URLS의 첫 번째 사용.
    """
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    if dimensions is None:
        dimensions = ["query"]

    target_site = site_url or (config.GSC_SITE_URLS[0] if config.GSC_SITE_URLS else None)
    if not target_site:
        return None

    creds = Credentials(
        token=None,
        refresh_token=config.GOOGLE_REFRESH_TOKEN,
        client_id=config.GOOGLE_CLIENT_ID,
        client_secret=config.GOOGLE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
    )
    creds.refresh(Request())

    payload = {
        "startDate": resolve_date(start_date),
        "endDate": resolve_date(end_date),
        "dimensions": dimensions,
        "rowLimit": row_limit,
        "searchType": search_type,
    }
    r = requests.post(
        f"https://www.googleapis.com/webmasters/v3/sites/{requests.utils.quote(target_site, safe='')}/searchAnalytics/query",
        headers={"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"},
        json=payload,
        timeout=15,
    )
    data = r.json()
    if "rows" not in data:
        return []

    out = []
    page_idx = dimensions.index("page") if "page" in dimensions else None
    for row in data["rows"]:
        rec = {dim: row["keys"][i] for i, dim in enumerate(dimensions)}
        rec.update({
            "clicks": row["clicks"],
            "impressions": row["impressions"],
            "ctr": round(row["ctr"], 4),
            "position": round(row["position"], 2),
        })
        if page_idx is not None:
            rec["page_key"] = canonicalize_page(rec["page"])
        out.append(rec)
    return out


def get_ga4_data_detailed(
    start_date: str = "7daysAgo",
    end_date: str = "yesterday",
    dimensions=None,
    metrics=None,
    row_limit: int = 1000,
):
    """
    GA4 파라미터화 버전. landingPage/pagePath 차원 사용 시 page_key 자동 부여.
    """
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Metric, Dimension
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    if dimensions is None:
        dimensions = ["date"]
    if metrics is None:
        metrics = ["sessions", "conversions", "totalRevenue"]

    creds = Credentials(
        token=None,
        refresh_token=config.GOOGLE_REFRESH_TOKEN,
        client_id=config.GOOGLE_CLIENT_ID,
        client_secret=config.GOOGLE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/analytics.readonly"],
    )
    creds.refresh(Request())
    client = BetaAnalyticsDataClient(credentials=creds)

    req = RunReportRequest(
        property=f"properties/{config.GA4_PROPERTY_ID}",
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimensions=[Dimension(name=d) for d in dimensions],
        metrics=[Metric(name=m) for m in metrics],
        limit=row_limit,
    )
    resp = client.run_report(req)

    out = []
    dim_names = [h.name for h in resp.dimension_headers]
    met_names = [h.name for h in resp.metric_headers]
    for row in resp.rows:
        rec = {dim_names[i]: row.dimension_values[i].value for i in range(len(dim_names))}
        for i, m in enumerate(met_names):
            try:
                rec[m] = float(row.metric_values[i].value)
            except (ValueError, TypeError):
                rec[m] = row.metric_values[i].value
        # page_key 부여 (landingPage 또는 pagePath 차원 있을 때)
        page_field = next((d for d in ("landingPage", "pagePath", "landingPagePlusQueryString") if d in rec), None)
        if page_field:
            rec["page_key"] = canonicalize_page(rec[page_field])
        out.append(rec)
    return out


def get_naver_keyword_stats(keywords, show_detail: bool = True):
    """
    네이버 검색광고 키워드도구 (/keywordstool):
    절대 월간검색수, 평균 CTR, 경쟁지수, 평균노출광고수.
    Naver DataLab 트렌드(상대지표)의 절대값 보완.

    keywords: list[str] 또는 쉼표구분 str. 최대 5개.
    """
    import hmac, hashlib, base64, time as _time

    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split(",") if k.strip()]
    keywords = keywords[:5]
    if not keywords:
        return None
    if not (config.NAVER_API_KEY and config.NAVER_SECRET_KEY and config.NAVER_CUSTOMER_ID):
        return None

    BASE = "https://api.naver.com"
    PATH = "/keywordstool"
    ts = str(int(_time.time() * 1000))
    msg = f"{ts}.GET.{PATH}".encode("utf-8")
    sig = base64.b64encode(
        hmac.new(config.NAVER_SECRET_KEY.encode("utf-8"), msg, hashlib.sha256).digest()
    ).decode("utf-8")

    headers = {
        "X-Timestamp": ts,
        "X-API-KEY": config.NAVER_API_KEY,
        "X-Customer": str(config.NAVER_CUSTOMER_ID),
        "X-Signature": sig,
    }
    params = {
        "hintKeywords": ",".join(keywords),
        "showDetail": "1" if show_detail else "0",
    }
    try:
        r = requests.get(BASE + PATH, headers=headers, params=params, timeout=15)
        if r.status_code != 200:
            return None
        data = r.json()
    except Exception:
        return None

    def _to_int(v):
        if v is None:
            return 0
        if isinstance(v, str) and "<" in v:
            return 5  # API가 노출량 적을 때 '< 10' 반환
        try:
            return int(v)
        except (ValueError, TypeError):
            return 0

    def _to_float(v):
        try:
            return round(float(v), 2)
        except (ValueError, TypeError):
            return 0.0

    out = []
    for k in data.get("keywordList", []):
        out.append({
            "keyword": k.get("relKeyword"),
            "monthly_pc_search": _to_int(k.get("monthlyPcQcCnt")),
            "monthly_mobile_search": _to_int(k.get("monthlyMobileQcCnt")),
            "monthly_total_search": _to_int(k.get("monthlyPcQcCnt")) + _to_int(k.get("monthlyMobileQcCnt")),
            "monthly_pc_clicks": _to_int(k.get("monthlyAvePcClkCnt")),
            "monthly_mobile_clicks": _to_int(k.get("monthlyAveMobileClkCnt")),
            "pc_ctr": _to_float(k.get("monthlyAvePcCtr")),
            "mobile_ctr": _to_float(k.get("monthlyAveMobileCtr")),
            "comp_index": k.get("compIdx"),  # 낮음/중간/높음
            "avg_ad_depth": _to_int(k.get("plAvgDepth")),
        })
    # 총 검색량 내림차순
    out.sort(key=lambda x: x["monthly_total_search"], reverse=True)
    return out or None


def compute_kghs(weeks: int = 4):
    """
    Korean Growth Health Score v2.

    v2 변경점 (vs v1):
      • SocialHealth(Threads) 컴포넌트 추가 → 5개로 확장
      • 데이터 부재 컴포넌트의 1.0 fallback 제거. confidence(0~1)을 가중치에 곱해
        실데이터 있는 컴포넌트만 총점에 반영. coverage(0~1) 별도 노출.
      • 컴포넌트별 trend 문자열 (W-1 또는 weeks-주 MA 대비 변화율)
      • alerts: 임계값 위반 시 조기경보 메시지 리스트

    score 의미: 1.0 = 평년, 1.3+ = 양호, 0.9↓ = 주의, 0.7↓ = 위험
    """
    components = {}  # name -> {score, confidence, trend, note}

    def _comp(name, score=1.0, confidence=0.0, trend=None, note=None):
        components[name] = {
            "score": round(float(score), 2),
            "confidence": round(float(confidence), 2),
            "trend": trend,
            "note": note,
        }

    def _arrow(pct, pos_thresh=1.0):
        return "↑" if pct > pos_thresh else "↓" if pct < -pos_thresh else "→"

    # ── NaverHealth: 키워드 트렌드 평균 변화율 ──
    try:
        trends = get_naver_trends()
        if trends:
            avg_diff = sum(t["diff"] for t in trends) / len(trends)
            score = max(0.5, min(1.0 + avg_diff / 100, 2.0))
            _comp("NaverHealth", score=score, confidence=1.0,
                  trend=f"{_arrow(avg_diff)} {avg_diff:+.1f}p",
                  note=f"키워드 {len(trends)}개 평균 트렌드")
        else:
            _comp("NaverHealth", note="네이버 DataLab 미연동")
    except Exception as e:
        _comp("NaverHealth", note=f"오류: {type(e).__name__}")

    # ── GoogleHealth: GSC CTR (벤치마크 3%) + weeks-주 MA 대비 트렌드 ──
    try:
        gsc_now = get_gsc_data()
        if gsc_now:
            total_clicks = sum(s["clicks"] for s in gsc_now)
            total_imp = sum(s["impressions"] for s in gsc_now)
            ctr = (total_clicks / total_imp) if total_imp else 0
            score = min(ctr / 0.03, 1.5)

            # 4주(weeks) baseline CTR 시도 — 실패해도 점수는 유효
            trend_str = None
            try:
                base_rows = get_gsc_data_detailed(
                    start_date=f"{weeks*7}daysAgo", end_date="8daysAgo")
                if base_rows:
                    bc = sum(r["clicks"] for r in base_rows)
                    bi = sum(r["impressions"] for r in base_rows)
                    base_ctr = (bc / bi) if bi else 0
                    if base_ctr > 0:
                        pct = (ctr / base_ctr - 1) * 100
                        trend_str = f"{_arrow(pct)} CTR {pct:+.1f}% (vs {weeks}주 MA)"
            except Exception:
                pass

            _comp("GoogleHealth", score=score, confidence=1.0,
                  trend=trend_str, note=f"CTR {ctr*100:.2f}%")
        else:
            _comp("GoogleHealth", note="GSC 미연동")
    except Exception as e:
        _comp("GoogleHealth", note=f"오류: {type(e).__name__}")

    # ── ConversionHealth: GA4 전환 W-1 대비 ──
    try:
        ga4 = get_ga4_data()
        if ga4 and ga4.get("prev_conversions", 0) > 0:
            ratio = ga4["conversions"] / ga4["prev_conversions"]
            score = min(ratio, 2.0)
            pct = (ratio - 1) * 100
            _comp("ConversionHealth", score=score, confidence=1.0,
                  trend=f"{_arrow(pct)} 전환 {pct:+.1f}%",
                  note=f"전환 {ga4['conversions']}건 (전주 {ga4['prev_conversions']}건)")
        elif ga4:
            _comp("ConversionHealth", confidence=0.3, note="전주 데이터 없음")
        else:
            _comp("ConversionHealth", note="GA4 미연동")
    except Exception as e:
        _comp("ConversionHealth", note=f"오류: {type(e).__name__}")

    # ── PaidEfficiency: Meta CPA W-1 대비 (낮을수록 좋음) ──
    try:
        meta = get_meta_data()
        if meta and meta.get("prev_cpa", 0) > 0:
            ratio = meta["prev_cpa"] / max(meta["cpa"], 1)
            score = min(ratio, 2.0)
            cpa_pct = (meta["cpa"] / meta["prev_cpa"] - 1) * 100
            # CPA는 낮을수록 좋음 → 화살표 방향 반전
            arrow = "↑" if cpa_pct < -1 else "↓" if cpa_pct > 1 else "→"
            _comp("PaidEfficiency", score=score, confidence=1.0,
                  trend=f"{arrow} CPA {cpa_pct:+.1f}%",
                  note=f"CPA {meta['cpa']:,.0f}원")
        elif meta:
            _comp("PaidEfficiency", confidence=0.3, note="전주 CPA 데이터 없음")
        else:
            _comp("PaidEfficiency", note="Meta 광고 미연동")
    except Exception as e:
        _comp("PaidEfficiency", note=f"오류: {type(e).__name__}")

    # ── SocialHealth: Threads 조회수 W-1 대비 (NEW) ──
    try:
        th = get_threads_data()
        if th and th.get("views_prev", 0) > 0:
            ratio = th["views"] / th["views_prev"]
            score = max(0.5, min(ratio, 2.0))
            pct = (ratio - 1) * 100
            _comp("SocialHealth", score=score, confidence=1.0,
                  trend=f"{_arrow(pct)} 조회 {pct:+.1f}%",
                  note=f"이번주 조회 {th['views']:,}회")
        elif th:
            _comp("SocialHealth", confidence=0.3, note="저번주 조회 데이터 없음")
        else:
            _comp("SocialHealth", note="Threads 미연동")
    except Exception as e:
        _comp("SocialHealth", note=f"오류: {type(e).__name__}")

    # ── 가중치 (confidence 적용한 정규화 합산) ──
    base_weights = {
        "NaverHealth":      0.20,
        "GoogleHealth":     0.20,
        "ConversionHealth": 0.30,
        "PaidEfficiency":   0.20,
        "SocialHealth":     0.10,
    }

    weighted_sum = 0.0
    weight_total = 0.0
    for name, c in components.items():
        w_eff = base_weights.get(name, 0) * c["confidence"]
        weighted_sum += c["score"] * w_eff
        weight_total += w_eff

    if weight_total > 0:
        total = round(weighted_sum / weight_total, 2)
        coverage = round(weight_total, 2)  # 0~1 (base weight 합이 1.0)
    else:
        total = 1.0
        coverage = 0.0

    # ── alerts (조기경보) ──
    alerts = []
    for name, c in components.items():
        if c["confidence"] == 0:
            continue
        if c["score"] < 0.7:
            alerts.append(f"🔴 {name}: 위험 수준 (score {c['score']})")
        elif c["score"] < 0.9:
            alerts.append(f"🟡 {name}: 주의 (score {c['score']})")
        # 트렌드 문자열에서 % 추출해 -30% 이하면 급락 alert
        if c["trend"]:
            try:
                pct_token = next((t for t in c["trend"].split() if t.endswith("%")), None)
                if pct_token:
                    pct_val = float(pct_token.rstrip("%").replace("+", ""))
                    if pct_val <= -30:
                        alerts.append(f"⚠️ {name}: 급락 감지 ({c['trend']})")
            except (ValueError, IndexError):
                pass
    if coverage < 0.5:
        alerts.append(
            f"⚪ 데이터 커버리지 낮음 ({coverage*100:.0f}%) — 점수 신뢰도 제한적")

    return {
        "version": "v2",
        "kghs": total,            # 1.0 = 평년, 2.0 = 매우 좋음, 0.5 미만 = 위험
        "coverage": coverage,     # 0~1, 신뢰 가능한 컴포넌트의 가중치 합
        "components": components, # {name: {score, confidence, trend, note}}
        "weights": base_weights,
        "alerts": alerts,
        "interpretation": (
            "🟢 매우 양호" if total >= 1.3 else
            "🟡 평년 수준" if total >= 0.9 else
            "🔴 주의 필요"
        ),
    }


def cpa_status(cpa, prev_cpa):
    if prev_cpa == 0:
        return "🟡", 0
    change = (cpa - prev_cpa) / prev_cpa * 100
    if change <= -5:
        return "🟢", change
    elif change >= 10:
        return "🔴", change
    else:
        return "🟡", change

def budget_bar(amount, total, width=20):
    ratio = amount / total if total > 0 else 0
    filled = int(ratio * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"{bar} {ratio*100:.0f}%"

def get_ai_suggestions(data_summary):
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    prompt = f"""
퍼포먼스 마케팅 전문가로서 아래 데이터를 분석해서 한국어로 답해줘.

{data_summary}

아래 형식으로 정확히 작성해줘 (이모지 포함):
🔴 긴급: (지금 당장 해야 할 것 - 구체적 수치 포함)
🟡 권장: (이번 주 안에 할 것 - 예상 효과 포함)
🟢 선택: (여유 있을 때 할 것)
💰 예산 시뮬레이션: (예산 조정 시 예상 전환 변화)
"""
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

def render_dashboard(channels, is_demo=False):
    label = " [dim](데모)[/dim]" if is_demo else ""
    console.print(f"\n[bold blue]📊 Hydra Growth CLI[/bold blue]{label}")
    console.print(f"[dim]최근 7일 · {(datetime.now()-timedelta(days=7)).strftime('%Y.%m.%d')} ~ {datetime.now().strftime('%Y.%m.%d')}[/dim]\n")

    # 성과 테이블
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold white on blue")
    table.add_column("채널", style="cyan", width=12)
    table.add_column("비용", justify="right", style="yellow", width=14)
    table.add_column("전환", justify="right", style="green", width=8)
    table.add_column("CPA", justify="right", width=14)
    table.add_column("CTR", justify="right", style="dim", width=8)
    table.add_column("vs 지난주", justify="right", width=12)

    total_spend = sum(c['spend'] for c in channels)

    for c in channels:
        status_icon, change = cpa_status(c['cpa'], c.get('prev_cpa', 0))
        cpa_text = Text(f"₩{c['cpa']:,.0f}")
        if status_icon == "🟢":
            cpa_text.stylize("green")
        elif status_icon == "🔴":
            cpa_text.stylize("red")
        else:
            cpa_text.stylize("yellow")

        if change > 0:
            change_str = f"[red]▲{abs(change):.0f}%[/red]"
        elif change < 0:
            change_str = f"[green]▼{abs(change):.0f}%[/green]"
        else:
            change_str = "[dim]-[/dim]"

        table.add_row(
            f"{status_icon} {c['name']}",
            f"₩{c['spend']:,.0f}",
            f"{c['conversions']}건",
            cpa_text,
            f"{c['ctr']:.1f}%",
            change_str
        )

    console.print(table)

    # 예산 비중 바
    console.print("\n[bold]예산 비중[/bold]")
    for c in channels:
        bar = budget_bar(c['spend'], total_spend)
        console.print(f"  [cyan]{c['name']:<10}[/cyan] {bar}  ₩{c['spend']:,.0f}")

    # AI 제안
    console.print("\n[bold yellow]🤖 AI 액션 제안[/bold yellow]")
    with console.status("[bold green]데이터 가져오는 중...[/bold green]"):
        meta = get_meta_data()
        ga4 = get_ga4_data()
        naver = get_naver_data()
        gsc = get_gsc_data()

        summary = "\n".join([
            f"{c['name']}: 비용 ₩{c['spend']:,.0f} / 전환 {c['conversions']}건 / CPA ₩{c['cpa']:,.0f} / CTR {c['ctr']:.1f}% / 지난주 대비 CPA {'▲' if c.get('prev_cpa',0) and c['cpa']>c['prev_cpa'] else '▼'}"
            for c in channels
        ])
        suggestion = get_ai_suggestions(summary)

    panel = Panel(suggestion, border_style="yellow", padding=(1, 2))
    console.print(panel)
    console.print()

@app.command()
def status():
    """실제 데이터 기반 성과 현황"""
    with console.status("[bold green]데이터 가져오는 중...[/bold green]"):
        meta = get_meta_data()
        ga4 = get_ga4_data()
        naver = get_naver_data()
        gsc = get_gsc_data()


    channels = []

    if meta and meta.get('spend', 0) > 0:
        channels.append({"name": "메타", **meta})
    if naver and naver.get('spend', 0) > 0:
        channels.append({"name": "네이버 SA", **naver})

    # GA4는 별도 섹션으로 표시
    if ga4:
        console.print(f"\n[bold cyan]📈 GA4 웹사이트 현황 (최근 7일)[/bold cyan]")
        console.print(f"  세션수:  [yellow]{ga4['sessions']:,}[/yellow]")
        console.print(f"  전환수:  [green]{ga4['conversions']}건[/green]")
        console.print(f"  매출:    [magenta]₩{ga4['revenue']:,.0f}[/magenta]")
        prev = ga4['prev_conversions']
        curr = ga4['conversions']
        if prev > 0:
            change = (curr - prev) / prev * 100
            arrow = "▲" if change > 0 else "▼"
            color = "green" if change > 0 else "red"
            console.print(f"  지난주 대비: [{color}]{arrow}{abs(change):.0f}%[/{color}]")
        console.print()



    threads = get_threads_data()
    if threads:
        def _pct(curr, prev):
            if not prev: return " [dim](첫 주)[/dim]"
            c = (curr - prev) / prev * 100
            if abs(c) > 500: return " [dim](신규)[/dim]"
            col = "green" if c > 0 else "red"
            arr = "▲" if c > 0 else "▼"
            return f" [{col}]{arr}{abs(c):.0f}%[/{col}]"
        console.print(f"\n[bold cyan]🧵 Threads 인사이트 (최근 7일 vs 전주)[/bold cyan]")
        console.print(f"  계정:    [cyan]@{threads['username']}[/cyan]  팔로워 {threads['followers']:,}명")
        console.print(f"  조회수:  {threads['views']:,}{_pct(threads['views'], threads['views_prev'])}")
        console.print(f"  좋아요:  {threads['likes']:,}{_pct(threads['likes'], threads['likes_prev'])}")
        console.print(f"  댓글:    {threads['replies']:,}  리포스트: {threads['reposts']:,}")
        if threads.get("top_posts"):
            console.print(f"\n  [bold white]📌 TOP 게시물[/bold white]")
            for i, p in enumerate(threads["top_posts"], 1):
                preview = p["text"][:45] + ("…" if len(p["text"]) > 45 else "")
                console.print(f"  {i}위  [white]{preview}[/white]")
                console.print(f"       조회 {p['views']:,}  좋아요 {p['likes']:,}  댓글 {p['replies']:,}")
            # AI 콘텐츠 추천
            try:
                import anthropic as _ant, os as _os
                posts_summary = "\n".join([
                    f"- {p['text'][:80]} (조회:{p['views']}, 좋아요:{p['likes']}, 댓글:{p['replies']})"
                    for p in threads["top_posts"]
                ])
                client = _ant.Anthropic(api_key=_os.getenv("ANTHROPIC_API_KEY"))
                msg = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=300,
                    messages=[{"role":"user","content":f"""Threads 계정 @{threads['username']} 최근 TOP 게시물:
{posts_summary}

한국어로 2-3줄 이내로 답해줘:
1. 어떤 콘텐츠 포맷/주제가 잘 되는지
2. 다음에 올릴 게시물 방향 1가지 구체적 제안"""}]
                )
                console.print(f"\n  [bold yellow]💡 AI 콘텐츠 추천[/bold yellow]")
                for line in msg.content[0].text.strip().split("\n"):
                    if line.strip():
                        console.print(f"  {line}")
            except Exception:
                pass

    trends = get_naver_trends()
    if trends:
        console.print(f"\n[bold magenta]🔍 네이버 키워드 트렌드 (최근 3개월)[/bold magenta]")
        for t in trends:
            color = "green" if t["trend"] == "▲" else ("red" if t["trend"] == "▼" else "yellow")
            sign = "+" if t["diff"] > 0 else ""
            console.print(f"  [{color}]{t['trend']}[/{color}] {t['keyword']:12}  검색량: [bold]{t['latest']}[/bold]  전월대비: [{color}]{sign}{t['diff']}[/{color}]")

    if not channels and not ga4 and not gsc:
        console.print("[red]데이터를 가져올 수 없어요.[/red]")
        raise typer.Exit()

    if channels:
        render_dashboard(channels)
    elif not channels:
        console.print("[dim]💡 광고 채널 데이터가 없어요. 광고 집행 후 다시 확인해보세요.[/dim]")

    if meta:
        channels.append({"name": "메타", **meta})

    if ga4:
        console.print(f"\n[bold cyan]📈 GA4 웹사이트 현황 (최근 7일)[/bold cyan]")
        console.print(f"  세션수:  [yellow]{ga4['sessions']:,}[/yellow]")
        console.print(f"  전환수:  [green]{ga4['conversions']}건[/green]")
        console.print(f"  매출:    [magenta]₩{ga4['revenue']:,.0f}[/magenta]")
        prev = ga4['prev_conversions']
        curr = ga4['conversions']
        if prev > 0:
            change = (curr - prev) / prev * 100
            arrow = "▲" if change > 0 else "▼"
            color = "green" if change > 0 else "red"
            console.print(f"  지난주 대비: [{color}]{arrow}{abs(change):.0f}%[/{color}]")
        console.print()

    if gsc:
        console.print(f"\n[bold green]🔍 오가닉 SEO 현황 (최근 7일)[/bold green]")
        for site in gsc:
            console.print(f"\n  [cyan]{site['site']}[/cyan]")
            console.print(f"  클릭수:    [yellow]{site['clicks']:,}[/yellow]")
            console.print(f"  노출수:    [dim]{site['impressions']:,}[/dim]")
            console.print(f"  평균순위:  [magenta]{site['avg_position']}위[/magenta]")

            if site['top_keywords']:
                console.print(f"\n  [bold]상위 키워드 TOP 5[/bold]")
                kw_table = Table(box=box.SIMPLE, show_header=True, header_style="dim")
                kw_table.add_column("키워드", style="cyan", width=25)
                kw_table.add_column("클릭", justify="right", style="yellow", width=8)
                kw_table.add_column("노출", justify="right", style="dim", width=10)
                kw_table.add_column("순위", justify="right", style="magenta", width=8)

                for kw in site['top_keywords']:
                    kw_table.add_row(
                        kw['keyword'],
                        str(kw['clicks']),
                        f"{kw['impressions']:,}",
                        f"{kw['position']}위"
                    )
                console.print(kw_table)
        console.print()


    if not channels:
        raise typer.Exit()

    render_dashboard(channels)

@app.command()
def demo():
    """데모 데이터로 미리보기"""
    channels = [
        {"name": "구글", "spend": 2100000, "conversions": 67, "cpa": 31343, "ctr": 4.2, "prev_cpa": 25000},
        {"name": "네이버", "spend": 1250000, "conversions": 38, "cpa": 32894, "ctr": 3.1, "prev_cpa": 34500},
        {"name": "메타",   "spend": 1840000, "conversions": 41, "cpa": 44878, "ctr": 1.8, "prev_cpa": 39000},
    ]
    render_dashboard(channels, is_demo=True)

if __name__ == "__main__":
    app()