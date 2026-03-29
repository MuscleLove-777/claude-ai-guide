#!/usr/bin/env python3
"""Claude AI完全ガイド - CLIエントリポイント

使い方:
    python main.py generate --keyword "Claude 使い方" --category "Claude 使い方"
    python main.py topics
    python main.py schedule
    python main.py build
    python main.py keywords --category "Claude Code"
    python main.py calendar --days 7
    python main.py deploy
    python main.py dashboard
"""
import argparse
import json
import logging
import sys
from pathlib import Path

# blog_engine へのフォールバックimport パス
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

import config
import prompts


def ensure_dirs():
    """必要なディレクトリを確保する"""
    if not hasattr(config, "OUTPUT_DIR"):
        config.OUTPUT_DIR = config.BASE_DIR / "output"
    if not hasattr(config, "ARTICLES_DIR"):
        config.ARTICLES_DIR = config.OUTPUT_DIR / "articles"
    if not hasattr(config, "SITE_DIR"):
        config.SITE_DIR = config.OUTPUT_DIR / "site"
    if not hasattr(config, "TOPICS_DIR"):
        config.TOPICS_DIR = config.OUTPUT_DIR / "topics"

    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    config.ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    config.SITE_DIR.mkdir(parents=True, exist_ok=True)
    config.TOPICS_DIR.mkdir(parents=True, exist_ok=True)


def cmd_generate(args):
    """単発で記事を生成する"""
    from article_generator import ArticleGenerator
    from seo_optimizer import SEOOptimizer
    from affiliate import AffiliateManager

    print(f"\n記事を生成します...")
    print(f"  キーワード: {args.keyword}")
    print(f"  カテゴリ: {args.category}\n")

    generator = ArticleGenerator(config, prompts)
    article = generator.generate_article(keyword=args.keyword, category=args.category, prompts=prompts)

    # アフィリエイト挿入
    try:
        aff = AffiliateManager(config, prompts)
        article = aff.insert_affiliate_links(article)
        print(f"  アフィリエイト: {article.get('affiliate_count', 0)}件挿入")
    except Exception as e:
        logger.warning("アフィリエイト挿入スキップ: %s", e)

    # SEOチェック
    optimizer = SEOOptimizer(config)
    seo_result = optimizer.check_seo_score(article)

    print(f"記事生成完了!")
    print(f"  タイトル: {article.get('title', '不明')}")
    print(f"  保存先: {article.get('file_path', '不明')}")
    print(f"  SEOスコア: {seo_result.get('total_score', '不明')}/100")
    print(f"  SEOグレード: {seo_result.get('grade', '不明')}\n")


def cmd_topics(args):
    """トピックを収集する"""
    from topic_collector import TopicCollector

    print("\nトピック収集を開始します...\n")
    collector = TopicCollector(config, prompts)
    topics = collector.collect_all()

    if topics:
        print(f"\n--- 収集結果: {len(topics)} 件 ---")
        for i, t in enumerate(topics[:15], 1):
            print(f"  {i:2d}. [{t.get('score', '-')}] {t.get('blog_title', t.get('title', '不明'))}")
            print(f"      カテゴリ: {t.get('category', '-')} | キーワード: {t.get('keyword', '-')}")
    else:
        print("新規トピックなし。シードトピックを使用します。")
        seed = collector.load_seed_topics()
        for cat, items in seed.items():
            print(f"\n  {cat}:")
            for item in items:
                print(f"    - [{item.get('score', '-')}] {item.get('title', '')}")
    print()


def cmd_schedule(args):
    """スケジューラーを起動する"""
    from scheduler import BlogScheduler

    print(f"\nスケジューラーを起動します")
    print(f"  投稿時刻: {config.SCHEDULE_HOURS}")
    print(f"  1日の記事数: {config.ARTICLES_PER_DAY}")
    print("  停止: Ctrl+C\n")

    scheduler = BlogScheduler(config, prompts)
    scheduler.start()


def cmd_build(args):
    """サイトをビルドする"""
    from site_generator import SiteGenerator

    print("\nサイトをビルドします...")
    gen = SiteGenerator(config)
    gen.build_site()
    print("サイトビルド完了!\n")


def cmd_keywords(args):
    """キーワードリサーチを実行する"""
    from keyword_researcher import KeywordResearcher

    print(f"\nキーワードリサーチ: {args.category} ({args.count}件)\n")

    researcher = KeywordResearcher(config, prompts)

    print("--- トレンドキーワード ---")
    keywords = researcher.research_trending_keywords(args.category, count=args.count)
    for i, kw in enumerate(keywords, 1):
        print(f"  {i:2d}. {kw['keyword']}  [Vol: {kw.get('volume', '-')} | 競合: {kw.get('competition', '-')}]")
    print()

    if keywords:
        base = keywords[0]["keyword"]
        print(f"--- ロングテール ({base}) ---")
        for i, lt in enumerate(researcher.suggest_long_tail_keywords(base), 1):
            print(f"  {i:2d}. {lt}")
        print()


def cmd_calendar(args):
    """コンテンツカレンダーを生成する"""
    from keyword_researcher import KeywordResearcher

    print(f"\nコンテンツカレンダー ({args.days}日分)\n")
    researcher = KeywordResearcher(config, prompts)
    calendar = researcher.get_content_calendar(days=args.days)

    print(f"{'日付':<14} {'カテゴリ':<20} {'キーワード':<30} {'タイプ'}")
    print("-" * 80)
    for entry in calendar:
        print(
            f"{entry.get('date', '-'):<14} "
            f"{entry.get('category', '-'):<20} "
            f"{entry.get('keyword', '-'):<30} "
            f"{entry.get('article_type', '-')}"
        )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(calendar, f, ensure_ascii=False, indent=2)
        print(f"\n保存: {args.output}")
    print()


def cmd_deploy(args):
    """GitHub Pagesにデプロイする"""
    from deployer import GitHubPagesDeployer

    print("\nGitHub Pagesにデプロイします...")
    deployer = GitHubPagesDeployer(config)

    status = deployer.check_status()
    print(f"  リポジトリ: {status['repo']}")
    print(f"  URL: {status['url']}\n")

    result = deployer.deploy()
    print(f"  結果: {result['status']}")
    print(f"  メッセージ: {result['message']}")
    if "url" in result:
        print(f"  URL: {result['url']}")
    print()


def cmd_dashboard(args):
    """ダッシュボードを起動する"""
    import uvicorn
    from dashboard import create_app

    host = config.DASHBOARD_HOST
    port = config.DASHBOARD_PORT

    print(f"\nダッシュボード起動: http://{host}:{port}")
    print("  停止: Ctrl+C\n")

    app = create_app(config, prompts)
    uvicorn.run(app, host=host, port=port)


def main():
    parser = argparse.ArgumentParser(
        description="Claude AI完全ガイド - ブログ管理CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="実行コマンド")

    # generate
    p_gen = subparsers.add_parser("generate", help="単発で記事を生成")
    p_gen.add_argument("--keyword", required=True, help="ターゲットキーワード")
    p_gen.add_argument("--category", required=True, help="カテゴリ")

    # topics
    subparsers.add_parser("topics", help="トピック収集")

    # schedule
    subparsers.add_parser("schedule", help="スケジューラー起動")

    # build
    subparsers.add_parser("build", help="サイトビルド")

    # keywords
    p_kw = subparsers.add_parser("keywords", help="キーワードリサーチ")
    p_kw.add_argument("--category", required=True, help="対象カテゴリ")
    p_kw.add_argument("--count", type=int, default=10, help="取得件数")

    # calendar
    p_cal = subparsers.add_parser("calendar", help="コンテンツカレンダー生成")
    p_cal.add_argument("--days", type=int, default=7, help="日数")
    p_cal.add_argument("--output", help="JSON保存パス")

    # deploy
    subparsers.add_parser("deploy", help="GitHub Pagesデプロイ")

    # dashboard
    subparsers.add_parser("dashboard", help="管理ダッシュボード起動")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    ensure_dirs()

    commands = {
        "generate": cmd_generate,
        "topics": cmd_topics,
        "schedule": cmd_schedule,
        "build": cmd_build,
        "keywords": cmd_keywords,
        "calendar": cmd_calendar,
        "deploy": cmd_deploy,
        "dashboard": cmd_dashboard,
    }

    handler = commands.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
