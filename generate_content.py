name: Daily Market Brief

on:
  schedule:
    - cron: '0 22 * * *'
  workflow_dispatch:

permissions:
  contents: write
  pages: write
  id-token: write

jobs:
  generate-brief:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Generate market brief
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: python generate_content.py

      - name: Commit and push
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add index.html latest_brief.json
          git diff --staged --quiet || git commit -m "시황 브리핑 업데이트"
          git push

  deploy-pages:
    needs: generate-brief
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          ref: main

      - name: Setup Pages
        uses: actions/configure-pages@v4

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: '.'

      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

---

## 📄 파일 2: `requirements.txt`

GitHub → `requirements.txt` → ✏️ 편집 → 전체 삭제 → 아래 내용 붙여넣기:
```
anthropic>=0.40.0
feedparser>=6.0.11
yfinance>=0.2.50
