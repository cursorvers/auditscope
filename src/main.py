"""AuditScope メインオーケストレーター"""

import os
import sys
import yaml
from datetime import datetime
from typing import Dict, List

from fetch_pubmed import fetch_cluster
from retraction_filter import filter_papers
from summarize import summarize
from audit import append_audit, get_last_hash, create_audit_entry, verify_chain_integrity
from send_gmail import send_digest, generate_digest_html


def load_config() -> Dict:
    """設定ファイルを読み込み"""
    try:
        with open("config.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print("Error: config.yaml not found")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing config.yaml: {e}")
        sys.exit(1)


def validate_environment():
    """必要な環境変数をチェック"""
    required_vars = ["GEMINI_API_KEY", "GMAIL_ADDRESS", "GMAIL_APP_PASSWORD"]
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print(f"Error: Missing environment variables: {', '.join(missing)}")
        sys.exit(1)


def main():
    """メイン処理"""
    try:
        print("🏥 AuditScope Daily Digest - Starting...")
        
        # 設定と環境変数の検証
        validate_environment()
        config = load_config()
        
        # 監査チェーン整合性確認
        if not verify_chain_integrity():
            print("Warning: Audit chain integrity check failed")
        
        # 前回のハッシュ取得
        prev_hash = get_last_hash()
        print(f"Previous audit hash: {prev_hash[:8] + '...' if prev_hash else 'None'}")
        
        # 各クラスターから論文取得
        papers_by_cluster = {}
        audit_entries = []
        
        for cluster, query in config["pubmed"]["query_clusters"].items():
            print(f"\n📚 Fetching {cluster} papers...")
            
            papers = fetch_cluster(
                query=query,
                lookback_days=config["pubmed"]["lookback_days"],
                max_results=config["pubmed"]["max_per_cluster"]
            )
            
            print(f"Found {len(papers)} papers for {cluster}")
            
            if papers:
                # 撤回論文フィルタリング
                if config["governance"]["retraction_filter"]:
                    kept_papers, flagged_papers = filter_papers(papers)
                    print(f"Retraction check: {len(kept_papers)} kept, {len(flagged_papers)} flagged")
                    papers = kept_papers + flagged_papers  # flagged papers も含める（要約で警告）
                
                # 各論文を要約
                summarized_papers = []
                for paper in papers:
                    print(f"Summarizing PMID {paper.get('pmid', 'unknown')}...")
                    
                    summary = summarize(
                        paper=paper,
                        governance_flags=config["governance"],
                        model=config["model"]["name"],
                        temp=config["model"]["temperature"]
                    )
                    
                    paper["summary"] = summary
                    summarized_papers.append(paper)
                    
                    # 監査エントリ作成
                    audit_entry = create_audit_entry(paper, summary, cluster)
                    audit_entries.append(audit_entry)
                
                papers_by_cluster[cluster] = summarized_papers
        
        # 総論文数確認
        total_papers = sum(len(papers) for papers in papers_by_cluster.values())
        print(f"\n📊 Total papers processed: {total_papers}")
        
        # 監査ログ記録
        today = datetime.now().strftime("%Y-%m-%d")
        current_hash = append_audit(today, audit_entries, prev_hash)
        print(f"Audit logged: {current_hash[:8]}...")
        
        # メール生成・送信
        print("\n📧 Generating and sending email...")
        
        subject = f"Medical AI Digest - {datetime.now().strftime('%Y/%m/%d')} ({total_papers}件)"
        if total_papers == 0:
            subject = f"Medical AI Digest - {datetime.now().strftime('%Y/%m/%d')} (新着論文なし)"
        
        html_body = generate_digest_html(papers_by_cluster, config)
        
        send_digest(
            to=config["delivery"]["recipient"],
            subject=subject,
            html_body=html_body,
            address=os.getenv("GMAIL_ADDRESS"),
            app_password=os.getenv("GMAIL_APP_PASSWORD")
        )
        
        print("✅ Daily digest completed successfully")
        
    except Exception as e:
        print(f"❌ Error in main process: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()