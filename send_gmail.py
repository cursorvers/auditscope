# AuditScope v2 — governance-focused derivative of:
#   medical-paper-summarizer-public (MIT, © yush02084)
#   https://github.com/yush02084/medical-paper-summarizer-public

"""
Gmail送信モジュール（AuditScope v2版）

Word文書添付対応のメール送信機能。
「うちで使って大丈夫？」の結果配信。
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def send_gmail(
    to_address: str,
    subject: str,
    body: str,
    gmail_address: str,
    gmail_password: str,
    attachment_path: Optional[str] = None
) -> bool:
    """
    Gmail経由でメールを送信する
    
    「うちで使って大丈夫？」のAuditScope v2レポートを
    臨床医・管理者に配信する。Word文書添付対応。
    
    Args:
        to_address: 送信先メールアドレス
        subject: 件名（"AuditScope v2 — YYYY-MM-DD (N件)"形式推奨）
        body: メール本文
        gmail_address: 送信元Gmailアドレス（GMAIL_ADDRESS環境変数）
        gmail_password: Gmailアプリパスワード（GMAIL_APP_PASSWORD環境変数）
        attachment_path: 添付ファイルパス（Wordレポート、任意）
        
    Returns:
        送信成功時True、失敗時False
    """
    try:
        # メッセージ作成
        msg = MIMEMultipart()
        msg["From"] = gmail_address
        msg["To"] = to_address
        msg["Subject"] = subject

        # 本文追加
        msg.attach(MIMEText(body, "plain", "utf-8"))

        # 添付ファイル処理
        if attachment_path and Path(attachment_path).exists():
            with open(attachment_path, "rb") as f:
                attachment = MIMEApplication(f.read())
                attachment.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=Path(attachment_path).name
                )
                msg.attach(attachment)
            logger.info(f"添付ファイル: {Path(attachment_path).name}")
        elif attachment_path:
            logger.warning(f"添付ファイルが見つかりません: {attachment_path}")

        # SMTP送信
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(gmail_address, gmail_password)
        server.send_message(msg)
        server.quit()

        logger.info(f"うちで使って大丈夫？→メール送信完了: {to_address}")
        return True

    except Exception as e:
        logger.error(f"うちで使って大丈夫？→メール送信失敗: {e}")
        return False