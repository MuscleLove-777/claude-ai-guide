"""Claude AI完全ガイド - アフィリエイトリンク自動挿入モジュール（スタンドアロン版）

blog_engineの共通モジュールを使用し、フォールバックとしてローカル実装を持つ。
Claude特化のアフィリエイト構造（dict形式）に対応。
"""
import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_engine_path = str(Path(__file__).parent.parent)
if _engine_path not in sys.path:
    sys.path.insert(0, _engine_path)


class AffiliateManager:
    """アフィリエイトリンクの管理と自動挿入を行うクラス

    config.AFFILIATE_LINKSが以下の2形式に対応:
    - dict of list (blog_engine標準): {"カテゴリ": [{"service": ..., "url": ..., "description": ...}]}
    - dict of dict (003_Claude形式): {"名前": {"url": ..., "text": ..., "description": ...}}
    """

    def __init__(self, config, prompts=None):
        self.raw_links = getattr(config, "AFFILIATE_LINKS", {})
        self.amazon_tag = getattr(config, "AFFILIATE_TAG", "")
        self.adsense_id = getattr(config, "ADSENSE_CLIENT_ID", "")
        self.adsense_enabled = bool(self.adsense_id)
        self.prompts = prompts

        # セクションタイトルとinsert位置
        self.section_title = "## Claudeをもっと活用するためのリソース"
        self.insert_before = "## まとめ"
        if prompts:
            if hasattr(prompts, "AFFILIATE_SECTION_TITLE"):
                self.section_title = prompts.AFFILIATE_SECTION_TITLE
            if hasattr(prompts, "AFFILIATE_INSERT_BEFORE"):
                self.insert_before = prompts.AFFILIATE_INSERT_BEFORE

    def insert_affiliate_links(self, article: dict) -> dict:
        """記事にアフィリエイトリンクを挿入する"""
        content = article.get("content", "")
        category = article.get("category", "")
        keyword = article.get("keyword", "")

        relevant = self._find_relevant_links(category, keyword)

        if relevant:
            section = self._build_affiliate_section(relevant)
            if self.insert_before in content:
                content = content.replace(self.insert_before, f"{section}\n\n{self.insert_before}")
            else:
                content += f"\n\n{section}"
            article["content"] = content
            article["has_affiliate"] = True
            article["affiliate_count"] = len(relevant)
            logger.info("%d件のアフィリエイトリンクを挿入", len(relevant))
        else:
            article["has_affiliate"] = False
            article["affiliate_count"] = 0

        return article

    def _find_relevant_links(self, category: str, keyword: str) -> list[dict]:
        """カテゴリ/キーワードに関連するリンクを抽出する"""
        relevant = []

        for name, data in self.raw_links.items():
            # dict of dict形式（003_Claude形式）
            if isinstance(data, dict) and "url" in data:
                name_lower = name.lower()
                cat_lower = category.lower()
                kw_lower = keyword.lower()
                if (name_lower in cat_lower or name_lower in kw_lower
                        or cat_lower in name_lower or kw_lower in name_lower
                        or "書籍" in name or "amazon" in name_lower or "楽天" in name_lower
                        or "udemy" in name_lower):
                    relevant.append({
                        "service": name,
                        "url": data["url"],
                        "description": data.get("description", data.get("text", "")),
                    })
            # dict of list形式（blog_engine標準）
            elif isinstance(data, list):
                for item in data:
                    relevant.append(item)

        # 重複除去
        seen = set()
        unique = []
        for link in relevant:
            key = link.get("service", link.get("url", ""))
            if key not in seen:
                seen.add(key)
                unique.append(link)

        # 少なすぎる場合は書籍系を追加
        if len(unique) < 2:
            for name, data in self.raw_links.items():
                if isinstance(data, dict) and "url" in data:
                    if name not in seen:
                        unique.append({
                            "service": name,
                            "url": data["url"],
                            "description": data.get("description", data.get("text", "")),
                        })
                        seen.add(name)
                if len(unique) >= 4:
                    break

        return unique[:5]

    def _build_affiliate_section(self, links: list[dict]) -> str:
        """アフィリエイトセクションのMarkdownを構築する"""
        section = f"{self.section_title}\n\n"
        section += "この記事の内容をさらに深めるために、以下のリソースが役立ちます。\n\n"

        for link in links:
            url = link["url"]
            if "amazon" in url.lower() and self.amazon_tag:
                sep = "&" if "?" in url else "?"
                url = f"{url}{sep}tag={self.amazon_tag}"
            section += f"- **[{link['service']}]({url})** - {link['description']}\n"

        section += "\n*上記リンクからご利用いただくと、サイト運営の支援になります。*\n"
        return section

    def get_adsense_head_tag(self) -> str:
        if not self.adsense_enabled:
            return ""
        return (
            f'<script async src="https://pagead2.googlesyndication.com/pagead/js/'
            f'adsbygoogle.js?client={self.adsense_id}" crossorigin="anonymous"></script>'
        )

    def get_adsense_article_ad(self) -> str:
        if not self.adsense_enabled:
            return ""
        return f"""
<div style="text-align:center;margin:24px 0;">
  <ins class="adsbygoogle" style="display:block"
       data-ad-client="{self.adsense_id}" data-ad-slot="auto"
       data-ad-format="auto" data-full-width-responsive="true"></ins>
  <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
</div>"""
