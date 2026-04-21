# Migration Guide: AuditScope v1 → v2

AuditScope v2 は元バズ [yush02084/medical-paper-summarizer-public](https://github.com/yush02084/medical-paper-summarizer-public) の **Word 添付 daily digest 形式** を完全 port し、医療AIガバナンス文脈に再定義したメジャーバージョンです。v1 (HTML メール + 7軸 overlay) とは配信形式・config schema・プロンプト設計が大きく異なります。

## TL;DR

- **v1 は `legacy/v1` branch + `v1.0.0` tag で凍結**。fork を壊しません。
- **v2 は master で新規開発**。Word 添付 + summary index + 7軸 governance matrix + 結論/自問チェック の二部構成。
- Breaking change のため、既存 forker は **v1 のまま継続利用可能**。v2 へ移行するかは opt-in。
- v1→v2 の機械的マイグレーションは提供されません。config.yaml を書き直す必要があります (setup.py で対話生成可能)。

## v1 継続利用する場合

```bash
# fork したリポジトリで
git fetch origin
git checkout -b my-v1 v1.0.0
# もしくは legacy/v1 branch を tracking
git checkout -b my-v1 origin/legacy/v1
```

v1 の daily-digest.yml / main.py / summarize.py / send_gmail.py はすべて `v1.0.0` tag で固定されており、バグ修正 patch は v1.x branch で受け付けます (critical fix のみ)。

## v2 へ移行する場合

### 前提
- Python 3.11 (v1 と同じ)
- Gmail + App Password (v1 と同じ)
- Gemini API key (v1 と同じ、ただし v2 は prompt 設計変更により token 使用量がやや増加)
- **python-docx / biopython** が追加依存 (v1 の `requests` ベース fetch は廃止し BioPython に統一)

### 手順

1. **fork を v2 master に rebase しない**。かわりに新規 fork を切るか、独立 branch で v2 を試す。
2. `pip install -r requirements.txt` を再実行 (python-docx / biopython が追加される)。
3. `python setup.py` を実行。Gemini が対話形式で専門領域を聞き出し、`config.yaml` を再生成する (MeSH は使わず、Title/Abstract 実出現語のみで検索式を作る)。
4. GHA Secrets は v1 と互換 (`GEMINI_API_KEY` / `GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD`)。
5. 配信形式の変更: 本文は要点のみ、**Word 添付** に詳細が入る。Gmail クライアントで `.docx` を開ける環境が必要。

### 主な変更点

| 項目 | v1 | v2 |
|---|---|---|
| 配信形式 | HTML メール本文 | テキスト本文 + **Word 添付** |
| 論文取得 | `requests` + E-utilities 直叩き | `biopython` の Entrez API |
| 要約 | Deployment/Use/Safety 3 cluster | 7 軸 governance matrix + 結論/自問3チェック |
| 評価 | ★1-5 行内表示 | ★→ risk rating (低/中/高) + 2 段階評価 (スクリーニング→詳細) |
| 参照 | PubMed URL のみ | + crosswalk refs (GuideScope MCP resource 参照) |
| 設定 | 手書き config.yaml | setup.py で Gemini 対話生成 |

### 非互換点 (breaking)

- `config.yaml` の schema が変更 (tier 体系: tier1 journals / primary-secondary specialties / study_type_scores)
- `audit.py` の JSONL schema v2 (v1 の audit-hash log は読み込めない)
- HTML テンプレート (`templates/email.html.j2` 相当) は廃止
- `governance_overlay.md` プロンプトは `ai_summarizer.py` 内に統合

## なぜ v2 に破壊変更を入れたか

元バズ format の「**Word 添付 + summary index + ★評価 + 結論/実用 2 セクション**」は、**月曜朝 3 秒で今週の医療AI動向を判断できる** UX として完成度が高く、単なる HTML メール拡張では再現できないと判断しました。医療AIガバナンス 7 軸は、元バズの「今日の1本 + 実用」セクションを「結論 + 自問3チェック + 7軸 matrix」に差し替えることで自然に融合します。

判断の詳細は [`~/.claude/state/runs/2026-04-21-auditscope-v2/SPEC.md`](./docs/wave1-drafts/SPEC-reference.md) を参照 (ローカル運用メモ、公開版は v2 リリース時に整備)。

## サポート

- v1 critical bug → `legacy/v1` branch に PR
- v2 issue → master の Issues
- 質問 → Discussions

v2 の open development は Wave 単位で進めます。進捗は [Wave 1 drafts](./docs/wave1-drafts/) を参照。
