"""Claude AI完全ガイド - プロンプト定義

Claude AI特化ブログ用のプロンプトを一元管理する。
"""

PERSONA = """あなたはClaude AIの日本語エキスパートブロガーです。
Anthropicの最新動向を常に追い、Claude Pro/Max/Team/Enterprise全プランを
実際に使い込んでいるパワーユーザーです。

【文体ルール】
- 「です・ます」調で親しみやすく
- 専門用語には必ず（）で簡単な説明を添える
- 具体的な操作手順はステップ形式で記載
- スクリーンショットの代わりに詳細なUI説明を入れる
- 比較記事では必ず表形式を使用
- 記事の最初に「この記事でわかること」を箇条書きで提示

【SEOルール】
- タイトルにメインキーワードを必ず含める
- H2/H3見出しにもキーワードを自然に含める
- 冒頭150文字以内にメインキーワードを入れる
- 「結論から言うと」のパターンで冒頭にまとめを置く
- 内部リンク用のアンカーテキストを自然に含める
"""

ARTICLE_FORMAT = """
## この記事でわかること
（3-5個の箇条書き）

## 結論から言うと
（忙しい人向けの3行まとめ）

## {topic}とは？
（初心者向けの基礎解説）

## {topic}の使い方・手順
（ステップバイステップ）

## 実際に使ってみた感想・レビュー
（具体的なユースケース）

## 料金・コスパ分析
（プラン比較表があれば）

## ChatGPT・Geminiとの違い
（比較表形式）

## よくある質問（FAQ）
（Q&A形式 -- FAQスキーマ対応）

## まとめ
"""

CATEGORY_PROMPTS = {
    "Claude 使い方": (
        "初心者から中級者向けの操作ガイド。スクリーンショット的な説明を詳しく。"
        "「Claude 使い方」「Claude やり方」をキーワードに。"
    ),
    "Claude 料金・プラン": (
        "Free/Pro/Max/Team/Enterpriseの比較表を必ず含める。"
        "「Claude 料金」「Claude 無料」「Claude Pro 価格」をキーワードに。"
    ),
    "Claude Code": (
        "開発者向け。インストール手順、コマンド一覧、実践例。"
        "「Claude Code 使い方」「Claude Code インストール」をキーワードに。"
    ),
    "Claude vs ChatGPT": (
        "機能比較表、価格比較、得意分野の違い。"
        "「Claude ChatGPT 比較」「Claude ChatGPT どっち」をキーワードに。"
    ),
    "Claude API・開発": (
        "APIキー取得、SDK使い方、コード例。"
        "「Claude API 使い方」「Anthropic API」をキーワードに。"
    ),
    "Claude 最新ニュース": (
        "Anthropicの公式発表、新機能リリース情報。速報性重視。"
    ),
    "Claude プロンプト術": (
        "効果的なプロンプトの書き方、テンプレート集。"
        "「Claude プロンプト」「Claude 指示の出し方」をキーワードに。"
    ),
    "Claude 活用事例": (
        "ビジネス/学習/プログラミング等の実用例。"
        "「Claude 活用」「Claude 仕事」をキーワードに。"
    ),
}

KEYWORD_PROMPT_EXTRA = """
Claude AI に関連する日本語キーワードを提案してください。
特に以下のパターンを重視:
- 「Claude 使い方」「Claude 始め方」系（初心者向け）
- 「Claude vs ○○」「Claude ○○ 比較」系（比較検索）
- 「Claude ○○ できない」「Claude ○○ エラー」系（トラブルシューティング）
- 「Claude 料金」「Claude 無料」系（価格関連）
- 「Claude Code」「Claude API」系（開発者向け）
- 「Claude 最新」「Claude アップデート」系（ニュース系）
月間検索ボリュームが高いと推測されるキーワードを優先してください。
"""

AFFILIATE_SECTION_TITLE = "## Claudeをもっと活用するためのリソース"
AFFILIATE_INSERT_BEFORE = "## まとめ"

# トピック自動収集用ソース
NEWS_SOURCES = {
    "Anthropic公式": "https://www.anthropic.com/news",
    "Anthropic Research": "https://www.anthropic.com/research",
    "Claude Changelog": "https://docs.anthropic.com/en/docs/about-claude/changelog",
    "The Verge AI": "https://www.theverge.com/ai-artificial-intelligence",
    "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/",
    "AI News JP": "https://ainow.ai/",
}

# FAQ用のスキーマテンプレート（SEO対策）
FAQ_SCHEMA_ENABLED = True


def build_keyword_prompt(config):
    """キーワード選定プロンプトを構築する"""
    categories_text = "\n".join(f"- {cat}" for cat in config.TARGET_CATEGORIES)
    return (
        "Claude AI完全ガイド用のキーワードを選定してください。\n\n"
        "以下のカテゴリから1つ選び、そのカテゴリで今注目されている"
        "Claude AI関連のトピック・キーワードを1つ提案してください。\n\n"
        f"カテゴリ一覧:\n{categories_text}\n\n"
        f"{KEYWORD_PROMPT_EXTRA}\n\n"
        "以下の形式でJSON形式のみで回答してください（説明不要）:\n"
        '{"category": "カテゴリ名", "keyword": "キーワード"}'
    )


def build_article_prompt(keyword, category, config):
    """Claude AI特化の記事生成プロンプトを構築する"""
    category_hint = CATEGORY_PROMPTS.get(category, "")

    return f"""{PERSONA}

以下のキーワードに関する高品質なブログ記事を生成してください。

【基本条件】
- ブログ名: {config.BLOG_NAME}
- キーワード: {keyword}
- カテゴリ: {category}
- 言語: 日本語
- 文字数: {config.MAX_ARTICLE_LENGTH}文字程度（じっくり読める長さ）

【カテゴリ固有の指示】
{category_hint}

【記事フォーマット】
{ARTICLE_FORMAT}

【SEO要件】
1. タイトルにキーワード「{keyword}」を必ず含めること
2. タイトルは32文字以内で魅力的に
3. H2、H3の見出し構造を適切に使用すること
4. キーワード密度は{config.MIN_KEYWORD_DENSITY}%〜{config.MAX_KEYWORD_DENSITY}%を目安に
5. メタディスクリプションは{config.META_DESCRIPTION_LENGTH}文字以内
6. FAQセクション（よくある質問）を必ず含めること

【条件】
- {config.MAX_ARTICLE_LENGTH}文字程度
- 専門用語には必ず簡単な補足説明を付ける
- 具体的な数字やデータを含める
- 比較表がある場合はMarkdownテーブルで記載
- 内部リンクのプレースホルダーを2〜3箇所に配置（{{{{internal_link:関連トピック}}}}の形式）
- FAQセクションはQ&A形式で3〜5個

【出力形式】
以下のJSON形式で出力してください。JSONブロック以外のテキストは出力しないでください。

```json
{{
  "title": "SEO最適化されたタイトル",
  "content": "# タイトル\\n\\n本文（Markdown形式）...",
  "meta_description": "120文字以内のメタディスクリプション",
  "tags": ["タグ1", "タグ2", "タグ3", "タグ4", "タグ5"],
  "slug": "url-friendly-slug",
  "faq": [
    {{"question": "質問1", "answer": "回答1"}},
    {{"question": "質問2", "answer": "回答2"}}
  ]
}}
```

【注意事項】
- content内のMarkdownは適切にエスケープしてJSON文字列として有効にすること
- tagsは5個ちょうど生成すること
- slugは半角英数字とハイフンのみ使用すること
- faqは3〜5個生成すること
- 読者にとって実用的で具体的な内容を心がけること"""
