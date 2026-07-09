# Mmall Sourcing Radar

Static archive for Mmall MD teams to review Naver popularity signals by Day, category, and report date.

## Contents

- `index.html`: archive home with category filters, search, and latest category comparison
- `day-*.html`: individual report pages
- `manifest.json`: report index for generated pages
- `styles.css`: Hyundai Card style UI layer for the static site

## Local Preview

```bash
python3 -m http.server 8765
```

Then open:

```text
http://127.0.0.1:8765/index.html
```

## Data Note

The site uses Naver DataLab Shopping Insight TOP rankings, Naver Shopping result surfaces, and Mmall mobile pre-login search exposure snapshots. DataLab and Shopping Insight values are normalized ratios, not absolute search volume.
