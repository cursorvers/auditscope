# AuditScope v2 — governance-focused derivative of:
#   medical-paper-summarizer-public (MIT, © yush02084)
#   https://github.com/yush02084/medical-paper-summarizer-public

"""
論文フィルタリング・ガバナンス評価モジュール（AuditScope v2版）

AI医療システムの研究論文について、品質スコア＋ガバナンス関連性を評価し、
「うちで使って大丈夫？」の観点から重要論文を選出する。
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from pubmed_searcher import Paper

logger = logging.getLogger(__name__)


class PaperFilter:
    """論文フィルタリング・ガバナンス評価クラス"""

    def __init__(self, config: dict, history_file: Optional[str] = None):
        """
        初期化

        Args:
            config: config.yamlから読み込んだ設定辞書
            history_file: 履歴ファイルのパス
        """
        self.config = config
        self.history_file = history_file or "history.json"
        self.history = self._load_history()

    def _load_history(self) -> dict:
        """履歴ファイルを読み込む"""
        path = Path(self.history_file)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # processed_ids キーがない場合は補完
                if "processed_ids" not in data:
                    data["processed_ids"] = []
                return data
            except Exception as e:
                logger.warning(f"履歴ファイル読み込み失敗: {e}")
        return {"processed_ids": [], "last_run": None}

    def save_history(self, papers: list[Paper]):
        """
        処理済み論文PMIDを履歴に保存する

        Args:
            papers: 処理対象の論文リスト
        """
        now = datetime.now().isoformat()
        
        # 新しいPMIDを処理済みリストに追加
        for paper in papers:
            if paper.pmid not in self.history["processed_ids"]:
                self.history["processed_ids"].append(paper.pmid)

        # 最終実行日時を更新
        self.history["last_run"] = now

        # 古い履歴のクリーンアップ（180日以上前のPMIDを削除）
        # 簡易実装: 配列長が1000を超えたら古い500件を削除
        if len(self.history["processed_ids"]) > 1000:
            self.history["processed_ids"] = self.history["processed_ids"][-500:]
            logger.info("履歴をクリーンアップしました（古い500件を削除）")

        # 保存
        path = Path(self.history_file)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

        logger.info(f"履歴を保存しました（処理済み: {len(self.history['processed_ids'])}件）")

    def filter_and_rank(self, papers: list[Paper]) -> list[Paper]:
        """
        論文をフィルタリングし、品質+ガバナンススコアで順位付けする

        Args:
            papers: PubMed検索結果の論文リスト

        Returns:
            スコア順にソートされた上位N件の論文リスト
        """
        max_papers = self.config.get("max_papers_per_run", 10)

        logger.info("うちで使って大丈夫？→論文フィルタリング開始...")
        
        # 1. 重複排除（過去に処理済みの論文を除外）
        new_papers = self._remove_duplicates(papers)
        logger.info(f"重複排除: {len(papers)}件 → {len(new_papers)}件")

        # 2. 除外対象の論文タイプを除外
        filtered = self._exclude_types(new_papers)
        logger.info(f"タイプ除外: {len(new_papers)}件 → {len(filtered)}件")

        # 3. アブストラクトなしの論文を除外
        filtered = [p for p in filtered if p.abstract.strip()]
        logger.info(f"アブストラクト必須: {len(filtered)}件")

        # 4. 撤回論文の検出・除外
        filtered = self._exclude_retracted(filtered)
        logger.info(f"撤回論文除外後: {len(filtered)}件")

        # 5. 品質スコア計算
        for paper in filtered:
            paper.quality_score = self._calculate_quality_score(paper)

        # 6. ガバナンス関連性スコア計算
        for paper in filtered:
            paper.governance_score = self.governance_relevance_score(paper)

        # 7. 総合スコア（品質×0.7 + ガバナンス×0.3）でソート
        for paper in filtered:
            paper._total_score = paper.quality_score * 0.7 + paper.governance_score * 0.3

        filtered.sort(key=lambda p: p._total_score, reverse=True)

        # 8. 上位N件を選出
        top_papers = filtered[:max_papers]
        for rank, paper in enumerate(top_papers, 1):
            paper.priority_rank = rank

        logger.info(f"うちで使って大丈夫？→上位{len(top_papers)}件を選出")
        for paper in top_papers:
            logger.debug(
                f"  #{paper.priority_rank} [品質:{paper.quality_score:.1f} "
                f"ガバナンス:{paper.governance_score:.1f}] {paper.title[:50]}..."
            )

        return top_papers

    def _remove_duplicates(self, papers: list[Paper]) -> list[Paper]:
        """過去に処理済みの論文を除外する"""
        processed = set(self.history.get("processed_ids", []))
        return [p for p in papers if p.pmid not in processed]

    def _exclude_types(self, papers: list[Paper]) -> list[Paper]:
        """除外対象の論文タイプを除外する"""
        exclude = {"Case Reports", "Editorial", "Comment", "Letter", "Published Erratum"}
        result = []
        for paper in papers:
            paper_types = set(paper.pub_types)
            # 論文タイプが全て除外対象の場合のみ除外
            if paper_types and paper_types.issubset(exclude | {"Journal Article"}):
                non_journal = paper_types - {"Journal Article"}
                if non_journal and non_journal.issubset(exclude):
                    continue
            result.append(paper)
        return result

    def _exclude_retracted(self, papers: list[Paper]) -> list[Paper]:
        """撤回論文を検出・除外する"""
        result = []
        retraction_indicators = [
            "retracted", "retraction", "withdrawn", "expression of concern"
        ]
        
        for paper in papers:
            title_lower = paper.title.lower()
            abstract_lower = paper.abstract.lower()
            
            # タイトルまたはアブストラクトに撤回指標が含まれる場合は除外
            is_retracted = any(
                indicator in title_lower or indicator in abstract_lower
                for indicator in retraction_indicators
            )
            
            if is_retracted:
                logger.debug(f"撤回論文を除外: {paper.title[:60]}...")
                continue
            
            result.append(paper)
        
        return result

    def _calculate_quality_score(self, paper: Paper) -> float:
        """
        論文の品質スコアを計算する（0-10点）

        スコア構成:
        - 研究デザインスコア: 0-10
        - ジャーナルティアスコア: 0-10の範囲で重み付け
        - 専門領域マッチスコア: ボーナス点

        Args:
            paper: 評価対象の論文

        Returns:
            品質スコア（0-10）
        """
        score = 0.0

        # 1. 研究デザインスコア
        study_scores = self.config.get("study_type_scores", {})
        max_study_score = 0.0
        for pt in paper.pub_types:
            s = study_scores.get(pt, 3)  # デフォルト3点
            max_study_score = max(max_study_score, s)
        score += max_study_score * 0.5  # 0-5点

        # 2. ジャーナルティアスコア
        tier_score = self._score_journal_tier(paper)
        score += tier_score * 0.3  # 0-3点

        # 3. 専門領域マッチスコア（AI/医療関連）
        specialty_score = self._score_specialty_match(paper)
        score += specialty_score * 0.2  # 0-2点

        return min(score, 10.0)

    def _score_journal_tier(self, paper: Paper) -> float:
        """ジャーナルティアに基づくスコア（0-10）"""
        tier1_journals = self.config.get("tier1_journals", [])
        tier2_journals = self.config.get("tier2_journals", [])
        tier3_journals = self.config.get("tier3_journals", [])

        if paper.journal in tier1_journals:
            return 10.0
        elif paper.journal in tier2_journals:
            return 8.0
        elif paper.journal in tier3_journals:
            return 6.0
        else:
            return 3.0

    def _score_specialty_match(self, paper: Paper) -> float:
        """AI/医療専門領域とのマッチ度スコア（0-10）"""
        primary_specialties = self.config.get("primary_specialties", [])
        secondary_specialties = self.config.get("secondary_specialties", [])

        # タイトル、アブストラクト、MeSH、キーワードを統合
        text = " ".join([
            paper.title.lower(),
            paper.abstract.lower(),
            " ".join([m.lower() for m in paper.mesh_terms]),
            " ".join([k.lower() for k in paper.keywords])
        ])

        score = 0.0

        # 主要専門領域マッチ（各2点、最大6点）
        for specialty in primary_specialties:
            if specialty.lower() in text:
                score += 2.0
        score = min(score, 6.0)

        # 次点専門領域マッチ（各1点、最大4点）
        secondary_matches = 0
        for specialty in secondary_specialties:
            if specialty.lower() in text:
                secondary_matches += 1
        score += min(secondary_matches, 4.0)

        return min(score, 10.0)

    def governance_relevance_score(self, paper: Paper) -> float:
        """
        ガバナンス関連性スコアを計算する（0-10点）
        
        AI医療システムのガバナンス課題（validation, bias, fairness, 
        hallucination, retraction, reproducibility, audit, etc.）への
        関連度を評価する。
        
        Args:
            paper: 評価対象の論文
            
        Returns:
            ガバナンス関連性スコア（0-10）
        """
        governance_keywords = self.config.get("governance_keywords", [
            "validation", "bias", "fairness", "hallucination", "retraction",
            "reproducibility", "audit", "prompt injection", "PHI", "model drift",
            "automation bias", "adversarial", "accountability", "COI", "overfitting",
            "transparency", "explainability", "generalizability", "distribution shift",
            "clinical utility"
        ])

        # タイトル、アブストラクトを統合して検索対象にする
        text = (paper.title + " " + paper.abstract).lower()

        score = 0.0
        matched_keywords = []

        # キーワードマッチングによるスコア計算
        for keyword in governance_keywords:
            if keyword.lower() in text:
                matched_keywords.append(keyword)
                
                # 重要度に応じてスコア配分
                if keyword.lower() in ["validation", "bias", "fairness", "audit", "transparency"]:
                    score += 2.0  # 高重要度
                elif keyword.lower() in ["hallucination", "model drift", "explainability", "clinical utility"]:
                    score += 1.5  # 中重要度
                else:
                    score += 1.0  # 基本重要度

        # タイトルでのマッチにはボーナス
        title_lower = paper.title.lower()
        title_bonus = 0.0
        for keyword in governance_keywords:
            if keyword.lower() in title_lower:
                title_bonus += 0.5

        score += title_bonus

        # 最大10点に制限
        final_score = min(score, 10.0)
        
        if matched_keywords:
            logger.debug(
                f"ガバナンスマッチ [{final_score:.1f}点]: {', '.join(matched_keywords[:5])} "
                f"- {paper.title[:40]}..."
            )
        
        return final_score