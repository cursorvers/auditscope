# 🏥 AuditScope - Medical AI Paper Digest

臨床医向けのPubMed論文自動要約システム。毎朝7時にAI関連医学論文の要約をメール配信します。

医療AIガバナンスの7軸（引用・幻覚防止・再現性・免責・撤回チェック・利益相反・監査ログ）を組み込んだ、信頼性の高い情報提供を実現します。

## 📋 デモ（メール構成例）

```
件名: Medical AI Digest - 2024/12/28 (9件)

🏥 Medical AI Daily Digest
2024年12月28日 | 9件の新着論文

📋 今日のTL;DR
• Deployment: Large Language Models in Clinical Decision Support...
• Use Cases: AI-Powered Triage Systems in Emergency Medicine...  
• Safety: Addressing Algorithmic Bias in Diagnostic AI...

🚀 Deployment
[論文カード1] タイトル + 要約 + ガバナンスバッジ + PubMedリンク

🔬 Use Cases  
[論文カード2-4] ...

🛡️ Safety & Ethics
[論文カード5-9] ...

免責事項: この要約は医療従事者への情報提供を目的とし...
```

## ⚡ Setup - 10分で動かす

### 1. このテンプレートを使用
GitHub で「Use this template」→ 新しいリポジトリを作成

### 2. Google AI Studio API キー取得
1. [Google AI Studio](https://aistudio.google.com/) にアクセス
2. 「Get API key」→ 新しいプロジェクトでキー作成
3. キーをコピー（後でSecretsに設定）

### 3. Gmail アプリパスワード生成
1. Googleアカウント設定 → セキュリティ → 2段階認証 有効化
2. アプリパスワード生成 → 「その他」を選択
3. 生成されたパスワードをコピー

### 4. GitHub Secrets 設定
リポジトリ設定 → Secrets and variables → Actions → New repository secret

```
GEMINI_API_KEY: (Step 2のAPIキー)
GMAIL_ADDRESS: your.email@gmail.com  
GMAIL_APP_PASSWORD: (Step 3のアプリパスワード)
```

### 5. config.yaml 編集
配信先メールアドレスを変更:

```yaml
delivery:
  recipient: "your.email@example.com"  # ここを変更
```

### 6. テスト実行
Actions タブ → 「Daily Medical Paper Digest」→ 「Run workflow」

## 🎯 カスタマイズ

### PubMed 検索クエリ変更
`config.yaml` の `query_clusters` を編集:

```yaml
pubmed:
  query_clusters:
    deployment: '("clinical decision support"[MeSH] OR "AI implementation")'
    # 専門領域に応じてクエリを調整
```

### ガバナンス軸の ON/OFF
不要な機能を無効化:

```yaml
governance:
  per_sentence_citation: false  # 引用を無効化
  retraction_filter: false     # 撤回チェックを無効化
```

### 配信時刻変更
`.github/workflows/daily-digest.yml` の cron を編集:

```yaml
schedule:
  - cron: "0 23 * * *"  # UTC 23:00 = JST 08:00
```

## 📊 監査ログ

`logs/audit/YYYY-MM-DD.json` にSHA256ハッシュチェーンで処理履歴を記録:

```json
{
  "date": "2024-12-28",
  "prev_hash": "a1b2c3...",
  "entries": [...],
  "current_hash": "d4e5f6..."
}
```

チェーン整合性により、処理内容の改ざん検知が可能です。

## 🔧 トラブルシューティング

### Gmail が届かない
- Gmail アプリパスワードが正しいか確認
- スパムフォルダを確認  
- 2段階認証が有効になっているか確認

### API クォータエラー
- Gemini API の利用制限を確認
- `config.yaml` の `max_per_cluster` を削減

### Retraction CSV 404エラー
```yaml
governance:
  retraction_filter: false  # 一時的に無効化
```

### ワークフローが失敗する
- Actions タブのログを確認
- 自動的に Issue が作成されます

## ⚖️ 免責・ライセンス

### MIT ライセンス
Copyright 2026 cursorvers

### 医療免責
- 本システムは医師法上の医療行為を構成しません
- 診断・治療の推奨を行うものではありません  
- 臨床判断は必ず原著論文・ガイドラインを参照してください
- システムの出力内容について一切の責任を負いません

## 🏗️ Governance 設計の背景

医療AI導入における信頼性・透明性・説明責任を担保するため、以下7軸のガバナンスフレームワークを採用:

1. **文章単位引用**: 情報の出典明確化
2. **幻覚防止**: AI の推測・補完を排除
3. **再現性担保**: 研究の検証可能性確保
4. **免責の明文化**: 責任範囲の明確化
5. **撤回論文への対応**: 科学的信頼性の維持
6. **利益相反の開示**: 透明性の確保
7. **監査証跡**: 処理履歴の検証可能性

詳細な設計思想: [https://cursorvers.jp/tools/auditscope/](https://cursorvers.jp/tools/auditscope/)

---

**🚀 今すぐ始める**: 「Use this template」→ Secrets 設定 → config.yaml 編集 → Run workflow