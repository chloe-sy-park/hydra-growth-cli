"""
Hydra-growth 공통 유틸.
주 목적: cross-source 조인을 위한 page URL 정규화 키 생성.
"""
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from datetime import datetime, timedelta


# 마케팅 트래킹 파라미터 (정규화 시 제거)
_DROP_PARAMS = {
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term',
    'gclid', 'fbclid', 'mc_cid', 'mc_eid', '_ga', 'ref', 'igshid',
    'mibextid', 'srsltid',
}


def canonicalize_page(url: str) -> str:
    """
    GSC 'page', GA4 'landingPage/pagePath', Meta 광고 destination URL을
    동일한 키로 변환해서 페이지 단위 조인을 가능하게 함.

    규칙:
      1) 스키마 https로 통일
      2) host 소문자 + 'www.' 제거
      3) path trailing slash 제거 (단, 루트 '/' 유지)
      4) 마케팅 추적 파라미터 제거, 나머지는 정렬
      5) fragment 제거
    """
    if not url:
        return ""
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url.lstrip('/')

    p = urlparse(url)
    netloc = p.netloc.lower()
    if netloc.startswith('www.'):
        netloc = netloc[4:]

    path = p.path.rstrip('/') or '/'

    qs = {k: v for k, v in parse_qs(p.query).items() if k.lower() not in _DROP_PARAMS}
    query = urlencode(sorted(qs.items()), doseq=True) if qs else ''

    return urlunparse(('https', netloc, path, '', query, ''))


def resolve_date(s: str) -> str:
    """
    'today', '7daysAgo', '30daysAgo', 또는 'YYYY-MM-DD' 입력을
    실제 날짜 문자열로 변환. GSC API는 yesterday까지만 허용.
    """
    if not s or s == "today":
        return datetime.now().strftime("%Y-%m-%d")
    if s == "yesterday":
        return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    if s.endswith("daysAgo"):
        try:
            n = int(s.replace("daysAgo", ""))
            return (datetime.now() - timedelta(days=n)).strftime("%Y-%m-%d")
        except ValueError:
            pass
    # 이미 YYYY-MM-DD 형식이라고 가정
    return s
