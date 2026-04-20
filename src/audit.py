"""監査ログモジュール（SHA256ハッシュチェーン）"""

import os
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Optional


def append_audit(date: str, entries: List[Dict], prev_hash: Optional[str]) -> str:
    """
    監査ログにエントリを追加し、ハッシュチェーンを更新
    
    Args:
        date: 監査日付 (YYYY-MM-DD形式)
        entries: 監査エントリのリスト
        prev_hash: 前回のハッシュ値
        
    Returns:
        新しいテールハッシュ
    """
    # 監査ログディレクトリを作成
    log_dir = "logs/audit"
    os.makedirs(log_dir, exist_ok=True)
    
    # 当日のログファイルパス
    log_file = os.path.join(log_dir, f"{date}.json")
    
    # ハッシュチェーン用のデータ構築
    chain_data = {
        "date": date,
        "timestamp": datetime.now().isoformat(),
        "prev_hash": prev_hash,
        "entries": entries,
        "entry_count": len(entries)
    }
    
    # エントリ内容のハッシュ計算
    entries_json = json.dumps(entries, sort_keys=True, ensure_ascii=False)
    content_hash = hashlib.sha256(entries_json.encode()).hexdigest()
    
    # チェーンハッシュ計算 (prev_hash + content_hash)
    chain_input = f"{prev_hash or ''}{content_hash}"
    current_hash = hashlib.sha256(chain_input.encode()).hexdigest()
    
    # 最終的な監査レコード
    audit_record = {
        **chain_data,
        "content_hash": content_hash,
        "current_hash": current_hash
    }
    
    # ファイルに書き出し
    try:
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(audit_record, f, ensure_ascii=False, indent=2)
        
        print(f"Audit log written: {log_file} (hash: {current_hash[:8]}...)")
        return current_hash
        
    except Exception as e:
        print(f"Failed to write audit log: {e}")
        return ""


def get_last_hash() -> Optional[str]:
    """
    最新の監査ログからハッシュ値を取得
    
    Returns:
        最新のハッシュ値、または存在しない場合はNone
    """
    log_dir = "logs/audit"
    
    if not os.path.exists(log_dir):
        return None
    
    try:
        # 最新のログファイルを検索
        log_files = [f for f in os.listdir(log_dir) if f.endswith('.json')]
        if not log_files:
            return None
        
        latest_file = sorted(log_files)[-1]
        latest_path = os.path.join(log_dir, latest_file)
        
        with open(latest_path, 'r', encoding='utf-8') as f:
            audit_data = json.load(f)
        
        return audit_data.get("current_hash")
        
    except Exception as e:
        print(f"Failed to read last audit hash: {e}")
        return None


def create_audit_entry(paper: Dict, summary: Dict, cluster: str) -> Dict:
    """
    個別論文の監査エントリを作成
    
    Args:
        paper: 論文情報
        summary: 要約結果
        cluster: クラスター名
        
    Returns:
        監査エントリ辞書
    """
    return {
        "pmid": paper.get("pmid", ""),
        "title": paper.get("title", "")[:100] + "...",  # タイトルは100文字まで
        "cluster": cluster,
        "doi": paper.get("doi", ""),
        "retraction_flag": paper.get("retraction_flag", False),
        "summary_audit": summary.get("audit", {}),
        "governance_flags": {
            "per_sentence_citation": bool(summary.get("per_sentence_citations")),
            "hallucination_check": bool(summary.get("hallucination_flags")),
            "reproducibility_block": bool(summary.get("reproducibility_block")),
            "coi_extracted": bool(summary.get("coi_extracted")),
            "disclaimer": bool(summary.get("disclaimer"))
        },
        "processed_at": datetime.now().isoformat()
    }


def verify_chain_integrity(log_dir: str = "logs/audit") -> bool:
    """
    監査ログチェーンの整合性を検証
    
    Args:
        log_dir: 監査ログディレクトリ
        
    Returns:
        チェーンが正常ならTrue
    """
    if not os.path.exists(log_dir):
        return True  # ログがない場合は正常とみなす
    
    try:
        log_files = sorted([f for f in os.listdir(log_dir) if f.endswith('.json')])
        
        prev_hash = None
        
        for log_file in log_files:
            with open(os.path.join(log_dir, log_file), 'r', encoding='utf-8') as f:
                record = json.load(f)
            
            # 前回ハッシュの確認
            if record.get("prev_hash") != prev_hash:
                print(f"Chain break detected in {log_file}")
                return False
            
            # コンテンツハッシュの再計算
            entries_json = json.dumps(record["entries"], sort_keys=True, ensure_ascii=False)
            expected_content_hash = hashlib.sha256(entries_json.encode()).hexdigest()
            
            if record.get("content_hash") != expected_content_hash:
                print(f"Content hash mismatch in {log_file}")
                return False
            
            # チェーンハッシュの再計算
            chain_input = f"{prev_hash or ''}{record['content_hash']}"
            expected_current_hash = hashlib.sha256(chain_input.encode()).hexdigest()
            
            if record.get("current_hash") != expected_current_hash:
                print(f"Chain hash mismatch in {log_file}")
                return False
            
            prev_hash = record["current_hash"]
        
        print(f"Audit chain verified: {len(log_files)} files")
        return True
        
    except Exception as e:
        print(f"Chain verification error: {e}")
        return False