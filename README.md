# AuditScope v2 — うちで使って大丈夫？

[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> 臨床医の自問をそのまま検査項目に変換する、医療AI論文ガバナンス監視 OSS テンプレート。

毎日届く医療AI論文を、7軸のガバナンス視点で自動評価し、Word レポートとして受け取れます。fork して自分の専門領域に config を合わせるだけで、自分専用のエビデンス監査パイプラインになります。あなたの臨床現場で「この AI システム、うちで使って大丈夫？」という問いを、継続的に検証し続けるためのツールです。

## ⚠️ Breaking Change: v1からの非互換

> **重要**: v1 "Daily Digest" ユーザーは直接アップグレードしないでください

v1をお使いの方は `legacy/v1` ブランチまたは `v1.0.0` タグを参照し、移行については [MIGRATION.md](MIGRATION.md) をご確認ください。

| 変更項目 | v1 (legacy) | v2 (current) |
|----------|-------------|--------------|
| 出力形式 | HTML メール | Word 添付ファイル |
| 設定方法 | ハードコード | setup.py で対話設定 |
| パイプライン | 単段階評価 | 2段階ガバナンス評価 |
| 対象ユーザー | 単一ダイジェスト | Fork & 個別カスタマイズ |

## Why AuditScope? — うちで使って大丈夫？

**うちの患者層で使える？** → 相当論文と除外基準を毎日自動チェック。専門領域に特化した query templates で関連文献を継続監視し、あなたの診療科の患者特性に適用可能性を評価します。

**監査どうする？** → 7軸マトリクス + JSONL audit log で完全な証跡管理。各論文を citation・hallucination・reproducibility の観点から数値化し、監査対応可能な記録を自動生成します。

**外したとき誰が責任？** → retraction/COI/disclaimer の自動チェックで責任範囲を明確化。撤回DB突合、利益相反開示状況、免責文の適切性を事前に検証し、臨床判断の根拠を客観視します。

## 7軸ガバナンス評価フレームワーク

- **per_sentence_citation** — 主張に引用があるか（情報源の追跡可能性）
- **hallucination** — 事実と乖離した合成がないか（AI生成内容の信頼性）
- **reproducibility** — コード/データ/プロンプト/重み開示（再現検証可能性）
- **disclaimer** — 臨床使用上の注意明記（責任範囲の明確化）
- **retraction** — 撤回DB/懸念表明チェック（学術的信頼性）
- **COI** — 資金/著者 COI 開示（透明性・公正性）
- **audit_hash** — 監査証跡/バージョニング（処理履歴の検証可能性）

各論文は各軸で `low / medium / high / n/a` の4段階評価を受け、最高リスク軸が全体リスク等級となります。

## Architecture

```
PubMed (BioPython Entrez)
        │
        ▼
  paper_filter ─── retraction DB / study-type score
        │
        ▼
  ai_summarizer ─── Gemini 2.0 flash / 2-stage 7-axis
        │
        ▼
  word_generator ─── python-docx (CJK Yu Gothic)
        │
        ▼
  send_gmail ─── SMTP app password
        │
        ▼
  logs/audit.jsonl ─── v2 schema (run_id + sha256 hashes)
```

## Quickstart — Fork & 自分専用パイプライン構築

1. **Fork**: https://github.com/masa-stage1/auditscope を fork します
2. **依存関係インストール**: `pip install -r requirements.txt`
3. **環境設定**: `.env.example` を `.env` にコピーし、以下を設定
   - `GEMINI_API_KEY` (Google AI Studio から取得)
   - `GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD` (Gmail 2段階認証 + アプリパスワード)
   - `NCBI_API_KEY` (オプション、PubMed API レート制限回避)
4. **設定生成**: `python setup.py` — Gemini があなたの専門領域・関心事項をインタビューし、最適な `config.yaml` を自動生成します
5. **ローカルテスト**: `python main.py --dry-run` でパイプライン動作確認
6. **本格運用**: GitHub に push すると、毎日 07:00 JST に GitHub Actions が自動実行されます

## Configuration — config.yaml 設定ガイド

### 主要設定ブロック

- **tier1/2/3 journals**: ジャーナル階層による信頼度評価
- **primary_specialties**: あなたの専門領域キーワード
- **query_templates**: 4クラスター検索 (tier1_clinical, deployment, use_case, safety)
- **governance_keywords**: ガバナンス関連語句の監視対象
- **governance_axes**: 7軸の有効/無効設定
- **date_window_hours**: 検索対象期間 (24時間 = 毎日実行想定)
- **screening_threshold**: 2段階評価での詳細分析閾値

### query_templates 例

```yaml
query_templates:
  safety: "(validation OR bias OR hallucination OR \"model drift\" OR \"automation bias\")"
```

**重要**: MeSH terms は使用しません。実際の論文で使われる語句のみを記載してください。

## GuideScope Integration — 医療AI規制クロスウォーク

AuditScope の 7軸は、GuideScope medical-corpus の PMDA/FDA/EU AI Act ガバナンス列にマッピング可能です。

### 推奨マッピング表

| AuditScope axis        | GuideScope column      |
|------------------------|------------------------|
| per_sentence_citation  | C (透明性)             |
| hallucination          | C (透明性) + K (臨床評価) |
| reproducibility        | C (透明性) + M (ライフサイクル) |
| disclaimer             | E (Human oversight)    |
| retraction             | G (PCCP市販後)         |
| COI                    | H (責任) + I (同意プライバシー) |
| audit_hash             | D (監査ログ)           |

### 使用方法

`config.yaml` の `crosswalk_refs` セクションを設定すると、Word レポートのフッター部分に該当する規制ガイダンス参照が自動挿入されます。詳細な PMDA/FDA/EU AI Act/ISO/IEC 42001/NIST AI RMF ガイダンス内容は `/Users/masayuki/Dev/guidescope` で提供されています。

GuideScope MCP をインストールしていない場合でも AuditScope は正常動作します。クロスウォーク参照はオプション・助言的機能です。

## 出力サンプル — Word レポート構成

生成される Word 文書の構成:

- **ヘッダーブロック**: 実行日時、検索条件、総論文数
- **リスク要約テーブル**: 7軸別のリスク分布統計
- **論文詳細セクション**: 論文別の7軸評価結果、要約、引用情報
- **フッター**: 監査証跡ハッシュ、GuideScope クロスウォーク参照 (設定時)

サンプル確認: `python main.py --dry-run --sample-output` でテスト文書を生成できます。

## Contributing / License / Attribution

### 貢献方法

Pull Request 歓迎です。コード変更時は `python3 -m py_compile *.py` で構文チェックをお願いします。

### ライセンス

MIT License. 本プロジェクトは `yush02084/medical-paper-summarizer-public` (MIT) の派生作品です。

### 帰属表示

各 .py ファイルおよび LICENSE ファイルに上流プロジェクト帰属を記載しています。配布時は帰属表示を維持してください。

---

> **2024年医療AI論文監視の新標準** — Fork して今すぐ始める: `python setup.py`