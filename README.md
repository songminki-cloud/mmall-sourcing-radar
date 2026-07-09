# Mmall Signal Desk

M몰 MD가 네이버 인기검색어 신호를 Day, 카테고리, 기준일별로 확인하는 정적 아카이브입니다.

## 구성

- `index.html`: 최신 리포트, 최근 3개 리포트, 모든 리포트 검색/정렬
- `day-*.html`: Day별 상세 브리프
- `manifest.json`: 생성 페이지 색인
- `styles.css`: 정적 사이트 UI 스타일

## 로컬 미리보기

```bash
python3 -m http.server 8765
```

브라우저에서 아래 주소를 엽니다.

```text
http://127.0.0.1:8765/index.html
```

## 데이터 기준

네이버 DataLab 쇼핑인사이트 TOP 랭킹, 네이버쇼핑 상위 노출 상품명, M몰 모바일 로그인 전 검색 노출을 기준으로 합니다. DataLab과 쇼핑인사이트 값은 정규화된 비율이며 절대 검색량이 아닙니다.
