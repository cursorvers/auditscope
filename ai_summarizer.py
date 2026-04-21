# AuditScope v2 — governance-focused derivative of:
#   medical-paper-summarizer-public (MIT, © yush02084)
#   https://github.com/yush02084/medical-paper-summarizer-public

"""
AI要約モジュール（AuditScope v2版）

7軸ガバナンス評価フレームワークによる論文要約機能。
2段階評価（スクリーニング→詳細）でガバナンス課題を特定。
「うちで使って大丈夫？」の臨床医視点に特化。
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import google.generativeai as genai
from pubmed_searcher import Paper

logger = logging.getLogger(__name__)

# 7軸ガバナンス評価プロンプト（埋め込み）
SCREENING_PROMPT_TEMPLATE = """You are assisting a practicing clinician who is deciding whether to adopt this AI tool in their own practice. They are the user, not a manufacturer.

Please evaluate this paper's governance relevance for clinical AI adoption.

Paper Title: {title}
Abstract: {abstract}
Journal: {journal}
Authors: {authors}

Provide a JSON response with:
{{
  "relevance": <0-10 integer score>,
  "risk_flags": [<list of detected governance risks>]
}}

Focus on governance issues like: bias, hallucination, validation gaps, reproducibility concerns, safety risks, regulatory compliance, audit challenges.

Score 0-3: Not relevant for AI governance
Score 4-6: Some governance relevance
Score 7-10: High governance significance

Never provide patient-facing explanations. Focus on clinician decision-making needs."""

DETAILED_ANALYSIS_PROMPT_TEMPLATE = """You are assisting a practicing clinician who is deciding whether to adopt this AI tool in their own practice. They are the user, not a manufacturer.

Evaluate this paper across the 7 governance axes for clinical AI adoption decision-making.

Paper Title: {title}
Abstract: {abstract}
Methods (if available): {methods}
Journal: {journal}
Authors: {authors}

7 Governance Axes:
1. per_sentence_citation: Are claims backed by appropriate references?
2. hallucination: Any factually dubious synthesis or unsupported claims?
3. reproducibility: Code/data availability? Prompt/weights disclosed? Reproducible methodology?
4. disclaimer: Clinical-use warnings? Scope-of-use limitations clearly stated?
5. retraction: Any retraction database flags? Expressions of concern?
6. COI: Funding/author conflicts disclosed? Big Tech involvement without disclosure?
7. audit_hash: Audit trail available? Model versioning? Output verification methods?

Provide JSON response:
{{
  "conclusion": "<brief clinical adoption guidance>",
  "self_doubt_3": [
    "うちの患者層で本当に使える？ → <specific assessment>",
    "監査どうする？ → <specific assessment>", 
    "外したとき誰が責任？ → <specific assessment>"
  ],
  "axes": {{
    "per_sentence_citation": {{"rating": "low|medium|high|n/a", "rationale": "<specific reasoning>"}},
    "hallucination": {{"rating": "low|medium|high|n/a", "rationale": "<specific reasoning>"}},
    "reproducibility": {{"rating": "low|medium|high|n/a", "rationale": "<specific reasoning>"}},
    "disclaimer": {{"rating": "low|medium|high|n/a", "rationale": "<specific reasoning>"}},
    "retraction": {{"rating": "low|medium|high|n/a", "rationale": "<specific reasoning>"}},
    "COI": {{"rating": "low|medium|high|n/a", "rationale": "<specific reasoning>"}},
    "audit_hash": {{"rating": "low|medium|high|n/a", "rationale": "<specific reasoning>"}}
  }}
}}

Rating scale: low=minimal risk, medium=moderate risk, high=significant risk, n/a=cannot evaluate
If you cannot properly evaluate any axis, use "n/a" with explanation - never hallucinate a rating.
Flag if authors include Big Tech health-AI groups without proper COI disclosure.
Never provide patient-facing explanations."""


def setup_gemini_client(api_key: str) -> genai.GenerativeModel:
    """
    Gemini クライアントのセットアップ
    
    Args:
        api_key: Gemini APIキー
        
    Returns:
        genai.GenerativeModel: 設定済みモデル
    """
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.0-flash-exp')


def log_token_usage(stage: str, paper_id: str, input_tokens: int, output_tokens: int) -> None:
    """
    トークン使用量をログに記録
    
    Args:
        stage: 評価段階（screening/detailed）
        paper_id: 論文ID
        input_tokens: 入力トークン数
        output_tokens: 出力トークン数
    """
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "stage": stage,
        "paper_id": paper_id,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens
    }
    
    os.makedirs("logs", exist_ok=True)
    with open("logs/audit.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")


def retry_with_backoff(func, max_retries: int = 3, base_delay: float = 1.0):
    """
    指数バックオフによるリトライ処理
    
    Args:
        func: 実行する関数
        max_retries: 最大リトライ回数
        base_delay: 基本遅延時間（秒）
        
    Returns:
        関数の実行結果
        
    Raises:
        Exception: 最大リトライ回数を超えた場合
    """
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            delay = base_delay * (2 ** attempt)
            logger.warning(f"API呼び出し失敗 (試行 {attempt + 1}/{max_retries}): {e}")
            logger.info(f"{delay}秒待機後にリトライします...")
            time.sleep(delay)


def perform_screening(paper: Paper, model: genai.GenerativeModel) -> Dict[str, Any]:
    """
    第1段階：スクリーニング評価を実行
    
    Args:
        paper: 評価対象論文
        model: Gemini モデル
        
    Returns:
        Dict[str, Any]: スクリーニング結果
    """
    prompt = SCREENING_PROMPT_TEMPLATE.format(
        title=paper.title,
        abstract=paper.abstract,
        journal=paper.journal,
        authors=", ".join(paper.authors) if paper.authors else "Not available"
    )
    
    def call_api():
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # JSON抽出
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        return json.loads(content)
    
    result = retry_with_backoff(call_api)
    
    # トークン使用量ログ（概算）
    input_tokens = len(prompt.split())
    output_tokens = len(str(result).split())
    log_token_usage("screening", paper.pmid, input_tokens, output_tokens)
    
    return result


def perform_detailed_analysis(paper: Paper, model: genai.GenerativeModel, axes: Dict[str, Any]) -> Dict[str, Any]:
    """
    第2段階：詳細分析を実行
    
    Args:
        paper: 評価対象論文
        model: Gemini モデル
        axes: ガバナンス軸設定
        
    Returns:
        Dict[str, Any]: 詳細分析結果
    """
    # メソッド部分の抽出試行（抄録から）
    methods_section = ""
    if paper.abstract:
        abstract_lower = paper.abstract.lower()
        if "methods:" in abstract_lower or "methodology:" in abstract_lower:
            methods_section = paper.abstract
    
    prompt = DETAILED_ANALYSIS_PROMPT_TEMPLATE.format(
        title=paper.title,
        abstract=paper.abstract,
        methods=methods_section or "Not available",
        journal=paper.journal,
        authors=", ".join(paper.authors) if paper.authors else "Not available"
    )
    
    def call_api():
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # JSON抽出
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        return json.loads(content)
    
    result = retry_with_backoff(call_api)
    
    # トークン使用量ログ（概算）
    input_tokens = len(prompt.split())
    output_tokens = len(str(result).split())
    log_token_usage("detailed", paper.pmid, input_tokens, output_tokens)
    
    return result


def validate_detailed_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    詳細分析結果の検証と補完
    
    Args:
        result: 詳細分析結果
        
    Returns:
        Dict[str, Any]: 検証済み結果
    """
    required_axes = [
        "per_sentence_citation", "hallucination", "reproducibility", 
        "disclaimer", "retraction", "COI", "audit_hash"
    ]
    
    # axes フィールドの補完
    if "axes" not in result:
        result["axes"] = {}
    
    for axis in required_axes:
        if axis not in result["axes"]:
            result["axes"][axis] = {
                "rating": "n/a", 
                "rationale": "評価データ不足のため判定不可能"
            }
        elif "rating" not in result["axes"][axis]:
            result["axes"][axis]["rating"] = "n/a"
        elif "rationale" not in result["axes"][axis]:
            result["axes"][axis]["rationale"] = "詳細な根拠情報が不足"
    
    # 必須フィールドの補完
    if "conclusion" not in result:
        result["conclusion"] = "ガバナンス評価が不完全なため、慎重な検討が必要"
    
    if "self_doubt_3" not in result:
        result["self_doubt_3"] = [
            "うちの患者層で本当に使える？ → 評価データ不足のため要追加調査",
            "監査どうする？ → 監査手法の詳細検討が必要",
            "外したとき誰が責任？ → 責任体制の事前明確化が必要"
        ]
    
    return result


def summarize_paper(paper: Paper, axes: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    論文のガバナンス軸による要約を生成する
    
    7軸ガバナンス評価フレームワーク:
    1. per_sentence_citation: 文単位での引用根拠の明確性
    2. hallucination: 幻覚・虚偽情報生成のリスク評価
    3. reproducibility: 再現性・検証可能性の担保
    4. disclaimer: 免責・限界の適切な明示
    5. retraction: 撤回リスクの事前検出
    6. COI: 利益相反の開示・影響評価
    7. audit_hash: 監査証跡・検証可能性の確保
    
    2段階評価プロセス:
    - スクリーニング評価: 基本的なガバナンス問題の検出
    - 詳細評価: 深度のあるリスク分析・推奨事項生成
    
    Args:
        paper: 評価対象の論文オブジェクト
        axes: ガバナンス軸の設定（config.yamlから）
        config: 全体設定（screening_threshold等を含む）
        
    Returns:
        ガバナンス評価結果辞書
        {
            "paper_id": "PMID:...",
            "title": "...",
            "screening": {"relevance": int, "risk_flags": [str]},
            "detailed": {  # スクリーニング通過時のみ
                "conclusion": str,
                "self_doubt_3": [str, str, str],
                "axes": {軸名: {"rating": str, "rationale": str}, ...}
            }
        }
    """
    # APIキー確認
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY環境変数が設定されていません")
    
    # Geminiクライアント設定
    model = setup_gemini_client(api_key)
    
    # 結果の初期化
    result = {
        "paper_id": f"PMID:{paper.pmid}",
        "title": paper.title,
        "screening": {"relevance": 0, "risk_flags": []},
        "detailed": None
    }
    
    try:
        # 第1段階：スクリーニング評価
        logger.info(f"スクリーニング評価開始: {paper.pmid}")
        screening_result = perform_screening(paper, model)
        result["screening"] = screening_result
        
        # 閾値チェック
        screening_threshold = config.get("screening_threshold", 6)
        if screening_result.get("relevance", 0) >= screening_threshold:
            # 第2段階：詳細分析
            logger.info(f"詳細分析開始: {paper.pmid}")
            detailed_result = perform_detailed_analysis(paper, model, axes)
            result["detailed"] = validate_detailed_result(detailed_result)
        else:
            logger.info(f"スクリーニング閾値未満のため詳細分析をスキップ: {paper.pmid}")
    
    except Exception as e:
        logger.error(f"論文評価エラー {paper.pmid}: {e}")
        # フェイルクローズドでエラー情報を記録
        result["screening"] = {
            "relevance": 0,
            "risk_flags": ["evaluation_error"]
        }
        result["error"] = str(e)
    
    return result