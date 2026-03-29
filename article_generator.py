"""Claude AI完全ガイド - 記事生成エンジン（スタンドアロン版）

blog_engineの共通モジュールを使用し、フォールバックとしてローカル実装を持つ。
"""
import sys
from pathlib import Path

# blog_engine へのフォールバックimport
_engine_path = str(Path(__file__).parent.parent)
if _engine_path not in sys.path:
    sys.path.insert(0, _engine_path)

try:
    from blog_engine.article_generator import ArticleGenerator
except ImportError:
    # スタンドアロンフォールバック
    import json
    import logging
    import re
    from datetime import datetime

    from google import genai

    logger = logging.getLogger(__name__)

    class ArticleGenerator:
        """Gemini APIを使ったブログ記事生成エンジン（スタンドアロン版）"""

        def __init__(self, config, prompts=None):
            if not config.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY が設定されていません。")

            self.config = config
            self.prompts = prompts
            self.client = genai.Client(api_key=config.GEMINI_API_KEY)
            self.model_name = config.GEMINI_MODEL

            self.articles_dir = Path(config.BASE_DIR) / "output" / "articles"
            self.articles_dir.mkdir(parents=True, exist_ok=True)

        def generate_article(self, keyword: str, category: str, prompts=None) -> dict:
            """キーワードとカテゴリからSEO最適化されたブログ記事を生成する"""
            prompts = prompts or self.prompts

            if prompts and hasattr(prompts, "build_article_prompt"):
                prompt = prompts.build_article_prompt(keyword, category, self.config)
            else:
                prompt = self._build_default_prompt(keyword, category)

            response = self.client.models.generate_content(
                model=self.model_name, contents=prompt
            )
            article = self._parse_response(response.text)
            article["keyword"] = keyword
            article["category"] = category
            article["generated_at"] = datetime.now().isoformat()

            file_path = self._save_article(article)
            article["file_path"] = str(file_path)
            return article

        def _build_default_prompt(self, keyword, category):
            config = self.config
            return f"""あなたはClaude AIのエキスパートブロガーです。
キーワード「{keyword}」、カテゴリ「{category}」で
{config.MAX_ARTICLE_LENGTH}文字程度のSEO最適化された記事を
JSON形式で生成してください。

```json
{{
  "title": "タイトル",
  "content": "本文（Markdown形式）",
  "meta_description": "120文字以内",
  "tags": ["タグ1", "タグ2", "タグ3", "タグ4", "タグ5"],
  "slug": "url-friendly-slug",
  "faq": [{{"question": "Q", "answer": "A"}}]
}}
```"""

        def _parse_response(self, response_text):
            json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
            try:
                if json_match:
                    data = json.loads(json_match.group(1))
                else:
                    cleaned = response_text.strip()
                    start = cleaned.find("{")
                    end = cleaned.rfind("}") + 1
                    if start >= 0 and end > start:
                        cleaned = cleaned[start:end]
                    data = json.loads(cleaned)
            except json.JSONDecodeError as e:
                raise ValueError(f"JSONパース失敗: {e}") from e

            required = ["title", "content", "meta_description", "tags", "slug"]
            missing = [f for f in required if f not in data]
            if missing:
                raise ValueError(f"必須フィールド不足: {missing}")

            if not isinstance(data["tags"], list):
                data["tags"] = [data["tags"]]
            data["slug"] = re.sub(r"[^a-z0-9-]", "", data["slug"].lower().replace(" ", "-"))
            return data

        def _save_article(self, article):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            slug = article.get("slug", "untitled")
            filename = f"{timestamp}_{slug}.json"
            file_path = self.articles_dir / filename

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(article, f, ensure_ascii=False, indent=2)
            return file_path
