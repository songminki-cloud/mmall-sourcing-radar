#!/usr/bin/env python3
"""Publish 전 필수 검증: manifest.json과 실제 day-*.html 파일, index.html 카드가 어긋나지 않는지 확인한다.
하나라도 실패하면 exit 1로 push를 막는다."""
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

    if ok:
        print(f"PASS: Day 1~{len(days)} 전체 {len(days)}개, manifest/파일/index.html 모두 일치")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
