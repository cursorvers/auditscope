"""論文要約モジュール（Gemini API）"""

import os
import json
import hashlib
from datetime import datetime
from typing import Dict
import google.generativeai as genai


def summarize(paper: Dict, governance_flags: Dict, model: str, temp: float) -> Dict:
    """
    Gemini APIを使用して論文を要約
    
    Args:
        paper: 論文情報
        governance_flags: ガバナンス設定
        model: 使用するモデル名
        temp: Temperature設定
        
    Returns:
        要約結果辞書
    """
    try:
        # Gemini API設定
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        genai.configure(api_key=api_key)
        
        # プロンプト構築
        base_prompt = load_base_prompt()
        governance_overlay = load_governance_overlay(governance_flags)
        full_prompt = f"{base_prompt}\n\n{governance_overlay}"
        
        # 論文情報を追加
        paper_text = format_paper_for_prompt(paper)
        final_prompt = f"{full_prompt}\n\n{paper_text}"
        
        # モデル設定
        model_instance = genai.GenerativeModel(model)
        generation_config = {
            "temperature": temp,
            "response_mime_type": "application/json"
        }
        
        # API呼び出し
        response = model_instance.generate_content(
            final_prompt,
            generation_config=generation_config
        )
        
        # レスポンス解析
        result = json.loads(response.text)
        
        # 監査情報を追加
        result["audit"] = {
            "prompt_sha256": hashlib.sha256(final_prompt.encode()).hexdigest(),
            "model_version": model,
            "retrieved_at": datetime.now().isoformat()
        }
        
        return result
        
    except Exception as e:
        print(f"Summarization error for PMID {paper.get('pmid', 'unknown')}: {e}")
        return {
            "summary_3_sentences": "要約生成に失敗しました。",
            "per_sentence_citations": [],
            "hallucination_flags": ["API_ERROR"],
            "reproducibility_block": {},
            "coi_extracted": "取得エラー",
            "disclaimer": "この要約は生成に失敗しました。",
            "audit": {
                "prompt_sha256": "",
                "model_version": model,
                "retrieved_at": datetime.now().isoformat(),
                "error": str(e)
            }
        }


def load_base_prompt() -> str:
    """基本プロンプトを読み込み"""
    try:
        with open("prompts/base.md", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "論文を3文で要約してください。日本語で出力してください。"


def load_governance_overlay(governance_flags: Dict) -> str:
    """ガバナンスオーバーレイを読み込み、フラグに応じて調整"""
    try:
        with open("prompts/governance_overlay.md", "r", encoding="utf-8") as f:
            overlay = f.read()
        
        # 無効化されたフラグの処理
        if not governance_flags.get("per_sentence_citation", True):
            overlay = overlay.replace("各文末に [PMID:xxx, §section] を付与", "")
        
        if not governance_flags.get("hallucination_selfcheck", True):
            overlay = overlay.replace("不明点は「本文未記載」と明示", "")
        
        if not governance_flags.get("reproducibility_block", True):
            overlay = overlay.replace("dataset / n / primary endpoint / study design", "")
        
        if not governance_flags.get("disclaimer", True):
            overlay = overlay.replace("臨床判断の代替ではない", "")
        
        if not governance_flags.get("coi_label", True):
            overlay = overlay.replace("funding/COI 記載を原文引用で転記", "")
        
        return overlay
        
    except FileNotFoundError:
        return "構造化された要約を生成してください。JSON形式で出力してください。"


def format_paper_for_prompt(paper: Dict) -> str:
    """論文情報をプロンプト用にフォーマット"""
    return f"""
論文情報:
PMID: {paper.get('pmid', 'N/A')}
タイトル: {paper.get('title', 'N/A')}
著者: {', '.join(paper.get('authors', []))}
ジャーナル: {paper.get('journal', 'N/A')}
出版年: {paper.get('year', 'N/A')}
DOI: {paper.get('doi', 'N/A')}

アブストラクト:
{paper.get('abstract', 'アブストラクトなし')}
"""