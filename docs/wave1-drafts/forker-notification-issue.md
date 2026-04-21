# Forker Notification Issue (DRAFT — 未配布)

**配布タイミング**: v2 がマスターにマージされ、README red banner が反映された時点で Issues タブに公開し、既存 forker を @mention する。それまでは本ファイルは下書きとして保持。

---

## Title
[Important] AuditScope v2 breaking change — v1 は `legacy/v1` branch で継続利用可能です

## Body

AuditScope を fork していただきありがとうございます。

v2 リリースに向けて、配信形式を元バズ [yush02084/medical-paper-summarizer-public](https://github.com/yush02084/medical-paper-summarizer-public) の **Word 添付 daily digest** に全面 port します。これは v1 の HTML メール + 7軸 overlay 構成とは非互換な破壊変更です。

### 既存 fork への影響

- **v1 をそのまま使い続ける場合**: 何もする必要はありません。`legacy/v1` branch と `v1.0.0` tag が固定されており、critical bug fix のみ v1.x で受け付けます。
- **v2 に移行する場合**: 新規 fork を切るか、既存 fork で `v1.0.0` から独立 branch を作って試すことを推奨します。master の pull merge はコンフリクト必至なので避けてください。

### 移行ガイド

[`MIGRATION.md`](../MIGRATION.md) に手順、変更点、非互換点をまとめています。v2 は:

- Word 添付 + summary index + ★→risk rating (低/中/高)
- 結論 + 自問3チェック (「うちで使って大丈夫？」)
- 7 軸 governance matrix (論文×軸)
- BioPython ベース PubMed 取得 + Gemini 2段階評価 (スクリーニング→詳細)

### なぜ breaking change にしたか

HTML メール拡張では「月曜朝 3 秒で判断」の UX に届かず、Word 添付前提の情報設計が必要と判断しました。詳細は MIGRATION.md の末尾セクション参照。

### スケジュール

- Wave 1 (現在): v1 凍結 + docs 準備
- Wave 2-5: v2 実装 + 統合
- Wave 6: v2 リリース (本 Issue 公開時)

配信系の操作はユーザー明示承認制のため、実際の公開日は未定です。v2 の進捗は Discussions で随時シェアします。

質問や懸念があれば本 Issue にコメントください。v1 継続利用を妨げる変更は入れません。

---

## 配布時チェックリスト (v2 リリース時)

- [ ] `legacy/v1` branch が remote に push 済み
- [ ] `v1.0.0` tag が remote に push 済み
- [ ] `MIGRATION.md` が master に存在
- [ ] README red banner が反映済み
- [ ] forker 一覧を `gh api /repos/cursorvers/auditscope/forks --paginate` で取得し mention
- [ ] Issue 公開後 Discussions にも告知 scratch
