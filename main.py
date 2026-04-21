# AuditScope v2 — governance-focused derivative of:
#   medical-paper-summarizer-public (MIT, © yush02084)
#   https://github.com/yush02084/medical-paper-summarizer-public

"""
AuditScope v2 メインパイプライン

PubMed検索 → フィルタリング → AI要約 → Word出力 → Gmail送信の
パイプラインを実行し、各ステージで監査ログを記録する。
「うちで使って大丈夫？」の臨床医視点で論文を評価・配信。
"""

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

from pubmed_searcher import PubMedSearcher
from paper_filter import PaperFilter
from ai_summarizer import summarize_paper
from word_generator import generate_report
from send_gmail import send_gmail

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/auditscope.log", encoding="utf-8", mode="a")
    ]
)
logger = logging.getLogger(__name__)


def load_config(config_path: str = "config.yaml") -> dict:
    """設定ファイルを読み込む"""
    path = Path(config_path)
    if not path.exists():
        logger.error(f"設定ファイルが見つかりません: {config_path}")
        logger.error("うちで使って大丈夫？→まず設定を確認してください")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    logger.info(f"設定ファイルを読み込みました: {config_path}")
    return config


def log_audit_entry(stage: str, inputs_data: dict, outputs_data: dict):
    """監査ログエントリーをJSONL形式で記録"""
    audit_log_path = Path("logs/audit.jsonl")
    audit_log_path.parent.mkdir(exist_ok=True)
    
    # ハッシュ計算（機密データは含めない）
    inputs_hash = hashlib.md5(json.dumps(inputs_data, sort_keys=True).encode()).hexdigest()
    outputs_hash = hashlib.md5(json.dumps(outputs_data, sort_keys=True).encode()).hexdigest()
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "stage": stage,
        "inputs_hash": inputs_hash,
        "outputs_hash": outputs_hash
    }
    
    with open(audit_log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main():
    """メインエントリーポイント"""
    parser = argparse.ArgumentParser(
        description="AuditScope v2 — AI医療システムガバナンス論文監視"
    )
    parser.add_argument(
        "--config", default="config.yaml",
        help="設定ファイルのパス（デフォルト: config.yaml）"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Gmail送信をスキップ（テスト用）"
    )
    parser.add_argument(
        "--hours-back", type=int, default=None,
        help="検索対象時間（デフォルト: 設定ファイルの値）"
    )
    args = parser.parse_args()

    # 環境変数の読み込み
    load_dotenv()

    # 設定読み込み
    config = load_config(args.config)

    # 必要な環境変数の確認
    ncbi_email = os.getenv("NCBI_EMAIL", "user@example.com")
    ncbi_api_key = os.getenv("NCBI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    gmail_address = os.getenv("GMAIL_ADDRESS")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")

    if not gemini_key:
        logger.error("GEMINI_API_KEY が設定されていません")
        logger.error("うちで使って大丈夫？→環境変数を確認してください")
        sys.exit(1)

    if not args.dry_run and (not gmail_address or not gmail_password):
        logger.error("GMAIL_ADDRESS, GMAIL_APP_PASSWORD が設定されていません")
        logger.error("うちで使って大丈夫？→メール設定を確認してください")
        sys.exit(1)

    # 検索期間の設定
    hours_back = args.hours_back or config.get("date_window_hours", 24)

    logger.info("=" * 60)
    logger.info("AuditScope v2 実行開始 — うちで使って大丈夫？")
    logger.info(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"検索期間: 過去{hours_back}時間")
    logger.info(f"ドライラン: {'はい' if args.dry_run else 'いいえ'}")
    logger.info("=" * 60)

    try:
        # ステップ1: PubMed検索
        logger.info("━━━ ステップ1: PubMed検索 ━━━")
        searcher = PubMedSearcher(config, ncbi_email, ncbi_api_key)
        papers = searcher.search(hours_back=hours_back)

        # 監査ログ記録
        log_audit_entry(
            "pubmed_search",
            {"hours_back": hours_back, "query_count": len(config.get("query_templates", {}))},
            {"papers_found": len(papers)}
        )

        if not papers:
            logger.info("うちで使って大丈夫？→新規論文なし。「新規論文なし」メールを送信")
            
            if not args.dry_run:
                # 新規論文なしの通知
                date_str = datetime.now().strftime("%Y-%m-%d")
                subject = f"AuditScope v2 — {date_str} (0件)"
                body = ("うちで使って大丈夫？→本日は新規論文が見つかりませんでした。\n\n"
                       "設定の見直しや検索クエリの調整を検討してください。")
                
                send_gmail(
                    to_address=gmail_address,
                    subject=subject,
                    body=body,
                    gmail_address=gmail_address,
                    gmail_password=gmail_password
                )
            return

        # ステップ2: フィルタリング・ガバナンス評価
        logger.info("━━━ ステップ2: フィルタリング・ガバナンス評価 ━━━")
        filterer = PaperFilter(config)
        top_papers = filterer.filter_and_rank(papers)

        # 監査ログ記録
        log_audit_entry(
            "paper_filter",
            {"input_papers": len(papers)},
            {"filtered_papers": len(top_papers), "avg_governance_score": sum(p.governance_score for p in top_papers) / len(top_papers) if top_papers else 0}
        )

        if not top_papers:
            logger.info("うちで使って大丈夫？→フィルタリング後に論文なし")
            return

        # 選出論文の表示
        logger.info("うちで使って大丈夫？→選出された論文:")
        for paper in top_papers:
            logger.info(
                f"  #{paper.priority_rank} [品質:{paper.quality_score:.1f} "
                f"ガバナンス:{paper.governance_score:.1f}] {paper.title[:60]}..."
            )

        # ステップ3: AI要約（スケルトン呼び出し）
        logger.info("━━━ ステップ3: AI要約生成 ━━━")
        try:
            summaries = {}
            for paper in top_papers:
                summary = summarize_paper(paper, config.get("governance_axes", {}))
                summaries[paper.pmid] = summary
                
            # 監査ログ記録
            log_audit_entry(
                "ai_summarizer",
                {"papers_count": len(top_papers)},
                {"summaries_generated": len(summaries)}
            )
        except NotImplementedError as e:
            logger.error(f"AI要約でエラー: {e}")
            logger.error("うちで使って大丈夫？→Wave 3で実装予定のため処理中断")
            # Fail-closed: Geminiエラー時は送信しない
            sys.exit(1)

        # ステップ4: Word文書生成（スケルトン呼び出し）
        logger.info("━━━ ステップ4: Word文書生成 ━━━")
        try:
            output_path = generate_report(top_papers, summaries, "output/auditscope_report.docx")
            
            # 監査ログ記録
            log_audit_entry(
                "word_generator",
                {"papers_count": len(top_papers)},
                {"report_generated": bool(output_path)}
            )
        except NotImplementedError as e:
            logger.error(f"Word生成でエラー: {e}")
            logger.error("うちで使って大丈夫？→Wave 3で実装予定のため処理中断")
            # Fail-closed: Word生成エラー時も送信しない
            sys.exit(1)

        # ステップ5: Gmail送信
        if not args.dry_run:
            logger.info("━━━ ステップ5: Gmail送信 ━━━")
            date_str = datetime.now().strftime("%Y-%m-%d")
            subject = f"AuditScope v2 — {date_str} ({len(top_papers)}件)"
            
            body = (
                f"うちで使って大丈夫？→AI医療システムガバナンス論文レビュー\n\n"
                f"本日の注目論文 {len(top_papers)}件を選出しました。\n"
                f"ガバナンス関連度が高い順に整理しています。\n\n"
                f"添付のWordファイルをご確認ください。"
            )
            
            # Word文書が存在する場合のみ添付
            attachment_path = output_path if Path(output_path).exists() else None
            
            send_gmail(
                to_address=gmail_address,
                subject=subject,
                body=body,
                gmail_address=gmail_address,
                gmail_password=gmail_password,
                attachment_path=attachment_path
            )

            # 監査ログ記録
            log_audit_entry(
                "send_gmail",
                {"recipient": gmail_address, "attachment": bool(attachment_path)},
                {"sent": True}
            )
        else:
            logger.info("━━━ ドライランモード: Gmail送信をスキップ ━━━")

        # ステップ6: 履歴更新
        logger.info("━━━ ステップ6: 履歴更新 ━━━")
        filterer.save_history(top_papers)

        logger.info("=" * 60)
        logger.info("うちで使って大丈夫？→AuditScope v2 処理完了")
        logger.info("=" * 60)

    except KeyboardInterrupt:
        logger.info("ユーザーにより中断されました")
        sys.exit(0)
    except Exception as e:
        logger.error(f"予期しないエラーが発生しました: {e}", exc_info=True)
        logger.error("うちで使って大丈夫？→システム障害の可能性があります")
        sys.exit(1)


if __name__ == "__main__":
    main()