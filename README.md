# LFS Coverage Index

One of the three Empstat labour-data coverage indices. This repo is self-contained
and deploys to **https://lfs.empstat.org** via GitHub Pages.

- Site: `web/index.html` (reads `web/data/rankings.js`)
- Custom domain: `web/CNAME` = lfs.empstat.org
- Pipeline: `pipeline/` — refresh real data with:
  ```
  cd pipeline
  pip install -r requirements.txt
  python fetch_and_rank.py  --out ../web/data
  ```
- Weekly auto-refresh + deploy: `.github/workflows/weekly-update.yml` (Mondays 22:00 UTC)

Deploy steps: see DEPLOY_three_subdomains.md (provided alongside the three zips).
Sibling sites: lfs.empstat.org · census.empstat.org · admin.empstat.org.
Data: ILOSTAT (CC BY 4.0). Independent index; not published or endorsed by the ILO.
