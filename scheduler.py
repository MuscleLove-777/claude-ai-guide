"""Claude AI完全ガイド - スケジューラー（スタンドアロン版）

blog_engineの共通モジュールを使用し、フォールバックとしてローカル実装を持つ。
"""
import sys
from pathlib import Path

_engine_path = str(Path(__file__).parent.parent)
if _engine_path not in sys.path:
    sys.path.insert(0, _engine_path)

try:
    from blog_engine.scheduler import BlogScheduler
except ImportError:
    import json
    import logging
    from datetime import datetime

    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger

    logger = logging.getLogger(__name__)

    class BlogScheduler:
        """記事の自動生成スケジューラー（スタンドアロン版）"""

        def __init__(self, config, prompts=None):
            self.config = config
            self.prompts = prompts
            self.scheduler = BlockingScheduler()

            from article_generator import ArticleGenerator
            from site_generator import SiteGenerator
            from seo_optimizer import SEOOptimizer

            self.article_generator = ArticleGenerator(config, prompts)
            self.site_generator = SiteGenerator(config)
            self.seo_optimizer = SEOOptimizer(config)

            output_dir = getattr(config, "OUTPUT_DIR", Path(config.BASE_DIR) / "output")
            self.logs_dir = output_dir / "logs"
            self.logs_dir.mkdir(parents=True, exist_ok=True)

        def start(self):
            for hour in self.config.SCHEDULE_HOURS:
                trigger = CronTrigger(hour=hour, minute=0)
                self.scheduler.add_job(
                    self.run_job, trigger=trigger,
                    id=f"blog_job_{hour}",
                    name=f"記事生成ジョブ（{hour}時）",
                    misfire_grace_time=3600,
                )
                logger.info("ジョブ登録: 毎日 %d:00", hour)

            try:
                self.scheduler.start()
            except (KeyboardInterrupt, SystemExit):
                logger.info("スケジューラー停止")

        def run_job(self):
            logger.info("=== ジョブ実行開始 ===")
            start_time = datetime.now()
            result = {"timestamp": start_time.isoformat(), "status": "started", "errors": []}

            try:
                category, keyword = self._select_keyword()
                result["category"] = category
                result["keyword"] = keyword

                article = self.article_generator.generate_article(keyword=keyword, category=category)
                result["article_path"] = str(article.get("file_path", ""))

                try:
                    from affiliate import AffiliateManager
                    aff = AffiliateManager(self.config, self.prompts)
                    article = aff.insert_affiliate_links(article)
                except Exception:
                    pass

                seo = self.seo_optimizer.check_seo_score(article)
                result["seo_score"] = seo.get("total_score", 0)

                self.site_generator.build_site()

                try:
                    from deployer import GitHubPagesDeployer
                    deployer = GitHubPagesDeployer(self.config)
                    deployer.deploy()
                except Exception:
                    pass

                result["status"] = "success"
            except Exception as e:
                result["status"] = "error"
                result["errors"].append(str(e))
                logger.error("ジョブエラー: %s", e)

            result["duration_seconds"] = (datetime.now() - start_time).total_seconds()
            self._log_execution(result)
            return result

        def _select_keyword(self):
            from google import genai
            client = genai.Client(api_key=self.config.GEMINI_API_KEY)
            cats = "\n".join(f"- {c}" for c in self.config.TARGET_CATEGORIES)

            extra = ""
            if self.prompts and hasattr(self.prompts, "KEYWORD_PROMPT_EXTRA"):
                extra = self.prompts.KEYWORD_PROMPT_EXTRA

            prompt = (
                f"「{self.config.BLOG_NAME}」用キーワード選定:\n\n{extra}\n\n"
                f"カテゴリ:\n{cats}\n\n"
                'JSON形式のみ: {"category": "...", "keyword": "..."}'
            )
            resp = client.models.generate_content(model=self.config.GEMINI_MODEL, contents=prompt)
            text = resp.text.strip()
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            data = json.loads(text)
            return data["category"], data["keyword"]

        def _log_execution(self, result):
            today = datetime.now().strftime("%Y%m%d")
            log_file = self.logs_dir / f"{today}.json"
            logs = []
            if log_file.exists():
                with open(log_file, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            logs.append(result)
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
