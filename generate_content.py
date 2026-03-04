#!/usr/bin/env python3


"""
📈 주식 시황 브리핑 자동 생성기 (텔레그램 버전)
- 미국/국내 주식 뉴스 큐레이션
- Claude AI로 시황 분석 및 요약
- 매일 오전 7시 텔레그램 자동 발송
"""

import os
import json
import requests
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
        "^SOX":   "필라델피아반도체",
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
        "AAPL":  ("애플",          "대형기술주"),
        "MSFT":  ("마이크로소프트", "대형기술주"),
        "GOOGL": ("알파벳",        "대형기술주"),
        "AMZN":  ("아마존",        "대형기술주"),
        "META":  ("메타",          "대형기술주"),
        "NVDA":  ("엔비디아",      "반도체"),
        "TSLA":  ("테슬라",        "자동차/EV"),
        # 반도체
        "AMD":   ("AMD",           "반도체"),
        "AVGO":  ("브로드컴",      "반도체"),
        "MU":    ("마이크론",      "반도체"),
        "LRCX":  ("램리서치",      "반도체"),
        "AMAT":  ("AMAT",          "반도체"),
        "TSM":   ("TSMC",          "반도체"),
        "INTC":  ("인텔",          "반도체"),
        "QCOM":  ("퀄컴",          "반도체"),
        "ASML":  ("ASML",          "반도체"),
        # 소프트웨어
        "CRM":   ("세일즈포스",    "소프트웨어"),
        "NOW":   ("서비스나우",    "소프트웨어"),
        "ORCL":  ("오라클",        "소프트웨어"),
        "ADBE":  ("어도비",        "소프트웨어"),
        "PLTR":  ("팔란티어",      "소프트웨어"),
        "INTU":  ("인튜이트",      "소프트웨어"),
        # 금융
        "JPM":   ("JP모건",        "금융"),
        "BAC":   ("BOA",           "금융"),
        "GS":    ("골드만삭스",    "금융"),
        "BLK":   ("블랙록",        "금융"),
        "BX":    ("블랙스톤",      "금융"),
        "KKR":   ("KKR",           "금융"),
        "APO":   ("아폴로",        "금융"),
        # 자동차/EV
        "GM":    ("GM",            "자동차/EV"),
        "F":     ("포드",          "자동차/EV"),
        "RIVN":  ("리비안",        "자동차/EV"),
        # 에너지
        "XOM":   ("엑슨모빌",      "에너지"),
        "CVX":   ("셰브론",        "에너지"),
        # 중국 기업
        "BABA":  ("알리바바",      "중국기업"),
        "BIDU":  ("바이두",        "중국기업"),
        "PDD":   ("핀둬둬",        "중국기업"),
        "JD":    ("징둥닷컴",      "중국기업"),
        "XPEV":  ("샤오펑",        "중국기업"),
        "NIO":   ("니오",          "중국기업"),
        "LI":    ("리오토",        "중국기업"),
        # 크립토 관련
        "MSTR":  ("스트래티지",    "크립토"),
        "COIN":  ("코인베이스",    "크립토"),
        "HOOD":  ("로빈후드",      "크립토"),
        # 테마 (양자/원자력/AI)
        "IONQ":  ("아이온큐",      "양자컴퓨터"),
        "RGTI":  ("리게티",        "양자컴퓨터"),
        "CEG":   ("컨스텔레이션",  "원자력"),
        "VST":   ("비스트라",      "원자력"),
        "OKLO":  ("오클로",        "원자력"),
        "JOBY":  ("조비항공",      "미래모빌리티"),
    },
}

# ── 뉴스 소스 RSS 피드 ──────────────────────────────────────────────
RSS_FEEDS = {
    "us_stocks": [
        {"name": "Yahoo Finance",
         "url": "https://finance.yahoo.com/news/rssindex"},
        {"name": "Yahoo Finance Markets",
         "url": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EGSPC,%5EIXIC,%5EDJI&region=US&lang=en-US"},
    ],
    "kr_stocks": [
        {"name": "연합뉴스 경제",
         "url": "https://www.yna.co.kr/rss/economy.xml"},
        {"name": "한국경제 증권",
         "url": "https://www.hankyung.com/feed/stock"},
        {"name": "매일경제",
         "url": "https://www.mk.co.kr/rss/40300001/"},
        {"name": "네이버 금융 뉴스",
         "url": "https://finance.naver.com/news/rss/news.naver?mode=LSS2D&section_id=101&section_id2=258"},
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

def esc(text) -> str:
    """Telegram HTML 모드용 특수문자 이스케이프"""
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

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
    raw = getattr(entry, 'published', '') or getattr(entry, 'updated', '')
    if raw:
        try:
            parsed = email.utils.parsedate_to_datetime(raw)
            return parsed.astimezone(timezone.utc)
        except Exception:
            pass
    return None

def fetch_news_from_feed(source: dict, max_articles: int = 10, hours: int = 12) -> list:
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
            if pub_time and pub_time < cutoff:
                continue

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
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.2f}%"

def fetch_us_market_data() -> dict:
    """yfinance로 지수·섹터·종목 등락률 수집"""
    print("📊 뉴욕 증시 데이터 수집 중...")

    result = {"indices": {}, "sectors": {}, "stocks": {}, "top_movers": []}

    for ticker, name in WATCHLIST["indices"].items():
        try:
            data = yf.Ticker(ticker).history(period="2d")
            if len(data) >= 2:
                prev, curr = data["Close"].iloc[-2], data["Close"].iloc[-1]
                pct = (curr - prev) / prev * 100
                result["indices"][ticker] = {
                    "name": name, "close": round(curr, 2),
                    "pct": fmt_pct(pct), "pct_float": round(pct, 2),
                }
        except Exception as e:
            print(f"  ⚠️ 지수 오류 {ticker}: {e}")

    for ticker, name in WATCHLIST["sectors"].items():
        try:
            data = yf.Ticker(ticker).history(period="2d")
            if len(data) >= 2:
                prev, curr = data["Close"].iloc[-2], data["Close"].iloc[-1]
                pct = (curr - prev) / prev * 100
                result["sectors"][ticker] = {
                    "name": name, "pct": fmt_pct(pct), "pct_float": round(pct, 2),
                }
        except Exception as e:
            print(f"  ⚠️ 섹터 오류 {ticker}: {e}")

    all_tickers = list(WATCHLIST["stocks"].keys())
    try:
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
                        "name": name_kr, "sector": sector,
                        "close": round(curr, 2),
                        "pct": fmt_pct(pct), "pct_float": round(pct, 2),
                    }
            except Exception:
                pass
    except Exception as e:
        print(f"  ⚠️ 종목 배치 오류: {e}")

    sorted_stocks = sorted(
        [(t, v) for t, v in result["stocks"].items()],
        key=lambda x: x[1]["pct_float"]
    )
    losers  = sorted_stocks[:5]
    gainers = sorted_stocks[-5:][::-1]
    result["top_movers"] = {
        "gainers": [{"ticker": t, **v} for t, v in gainers],
        "losers":  [{"ticker": t, **v} for t, v in losers],
    }

    by_sector: dict[str, list] = {}
    for ticker, info in result["stocks"].items():
        sec = info["sector"]
        by_sector.setdefault(sec, []).append({
            "ticker": ticker, "name": info["name"],
            "pct": info["pct"], "pct_float": info["pct_float"],
        })
    for sec in by_sector:
        by_sector[sec].sort(key=lambda x: x["pct_float"])
    result["by_sector"] = by_sector

    print(f"  ✅ 지수 {len(result['indices'])}개 / 종목 {len(result['stocks'])}개 수집 완료")
    return result


def fetch_all_news() -> dict:
    """모든 소스에서 뉴스 수집"""
    print("📡 뉴스 수집 시작...")
    us_articles, kr_articles = [], []

    for source in RSS_FEEDS["us_stocks"]:
        articles = fetch_news_from_feed(source)
        us_articles.extend(articles)
        print(f"  ✅ {source['name']}: {len(articles)}개 기사")

    for source in RSS_FEEDS["kr_stocks"]:
        articles = fetch_news_from_feed(source)
        kr_articles.extend(articles)
        print(f"  ✅ {source['name']}: {len(articles)}개 기사")

    seen_us = set()
    us_unique = [a for a in us_articles if a['title'] not in seen_us and not seen_us.add(a['title'])]
    seen_kr = set()
    kr_unique = [a for a in kr_articles if a['title'] not in seen_kr and not seen_kr.add(a['title'])]

    print(f"\n📰 수집 완료: 미국 {len(us_unique)}개 / 국내 {len(kr_unique)}개\n")
    return {"us": us_unique[:20], "kr": kr_unique[:20]}

# ── Claude API로 시황 분석 ─────────────────────────────────────────

def generate_ny_detail(news: dict, market_data: dict) -> dict:
    print("🤖 뉴욕 증시 상세 분석 중...")
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    kst_now = get_kst_now()
    date_mm_dd = kst_now.strftime("%m/%d")

    idx_lines = [f"{v['name']} {v['pct']} ({v['close']})"
                 for v in market_data.get("indices", {}).values()]
    indices_str = ", ".join(idx_lines) if idx_lines else "데이터 없음"

    sector_data_str = ""
    for sector, stocks in market_data.get("by_sector", {}).items():
        stocks_fmt = ", ".join([f"{s['name']}({s['pct']})" for s in stocks])
        sector_data_str += f"  [{sector}] {stocks_fmt}\n"

    movers = market_data.get("top_movers", {})
    gainers_str = ", ".join([f"{g['name']}({g['pct']})" for g in movers.get("gainers", [])])
    losers_str  = ", ".join([f"{l['name']}({l['pct']})" for l in movers.get("losers", [])])
    us_news_text = json.dumps(news.get("us", [])[:15], ensure_ascii=False, indent=2)

    prompt = f"""당신은 미국 주식 시황 전문 애널리스트입니다.
아래 실제 시장 데이터와 뉴스를 바탕으로 {date_mm_dd} 뉴욕 증시 상세 분석을 작성하세요.

[실제 마감 데이터]
주요 지수: {indices_str}
섹터별 종목 등락률:
{sector_data_str}
상승 상위: {gainers_str}
하락 상위: {losers_str}

[관련 뉴스]
{us_news_text}

[작성 규칙]
1. 제공된 실제 수치(%)를 그대로 사용한다.
2. 뉴스에 없는 내용은 추가하지 않는다.
3. 구체적 매매 전략 제시 금지.
4. 모든 내용 한국어 작성.

다른 텍스트 없이 아래 JSON 형식으로만 응답하세요:

{{
  "ny_detail": {{
    "date_headline": "{date_mm_dd} 미 증시, [핵심 원인]으로 [등락]",
    "overview": "전체 개요 3~5문장. 지수별 수치 필수 포함.",
    "change_factors": ["변화 요인 1", "변화 요인 2", "변화 요인 3"],
    "sectors": [
      {{
        "name": "섹터명",
        "emoji": "💾",
        "headline": "섹터 한줄 요약",
        "key_stocks": "주요 종목 나열 (예: 엔비디아(-1.33%), AMD(-3.86%))",
        "analysis": "섹터 상세 분석 2~3문장."
      }}
    ]
  }}
}}

섹터는 뉴스에서 실제 언급된 것 위주로 3~5개 작성하세요."""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
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
    print("🤖 Claude AI 시황 분석 시작...")
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    kst_now = get_kst_now()
    weekdays_kr = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    date_kr = kst_now.strftime(f"%Y년 %m월 %d일 ({weekdays_kr[kst_now.weekday()]})")

    prompt = f"""당신은 주식 시황 전문 에디터입니다. 아래 규칙을 철저히 준수하여 {date_kr} 기준 시황 브리핑 JSON을 작성하세요.

[뉴스 선정 규칙]
1. 시장 영향력이 높은 순으로 미국 2개·국내 3개를 선정한다.
2. 동일 소스에서 2개 이상 선정하지 않는다.
3. 기업명 또는 구체적 수치가 포함된 기사를 우선 선정한다.

[요약 작성 규칙]
- 각 줄(line1~line3)은 한국어 기준 30~40자 내외로 작성한다.
- line1: 핵심 사실 (기업명·수치·사건 위주)
- line2: 배경/원인
- line3: 영향/전망
- 뉴스 원문에 없는 내용 추가 금지.

[인사이트 규칙]
- 본문 팩트가 시사하는 투자 정보 1~2줄.
- "매수", "매도" 등 구체적 매매 전략 제시 금지.

## 미국 주식 뉴스 (최근 12시간)
{json.dumps(news['us'], ensure_ascii=False, indent=2)}

## 국내 주식 뉴스 (최근 12시간)
{json.dumps(news['kr'], ensure_ascii=False, indent=2)}

다른 텍스트 없이 아래 JSON 형식으로만 응답하세요:

{{
  "us_market": {{
    "headline": "미국 증시 핵심 한줄 (지수명·수치 포함)",
    "summary": "뉴스 팩트 기반 3~4문장.",
    "key_points": ["팩트 기반 포인트", "팩트 기반 포인트", "팩트 기반 포인트"]
  }},
  "kr_market": {{
    "headline": "국내 증시 핵심 한줄 (지수명·수치 포함)",
    "summary": "뉴스 팩트 기반 3~4문장.",
    "key_points": ["팩트 기반 포인트", "팩트 기반 포인트", "팩트 기반 포인트"]
  }},
  "news_curation": [
    {{
      "title": "핵심 파악 가능한 제목 (20~30자)",
      "source": "출처명",
      "link": "뉴스 원문 URL",
      "line1": "핵심 사실 압축 (30~40자)",
      "line2": "배경·원인 설명 (30~40자)",
      "line3": "시장 영향·전망 (30~40자)",
      "insight": "💡 팩트 기반 투자정보 1~2줄"
    }}
  ],
  "investment_point": {{
    "today_focus": "오늘 시장에서 주목해야 할 팩트 기반 포인트 2~3문장",
    "risk_factor": "구체적 리스크 요인 1~2문장",
    "opportunity": "팩트가 시사하는 기회 요인 1~2문장 (매매전략 제시 금지)"
  }},
  "market_mood": "bullish 또는 bearish 또는 neutral"
}}

뉴스 큐레이션: 미국 2개, 국내 3개 (총 5개). 모든 내용 한국어 작성."""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = message.content[0].text.strip()
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0].strip()

    brief = json.loads(response_text)
    print("✅ Claude AI 분석 완료")
    return brief

# ── 텔레그램 전송 ──────────────────────────────────────────────────

def send_telegram_message(token: str, chat_id: str, text: str) -> bool:
    """텔레그램 메시지 전송"""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(url, json=payload, timeout=30)
        if resp.status_code == 200:
            print("  ✅ 텔레그램 전송 완료")
            return True
        else:
            print(f"  ⚠️ 전송 실패: {resp.status_code} / {resp.text[:300]}")
            return False
    except Exception as e:
        print(f"  ⚠️ 전송 오류: {e}")
        return False


def format_and_send_telegram(brief: dict, market_data: dict, ny_detail: dict,
                              token: str, chat_id: str):
    """브리핑 내용을 텔레그램으로 포맷 후 전송"""

    kst_now = get_kst_now()
    weekdays_kr = ["월", "화", "수", "목", "금", "토", "일"]
    date_str = kst_now.strftime(f"%Y.%m.%d({weekdays_kr[kst_now.weekday()]})")
    time_str = kst_now.strftime("%H:%M KST")

    mood = brief.get("market_mood", "neutral")
    mood_emoji = {"bullish": "🟢 BULL", "bearish": "🔴 BEAR", "neutral": "🟡 NEUTRAL"}.get(mood, "🟡 NEUTRAL")

    us  = brief.get("us_market", {})
    kr  = brief.get("kr_market", {})
    inv = brief.get("investment_point", {})
    news_list = brief.get("news_curation", [])

    # ── 메시지 1: 헤더 + 지수 + 미국 증시 ──────────────────────────
    indices_text = ""
    for v in market_data.get("indices", {}).values():
        arrow = "▲" if v["pct_float"] >= 0 else "▼"
        indices_text += f"  <code>{esc(v['name']):<10} {v['close']:>10,.2f}   {arrow}{abs(v['pct_float']):.2f}%</code>\n"

    us_points = "\n".join([f"  ▸ {esc(p)}" for p in us.get("key_points", [])])

    msg1 = (
        f"📈 <b>MARKET INTELLIGENCE</b>\n"
        f"{esc(date_str)} | {esc(time_str)} | {mood_emoji}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>주요 지수</b>\n"
        f"{indices_text}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🇺🇸 <b>미국 증시</b>\n"
        f"<b>{esc(us.get('headline', ''))}</b>\n\n"
        f"{esc(us.get('summary', ''))}\n\n"
        f"{us_points}"
    )
    send_telegram_message(token, chat_id, msg1)

    # ── 메시지 2: 뉴욕 상세 분석 ────────────────────────────────────
    if ny_detail:
        detail = ny_detail.get("ny_detail", {})
        factors_text = "\n".join([f"  • {esc(f)}" for f in detail.get("change_factors", [])])

        sectors_text = ""
        for s in detail.get("sectors", []):
            sectors_text += (
                f"\n{s.get('emoji', '')} <b>{esc(s.get('name', ''))}</b>\n"
                f"{esc(s.get('headline', ''))}\n"
                f"<code>{esc(s.get('key_stocks', ''))}</code>\n"
                f"{esc(s.get('analysis', ''))}\n"
            )

        msg2 = (
            f"🏛 <b>뉴욕 증시 상세 분석</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<b>{esc(detail.get('date_headline', ''))}</b>\n\n"
            f"{esc(detail.get('overview', ''))}\n\n"
            f"📌 <b>변화 요인</b>\n{factors_text}\n"
            f"━━━━━━━━━━━━━━━━━━"
            f"{sectors_text}"
        )
        if len(msg2) > 4000:
            msg2 = msg2[:4000] + "\n<i>...계속</i>"
        send_telegram_message(token, chat_id, msg2)

    # ── 메시지 3: 국내 증시 ──────────────────────────────────────────
    kr_points = "\n".join([f"  ▸ {esc(p)}" for p in kr.get("key_points", [])])

    msg3 = (
        f"🇰🇷 <b>국내 증시</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>{esc(kr.get('headline', ''))}</b>\n\n"
        f"{esc(kr.get('summary', ''))}\n\n"
        f"{kr_points}"
    )
    send_telegram_message(token, chat_id, msg3)

    # ── 메시지 4: 뉴스 큐레이션 ──────────────────────────────────────
    KR_SOURCES = {"연합뉴스", "한국경제", "매일경제", "네이버", "조선", "머니",
                  "이데일리", "서울경제", "헤럴드", "아시아경제", "뉴스1"}

    news_text = "📰 <b>주요 뉴스 큐레이션</b>\n"
    for item in news_list:
        src  = item.get('source', '')
        flag = "🇰🇷" if any(k in src for k in KR_SOURCES) else "🇺🇸"
        link = item.get('link', '')
        title_text = esc(item.get('title', ''))

        news_text += "\n━━━━━━━━━━━━━━━━━━\n"
        if link:
            news_text += f"{flag} <b><a href=\"{link}\">{title_text}</a></b>\n"
        else:
            news_text += f"{flag} <b>{title_text}</b>\n"
        news_text += f"<i>{esc(src)}</i>\n"
        news_text += f"① {esc(item.get('line1', ''))}\n"
        news_text += f"② {esc(item.get('line2', ''))}\n"
        news_text += f"③ {esc(item.get('line3', ''))}\n"
        news_text += f"💡 {esc(item.get('insight', ''))}\n"

    if len(news_text) > 4000:
        news_text = news_text[:4000] + "\n<i>...계속</i>"
    send_telegram_message(token, chat_id, news_text)

    # ── 메시지 5: 투자 포인트 ────────────────────────────────────────
    msg5 = (
        f"🎯 <b>오늘의 투자 포인트</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✅ <b>TODAY FOCUS</b>\n{esc(inv.get('today_focus', ''))}\n\n"
        f"⚠️ <b>RISK FACTOR</b>\n{esc(inv.get('risk_factor', ''))}\n\n"
        f"💰 <b>OPPORTUNITY</b>\n{esc(inv.get('opportunity', ''))}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>본 브리핑은 AI 생성 참고용 자료이며, 투자 판단의 책임은 투자자 본인에게 있습니다.</i>"
    )
    send_telegram_message(token, chat_id, msg5)

    print("\n✅ 텔레그램 브리핑 전송 완료!")

# ── 메인 실행 ──────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("📈 시황 브리핑 생성 시작 (텔레그램)")
    print(f"⏰ {get_kst_now().strftime('%Y-%m-%d %H:%M KST')}")
    print("=" * 50)

    telegram_token   = os.environ.get("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not telegram_token or not telegram_chat_id:
        raise ValueError("TELEGRAM_BOT_TOKEN 또는 TELEGRAM_CHAT_ID 환경 변수가 설정되지 않았습니다.")

    try:
        news        = fetch_all_news()
        market_data = fetch_us_market_data()
        brief       = generate_market_brief(news)
        ny_detail   = generate_ny_detail(news, market_data)

        format_and_send_telegram(brief, market_data, ny_detail, telegram_token, telegram_chat_id)

        # JSON 저장 (백업용)
        json_path = Path(__file__).parent / "latest_brief.json"
        json_path.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✅ JSON 백업 저장: {json_path}")

        print("\n🎉 완료!")

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        raise

if __name__ == "__main__":
    main()
