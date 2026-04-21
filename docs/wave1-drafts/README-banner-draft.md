# README Red Banner (DRAFT — 未適用)

**適用タイミング**: v2 master merge 直前。既存 README.md の先頭 (タイトル `# 🏥 AuditScope - Medical AI Paper Digest` の直下) に以下ブロックを挿入する。v1 legacy 継続利用者向けに目立たせる。

---

```markdown
> ## ⚠️ v2 Breaking Change Notice
>
> **AuditScope v2 は配信形式が大きく変わります** (HTML メール → Word 添付 daily digest、元バズ format の full port)。
>
> - **v1 継続利用**: `git checkout v1.0.0` または `legacy/v1` branch から fork してください。v1 は critical fix のみ受け付けます。
> - **v2 へ移行**: [`MIGRATION.md`](./MIGRATION.md) を参照。config.yaml の再生成が必要です (setup.py 対話生成で可能)。
> - **質問・懸念**: [forker 通知 Issue](#) (リンクは公開時に差し替え) または Discussions へ。
```

---

## 併記候補 (任意)

英語版も必要なら以下を下段に追加:

```markdown
> **English**: AuditScope v2 introduces a breaking change (HTML email → Word attachment daily digest, a full port of the upstream format). Existing forks are safe on `legacy/v1` / `v1.0.0`. See [MIGRATION.md](./MIGRATION.md) to upgrade.
```

## 適用後の削除タイミング

v2 リリースから 90 日経過 + 既存 forker の半数以上が v2 に移行 or v1 明示継続を表明した時点で banner を削除し、MIGRATION.md へのリンクを README 末尾の Appendix に移す。
