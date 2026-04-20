"""撤回論文フィルタリングモジュール"""

import os
import csv
import time
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Tuple


def filter_papers(papers: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """
    撤回論文をフィルタリング
    
    Args:
        papers: 論文リスト
        
    Returns:
        (kept_papers, flagged_papers) のタプル
    """
    retraction_pmids = get_retraction_pmids()
    
    kept = []
    flagged = []
    
    for paper in papers:
        pmid = paper.get("pmid", "")
        if pmid in retraction_pmids:
            paper["retraction_flag"] = True
            flagged.append(paper)
        else:
            paper["retraction_flag"] = False
            kept.append(paper)
    
    return kept, flagged


def get_retraction_pmids() -> set:
    """
    Retraction Watch データベースから撤回論文のPMIDを取得
    キャッシュ機能付き（24時間TTL）
    """
    cache_file = "/tmp/retraction_watch.csv"
    
    # キャッシュが存在し、24時間以内なら使用
    if os.path.exists(cache_file):
        file_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
        if datetime.now() - file_time < timedelta(hours=24):
            return parse_retraction_csv(cache_file)
    
    # キャッシュが古いか存在しない場合、新しいデータを取得
    try:
        url = "https://api.labs.crossref.org/data/retractionwatch"
        params = {"email": "contact@cursorvers.jp"}
        
        headers = {
            "User-Agent": "AuditScope/0.1 (+https://cursorvers.jp/tools/auditscope)"
        }
        
        print("Fetching Retraction Watch database...")
        response = requests.get(url, params=params, headers=headers, timeout=60)
        response.raise_for_status()
        
        # CSVファイルとして保存
        with open(cache_file, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        return parse_retraction_csv(cache_file)
        
    except Exception as e:
        print(f"Failed to fetch retraction data: {e}")
        # フォールバック：空のセットを返す（撤回チェックをスキップ）
        return set()


def parse_retraction_csv(csv_file: str) -> set:
    """
    Retraction Watch CSVファイルからPMIDを抽出
    """
    pmids = set()
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # PMIDカラムが存在する場合のみ追加
                pmid = row.get('PMID', '').strip()
                if pmid and pmid.isdigit():
                    pmids.add(pmid)
                    
    except Exception as e:
        print(f"Error parsing retraction CSV: {e}")
        
    print(f"Loaded {len(pmids)} retracted PMIDs from cache")
    return pmids