"""Claude AI完全ガイド - 管理ダッシュボード（スタンドアロン版）

blog_engineの共通モジュールを使用し、フォールバックとしてローカル実装を持つ。
"""
import sys
from pathlib import Path

_engine_path = str(Path(__file__).parent.parent)
if _engine_path not in sys.path:
    sys.path.insert(0, _engine_path)

try:
    from blog_engine.dashboard import create_app
except ImportError:
    import json
    import re
    from datetime import datetime, timedelta
    from typing import Optional

    import uvicorn
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.responses import HTMLResponse
    from pydantic import BaseModel

    def create_app(config, prompts=None):
        """ダッシュボードアプリケーション（スタンドアロン版）"""
        app = FastAPI(title=f"{config.BLOG_NAME} 管理ダッシュボード", version="1.0.0")

        theme = getattr(config, "THEME", {})
        primary = theme.get("primary", "#d97757")
        accent = theme.get("accent", "#1a1a2e")
        dark_bg = theme.get("dark_bg", "#0f0f1a")
        light_bg = theme.get("light_bg", "#fdf8f6")

        articles_dir = getattr(config, "ARTICLES_DIR", Path(config.BASE_DIR) / "output" / "articles")

        def _load_articles():
            articles = []
            if not articles_dir.exists():
                return articles
            for f in articles_dir.glob("*.json"):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    data.setdefault("slug", f.stem)
                    articles.append(data)
                except (json.JSONDecodeError, OSError):
                    continue
            articles.sort(key=lambda a: a.get("created_at", a.get("generated_at", "")), reverse=True)
            return articles

        CSS = f"""<style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Inter', 'Noto Sans JP', sans-serif; background: {light_bg}; color: #1E293B; display: flex; min-height: 100vh; }}
        .sidebar {{ width: 250px; background: {dark_bg}; color: #fff; padding: 24px 0; position: fixed; height: 100vh; }}
        .sidebar h1 {{ font-size: 18px; padding: 0 24px 24px; border-bottom: 1px solid {primary}; margin-bottom: 16px; }}
        .sidebar a {{ display: block; color: #94A3B8; text-decoration: none; padding: 12px 24px; font-size: 14px; }}
        .sidebar a:hover {{ color: #fff; background: {primary}; }}
        .main {{ margin-left: 250px; padding: 32px; flex: 1; }}
        .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; margin-bottom: 32px; }}
        .card {{ background: #fff; border-radius: 12px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
        .card-label {{ font-size: 13px; color: #64748B; margin-bottom: 8px; }}
        .card-value {{ font-size: 32px; font-weight: 700; color: {accent}; }}
        .table-wrap {{ background: #fff; border-radius: 12px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
        table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
        th {{ text-align: left; padding: 12px; border-bottom: 2px solid #E2E8F0; color: #64748B; }}
        td {{ padding: 12px; border-bottom: 1px solid #F1F5F9; }}
        td a {{ color: {primary}; text-decoration: none; }}
        .badge {{ display: inline-block; padding: 4px 10px; border-radius: 999px; font-size: 12px; background: {light_bg}; color: {primary}; }}
        </style>"""

        def _base(title, content):
            return f"""<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title} | {config.BLOG_NAME}</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Noto+Sans+JP:wght@400;600;700&display=swap" rel="stylesheet">
            {CSS}</head><body>
            <nav class="sidebar"><h1>{config.BLOG_NAME}</h1>
            <a href="/">ダッシュボード</a><a href="/articles">記事一覧</a></nav>
            <main class="main">{content}</main></body></html>"""

        @app.get("/", response_class=HTMLResponse)
        async def dashboard_top():
            articles = _load_articles()
            total = len(articles)
            rows = ""
            for a in articles[:10]:
                title_text = a.get("title", "無題")
                cat = a.get("category", "")
                rows += f'<tr><td>{a.get("generated_at", "-")[:10]}</td><td>{title_text}</td><td><span class="badge">{cat}</span></td></tr>'
            content = f"""<h1 style="margin-bottom:24px;">ダッシュボード</h1>
            <div class="cards"><div class="card"><div class="card-label">記事総数</div><div class="card-value">{total}</div></div></div>
            <div class="table-wrap"><h2 style="margin-bottom:16px;">最新記事</h2>
            <table><thead><tr><th>日付</th><th>タイトル</th><th>カテゴリ</th></tr></thead>
            <tbody>{rows if rows else '<tr><td colspan="3" style="text-align:center;padding:32px;color:#94A3B8;">まだ記事がありません</td></tr>'}</tbody></table></div>"""
            return HTMLResponse(_base("ダッシュボード", content))

        @app.get("/articles", response_class=HTMLResponse)
        async def articles_list():
            articles = _load_articles()
            rows = ""
            for a in articles:
                title_text = a.get("title", "無題")
                cat = a.get("category", "")
                rows += f'<tr><td>{a.get("generated_at", "-")[:16]}</td><td>{title_text}</td><td><span class="badge">{cat}</span></td></tr>'
            content = f"""<h1 style="margin-bottom:24px;">記事一覧</h1>
            <div class="table-wrap"><table><thead><tr><th>日時</th><th>タイトル</th><th>カテゴリ</th></tr></thead>
            <tbody>{rows if rows else '<tr><td colspan="3" style="text-align:center;padding:32px;">記事がありません</td></tr>'}</tbody></table></div>"""
            return HTMLResponse(_base("記事一覧", content))

        return app
