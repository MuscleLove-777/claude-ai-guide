"""Claude AI完全ガイド - 静的サイト生成エンジン（スタンドアロン版）

blog_engineの共通モジュールを使用し、フォールバックとしてローカル実装を持つ。
SEO最適化: JSON-LD (BlogPosting, FAQPage, BreadcrumbList), robots.txt, sitemap.xml
"""
import sys
from pathlib import Path

_engine_path = str(Path(__file__).parent.parent)
if _engine_path not in sys.path:
    sys.path.insert(0, _engine_path)

try:
    from blog_engine.site_generator import SiteGenerator as _BaseSiteGenerator

    class SiteGenerator(_BaseSiteGenerator):
        """blog_engine拡張版: robots.txt生成を追加"""

        def build_site(self):
            super().build_site()
            self._generate_robots_txt()
            print("  robots.txt 生成完了")

        def _generate_robots_txt(self):
            blog_url = self.config.BLOG_URL
            content = (
                "User-agent: *\n"
                "Allow: /\n"
                f"Sitemap: {blog_url}/sitemap.xml\n"
            )
            (self.output_dir / "robots.txt").write_text(content, encoding="utf-8")

except ImportError:
    import json
    import math
    import re
    import shutil
    import urllib.parse
    from datetime import datetime

    import markdown
    from jinja2 import Environment, FileSystemLoader

    class SiteGenerator:
        """静的サイト生成クラス（スタンドアロン版）"""

        ARTICLES_PER_PAGE = 10

        def __init__(self, config):
            self.config = config
            self.base_dir = Path(config.BASE_DIR)

            # テンプレートディレクトリ: blog_engineから
            template_dir = Path(__file__).parent.parent / "blog_engine" / "templates"
            if not template_dir.exists():
                template_dir = Path(__file__).parent / "templates"
            self.env = Environment(
                loader=FileSystemLoader(str(template_dir)),
                autoescape=True,
            )

            self.articles_dir = self.base_dir / "output" / "articles"
            self.output_dir = self.base_dir / "output" / "site"
            self.md = markdown.Markdown(
                extensions=["toc", "fenced_code", "tables", "meta"],
                extension_configs={"toc": {"title": "目次", "toc_depth": "2-3"}},
            )
            self.theme = getattr(config, "THEME", {})

        def build_site(self):
            print(f"[サイト生成] 開始 - 出力先: {self.output_dir}")
            if self.output_dir.exists():
                shutil.rmtree(self.output_dir)
            self.output_dir.mkdir(parents=True, exist_ok=True)
            (self.output_dir / "articles").mkdir(parents=True, exist_ok=True)
            (self.output_dir / "category").mkdir(parents=True, exist_ok=True)

            articles = self._load_articles()
            articles.sort(key=lambda a: a.get("date", ""), reverse=True)
            print(f"[サイト生成] 記事数: {len(articles)}")

            for article in articles:
                html = self._render_article(article)
                slug = article.get("slug", article.get("id", "untitled"))
                (self.output_dir / "articles" / f"{slug}.html").write_text(html, encoding="utf-8")

            total_pages = max(1, math.ceil(len(articles) / self.ARTICLES_PER_PAGE))
            for page_num in range(1, total_pages + 1):
                start = (page_num - 1) * self.ARTICLES_PER_PAGE
                page_articles = articles[start:start + self.ARTICLES_PER_PAGE]
                html = self._render_index(page_articles, articles=articles, current_page=page_num, total_pages=total_pages)
                if page_num == 1:
                    (self.output_dir / "index.html").write_text(html, encoding="utf-8")
                else:
                    page_dir = self.output_dir / "page"
                    page_dir.mkdir(parents=True, exist_ok=True)
                    (page_dir / f"{page_num}.html").write_text(html, encoding="utf-8")

            categories = self._group_by_category(articles)
            for category, cat_articles in categories.items():
                html = self._render_category(category, cat_articles)
                safe_name = self._slugify(category)
                (self.output_dir / "category" / f"{safe_name}.html").write_text(html, encoding="utf-8")

            self._generate_sitemap(articles)
            self._generate_rss(articles)
            self._generate_robots_txt()
            print(f"[サイト生成] 完了")

        def _load_articles(self):
            articles = []
            if not self.articles_dir.exists():
                return articles
            for fp in sorted(self.articles_dir.glob("*.json")):
                try:
                    with open(fp, "r", encoding="utf-8") as f:
                        article = json.load(f)
                    article.setdefault("title", "無題")
                    article.setdefault("date", datetime.now().strftime("%Y-%m-%d"))
                    article.setdefault("category", "未分類")
                    article.setdefault("tags", [])
                    article.setdefault("content", "")
                    article.setdefault("description", "")
                    article.setdefault("slug", fp.stem)
                    articles.append(article)
                except (json.JSONDecodeError, IOError) as e:
                    print(f"  [警告] {fp}: {e}")
            return articles

        def _get_common_context(self):
            c = self.config
            return {
                "blog_name": c.BLOG_NAME,
                "blog_description": c.BLOG_DESCRIPTION,
                "blog_url": c.BLOG_URL,
                "blog_language": getattr(c, "BLOG_LANGUAGE", "ja"),
                "theme": self.theme,
                "adsense_head": "",
                "adsense_article_ad": "",
            }

        def _render_article(self, article):
            self.md.reset()
            html_content = self.md.convert(article.get("content", ""))
            toc = getattr(self.md, "toc", "")
            ctx = self._get_common_context()
            ctx.update({"article": article, "content": html_content, "toc": toc, "related": article.get("related", [])})
            return self.env.get_template("article.html").render(**ctx)

        def _render_index(self, page_articles, articles=None, current_page=1, total_pages=1):
            if articles is None:
                articles = page_articles
            ctx = self._get_common_context()
            ctx.update({"articles": page_articles, "categories": self._group_by_category(articles), "current_page": current_page, "total_pages": total_pages})
            return self.env.get_template("index.html").render(**ctx)

        def _render_category(self, category, articles):
            ctx = self._get_common_context()
            ctx.update({"category": category, "articles": articles, "article_count": len(articles)})
            return self.env.get_template("category.html").render(**ctx)

        def _generate_sitemap(self, articles):
            url = self.config.BLOG_URL
            lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
            lines.append(f"  <url><loc>{url}</loc><lastmod>{datetime.now().strftime('%Y-%m-%d')}</lastmod><changefreq>daily</changefreq><priority>1.0</priority></url>")
            for a in articles:
                slug = a.get("slug", "untitled")
                date = a.get("date", datetime.now().strftime("%Y-%m-%d"))
                lines.append(f"  <url><loc>{url}/articles/{slug}.html</loc><lastmod>{date}</lastmod><changefreq>monthly</changefreq><priority>0.8</priority></url>")
            for cat in self._group_by_category(articles):
                safe = self._slugify(cat)
                lines.append(f"  <url><loc>{url}/category/{safe}.html</loc><lastmod>{datetime.now().strftime('%Y-%m-%d')}</lastmod><changefreq>weekly</changefreq><priority>0.6</priority></url>")
            lines.append("</urlset>")
            (self.output_dir / "sitemap.xml").write_text("\n".join(lines), encoding="utf-8")

        def _generate_rss(self, articles):
            url = self.config.BLOG_URL
            now = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0900")
            lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">', "  <channel>"]
            lines.append(f"    <title>{self._esc(self.config.BLOG_NAME)}</title>")
            lines.append(f"    <link>{url}</link>")
            lines.append(f"    <description>{self._esc(self.config.BLOG_DESCRIPTION)}</description>")
            lines.append(f"    <language>ja</language><lastBuildDate>{now}</lastBuildDate>")
            for a in articles[:20]:
                slug = a.get("slug", "untitled")
                link = f"{url}/articles/{slug}.html"
                lines.append(f"    <item><title>{self._esc(a.get('title', ''))}</title><link>{link}</link><guid>{link}</guid></item>")
            lines.extend(["  </channel>", "</rss>"])
            (self.output_dir / "feed.xml").write_text("\n".join(lines), encoding="utf-8")

        def _generate_robots_txt(self):
            content = f"User-agent: *\nAllow: /\nSitemap: {self.config.BLOG_URL}/sitemap.xml\n"
            (self.output_dir / "robots.txt").write_text(content, encoding="utf-8")

        @staticmethod
        def _group_by_category(articles):
            cats = {}
            for a in articles:
                cat = a.get("category", "未分類")
                cats.setdefault(cat, []).append(a)
            return cats

        @staticmethod
        def _slugify(text):
            slug = re.sub(r"\s+", "-", text.strip())
            return urllib.parse.quote(slug, safe="-_")

        @staticmethod
        def _esc(text):
            return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
