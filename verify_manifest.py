#!/usr/bin/env python3
"""Publish 전 필수 검증: manifest.json과 실제 day-*.html 파일, index.html 카드가 어긋나지 않는지 확인한다.
하나라도 실패하면 exit 1로 push를 막는다."""
import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def fail(msg):
    print(f"FAIL: {msg}")
    return False


def main():
    ok = True
    manifest = json.loads((ROOT / "manifest.json").read_text())
    days = sorted(x["day"] for x in manifest)

    # 1. day 번호가 1..N 연속인지 (이빨빠짐 방지)
    expected = list(range(1, len(days) + 1))
    if days != expected:
        missing = sorted(set(expected) - set(days))
        ok = fail(f"manifest day 번호가 연속이 아님. 빠진 day: {missing}")

    # 2. manifest에 있는 모든 page 파일이 실제로 존재하는지
    for entry in manifest:
        page = ROOT / entry["page"]
        if not page.exists():
            ok = fail(f"manifest에 있는 {entry['page']} 파일이 실제로 없음 (Day {entry['day']})")

    # 3. 디스크의 모든 day-*.html이 manifest에 등록돼 있는지 (역방향 누락)
    manifest_pages = {x["page"] for x in manifest}
    for f in sorted(ROOT.glob("day-*.html")):
        if f.name not in manifest_pages:
            ok = fail(f"{f.name} 파일은 있는데 manifest에 등록 안 됨")

    # 4. index.html 최신 3개 카드가 manifest 최신 3개 day와 일치하는지
    index_html = (ROOT / "index.html").read_text()
    latest3 = sorted(manifest, key=lambda x: x["day"], reverse=True)[:3]
    for entry in latest3:
        if entry["page"] not in index_html:
            ok = fail(f"index.html 최신 카드에 Day {entry['day']} ({entry['page']})가 없음")

    # 5. archive-grid에 전체 day가 다 링크돼 있는지
    archive_links = set(re.findall(r'archive-card" href="(day-[^"]+\.html)"', index_html))
    for entry in manifest:
        if entry["page"] not in archive_links:
            ok = fail(f"archive-grid에 Day {entry['day']} ({entry['page']})가 없음")

    # 6~8. 최신 3개 Day 마크업 회귀 검사 (2026-07-21 Day 30 포맷 퇴화 재발 방지)
    # 과거 Day 파일은 시기별로 마크업이 달라 소급 적용하지 않는다. 신규 발행분만 검사한다.
    latest3_pages = {ROOT / e["page"] for e in latest3}
    for f in sorted(latest3_pages):
        if not f.exists():
            continue
        html = f.read_text()

        # 6. footer 누락
        if "site-footer" not in html:
            ok = fail(f"{f.name}에 <footer class=\"site-footer\">가 없음")

        # 7. M몰 검색결과 문구가 카드 메모 안에 중복 노출됐는지
        if re.search(r"M몰\s*검색결과\s*[:：]", html):
            ok = fail(f"{f.name} 메모 문장에 '(M몰 검색결과: n개)'가 남아 있음 (버튼과 중복, 텍스트에서 제거해야 함)")

        # 8. 순위 배지 포맷 검사. 직전 순위 데이터가 있으면 "N위 → M위 ... · 이모지 상승/하락/중립",
        # 직전 순위 데이터를 원천에서 못 구했으면 "N위 · 이모지 상승/하락/중립"만 허용한다(2026-07-21 JD 확정).
        # 둘 중 어느 쪽도 아니면(이모지·추세 라벨 자체가 빠진 경우) 회귀로 본다.
        kicker_pattern = re.compile(r'^\d+위(\s*→\s*\d+위[^·]*)?\s*·\s*(📈 상승|📉 하락|➖ 중립)$')
        for kicker in re.findall(r'<p class="item-kicker">(.*?)</p>', html):
            if "신규" not in kicker and not kicker_pattern.match(kicker.strip()):
                ok = fail(f"{f.name}의 item-kicker '{kicker}'가 고정 포맷(N위 [→ M위] · 이모지 상승/하락/중립)에 안 맞음")

    # 9. 파일명 날짜와 페이지 내 기준일이 일치하는지 (2026-07-23 Day 32 기준일 라벨링 오류 재발 방지)
    for entry in manifest:
        page = ROOT / entry["page"]
        if not page.exists():
            continue
        m = re.match(r"day-\d+-(\d{4}-\d{2}-\d{2})-", entry["page"])
        if not m:
            continue
        filename_date = m.group(1)
        html = page.read_text()
        ref_match = re.search(r"기준일[^0-9]*(\d{4}-\d{2}-\d{2})", html)
        if ref_match and ref_match.group(1) != filename_date:
            ok = fail(
                f"{entry['page']}: 파일명 날짜({filename_date})와 본문 기준일({ref_match.group(1)})이 다름"
            )

    # 10. 최신 Day의 기준일이 오늘(스크립트 실행일, 로컬 시각) 날짜와 같은지 경고
    # 원본 DataLab 수집 파일은 항상 실행일보다 하루 전 날짜가 붙으므로, 그 날짜를 그대로
    # 기준일로 베끼면 하루가 밀린다(Day 32 사고). 발행 시점에는 반드시 오늘 날짜여야 한다.
    today = datetime.date.today().isoformat()
    if latest3:
        latest_entry = latest3[0]
        m = re.match(r"day-\d+-(\d{4}-\d{2}-\d{2})-", latest_entry["page"])
        if m and m.group(1) != today:
            print(
                f"WARN: 최신 Day({latest_entry['page']})의 날짜가 오늘({today})과 다름. "
                f"발행 당일 실행이 아니면 무시해도 되지만, 당일 발행이라면 기준일 오류 가능성이 높음."
            )

    # 11. index.html '최신 리포트' 섹션 카드가 정확히 3개인지 (2026-07-23 Day 32 발행 시
    # Day 29/28 카드가 안 지워지고 5개로 남았던 사고 재발 방지. 4번 검사는 '최신 3개가
    # 포함돼 있는지'만 봐서 이 사고를 못 잡았다)
    recent_section = re.search(r'<section class="recent-section".*?</section>', index_html, re.S)
    if recent_section:
        card_count = len(re.findall(r'<article class="latest-card recent-card', recent_section.group(0)))
        if card_count != 3:
            ok = fail(f"index.html 최신 리포트 섹션 카드가 {card_count}개임 (정확히 3개여야 함)")
    else:
        ok = fail("index.html에서 recent-section을 찾을 수 없음")

    # 12. 최신 카드의 latest-kicker 날짜가 실제 기준일(파일명 날짜)과 일치하는지
    # (2026-07-23 Day 32 카드 날짜 배지가 하루 밀렸던 사고 재발 방지)
    for entry in latest3:
        page = ROOT / entry["page"]
        if not page.exists():
            continue
        m = re.match(r"day-\d+-(\d{4}-\d{2}-\d{2})-", entry["page"])
        if not m:
            continue
        filename_date = m.group(1)
        card_match = re.search(
            re.escape(entry["page"]) + r'.*?<span class="latest-kicker">(\d{4}-\d{2}-\d{2})</span>',
            index_html, re.S
        )
        if card_match and card_match.group(1) != filename_date:
            ok = fail(
                f"index.html Day {entry['day']} 카드의 latest-kicker 날짜({card_match.group(1)})가 "
                f"실제 기준일({filename_date})과 다름"
            )

    if ok:
        print(f"PASS: Day 1~{len(days)} 전체 {len(days)}개, manifest/파일/index.html 모두 일치")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
