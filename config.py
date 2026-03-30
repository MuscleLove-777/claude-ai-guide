"""Claude AI完全ガイド - ブログ固有設定"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

# SEO最適化ブログ名 -- 検索意図に直結
BLOG_NAME = "Claude AI完全ガイド"
BLOG_DESCRIPTION = (
    "Anthropic Claude AIの使い方・最新情報・料金比較・活用術を毎日更新。"
    "Claude Pro/Max/Code/Computer Useの実践テクニックを初心者にもわかりやすく解説。"
)
BLOG_URL = "https://musclelove-777.github.io/claude-ai-guide"
BLOG_TAGLINE = "Claude AIを使いこなすための日本語情報サイト"
BLOG_LANGUAGE = "ja"

GITHUB_REPO = "MuscleLove-777/claude-ai-guide"
GITHUB_BRANCH = "gh-pages"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

OUTPUT_DIR = BASE_DIR / "output"
ARTICLES_DIR = OUTPUT_DIR / "articles"
SITE_DIR = OUTPUT_DIR / "site"
TOPICS_DIR = OUTPUT_DIR / "topics"

# SEO特化カテゴリ -- 検索ボリュームの高いキーワードを含める
TARGET_CATEGORIES = [
    "Claude 使い方",
    "Claude 料金・プラン",
    "Claude Code",
    "Claude vs ChatGPT",
    "Claude API・開発",
    "Claude 最新ニュース",
    "Claude プロンプト術",
    "Claude 活用事例",
]

# テーマカラー（Anthropicブランド: コーラル x ダークブルー）
THEME = {
    "primary": "#d97757",       # Anthropicコーラル
    "accent": "#1a1a2e",        # ディープネイビー
    "gradient_start": "#d97757",
    "gradient_end": "#b85c3f",
    "dark_bg": "#0f0f1a",
    "dark_surface": "#1a1a2e",
    "light_bg": "#fdf8f6",      # 暖かいオフホワイト
    "light_surface": "#ffffff",
}

MAX_ARTICLE_LENGTH = 4000  # 長めの記事でSEO有利
ARTICLES_PER_DAY = 2
SCHEDULE_HOURS = [8, 19]

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"

# SEO設定
ENABLE_SEO_OPTIMIZATION = True
MIN_SEO_SCORE = 75  # 高めに設定
MIN_KEYWORD_DENSITY = 1.0
MAX_KEYWORD_DENSITY = 3.0
META_DESCRIPTION_LENGTH = 120
ENABLE_INTERNAL_LINKS = True

# アフィリエイト
AFFILIATE_LINKS = {
    "Claude Pro": {
        "url": "https://claude.ai/upgrade",
        "text": "Claude Proプランに登録する",
        "description": "月額$20でClaude最新モデルが使い放題",
    },
    "Claude Max": {
        "url": "https://claude.ai/upgrade",
        "text": "Claude Maxプランに登録する",
        "description": "ヘビーユーザー向けの上位プラン",
    },
    "Anthropic API": {
        "url": "https://console.anthropic.com",
        "text": "Anthropic APIコンソール",
        "description": "開発者向けAPI利用はこちら",
    },
    "Udemy AI講座": {
        "url": "https://www.udemy.com",
        "text": "UdemyでAI活用講座を探す",
        "description": "AI活用スキルを動画で学ぶ",
    },
    "Amazon AI書籍": {
        "url": "https://www.amazon.co.jp",
        "text": "AmazonでAI関連書籍を探す",
        "description": "AI・Claude関連の書籍",
    },
    "楽天 AI書籍": {
        "url": "https://www.rakuten.co.jp",
        "text": "楽天でAI関連書籍を探す",
        "description": "AI・Claude関連の書籍",
    },
}
AFFILIATE_TAG = "musclelove07-22"

ADSENSE_CLIENT_ID = os.environ.get("ADSENSE_CLIENT_ID", "")
ADSENSE_ENABLED = bool(ADSENSE_CLIENT_ID)

DASHBOARD_HOST = "127.0.0.1"
DASHBOARD_PORT = 8083

# Google Analytics (GA4)
GOOGLE_ANALYTICS_ID = "G-CSFVD34MKK"

# Google Search Console 認証ファイル
SITE_VERIFICATION_FILES = {
    "googlea31edabcec879415.html": "google-site-verification: googlea31edabcec879415.html",
}
