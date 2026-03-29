"""Claude AI完全ガイド - キーワードリサーチモジュール（スタンドアロン版）

blog_engineの共通モジュールを使用し、フォールバックとしてローカル実装を持つ。
"""
import sys
from pathlib import Path

_engine_path = str(Path(__file__).parent.parent)
if _engine_path not in sys.path:
    sys.path.insert(0, _engine_path)

try:
    from blog_engine.keyword_researcher import KeywordResearcher
except ImportError:
    import json
    import logging
    from datetime import datetime, timedelta

    from google import genai

    logger = logging.getLogger(__name__)

    class KeywordResearcher:
        """キーワードリサーチャー（スタンドアロン版）"""

        def __init__(self, config, prompts=None):
            self.config = config
            self.prompts = prompts
            self.client = genai.Client(api_key=config.GEMINI_API_KEY)
            self.model_name = config.GEMINI_MODEL

        def _call_ai(self, prompt: str, max_tokens: int = 2000) -> str:
            response = self.client.models.generate_content(
                model=self.model_name, contents=prompt
            )
            return response.text.strip()

        def _parse_json_response(self, response_text: str):
            text = response_text.strip()
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            return json.loads(text)

        def _get_extra_prompt(self) -> str:
            if self.prompts and hasattr(self.prompts, "KEYWORD_PROMPT_EXTRA"):
                return self.prompts.KEYWORD_PROMPT_EXTRA
            return ""

        def research_trending_keywords(self, category: str, count: int = 10) -> list[dict]:
            extra = self._get_extra_prompt()
            prompt = (
                f"「{self.config.BLOG_NAME}」の「{category}」カテゴリで、"
                f"トレンドキーワードを{count}個提案してください。\n\n"
                f"{extra}\n\n"
                "JSON配列形式のみで回答:\n"
                '[{"keyword": "...", "volume": "高/中/低", "competition": "高/中/低", "article_type": "..."}]'
            )
            response = self._call_ai(prompt)
            return self._parse_json_response(response)

        def suggest_long_tail_keywords(self, base_keyword: str) -> list[str]:
            prompt = (
                f"「{base_keyword}」のロングテールキーワードを10個提案してください。\n\n"
                'JSON配列形式のみで回答: ["kw1", "kw2", ...]'
            )
            response = self._call_ai(prompt)
            return self._parse_json_response(response)

        def analyze_competition(self, keyword: str) -> dict:
            prompt = (
                f"「{keyword}」の競合分析をJSON形式で回答:\n"
                '{"keyword": "...", "difficulty": 1-10, "top_content_types": [...], '
                '"recommended_word_count": 数値, "key_topics": [...], "differentiation_tips": [...]}'
            )
            response = self._call_ai(prompt)
            return self._parse_json_response(response)

        def get_content_calendar(self, days: int = 7) -> list[dict]:
            start = datetime.now()
            dates = [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]
            cats = "\n".join(f"- {c}" for c in self.config.TARGET_CATEGORIES)
            extra = self._get_extra_prompt()
            prompt = (
                f"「{self.config.BLOG_NAME}」のコンテンツカレンダーを作成:\n\n"
                f"{extra}\n\n日付: {', '.join(dates)}\nカテゴリ:\n{cats}\n\n"
                'JSON配列形式のみ: [{"date": "YYYY-MM-DD", "keyword": "...", "category": "...", "article_type": "..."}]'
            )
            response = self._call_ai(prompt, max_tokens=3000)
            return self._parse_json_response(response)
