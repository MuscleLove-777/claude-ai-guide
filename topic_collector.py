"""Claude AI完全ガイド - トピック自動収集モジュール

NEWS_SOURCESからRSS + スクレイピングで最新記事を収集し、
Gemini APIでClaude関連のネタだけフィルタリング＆ランク付けする。
"""
import json
import logging
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# フォールバックimport
try:
    import feedparser
except ImportError:
    feedparser = None
    logger.warning("feedparser が未インストールです。RSS収集は無効になります。")

try:
    import requests
except ImportError:
    requests = None
    logger.warning("requests が未インストールです。スクレイピングは無効になります。")

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
    logger.warning("beautifulsoup4 が未インストールです。HTML解析は無効になります。")

try:
    from google import genai
except ImportError:
    genai = None
    logger.warning("google-genai が未インストールです。AIフィルタリングは無効になります。")


class TopicCollector:
    """Claude AI関連のトピックを自動収集するクラス"""

    def __init__(self, config, prompts=None):
        self.config = config
        self.prompts = prompts
        self.topics_dir = Path(config.BASE_DIR) / "output" / "topics"
        self.topics_dir.mkdir(parents=True, exist_ok=True)

        self.news_sources = {}
        if prompts and hasattr(prompts, "NEWS_SOURCES"):
            self.news_sources = prompts.NEWS_SOURCES

        self.client = None
        if genai and config.GEMINI_API_KEY:
            self.client = genai.Client(api_key=config.GEMINI_API_KEY)

        logger.info("TopicCollector を初期化しました（ソース数: %d）", len(self.news_sources))

    def collect_all(self) -> list[dict]:
        """全ソースからトピックを収集する"""
        logger.info("=== トピック収集開始 ===")
        all_items = []

        for name, url in self.news_sources.items():
            try:
                items = self._collect_from_source(name, url)
                all_items.extend(items)
                logger.info("  %s: %d 件取得", name, len(items))
            except Exception as e:
                logger.warning("  %s: 収集失敗 - %s", name, e)

        logger.info("合計 %d 件のアイテムを取得", len(all_items))

        # Claude関連のフィルタリング
        if all_items and self.client:
            filtered = self._filter_and_rank(all_items)
            logger.info("フィルタリング後: %d 件", len(filtered))
        else:
            filtered = self._simple_filter(all_items)
            logger.info("簡易フィルタリング後: %d 件", len(filtered))

        # 保存
        self._save_topics(filtered)
        return filtered

    def _collect_from_source(self, name: str, url: str) -> list[dict]:
        """単一ソースからアイテムを収集する"""
        items = []

        # まずRSSを試す
        rss_items = self._try_rss(url)
        if rss_items:
            for item in rss_items:
                item["source"] = name
            items.extend(rss_items)
            return items

        # RSSがなければスクレイピング
        scraped = self._try_scrape(url)
        if scraped:
            for item in scraped:
                item["source"] = name
            items.extend(scraped)

        return items

    def _try_rss(self, url: str) -> list[dict]:
        """RSSフィードからアイテムを取得する"""
        if feedparser is None:
            return []

        # よくあるRSS URLのパターンを試す
        rss_urls = [url]
        if not url.endswith((".xml", ".rss", "/feed", "/rss")):
            rss_urls.extend([
                f"{url.rstrip('/')}/feed",
                f"{url.rstrip('/')}/rss",
                f"{url.rstrip('/')}/feed.xml",
                f"{url.rstrip('/')}/rss.xml",
                f"{url.rstrip('/')}/atom.xml",
            ])

        for rss_url in rss_urls:
            try:
                feed = feedparser.parse(rss_url)
                if feed.entries:
                    items = []
                    for entry in feed.entries[:20]:
                        items.append({
                            "title": entry.get("title", ""),
                            "url": entry.get("link", ""),
                            "summary": entry.get("summary", "")[:300],
                            "published": entry.get("published", ""),
                            "source": "",
                        })
                    return items
            except Exception:
                continue

        return []

    def _try_scrape(self, url: str) -> list[dict]:
        """Webページをスクレイピングしてアイテムを取得する"""
        if requests is None or BeautifulSoup is None:
            return []

        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            }
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            items = []

            # 記事リンクを探す（一般的なパターン）
            for tag in soup.find_all(["h2", "h3", "article"]):
                link = tag.find("a")
                if link and link.get("href"):
                    title = link.get_text(strip=True)
                    href = link["href"]
                    if not href.startswith("http"):
                        # 相対URLを絶対URLに変換
                        from urllib.parse import urljoin
                        href = urljoin(url, href)
                    if title and len(title) > 5:
                        items.append({
                            "title": title,
                            "url": href,
                            "summary": "",
                            "published": "",
                            "source": "",
                        })

            # 重複除去
            seen = set()
            unique = []
            for item in items:
                if item["title"] not in seen:
                    seen.add(item["title"])
                    unique.append(item)

            return unique[:20]

        except Exception as e:
            logger.debug("スクレイピング失敗 (%s): %s", url, e)
            return []

    def _filter_and_rank(self, items: list[dict]) -> list[dict]:
        """Gemini APIでClaude関連のネタをフィルタリング＆ランク付けする"""
        if not self.client or not items:
            return self._simple_filter(items)

        titles_text = "\n".join(
            f"{i+1}. {item['title']}" for i, item in enumerate(items[:50])
        )

        prompt = f"""以下のニュース記事タイトルのリストから、
Claude AI（Anthropic）に関連するものだけを抽出し、
ブログ記事のネタとしての価値をスコアリングしてください。

【記事タイトルリスト】
{titles_text}

【評価基準】
- Claude AI、Anthropicに直接関連する記事: スコア80-100
- AIチャットボット全般で、Claude にも関連する記事: スコア60-79
- 間接的にAI業界に関連する記事: スコア40-59
- 関連性が低い記事: 除外

【カテゴリ候補】
{', '.join(self.config.TARGET_CATEGORIES)}

以下のJSON配列形式のみで回答してください（説明不要）:
```json
[
  {{"index": 1, "score": 95, "category": "Claude 最新ニュース", "blog_title_suggestion": "ブログ記事タイトル案", "keyword": "SEOキーワード"}}
]
```
スコア40未満の記事は含めないでください。"""

        try:
            response = self.client.models.generate_content(
                model=self.config.GEMINI_MODEL, contents=prompt
            )
            response_text = response.text.strip()

            # JSONを抽出
            if "```" in response_text:
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()

            ranked = json.loads(response_text)

            # 元のアイテムとマージ
            result = []
            for r in ranked:
                idx = r.get("index", 0) - 1
                if 0 <= idx < len(items):
                    item = items[idx].copy()
                    item["score"] = r.get("score", 50)
                    item["category"] = r.get("category", "Claude 最新ニュース")
                    item["blog_title"] = r.get("blog_title_suggestion", item["title"])
                    item["keyword"] = r.get("keyword", "")
                    result.append(item)

            # スコア順にソート
            result.sort(key=lambda x: x.get("score", 0), reverse=True)
            return result

        except Exception as e:
            logger.warning("AIフィルタリング失敗: %s", e)
            return self._simple_filter(items)

    def _simple_filter(self, items: list[dict]) -> list[dict]:
        """簡易キーワードベースのフィルタリング"""
        keywords = [
            "claude", "anthropic", "クロード", "アンソロピック",
            "claude code", "claude pro", "claude max",
        ]
        result = []
        for item in items:
            title_lower = item.get("title", "").lower()
            summary_lower = item.get("summary", "").lower()
            text = title_lower + " " + summary_lower

            for kw in keywords:
                if kw in text:
                    item["score"] = 70
                    item["category"] = "Claude 最新ニュース"
                    item["blog_title"] = item["title"]
                    item["keyword"] = kw
                    result.append(item)
                    break

        return result

    def _save_topics(self, topics: list[dict]):
        """トピックをJSONファイルに保存する"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = self.topics_dir / f"collected_{timestamp}.json"

        save_data = {
            "collected_at": datetime.now().isoformat(),
            "total_count": len(topics),
            "topics": topics,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)

        logger.info("トピックを保存: %s (%d件)", filepath, len(topics))
        return filepath

    def load_seed_topics(self) -> dict:
        """初期シードトピックを読み込む"""
        seed_path = Path(self.config.BASE_DIR) / "topics.json"
        if seed_path.exists():
            with open(seed_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def get_next_topic(self) -> dict | None:
        """次に記事にすべきトピックを取得する（スコア順）"""
        # まず収集済みトピックから探す
        topic_files = sorted(self.topics_dir.glob("collected_*.json"), reverse=True)
        for tf in topic_files[:3]:
            try:
                with open(tf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                topics = data.get("topics", [])
                if topics:
                    return topics[0]
            except (json.JSONDecodeError, IOError):
                continue

        # なければシードトピックから
        seed = self.load_seed_topics()
        if seed:
            best = None
            best_score = 0
            for category, items in seed.items():
                for item in items:
                    score = item.get("score", 0)
                    if score > best_score:
                        best_score = score
                        best = {
                            "title": item.get("title", ""),
                            "keyword": item.get("keyword", ""),
                            "category": category,
                            "score": score,
                        }
            return best

        return None


def main():
    """スタンドアロン実行用"""
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    sys.path.insert(0, str(Path(__file__).parent))
    import config
    import prompts

    collector = TopicCollector(config, prompts)

    print("\n=== Claude AI トピック収集 ===\n")
    topics = collector.collect_all()

    if topics:
        print(f"\n--- 収集結果: {len(topics)} 件 ---")
        for i, t in enumerate(topics[:10], 1):
            print(f"  {i:2d}. [{t.get('score', '-')}] {t.get('title', '不明')}")
            print(f"      カテゴリ: {t.get('category', '-')}")
            print(f"      キーワード: {t.get('keyword', '-')}")
    else:
        print("トピックが見つかりませんでした。シードトピックを使用します。")
        seed = collector.load_seed_topics()
        for cat, items in seed.items():
            print(f"\n  {cat}:")
            for item in items:
                print(f"    - [{item.get('score', '-')}] {item.get('title', '')}")


if __name__ == "__main__":
    main()
