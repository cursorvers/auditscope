# ガバナンス・オーバーレイ要件

以下の7つのガバナンス軸に従って、構造化された要約を生成してください。

## 1. 文章単位引用 (per_sentence_citation)
各文の末尾に `[PMID:xxx, §Abstract/Methods/Results]` 形式で出典を明記してください。

## 2. 幻覚チェック (hallucination_selfcheck)
- 不明確な点は「本文未記載」と明示
- 推測や補完は行わず、事実のみを記述
- 曖昧な表現には「〜と思われる」等の推測マーカーを避ける

## 3. 再現性ブロック (reproducibility_block)
以下の項目を固定スキーマで抽出してください:
- dataset: 使用データセット名・規模
- n: 症例数・サンプルサイズ  
- primary_endpoint: 主要評価項目
- study_design: 研究デザイン（RCT/観察研究等）

## 4. 免責条項 (disclaimer)
要約末尾に以下を固定文で付与:
「本要約は情報提供を目的とし、臨床判断の代替ではありません。診療方針は原著論文及び関連ガイドラインを参照してください。」

## 5. 撤回シグナル (retraction_filter)
撤回論文を引用している場合は警告フラグを設定してください。

## 6. 利益相反ラベル (coi_label)
funding・利益相反の記載を原文のまま転記してください。記載がない場合は「COI: 記載なし」と明記。

## 7. 監査ハッシュ (audit_hash)
以下の監査情報を要約外で返してください:
- prompt_sha256: プロンプトのSHA256ハッシュ
- model_version: 使用モデル名
- retrieved_at: 処理実行時刻（ISO8601）

## 出力形式 (JSON)

```json
{
  "summary_3_sentences": "3文要約",
  "bedside_implication": "臨床示唆1行",
  "per_sentence_citations": ["引用1", "引用2", "引用3"],
  "hallucination_flags": ["UNCLEAR_POINT1", "UNCLEAR_POINT2"],
  "reproducibility_block": {
    "dataset": "データセット情報",
    "n": "症例数",
    "primary_endpoint": "主要評価項目", 
    "study_design": "研究デザイン"
  },
  "coi_extracted": "COI記載の原文転記",
  "retraction_warning": false,
  "disclaimer": "固定免責文"
}
```

要約の品質とガバナンス要件の両立を重視してください。