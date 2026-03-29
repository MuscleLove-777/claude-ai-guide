#!/usr/bin/env python3
"""Claude AI完全ガイド - GitHub Actions用一括実行スクリプト

キーワード選定 → トピック収集 → 記事生成 → アフィリエイト挿入 → サイトビルド
を一括で実行する。

blog_engine共通モジュールを使用し、フォールバックとしてローカル実装を持つ。
"""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# パス設定
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

import config
import prompts


def run(cfg=None, prm=None):
    """メイン処理: キーワード選定 → 記事生成 → サイトビルド

    Args:
        cfg: ブログ設定モジュール（省略時はローカルconfig使用）
        prm: プロンプトモジュール（省略時はローカルprompts使用）
    """
    cfg = cfg or config
    prm = prm or prompts

    logger.info("=== %s 自動生成開始 ===", cfg.BLOG_NAME)
    start_time = datetime.now()

    # ディレクトリ確保
    for attr in ["OUTPUT_DIR", "ARTICLES_DIR", "SITE_DIR", "TOPICS_DIR"]:
        d = getattr(cfg, attr, None)
        if d:
            Path(d).mkdir(parents=True, exist_ok=True)

    # ステップ0: トピック収集（オプション）
    logger.info("ステップ0: トピック収集")
    try:
        from topic_collector import TopicCollector
        collector = TopicCollector(cfg, prm)
        topics = collector.collect_all()
        next_topic = collector.get_next_topic()
        if next_topic:
            logger.info("次のトピック: %s (スコア: %s)", next_topic.get("title", "?"), next_topic.get("score", "?"))
    except Exception as e:
        logger.warning("トピック収集スキップ: %s", e)
        next_topic = None

    # ステップ1: キーワード選定
    logger.info("ステップ1: キーワード選定")
    try:
        if next_topic and next_topic.get("keyword"):
            # トピックコレクターからキーワードを取得
            category = next_topic.get("category", cfg.TARGET_CATEGORIES[0])
            keyword = next_topic["keyword"]
            logger.info("トピックから選定: カテゴリ=%s, キーワード=%s", category, keyword)
        else:
            # Gemini APIでキーワード選定
            from google import genai

            if not cfg.GEMINI_API_KEY:
                logger.error("GEMINI_API_KEY が設定されていません")
                sys.exit(1)

            client = genai.Client(api_key=cfg.GEMINI_API_KEY)

            if prm and hasattr(prm, "build_keyword_prompt"):
                prompt = prm.build_keyword_prompt(cfg)
            else:
                categories_text = "\n".join(f"- {cat}" for cat in cfg.TARGET_CATEGORIES)
                prompt = (
                    f"{cfg.BLOG_NAME}用のキーワードを選定してください。\n\n"
                    f"カテゴリ一覧:\n{categories_text}\n\n"
                    'JSON形式のみ: {"category": "カテゴリ名", "keyword": "キーワード"}'
                )

            response = client.models.generate_content(model=cfg.GEMINI_MODEL, contents=prompt)
            response_text = response.text.strip()

            if "```" in response_text:
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()

            data = json.loads(response_text)
            # Geminiがリストで返す場合があるので先頭要素を取得
            if isinstance(data, list):
                data = data[0]
            category = data["category"]
            keyword = data["keyword"]

        logger.info("選定結果 - カテゴリ: %s, キーワード: %s", category, keyword)

    except Exception as e:
        logger.error("キーワード選定失敗: %s", e)
        sys.exit(1)

    # ステップ2: 記事生成
    logger.info("ステップ2: 記事生成")
    try:
        from article_generator import ArticleGenerator
        from seo_optimizer import SEOOptimizer

        generator = ArticleGenerator(cfg)
        article = generator.generate_article(keyword=keyword, category=category, prompts=prm)
        logger.info("記事生成完了: %s", article.get("title", "不明"))

        optimizer = SEOOptimizer(cfg)
        seo_result = optimizer.check_seo_score(article)
        logger.info("SEOスコア: %d/100 (グレード: %s)", seo_result.get("total_score", 0), seo_result.get("grade", "?"))

    except Exception as e:
        logger.error("記事生成失敗: %s", e)
        sys.exit(1)

    # ステップ2.5: アフィリエイトリンク挿入
    logger.info("ステップ2.5: アフィリエイトリンク挿入")
    try:
        from affiliate import AffiliateManager
        aff = AffiliateManager(cfg, prm)
        article = aff.insert_affiliate_links(article)
        logger.info("アフィリエイト: %d件挿入", article.get("affiliate_count", 0))
    except Exception as e:
        logger.warning("アフィリエイト挿入スキップ: %s", e)

    # ステップ3: サイトビルド
    logger.info("ステップ3: サイトビルド")
    try:
        from site_generator import SiteGenerator
        site_gen = SiteGenerator(cfg)
        site_gen.build_site()
        logger.info("サイトビルド完了")
    except Exception as e:
        logger.error("サイトビルド失敗: %s", e)
        sys.exit(1)

    # 完了
    duration = (datetime.now() - start_time).total_seconds()
    logger.info("=== 自動生成完了（%.1f秒） ===", duration)
    logger.info("  カテゴリ: %s", category)
    logger.info("  キーワード: %s", keyword)
    logger.info("  タイトル: %s", article.get("title", "不明"))
    logger.info("  SEOスコア: %d/100", seo_result.get("total_score", 0))


if __name__ == "__main__":
    run()
