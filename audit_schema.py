# AuditScope v2 — governance-focused derivative of:
#   medical-paper-summarizer-public (MIT, © yush02084)
#   https://github.com/yush02084/medical-paper-summarizer-public

"""
監査ログスキーマ v2 — 統一された監査記録形式

すべてのパイプライン段階での監査ログを統一スキーマで記録・管理。
入出力のハッシュ化、トークン使用量追跡、実行時間計測を含む。
「うちで使って大丈夫？」の監査証跡確保に対応。
"""

import hashlib
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


def new_run_id() -> str:
    """Generate a uuid4 string for pipeline-invocation tagging."""
    return str(uuid.uuid4())


def _hash_data(data: Any) -> str:
    """
    データをJSONシリアライズしてSHA256ハッシュ化する
    
    Args:
        data: ハッシュ化対象のデータ
        
    Returns:
        SHA256ハッシュ文字列（16進数）
    """
    if data is None:
        return hashlib.sha256(b"").hexdigest()
    
    try:
        # JSONシリアライズして文字列化
        json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        
        # 8KB制限チェック（大きなペイロードの切り詰め）
        if len(json_str) > 8192:
            truncated_data = {
                "_truncated": True,
                "_original_size": len(json_str),
                "_truncated_content": json_str[:8000]
            }
            json_str = json.dumps(truncated_data, sort_keys=True, ensure_ascii=False)
        
        return hashlib.sha256(json_str.encode('utf-8')).hexdigest()
        
    except (TypeError, ValueError) as e:
        # シリアライズできない場合は文字列表現を使用
        str_repr = str(data)
        if len(str_repr) > 8192:
            str_repr = str_repr[:8000] + "...[truncated]"
        return hashlib.sha256(str_repr.encode('utf-8')).hexdigest()


def audit_record(stage: str, *, 
                paper_id: Optional[str] = None,
                inputs: Any = None, 
                outputs: Any = None,
                tokens: Optional[Dict] = None, 
                duration_ms: int = 0,
                status: str = "ok", 
                error: Optional[str] = None,
                run_id: Optional[str] = None) -> Dict:
    """
    Build a v2-schema audit record. Hashes inputs/outputs internally.
    
    Args:
        stage: パイプライン段階名 (search|filter|summarize_screening|summarize_detailed|generate_report|send_mail)
        paper_id: 論文ID ("PMID:..." format) or None for aggregate stages
        inputs: 入力データ（任意の型、内部でハッシュ化される）
        outputs: 出力データ（任意の型、内部でハッシュ化される）
        tokens: トークン使用量辞書 {"input": int, "output": int} (Gemini stages only)
        duration_ms: 処理時間（ミリ秒）
        status: 実行状態 ("ok"|"error"|"skipped")
        error: エラーメッセージ（エラー時のみ）
        run_id: パイプライン実行ID（未指定時は新規生成）
        
    Returns:
        v2スキーマに準拠した監査レコード辞書
    """
    if run_id is None:
        run_id = new_run_id()
    
    # 入出力データのハッシュ化
    inputs_hash = _hash_data(inputs)
    outputs_hash = _hash_data(outputs)
    
    # v2スキーマレコード構築
    record = {
        "schema_version": "v2",
        "timestamp": datetime.now().isoformat() + "Z",
        "run_id": run_id,
        "stage": stage,
        "paper_id": paper_id,
        "inputs_hash": inputs_hash,
        "outputs_hash": outputs_hash,
        "tokens": tokens,
        "duration_ms": duration_ms,
        "status": status,
        "error": error
    }
    
    return record


def append_audit(record: Dict, path: str = "logs/audit.jsonl") -> None:
    """
    Append a v2-schema record as a single JSONL line.
    
    Args:
        record: 監査レコード辞書（audit_record()で生成）
        path: 出力ファイルパス（デフォルト: logs/audit.jsonl）
    """
    # ログディレクトリの作成
    log_path = Path(path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # JSONLファイルに追記
    with open(log_path, "a", encoding="utf-8") as f:
        json_line = json.dumps(record, ensure_ascii=False, separators=(',', ':'))
        f.write(json_line + "\n")