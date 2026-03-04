#!/usr/bin/env python3
"""
📈 주식 시황 브리핑 자동 생성기
- 미국/국내 주식 뉴스 큐레이션
- Claude AI로 시황 분석 및 요약
- 매일 오전 7시 HTML 자동 생성
"""

import os
import json
import feedparser
import anthropic
import yfinance as yf
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── 뉴욕 증시 종목 워치리스트 ─────────────────────────────────────────
WATCHLIST = {
    "indices": {
        "^GSPC":  "S&P500",
        "^IXIC":  "나스닥",
        "^DJI":   "다우",
        "^RUT":   "러셀2000",
        "^SOX":   "필라델피아 반도체",
    },
    "sectors": {
        "XLK":  "기술주",
        "XLF":  "금융주",
        "XLE":  "에너지",
        "XLI":  "산업재",
        "XLV":  "헬스케어",
        "XLY":  "임의소비재",
        "XLC":  "커뮤니케이션",
        "XLB":  "소재",
        "XLU":  "유틸리티",
    },
    "stocks": {
        # 대형 기술주
        "AAPL":  ("애플",      "대형기술주"),
        "MSFT":  ("마이크로소프트", "대형기술주"),
        "GOOGL": ("알파벳",    "대형기술주"),
        "AMZN":  ("아마존",    "대형기술주"),
        "META":  ("메타",      "대형기술주"),
        "NVDA":  ("엔비디아",  "반도체"),
        "TSLA":  ("테슬라",    "자동차/EV"),
        # 반도체
        "AMD":   ("AMD",       "반도체"),
        "AVGO":  ("브로드컴",  "반도체"),
        "MU":    ("마이크론",  "반도체"),
        "LRCX":  ("램리서치",  "반도체"),
        "AMAT":  ("AMAT",      "반도체"),
        "TSM":   ("TSMC",      "반도체"),
        "INTC":  ("인텔",      "반도체"),
        "QCOM":  ("퀄컴",      "반도체"),
        "ASML":  ("ASML",      "반도체"),
        # 소프트웨어
        "CRM":   ("세일즈포스","소프트웨어"),
        "NOW":   ("서비스나우","소프트웨어"),
        "ORCL":  ("오라클",    "소프트웨어"),
        "ADBE":  ("어도비",    "소프트웨어"),
        "PLTR":  ("팔란티어",  "소프트웨어"),
        "INTU":  ("인튜이트",  "소프트웨어"),
        # 금융
        "JPM":   ("JP모건",    "금융"),
        "BAC":   ("BOA",       "금융"),
        "GS":    ("골드만삭스","금융"),
        "BLK":   ("블랙록",    "금융"),
        "BX":    ("블랙스톤",  "금융"),
        "KKR":   ("KKR",       "금융"),
        "APO":   ("아폴로",    "금융"),
        # 자동차/EV
        "GM":    ("GM",        "자동차/EV"),
        "F":     ("포드",      "자동차/EV"),
        "RIVN":  ("리비안",    "자동차/EV"),
        # 에너지
        "XOM":   ("엑슨모빌",  "에너지"),
        "CVX":   ("셰브론",    "에너지"),
        # 중국 기업
        "BABA":  ("알리바바",  "중국기업"),
        "BIDU":  ("바이두",    "중국기업"),
        "PDD":   ("핀둬둬",    "중국기업"),
        "JD":    ("징둥닷컴",  "중국기업"),
        "XPEV":  ("샤오펑",    "중국기업"),
        "NIO":   ("니오",      "중국기업"),
        "LI":    ("리오토",    "중국기업"),
        # 크립토 관련
        "MSTR":  ("스트래티지","크립토"),
        "COIN":  ("코인베이스","크립토"),
        "HOOD":  ("로빈후드",  "크립토"),
        # 테마 (양자/원자력/AI)
        "IONQ":  ("아이온큐",  "양자컴퓨터"),
        "RGTI":  ("리게티",    "양자컴퓨터"),
        "CEG":   ("컨스텔레이션","원자력"),
        "VST":   ("비스트라",  "원자력"),
        "OKLO":  ("오클로",    "원자력"),
        "JOBY":  ("조비항공",  "미래모빌리티"),
    },
}

# ── 뉴스 소스 RSS 피드 ──────────────────────────────────────────────
RSS_FEEDS = {
    "us_stocks": [
        {
            "name": "Yahoo Finance",
            "url": "https://finance.yahoo.com/news/rssindex",
        },
        {
            "name": "Yahoo Finance Markets",
            "url": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EGSPC,%5EIXIC,%5EDJI&region=US&lang=en-US",
        },
    ],
    "kr_stocks": [
        {
            "name": "연합뉴스 경제",
            "url": "https://www.yna.co.kr/rss/economy.xml",
        },
        {
            "name": "한국경제 증권",
            "url": "https://www.hankyung.com/feed/stock",
        },
        {
            "name": "매일경제",
            "url": "https://www.mk.co.kr/rss/40300001/",
        },
        {
            "name": "네이버 금융 뉴스",
            "url": "https://finance.naver.com/news/rss/news.naver?mode=LSS2D&section_id=101&section_id2=258",
        },
    ],
}

# ── 유틸리티 함수 ──────────────────────────────────────────────────

def get_kst_now():
    """현재 KST 시간 반환"""
    kst = timezone(timedelta(hours=9))
    return datetime.now(kst)

def clean_html_text(text: str) -> str:
    """HTML 태그 제거"""
    import re
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&[a-zA-Z]+;', ' ', text)
    return text.strip()

def parse_published_time(entry) -> datetime | None:
    """RSS 항목의 발행 시각을 UTC datetime으로 파싱"""
    import email.utils
    for attr in ('published_parsed', 'updated_parsed', 'created_parsed'):
        t = getattr(entry, attr, None)
        if t:
            try:
                import time as _time
                return datetime.fromtimestamp(_time.mktime(t), tz=timezone.utc)
            except Exception:
                pass
    # published 문자열 직접 파싱 시도
    raw = getattr(entry, 'published', '') or getattr(entry, 'updated', '')
    if raw:
        try:
            parsed = email.utils.parsedate_to_datetime(raw)
            return parsed.astimezone(timezone.utc)
        except Exception:
            pass
    return None

def fetch_news_from_feed(source: dict, max_articles: int = 10,
                         hours: int = 12) -> list:
    """RSS 피드에서 최근 N시간 이내 뉴스만 수집"""
    articles = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0)"}
        feed = feedparser.parse(source["url"], request_headers=headers)

        for entry in feed.entries[:max_articles]:
            title = clean_html_text(getattr(entry, 'title', ''))
            if not title:
                continue

            pub_time = parse_published_time(entry)

            # 발행 시각을 파싱할 수 없으면 일단 포함 (피드마다 형식 상이)
            if pub_time and pub_time < cutoff:
                continue  # 12시간 초과 기사 제외

            summary = clean_html_text(getattr(entry, 'summary', ''))
            link = getattr(entry, 'link', '')
            published_str = getattr(entry, 'published', '') or getattr(entry, 'updated', '')

            articles.append({
                "source": source["name"],
                "title": title,
                "summary": summary[:400] if summary else "",
                "link": link,
                "published": published_str,
                "pub_utc": pub_time.isoformat() if pub_time else "",
            })
    except Exception as e:
        print(f"⚠️  피드 오류 [{source['name']}]: {e}")

    return articles

# ── 뉴욕 증시 실시간 데이터 ──────────────────────────────────────────

def fmt_pct(val: float) -> str:
    """등락률 포맷: +1.23% / -1.23%"""
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.2f}%"

def fetch_us_market_data() -> dict:
    """yfinance로 지수·섹터·종목 등락률 수집"""
    print("📊 뉴욕 증시 데이터 수집 중...")

    result = {"indices": {}, "sectors": {}, "stocks": {}, "top_movers": []}

    # ① 지수
    for ticker, name in WATCHLIST["indices"].items():
        try:
            data = yf.Ticker(ticker).history(period="2d")
            if len(data) >= 2:
                prev, curr = data["Close"].iloc[-2], data["Close"].iloc[-1]
                pct = (curr - prev) / prev * 100
                result["indices"][ticker] = {
                    "name": name,
                    "close": round(curr, 2),
                    "pct": fmt_pct(pct),
                    "pct_float": round(pct, 2),
                }
        except Exception as e:
            print(f"  ⚠️ 지수 오류 {ticker}: {e}")

    # ② 섹터 ETF
    for ticker, name in WATCHLIST["sectors"].items():
        try:
            data = yf.Ticker(ticker).history(period="2d")
            if len(data) >= 2:
                prev, curr = data["Close"].iloc[-2], data["Close"].iloc[-1]
                pct = (curr - prev) / prev * 100
                result["sectors"][ticker] = {
                    "name": name,
                    "pct": fmt_pct(pct),
                    "pct_float": round(pct, 2),
                }
        except Exception as e:
            print(f"  ⚠️ 섹터 오류 {ticker}: {e}")

    # ③ 개별 종목
    all_tickers = list(WATCHLIST["stocks"].keys())
    try:
        # 한 번에 배치 다운로드 (효율적)
        batch = yf.download(all_tickers, period="2d", auto_adjust=True,
                            progress=False, threads=True)
        close = batch["Close"]

        for ticker in all_tickers:
            try:
                name_kr, sector = WATCHLIST["stocks"][ticker]
                series = close[ticker].dropna()
                if len(series) >= 2:
                    prev, curr = float(series.iloc[-2]), float(series.iloc[-1])
                    pct = (curr - prev) / prev * 100
                    result["stocks"][ticker] = {
                        "name": name_kr,
                        "sector": sector,
                        "close": round(curr, 2),
                        "pct": fmt_pct(pct),
                        "pct_float": round(pct, 2),
                    }
            except Exception:
                pass
    except Exception as e:
        print(f"  ⚠️ 종목 배치 오류: {e}")

    # ④ Top 5 상승 / Top 5 하락 (종목 기준)
    sorted_stocks = sorted(
        [(t, v) for t, v in result["stocks"].items()],
        key=lambda x: x[1]["pct_float"]
    )
    losers = sorted_stocks[:5]   # 하락 상위
    gainers = sorted_stocks[-5:][::-1]  # 상승 상위
    result["top_movers"] = {
        "gainers": [{"ticker": t, **v} for t, v in gainers],
        "losers":  [{"ticker": t, **v} for t, v in losers],
    }

    # 섹터별 그룹핑
    by_sector: dict[str, list] = {}
    for ticker, info in result["stocks"].items():
        sec = info["sector"]
        by_sector.setdefault(sec, []).append({
            "ticker": ticker,
            "name": info["name"],
            "pct": info["pct"],
            "pct_float": info["pct_float"],
        })
    # 섹터 내 종목 등락률순 정렬
    for sec in by_sector:
        by_sector[sec].sort(key=lambda x: x["pct_float"])
    result["by_sector"] = by_sector

    idx_count = len(result["indices"])
    stk_count = len(result["stocks"])
    print(f"  ✅ 지수 {idx_count}개 / 종목 {stk_count}개 수집 완료")
    return result


def fetch_all_news() -> dict:
    """모든 소스에서 뉴스 수집"""
    print("📡 뉴스 수집 시작...")

    us_articles = []
    kr_articles = []

    for source in RSS_FEEDS["us_stocks"]:
        articles = fetch_news_from_feed(source)
        us_articles.extend(articles)
        print(f"  ✅ {source['name']}: {len(articles)}개 기사")

    for source in RSS_FEEDS["kr_stocks"]:
        articles = fetch_news_from_feed(source)
        kr_articles.extend(articles)
        print(f"  ✅ {source['name']}: {len(articles)}개 기사")

    # 중복 제거 (제목 기준)
    seen_us = set()
    us_unique = []
    for a in us_articles:
        if a['title'] not in seen_us:
            seen_us.add(a['title'])
            us_unique.append(a)

    seen_kr = set()
    kr_unique = []
    for a in kr_articles:
        if a['title'] not in seen_kr:
            seen_kr.add(a['title'])
            kr_unique.append(a)

    print(f"\n📰 수집 완료: 미국 {len(us_unique)}개 / 국내 {len(kr_unique)}개\n")
    return {"us": us_unique[:20], "kr": kr_unique[:20]}

# ── Claude API로 시황 분석 ─────────────────────────────────────────

def generate_ny_detail(news: dict, market_data: dict) -> dict:
    """Claude AI로 뉴욕 증시 섹터별 상세 분석 생성"""
    print("🤖 뉴욕 증시 상세 분석 중...")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)

    kst_now = get_kst_now()
    weekdays_kr = ["월", "화", "수", "목", "금", "토", "일"]
    date_mm_dd = kst_now.strftime("%m/%d")

    # 지수 요약 텍스트 생성
    idx_lines = []
    for t, v in market_data.get("indices", {}).items():
        idx_lines.append(f"{v['name']} {v['pct']} ({v['close']})")
    indices_str = ", ".join(idx_lines) if idx_lines else "데이터 없음"

    # 섹터별 종목 데이터를 텍스트로 정리
    sector_data_str = ""
    for sector, stocks in market_data.get("by_sector", {}).items():
        stocks_fmt = ", ".join([f"{s['name']}({s['pct']})" for s in stocks])
        sector_data_str += f"  [{sector}] {stocks_fmt}\n"

    # 상승/하락 상위 종목
    movers = market_data.get("top_movers", {})
    gainers_str = ", ".join([f"{g['name']}({g['pct']})" for g in movers.get("gainers", [])])
    losers_str  = ", ".join([f"{l['name']}({l['pct']})" for l in movers.get("losers", [])])

    # 미국 관련 뉴스만 필터링
    us_news_text = json.dumps(news.get("us", [])[:15], ensure_ascii=False, indent=2)

    prompt = f"""당신은 미국 주식 시황 전문 애널리스트입니다.
아래 실제 시장 데이터와 뉴스를 바탕으로 {date_mm_dd} 뉴욕 증시 상세 분석을 작성하세요.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[실제 마감 데이터]
주요 지수: {indices_str}

섹터별 종목 등락률:
{sector_data_str}
상승 상위: {gainers_str}
하락 상위: {losers_str}

[관련 뉴스]
{us_news_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[작성 규칙]
1. 제공된 실제 수치(%)를 그대로 사용한다 — 임의로 수치를 만들지 않는다.
2. 뉴스에 없는 내용은 추가하지 않는다 (팩트 기반 원칙).
3. 섹터 분석은 뉴스에서 언급된 섹터 위주로 작성한다.
4. 구체적 매매 전략("지금 사세요" 등) 제시 금지.
5. 모든 내용 한국어 작성.

다른 텍스트 없이 아래 JSON 형식으로만 응답하세요:

{{
  "ny_detail": {{
    "date_headline": "{date_mm_dd} 미 증시, [핵심 원인]으로 [등락], [변수]에 낙폭/상승폭 [변화]",
    "overview": "전체 개요 3~5문장. 지수별 수치 필수 포함. 왜 올랐고/떨어졌는지 핵심 흐름 서술.",
    "change_factors": ["변화 요인 1", "변화 요인 2", "변화 요인 3"],
    "sectors": [
      {{
        "name": "섹터명 (예: 반도체)",
        "emoji": "💾",
        "headline": "섹터 한줄 요약 — 대표 주가 수치 포함",
        "key_stocks": "주요 종목 나열 (예: 엔비디아(-1.33%), AMD(-3.86%))",
        "analysis": "섹터 상세 분석 3~5문장. 뉴스 팩트 + 실제 수치 기반."
      }}
    ]
  }}
}}

섹터는 뉴스에서 실제 언급된 것 위주로 3~6개 작성하세요.
섹터 이모지 참고: 반도체💾, 대형기술주🖥️, 소프트웨어📱, 금융💰, 에너지⛽, 자동차🚗, 중국기업🇨🇳, 크립토₿, 테마🔬"""

    message = client.messages.create(
        model="claude-opus-4-5-20251101",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = message.content[0].text.strip()
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0].strip()

    result = json.loads(response_text)
    print("✅ 뉴욕 증시 상세 분석 완료")
    return result


def generate_market_brief(news: dict) -> dict:
    """Claude AI로 시황 브리핑 생성"""
    print("🤖 Claude AI 시황 분석 시작...")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다.")

    client = anthropic.Anthropic(api_key=api_key)

    kst_now = get_kst_now()
    date_str = kst_now.strftime("%Y년 %m월 %d일 (%A)")

    # 한국어 요일
    weekdays_kr = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    date_kr = kst_now.strftime(f"%Y년 %m월 %d일 ({weekdays_kr[kst_now.weekday()]})")

    prompt = f"""당신은 주식 시황 전문 에디터입니다. 아래 규칙을 철저히 준수하여 {date_kr} 기준 시황 브리핑 JSON을 작성하세요.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[뉴스 선정 규칙]
1. 제공된 뉴스 중 시장 영향력이 높은 순으로 미국 2개·국내 3개를 선정한다.
2. 동일 소스에서 2개 이상 선정하지 않는다 (출처 다양성).
3. 기업명 또는 구체적 수치(%, 금액, 물량 등)가 포함된 기사를 우선 선정한다.
4. 사실 오류나 잘못된 전제가 있는 기사는 선정에서 제외한다.

[요약 작성 규칙]
- 각 줄(line1~line3)은 반드시 한국어 기준 30~40자 내외로 작성한다.
- 제목(title)은 3줄 요약을 읽지 않아도 핵심을 즉시 파악할 수 있어야 한다.
- 제목 문장이 line1~3에 그대로 반복되어서는 안 된다 (중복 표현 금지).
- line1: 핵심 사실 — 기업명·수치·사건 위주로 압축
- line2: 배경/원인 — 왜 이런 일이 발생했는지
- line3: 영향/전망 — 시장 또는 관련 업종에 미치는 파급 효과
- 창의적 해석보다 본문 팩트 전달을 최우선으로 한다.
- 뉴스 원문에 없는 내용을 추가하거나 과장하지 않는다.

[인사이트 작성 규칙]
- 인사이트는 본문 팩트가 시사하는 투자 정보를 1~2줄로 도출한다.
- 과거 유사 사례, 관련주, 관련 테마를 언급하면 더 좋다.
- "매수", "매도", "지금 사세요" 등 구체적 매매 전략 제시는 금지한다.
  (유사투자자문업 해당 행위 방지)
- 기업명이 뉴스에 있다면 인사이트에서 반드시 언급한다.

[윤리 지침]
- 검증된 사실만 기술하며, 추측·편향·정치적 해석을 배제한다.
- 오류가 포함된 전제는 즉시 정정 후 올바른 내용으로 대체한다.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 미국 주식 뉴스 (최근 12시간)
{json.dumps(news['us'], ensure_ascii=False, indent=2)}

## 국내 주식 뉴스 (최근 12시간)
{json.dumps(news['kr'], ensure_ascii=False, indent=2)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
다른 텍스트 없이 아래 JSON 형식으로만 응답하세요:

{{
  "us_market": {{
    "headline": "미국 증시 핵심 한줄 — 지수명·수치 포함 (예: S&P500 0.8% 하락, 관세 우려 재부각)",
    "summary": "뉴스 팩트 기반 3~4문장. 주요 지수 변동·섹터·매크로 변수 포함. 수치 명시.",
    "key_points": ["팩트 기반 포인트 (수치 포함)", "팩트 기반 포인트", "팩트 기반 포인트"]
  }},
  "kr_market": {{
    "headline": "국내 증시 핵심 한줄 — 지수명·수치 포함 (예: 코스피 1.2% 반등, 외국인 순매수 전환)",
    "summary": "뉴스 팩트 기반 3~4문장. 코스피·코스닥 동향, 외국인·기관 동향, 주요 업종 포함.",
    "key_points": ["팩트 기반 포인트 (수치 포함)", "팩트 기반 포인트", "팩트 기반 포인트"]
  }},
  "news_curation": [
    {{
      "title": "핵심 파악 가능한 제목 (20~30자, 기업명/수치 우선)",
      "source": "출처명",
      "link": "뉴스 원문 URL (제공된 link 필드 그대로 사용)",
      "line1": "핵심 사실 압축 (30~40자, 기업명·수치 포함)",
      "line2": "배경·원인 설명 (30~40자)",
      "line3": "시장 영향·전망 (30~40자)",
      "insight": "💡 팩트 기반 투자정보 1~2줄 (관련주·테마·과거사례 포함, 매매전략 제시 금지)"
    }}
  ],
  "investment_point": {{
    "today_focus": "오늘 시장에서 주목해야 할 팩트 기반 포인트 2~3문장",
    "risk_factor": "구체적 리스크 요인 — 수치 또는 이슈명 포함 1~2문장",
    "opportunity": "팩트가 시사하는 기회 요인 1~2문장 (매매전략 제시 금지)"
  }},
  "market_mood": "bullish 또는 bearish 또는 neutral"
}}

뉴스 큐레이션: 미국 2개, 국내 3개 (총 5개). 모든 내용 한국어 작성."""

    message = client.messages.create(
        model="claude-opus-4-5-20251101",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = message.content[0].text.strip()

    # JSON 파싱
    # ```json ... ``` 블록 처리
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0].strip()

    brief = json.loads(response_text)
    print("✅ Claude AI 분석 완료")
    return brief

# ── HTML 생성 ──────────────────────────────────────────────────────

def generate_html(brief: dict, market_data: dict = None, ny_detail: dict = None) -> str:
    """Bloomberg Terminal 스타일 HTML 생성"""

    kst_now = get_kst_now()
    weekdays_kr = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    date_display = kst_now.strftime(f"%Y.%m.%d {weekdays_kr[kst_now.weekday()]}")
    time_display = kst_now.strftime("%H:%M KST")

    mood = brief.get("market_mood", "neutral")
    mood_text  = {"bullish": "BULL", "bearish": "BEAR", "neutral": "NEUTRAL"}.get(mood, "NEUTRAL")
    mood_color = {"bullish": "#00B800", "bearish": "#FF3333", "neutral": "#FFB800"}.get(mood, "#FFB800")

    us = brief.get("us_market", {})
    kr = brief.get("kr_market", {})
    inv = brief.get("investment_point", {})
    news_list = brief.get("news_curation", [])

    # ── 지수 바 ─────────────────────────────────────────────────────
    index_bar_html = ""
    if market_data and market_data.get("indices"):
        items = ""
        for t, v in market_data["indices"].items():
            cls = "pos" if v["pct_float"] >= 0 else "neg"
            items += f'<div class="idx-item"><span class="idx-name">{v["name"]}</span><span class="idx-val">{v["close"]:,.2f}</span><span class="idx-pct {cls}">{v["pct"]}</span></div>'
        index_bar_html = f'<div class="index-bar">{items}</div>'

    # ── 뉴욕 상세 분석 블록 ──────────────────────────────────────────
    ny_detail_html = ""
    if ny_detail:
        detail = ny_detail.get("ny_detail", {})
        factors_html = "".join(
            [f'<span class="ftag">* {f}</span>' for f in detail.get("change_factors", [])]
        )
        sector_html = ""
        for s in detail.get("sectors", []):
            sector_html += f"""<div class="s-panel">
  <div class="s-head"><span class="s-emoji">{s.get('emoji','')}</span><span class="s-name">{s.get('name','')}</span><span class="s-hl">{s.get('headline','')}</span></div>
  <div class="s-tickers">{s.get('key_stocks','')}</div>
  <div class="s-body">{s.get('analysis','')}</div>
</div>"""
        ny_detail_html = f"""<div class="panel">
  <div class="panel-hd"><span class="panel-tag">NYSE</span>뉴욕 증시 상세 분석</div>
  <div class="panel-bd">
    <div class="ny-hl">{detail.get('date_headline','')}</div>
    <div class="ny-ov">{detail.get('overview','')}</div>
    <div class="ftags">{factors_html}</div>
    <div class="sectors">{sector_html}</div>
  </div>
</div>"""

    # ── 시장 요약 포인트 ─────────────────────────────────────────────
    us_points_html = "".join([f'<li><span class="bullet">▸</span>{p}</li>' for p in us.get("key_points", [])])
    kr_points_html = "".join([f'<li><span class="bullet">▸</span>{p}</li>' for p in kr.get("key_points", [])])

    # ── 뉴스 카드 ────────────────────────────────────────────────────
    kr_sources = {"연합뉴스","한국경제","매일경제","네이버 금융 뉴스","네이버","조선비즈",
                  "머니투데이","이데일리","서울경제","파이낸셜뉴스","헤럴드경제","아시아경제","뉴스1"}
    news_cards_html = ""
    for news_item in news_list:
        src  = news_item.get('source', '')
        flag = "KR" if any(k in src for k in kr_sources) else "US"
        flag_cls = "flag-kr" if flag == "KR" else "flag-us"
        link = news_item.get('link', '')
        link_html = f'<a class="orig-link" href="{link}" target="_blank" rel="noopener">원문 ↗</a>' if link else ''
        news_cards_html += f"""<div class="news-panel">
  <div class="news-meta"><span class="flag {flag_cls}">{flag}</span><span class="news-src">{src}</span>{link_html}</div>
  <div class="news-title">{news_item.get('title','')}</div>
  <div class="news-lines">
    <div class="nl"><span class="nl-n">01</span>{news_item.get('line1','')}</div>
    <div class="nl"><span class="nl-n">02</span>{news_item.get('line2','')}</div>
    <div class="nl"><span class="nl-n">03</span>{news_item.get('line3','')}</div>
  </div>
  <div class="insight">{news_item.get('insight','')}</div>
</div>"""

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="robots" content="noindex, nofollow">
  <title>MARKET INTELLIGENCE · {date_display}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&display=swap');

    :root {{
      --blk:   #000000;
      --bg1:   #080808;
      --bg2:   #0f0f0f;
      --bg3:   #141414;
      --bdr:   #1e1e1e;
      --bdr2:  #2a2a2a;
      --org:   #FF6600;
      --org2:  #cc5200;
      --amb:   #FFB800;
      --pos:   #00B800;
      --neg:   #FF3333;
      --txt:   #E0E0E0;
      --txt2:  #888888;
      --txt3:  #555555;
      --mono:  'JetBrains Mono', 'Courier New', monospace;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      background: var(--blk);
      color: var(--txt);
      font-family: -apple-system, 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif;
      font-size: 13px;
      line-height: 1.55;
      padding-bottom: 60px;
    }}

    /* ── HEADER ── */
    .hdr {{
      background: var(--bg1);
      border-bottom: 2px solid var(--org);
      padding: 10px 14px 8px;
      position: sticky;
      top: 0;
      z-index: 200;
    }}
    .hdr-top {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 2px;
    }}
    .hdr-logo {{
      font-family: var(--mono);
      font-size: 15px;
      font-weight: 700;
      color: var(--org);
      letter-spacing: 2px;
      text-transform: uppercase;
    }}
    .hdr-right {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .hdr-mood {{
      font-family: var(--mono);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 1px;
      color: {mood_color};
      border: 1px solid {mood_color};
      padding: 2px 8px;
    }}
    .hdr-dt {{
      font-family: var(--mono);
      font-size: 10px;
      color: var(--txt3);
      letter-spacing: 0.5px;
    }}

    /* ── INDEX BAR ── */
    .index-bar {{
      display: flex;
      overflow-x: auto;
      background: var(--bg2);
      border-bottom: 1px solid var(--bdr);
      padding: 6px 14px;
      gap: 20px;
      scrollbar-width: none;
    }}
    .index-bar::-webkit-scrollbar {{ display: none; }}
    .idx-item {{
      display: flex;
      align-items: center;
      gap: 6px;
      white-space: nowrap;
      flex-shrink: 0;
    }}
    .idx-name {{
      font-family: var(--mono);
      font-size: 10px;
      color: var(--txt3);
      letter-spacing: 0.5px;
    }}
    .idx-val {{
      font-family: var(--mono);
      font-size: 11px;
      font-weight: 600;
      color: var(--amb);
    }}
    .idx-pct {{
      font-family: var(--mono);
      font-size: 11px;
      font-weight: 700;
    }}
    .idx-pct.pos {{ color: var(--pos); }}
    .idx-pct.neg {{ color: var(--neg); }}

    /* ── PANEL (공통 섹션) ── */
    .panel {{
      margin: 10px 10px 0;
      border: 1px solid var(--bdr);
      background: var(--bg1);
      overflow: hidden;
    }}
    .panel-hd {{
      background: var(--bg3);
      border-bottom: 1px solid var(--bdr);
      padding: 7px 12px;
      font-family: var(--mono);
      font-size: 11px;
      font-weight: 700;
      color: var(--org);
      letter-spacing: 1.5px;
      text-transform: uppercase;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .panel-tag {{
      background: var(--org);
      color: #000;
      font-size: 9px;
      font-weight: 700;
      padding: 1px 5px;
      letter-spacing: 1px;
    }}
    .panel-bd {{ padding: 12px; }}

    /* ── 미국/국내 시장 요약 ── */
    .mkt-hl {{
      font-size: 14px;
      font-weight: 700;
      color: var(--txt);
      line-height: 1.45;
      margin-bottom: 8px;
      padding-left: 8px;
      border-left: 2px solid var(--org);
    }}
    .mkt-sum {{
      font-size: 12px;
      color: var(--txt2);
      line-height: 1.7;
      margin-bottom: 10px;
    }}
    .kp-list {{
      list-style: none;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}
    .kp-list li {{
      display: flex;
      align-items: flex-start;
      gap: 6px;
      font-size: 12px;
      color: var(--txt);
    }}
    .bullet {{
      color: var(--org);
      flex-shrink: 0;
      font-size: 10px;
      margin-top: 2px;
    }}

    /* ── 뉴욕 상세: 헤드라인 / 개요 / 변화요인 ── */
    .ny-hl {{
      font-family: var(--mono);
      font-size: 12px;
      font-weight: 700;
      color: var(--amb);
      line-height: 1.5;
      margin-bottom: 10px;
      padding: 8px 10px;
      background: var(--bg2);
      border-left: 3px solid var(--org);
    }}
    .ny-ov {{
      font-size: 12.5px;
      color: var(--txt2);
      line-height: 1.75;
      margin-bottom: 10px;
    }}
    .ftags {{
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      margin-bottom: 12px;
    }}
    .ftag {{
      font-family: var(--mono);
      font-size: 10px;
      color: var(--amb);
      background: var(--bg3);
      border: 1px solid var(--bdr2);
      padding: 2px 7px;
      letter-spacing: 0.3px;
    }}

    /* ── 섹터 패널 ── */
    .sectors {{ display: flex; flex-direction: column; gap: 7px; }}
    .s-panel {{
      border: 1px solid var(--bdr);
      background: var(--bg2);
      overflow: hidden;
    }}
    .s-head {{
      display: flex;
      align-items: center;
      gap: 7px;
      padding: 6px 10px;
      background: var(--bg3);
      border-bottom: 1px solid var(--bdr);
    }}
    .s-emoji {{ font-size: 13px; }}
    .s-name {{
      font-family: var(--mono);
      font-size: 11px;
      font-weight: 700;
      color: var(--org);
      letter-spacing: 0.8px;
      text-transform: uppercase;
    }}
    .s-hl {{
      font-size: 11px;
      color: var(--txt2);
      margin-left: auto;
      text-align: right;
    }}
    .s-tickers {{
      padding: 5px 10px;
      font-family: var(--mono);
      font-size: 11px;
      color: var(--amb);
      border-bottom: 1px solid var(--bdr);
      background: rgba(255,184,0,0.04);
      letter-spacing: -0.2px;
    }}
    .s-body {{
      padding: 8px 10px;
      font-size: 12px;
      color: var(--txt2);
      line-height: 1.7;
    }}

    /* ── 뉴스 패널 ── */
    .news-panel {{
      border: 1px solid var(--bdr);
      background: var(--bg2);
      margin-bottom: 7px;
      overflow: hidden;
    }}
    .news-meta {{
      display: flex;
      align-items: center;
      gap: 7px;
      padding: 5px 10px;
      background: var(--bg3);
      border-bottom: 1px solid var(--bdr);
    }}
    .flag {{
      font-family: var(--mono);
      font-size: 9px;
      font-weight: 700;
      padding: 1px 5px;
      letter-spacing: 1px;
    }}
    .flag-us {{ background: #1a3a6b; color: #6699ff; border: 1px solid #1a3a6b; }}
    .flag-kr {{ background: #3a0a0a; color: #ff6666; border: 1px solid #3a0a0a; }}
    .news-src {{
      font-family: var(--mono);
      font-size: 10px;
      color: var(--txt3);
    }}
    .orig-link {{
      margin-left: auto;
      font-family: var(--mono);
      font-size: 10px;
      color: var(--org);
      text-decoration: none;
      border: 1px solid var(--org2);
      padding: 1px 6px;
    }}
    .orig-link:hover {{ background: var(--org2); color: #000; }}
    .news-title {{
      padding: 8px 10px 6px;
      font-size: 13px;
      font-weight: 700;
      color: var(--txt);
      line-height: 1.4;
      border-bottom: 1px dashed var(--bdr);
    }}
    .news-lines {{
      padding: 6px 10px;
      display: flex;
      flex-direction: column;
      gap: 4px;
      border-bottom: 1px solid var(--bdr);
    }}
    .nl {{
      display: flex;
      align-items: flex-start;
      gap: 8px;
      font-size: 12px;
      color: var(--txt2);
      line-height: 1.55;
    }}
    .nl-n {{
      font-family: var(--mono);
      font-size: 9px;
      font-weight: 700;
      color: var(--org);
      background: var(--bg3);
      border: 1px solid var(--bdr2);
      padding: 1px 4px;
      flex-shrink: 0;
      margin-top: 1px;
      letter-spacing: 0.5px;
    }}
    .insight {{
      padding: 7px 10px;
      font-size: 11.5px;
      color: var(--amb);
      background: rgba(255,184,0,0.05);
      border-top: 1px solid rgba(255,184,0,0.15);
      line-height: 1.55;
    }}

    /* ── 투자 포인트 ── */
    .inv-grid {{
      display: flex;
      flex-direction: column;
      gap: 7px;
    }}
    .inv-row {{
      border: 1px solid var(--bdr2);
      padding: 9px 11px;
      background: var(--bg2);
    }}
    .inv-row.focus  {{ border-left: 3px solid var(--pos); }}
    .inv-row.risk   {{ border-left: 3px solid var(--neg); }}
    .inv-row.oppty  {{ border-left: 3px solid var(--amb); }}
    .inv-lbl {{
      font-family: var(--mono);
      font-size: 9px;
      font-weight: 700;
      letter-spacing: 1.5px;
      margin-bottom: 5px;
      text-transform: uppercase;
    }}
    .inv-row.focus .inv-lbl  {{ color: var(--pos); }}
    .inv-row.risk  .inv-lbl  {{ color: var(--neg); }}
    .inv-row.oppty .inv-lbl  {{ color: var(--amb); }}
    .inv-txt {{
      font-size: 12.5px;
      color: var(--txt);
      line-height: 1.65;
    }}

    /* ── 푸터 ── */
    .footer {{
      margin: 20px 10px 0;
      padding: 10px;
      border-top: 1px solid var(--bdr);
      font-family: var(--mono);
      font-size: 9px;
      color: var(--txt3);
      letter-spacing: 0.5px;
      line-height: 1.8;
    }}
  </style>
</head>
<body>

  <!-- HEADER -->
  <div class="hdr">
    <div class="hdr-top">
      <div class="hdr-logo">▶ MARKET INTELLIGENCE</div>
      <div class="hdr-right">
        <div class="hdr-mood">{mood_text}</div>
        <div class="hdr-dt">{date_display} / {time_display}</div>
      </div>
    </div>
  </div>

  <!-- INDEX BAR -->
  {index_bar_html}

  <!-- US MARKET SUMMARY -->
  <div class="panel">
    <div class="panel-hd"><span class="panel-tag">US</span>미국 증시 요약</div>
    <div class="panel-bd">
      <div class="mkt-hl">{us.get('headline', '')}</div>
      <div class="mkt-sum">{us.get('summary', '')}</div>
      <ul class="kp-list">{us_points_html}</ul>
    </div>
  </div>

  <!-- NY DETAIL -->
  {ny_detail_html}

  <!-- KR MARKET SUMMARY -->
  <div class="panel">
    <div class="panel-hd"><span class="panel-tag">KR</span>국내 증시 요약</div>
    <div class="panel-bd">
      <div class="mkt-hl">{kr.get('headline', '')}</div>
      <div class="mkt-sum">{kr.get('summary', '')}</div>
      <ul class="kp-list">{kr_points_html}</ul>
    </div>
  </div>

  <!-- NEWS CURATION -->
  <div class="panel">
    <div class="panel-hd"><span class="panel-tag">NEWS</span>주요 뉴스 큐레이션</div>
    <div class="panel-bd" style="padding-bottom:4px;">
      {news_cards_html}
    </div>
  </div>

  <!-- INVESTMENT POINT -->
  <div class="panel">
    <div class="panel-hd"><span class="panel-tag">INTEL</span>오늘의 투자 포인트</div>
    <div class="panel-bd">
      <div class="inv-grid">
        <div class="inv-row focus">
          <div class="inv-lbl">▌ TODAY FOCUS</div>
          <div class="inv-txt">{inv.get('today_focus', '')}</div>
        </div>
        <div class="inv-row risk">
          <div class="inv-lbl">▌ RISK FACTOR</div>
          <div class="inv-txt">{inv.get('risk_factor', '')}</div>
        </div>
        <div class="inv-row oppty">
          <div class="inv-lbl">▌ OPPORTUNITY</div>
          <div class="inv-txt">{inv.get('opportunity', '')}</div>
        </div>
      </div>
    </div>
  </div>

  <div class="footer">
    MARKET INTELLIGENCE TERMINAL · AI-GENERATED BRIEFING · FOR REFERENCE ONLY<br>
    INVESTMENT DECISIONS ARE SOLELY THE RESPONSIBILITY OF THE INVESTOR<br>
    GENERATED {date_display} {time_display} · POWERED BY CLAUDE AI
  </div>

</body>
</html>"""

    return html

# ── 메인 실행 ──────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("📈 시황 브리핑 생성 시작")
    print(f"⏰ {get_kst_now().strftime('%Y-%m-%d %H:%M KST')}")
    print("=" * 50)

    try:
        # 1. 뉴스 수집
        news = fetch_all_news()

        # 2. 뉴욕 증시 실시간 데이터 수집
        market_data = fetch_us_market_data()

        # 3. Claude AI 분석 (뉴스 큐레이션 + 시황 요약)
        brief = generate_market_brief(news)

        # 4. 뉴욕 증시 상세 서술 분석
        ny_detail = generate_ny_detail(news, market_data)

        # 5. HTML 생성
        html_content = generate_html(brief, market_data, ny_detail)

        # 4. 파일 저장
        output_path = Path(__file__).parent / "index.html"
        output_path.write_text(html_content, encoding="utf-8")
        print(f"\n✅ HTML 생성 완료: {output_path}")

        # 5. 브리핑 JSON 저장 (디버깅용)
        json_path = Path(__file__).parent / "latest_brief.json"
        json_path.write_text(
            json.dumps(brief, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"✅ JSON 저장 완료: {json_path}")

        print("\n🎉 시황 브리핑 생성 완료!")

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        raise

if __name__ == "__main__":
    main()
