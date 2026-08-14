#!/usr/bin/env python3
"""승인 패키지(day-N-approved-package.json) → 발행 산출물 결정적 렌더러.

발행 단계에서 LLM이 HTML을 조립하다 생긴 템플릿 이탈·마크업 회귀(2026-08-03 Day 40,
2026-07-21 Day 30 등)를 클래스로 없앤다. 이 스크립트가 day-*.html 생성,
manifest.json 항목 추가/교체, index.html 최신 카드·아카이브 카드 갱신을 전부 수행한다.
발행 절차에서 사람이든 모델이든 HTML을 손으로 만들지 않는다.

사용:
    python3 render_day_page.py <day-N-approved-package.json 경로>

렌더 후에는 반드시 verify_manifest.py와 stage1_report_guard.py를 실행한다.
"""
from __future__ import annotations

import html as html_mod
import json
import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GENERATOR_TAG = "render-day-page v1"

CATEGORY_SLUGS = {
    "디지털/가전": "digital",
    "스포츠/레저": "sports",
    "가구/인테리어": "interior",
    "생활/건강": "health",
    "패션잡화": "fashion-accessory",
    "화장품/미용": "cosmetics-beauty",
    "식품": "food",
    "패션의류": "fashion",
    "출산/육아": "parenting",
}

BADGE_TREND = {"상승": "up", "하락": "down", "중립": "neutral"}


def esc(text: str) -> str:
    return html_mod.escape(text or "", quote=False)


def parse_header(header: str, keyword: str) -> tuple[str, str, str]:
    """헤더에서 (네이버 링크, 키커 문구, trend 클래스)를 뽑는다."""
    link = re.search(r"\((https?://[^)]+)\)", header or "")
    naver_url = link.group(1) if link else (
        "https://msearch.shopping.naver.com/search/all?query=" + urllib.parse.quote(keyword)
    )
    parts = re.split(r"\s*·\s*", header or "", maxsplit=1)
    kicker = parts[1].strip() if len(parts) > 1 else ""
    badge = re.search(r"(상승|하락|중립)", kicker)
    trend = BADGE_TREND.get(badge.group(1), "neutral") if badge else "neutral"
    if badge:
        # 배지는 항상 '순위부 · 이모지 단어' 표준형으로 재조립한다 (verify_manifest 고정 포맷).
        emoji = {"up": "📈", "down": "📉", "neutral": "➖"}[trend]
        rank_part = re.split(r"\s*·\s*", kicker)[0].strip()
        kicker = f"{rank_part} · {emoji} {badge.group(1)}"
    return naver_url, kicker, trend


def mmall_button(keyword: str, mmall: dict | None) -> str:
    url = "https://mpointmall.hyundaicard.com/web/index.html#/search/result?q=" + urllib.parse.quote(keyword)
    if mmall is None or mmall.get("count") is None:
        label = "M몰에서 보기 · 데이터 미확인"
    else:
        label = f"M몰에서 보기 · {int(mmall['count'])}개"
    return (
        f'<a class="market-link market-link-secondary" href="{url}" '
        f'target="_blank" rel="noreferrer">{label}</a>'
    )


def bullet_lines(text: str) -> list[tuple[str, str]]:
    """'• 라벨: 내용' 형태의 줄 목록을 (라벨, 내용)으로 파싱한다."""
    rows = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line.startswith("•"):
            continue
        body = line.lstrip("• ").strip()
        if ":" in body:
            label, rest = body.split(":", 1)
            rows.append((label.strip(), rest.strip()))
        else:
            rows.append(("", body))
    return rows


def keyword_card(index: int, entry: dict) -> str:
    keyword = entry["keyword"]
    naver_url, kicker, trend = parse_header(entry.get("header", ""), keyword)
    memo = " ".join((entry.get("memo") or "").split())
    return f"""        <article class="keyword-card" id="keyword-{index:02d}" data-trend="{trend}" data-keyword="{esc(keyword)}">
        <div class="card-top">
          <div class="card-title-block">
            <div class="card-title-row">
              <h3><span class="item-number" aria-label="{index}번">{index:02d}</span><span>{esc(keyword)}</span></h3>
              <p class="item-kicker">{esc(kicker)}</p>
            </div>
          </div>
        </div>
          <p class="memo">{esc(memo)}</p>
          <nav class="card-actions">
            <a class="market-link market-link-primary" href="{naver_url}" target="_blank" rel="noreferrer">네이버쇼핑에서 보기</a>
            {mmall_button(keyword, entry.get("mmall"))}
          </nav>
        </article>"""


def side_nav(manifest: list[dict], day: int, category: str, page_name: str, date: str) -> str:
    same = sorted(
        (e for e in manifest if e["category"] == category and int(e["day"]) != day),
        key=lambda e: int(e["day"]),
        reverse=True,
    )[:4]
    links = [
        f'        <a class="side-link current" href="{page_name}">Day {day} · {date}</a>'
    ]
    for e in same:
        links.append(
            f'        <a class="side-link" href="{e["page"]}">Day {e["day"]} · {e["date"]}</a>'
        )
    return "\n".join(links)


def render_page(pkg: dict, manifest: list[dict], page_name: str) -> str:
    day, date, category = pkg["day"], pkg["date"], pkg["category"]
    paragraphs = [" ".join(p.split()) for p in pkg["md_comment_paragraphs"]]
    description = paragraphs[0]
    cards = "\n".join(keyword_card(i + 1, k) for i, k in enumerate(pkg["keywords"]))
    judgment = "".join(
        f"<p><span><b>• {esc(label)}:</b> {esc(body)}</span></p>" if label else f"<p><span>{esc(body)}</span></p>"
        for label, body in bullet_lines(pkg.get("md_judgment", ""))
    )
    focus = "\n".join(f"          <p><span>{esc(p)}</span></p>" for p in paragraphs)
    source_date = pkg.get("source_date") or ""
    counts = []
    for k in pkg["keywords"]:
        m = k.get("mmall")
        counts.append(f"{k['keyword']} {int(m['count'])}개" if m and m.get("count") is not None else f"{k['keyword']} 미확인")
    basis_items = [
        f"원천은 네이버 DataLab {category} 인기검색어 Top500 수집분과 {date} M몰 로그인 전 모바일 검색 실측입니다.",
        "M몰 검색결과는 " + ", ".join(counts) + "입니다.",
    ]
    for label, body in bullet_lines(pkg.get("notes", "")):
        basis_items.append(f"{label}: {body}" if label else body)
    basis = "".join(f"<li><span>{esc(item)}</span></li>" for item in basis_items)

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Day {day} · {category} · {date}</title>
  <link rel="icon" href="data:,">
  <link rel="stylesheet" href="styles.css?v=20260711-mobile-cta-v2">
  <meta name="generator" content="{GENERATOR_TAG}">
  <meta name="description" content="Day {day} {category} 변화 리포트 — {esc(description)}">
</head>
<body>
  <main class="site">
    <header class="report-hero">
      <a class="back-link" href="index.html">목록으로</a>
      <h1>Day {day} · {category}</h1>
      <p class="report-date">기준일 {date}</p>
      <p class="hero-copy">네이버 DataLab {category} 인기검색어 Top500에서 눈에 띄는 키워드를 골라, 왜 지금 검색되는지와 M몰 소싱 관점을 함께 정리한 MD 리포트입니다.</p>
    </header>

    <section class="focus-section">
      <h2>MD 코멘트</h2>
      <div class="focus-list">
{focus}
      </div>
    </section>

    <div class="report-layout">
      <aside class="side-nav">
        <p>같은 카테고리</p>
{side_nav(manifest, day, category, page_name, date)}
      </aside>
      <section class="keyword-list">
{cards}
      </section>
    </div>

    <section class="focus-section">
      <h2>MD 판단</h2>
      <div class="focus-list">{judgment}</div>
    </section>
    <details class="evidence-section">
      <summary>리포트 작성 기준</summary>
      <ul class="basis-list">{basis}</ul>
      <p class="evidence-caption">원천 확인 자료</p>
      <div class="evidence-grid"></div>
    </details>
    <footer class="site-footer">
      <p>기준: 네이버 DataLab 쇼핑인사이트 인기검색어 Top500, M몰 모바일 로그인 전 검색 노출, 확인된 화제성 출처.</p>
      <p>DataLab과 쇼핑 클릭 지표는 정규화된 비율이며 절대 검색량이 아닙니다. M몰 수치는 내부 재고가 아니라 모바일 노출면 기준입니다.</p>
    </footer>
  </main>
</body>
</html>
"""


def featured_card(pkg: dict, page_name: str) -> str:
    day, category, date = pkg["day"], pkg["category"], pkg["date"]
    first = " ".join(pkg["md_comment_paragraphs"][0].split())
    kw_links = "".join(
        f'<a href="{page_name}#keyword-{i + 1:02d}">{esc(k["keyword"])}</a>'
        for i, k in enumerate(pkg["keywords"][:5])
    )
    return f"""<article class="latest-card recent-card featured">
              <a class="latest-card-main" href="{page_name}" aria-label="Day {day} {category} 리포트 열기">
                <span class="latest-kicker">{date}</span>
                <h2>Day {day} · {category}</h2>
                <p>{esc(first)}</p>
              </a>
              <div class="latest-keywords">{kw_links}</div>
            </article>"""


def archive_card(pkg: dict, page_name: str) -> str:
    day, category, date = pkg["day"], pkg["category"], pkg["date"]
    keywords = [k["keyword"] for k in pkg["keywords"]]
    search_text = " ".join(
        [date, category]
        + keywords
        + [" ".join(p.split()) for p in pkg["md_comment_paragraphs"]]
        + [" ".join((k.get("memo") or "").split()) for k in pkg["keywords"]]
    )
    preview = ", ".join(keywords[:4])
    return f"""        <a class="archive-card" href="{page_name}" data-day="{day}" data-category="{esc(category)}" data-search="{html_mod.escape(search_text)}">
          <span class="archive-kicker">Day {day} · {date}</span>
          <strong>{esc(category)}</strong>
          <em>{esc(preview)}</em>
        </a>"""


def update_index(index_html: str, pkg: dict, page_name: str) -> str:
    # 최신 3개 카드: 기존 카드 블록을 모두 수집해 [새 featured, 이전 1, 이전 2]로 재구성.
    section_match = re.search(r'(<section class="recent-section".*?</section>)', index_html, re.S)
    if not section_match:
        raise SystemExit("index.html에서 recent-section을 찾지 못했습니다")
    section = section_match.group(1)
    cards = re.findall(r'<article class="latest-card recent-card[^"]*">.*?</article>', section, re.S)
    if not cards:
        raise SystemExit("index.html에서 최신 카드를 찾지 못했습니다")
    # 재렌더(같은 페이지) 시 자기 카드는 제외하고 재구성한다.
    cards = [c for c in cards if page_name not in c]
    def demote(card: str) -> str:
        return card.replace('recent-card featured', 'recent-card plain')

    rebuilt = [featured_card(pkg, page_name)]
    if cards:
        rebuilt.append(demote(cards[0]))
        rebuilt.extend(cards[1:2])
    # 카드 전체 블록을 통째로 교체한다.
    all_old = re.findall(r'<article class="latest-card recent-card[^"]*">.*?</article>', section, re.S)
    section_head, section_tail = section.split(all_old[0], 1)
    for c in all_old[1:]:
        section_tail = section_tail.replace(c, "", 1)
    new_section = section_head + "\n\n\n".join(rebuilt[:3]) + section_tail
    index_html = index_html.replace(section, new_section, 1)
    index_html = re.sub(
        r'<p class="hero-copy">.*?</p>',
        '<p class="hero-copy">네이버 DataLab 카테고리별 인기검색어를 넓게 보고, M몰 모바일 검색 노출과 외부 수요 신호를 함께 읽어 다음 소싱 후보를 정리한 MD 리포트입니다.</p>',
        index_html,
        count=1,
        flags=re.S,
    )

    # 아카이브 카드: 기존 자기 카드 제거 후 맨 앞에 삽입.
    index_html = re.sub(
        rf'\s*<a class="archive-card" href="{re.escape(page_name)}".*?</a>',
        "",
        index_html,
        flags=re.S,
    )
    first_archive = re.search(r'[ \t]*<a class="archive-card" ', index_html)
    if not first_archive:
        raise SystemExit("index.html에서 archive-card를 찾지 못했습니다")
    index_html = (
        index_html[: first_archive.start()]
        + archive_card(pkg, page_name)
        + "\n"
        + index_html[first_archive.start():]
    )
    return index_html


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    pkg = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    day, date, category = int(pkg["day"]), pkg["date"], pkg["category"]
    slug = CATEGORY_SLUGS.get(category)
    if not slug:
        raise SystemExit(f"모르는 카테고리: {category}")
    page_name = f"day-{day}-{date}-{slug}.html"

    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    existing = [e for e in manifest if int(e["day"]) == day]
    if existing and existing[0]["page"] != page_name:
        raise SystemExit(
            f"Day {day}가 이미 다른 페이지({existing[0]['page']})로 발행돼 있습니다. "
            "재발행이면 기존 항목을 먼저 정리하세요."
        )
    rising = sum(1 for k in pkg["keywords"] if "상승" in (k.get("header") or ""))
    entry = {
        "day": day,
        "date": date,
        "category": category,
        "items": len(pkg["keywords"]),
        "rising": rising,
        "page": page_name,
        "evidence_docs": [],
    }
    manifest = [e for e in manifest if int(e["day"]) != day] + [entry]
    manifest.sort(key=lambda e: int(e["day"]))

    page_html = render_page(pkg, manifest, page_name)
    (ROOT / page_name).write_text(page_html, encoding="utf-8")
    (ROOT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    index_html = update_index((ROOT / "index.html").read_text(encoding="utf-8"), pkg, page_name)
    (ROOT / "index.html").write_text(index_html, encoding="utf-8")

    print(f"RENDERED: {page_name} | manifest {len(manifest)}개 | index 갱신")
    print("다음 단계: python3 verify_manifest.py && stage1_report_guard.py 실행 후 push")
    return 0


if __name__ == "__main__":
    sys.exit(main())
