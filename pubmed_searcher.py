# AuditScope v2 — governance-focused derivative of:
#   medical-paper-summarizer-public (MIT, © yush02084)
#   https://github.com/yush02084/medical-paper-summarizer-public

"""
PubMed論文検索モジュール（AuditScope v2版）

AI医療システムのガバナンス課題を調査するため、
PubMed E-utilities APIを使用して関連論文を検索・取得する。
「うちで使って大丈夫？」という臨床医の視点に特化。
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field
import os

from Bio import Entrez

logger = logging.getLogger(__name__)


@dataclass
class Paper:
    """論文データクラス（ガバナンス評価対応）"""
    pmid: str = ""
    title: str = ""
    authors: list = field(default_factory=list)
    journal: str = ""
    pub_date: str = ""
    abstract: str = ""
    pub_types: list = field(default_factory=list)
    doi: str = ""
    mesh_terms: list = field(default_factory=list)
    keywords: list = field(default_factory=list)
    # フィルタリング後に付与
    quality_score: float = 0.0
    governance_score: float = 0.0
    priority_rank: int = 0
    # AI要約結果
    summary: dict = field(default_factory=dict)


class PubMedSearcher:
    """PubMed検索クラス（AuditScope v2版）"""

    def __init__(self, config: dict, email: str, api_key: Optional[str] = None):
        """
        初期化

        Args:
            config: config.yamlから読み込んだ設定辞書
            email: NCBI E-utilities用メールアドレス
            api_key: NCBI APIキー（任意）
        """
        self.config = config
        Entrez.email = email
        
        # NCBI APIキーの設定とレート制限調整
        self._has_api_key = False
        api_key_env = config.get("ncbi_api_key_env", "NCBI_API_KEY")
        if not api_key:
            api_key = os.getenv(api_key_env)
        
        if api_key and len(api_key) > 10 and api_key != "none":
            Entrez.api_key = api_key
            self._has_api_key = True
            self.rate_limit = 0.1  # 10リクエスト/秒
            logger.info("NCBI APIキーを設定しました（10 req/s）")
        else:
            self.rate_limit = 0.34  # 3リクエスト/秒
            logger.info("NCBI APIキーなしで動作します（3 req/s）")

    def _build_query(self, hours_back: int) -> str:
        """
        PubMed検索クエリを構築する
        
        config.yamlのquery_templatesから読み込み、
        ガバナンス関連クエリを組み合わせる。
        日付フィルタはesearchのmindate/maxdateパラメータで指定。

        Returns:
            PubMed検索クエリ文字列
        """
        query_templates = self.config.get("query_templates", {})
        
        # 各テンプレートからクエリを取得
        queries = []
        for template_name in ["tier1_clinical", "deployment", "use_case", "safety"]:
            if template_name in query_templates:
                queries.append(f"({query_templates[template_name]})")
        
        if not queries:
            # フォールバック: 基本的なAIガバナンスクエリ
            queries = [
                "(AI OR \"artificial intelligence\" OR \"machine learning\" OR \"deep learning\") AND (clinical OR medical OR healthcare)",
                "(validation OR bias OR hallucination OR \"model drift\" OR \"automation bias\")"
            ]
            logger.warning("query_templatesが未設定のため、デフォルトクエリを使用します")

        # ORで結合
        full_query = " OR ".join(queries)
        
        logger.info(f"検索クエリ構築完了: {full_query[:200]}...")
        return full_query

    def _execute_esearch(
        self, query: str, max_results: int,
        min_date: str, max_date: str
    ) -> Optional[dict]:
        """
        PubMed ESearchを実行する（エラー時フォールバック付き）

        HTTP 400等のエラー発生時に以下の順でリトライ:
        1. APIキーを除外して再試行
        2. クエリを簡略化して再試行

        Returns:
            検索結果dict（全て失敗時はNone）
        """
        # 試行1: 通常の検索
        result = self._try_esearch(query, max_results, min_date, max_date)
        if result is not None:
            return result

        # 試行2: APIキーを一時的に無効化してリトライ
        if self._has_api_key:
            logger.warning("APIキーを無効化してリトライ中...")
            saved_key = Entrez.api_key
            Entrez.api_key = None
            self.rate_limit = 0.34

            result = self._try_esearch(query, max_results, min_date, max_date)

            # APIキーを復元
            Entrez.api_key = saved_key
            self.rate_limit = 0.1

            if result is not None:
                logger.warning("APIキーなしで検索成功。NCBI_API_KEYの値を確認してください")
                return result

        # 試行3: クエリを簡略化（tier1_clinicalのみ）
        logger.warning("クエリを簡略化してリトライ中...")
        tier1_query = self.config.get("query_templates", {}).get("tier1_clinical")
        if tier1_query:
            if self._has_api_key:
                saved_key = Entrez.api_key
                Entrez.api_key = None
            
            result = self._try_esearch(tier1_query, max_results, min_date, max_date)
            
            if self._has_api_key:
                Entrez.api_key = saved_key

            if result is not None:
                logger.warning("簡略化クエリで検索成功")
                return result

        logger.error("全ての検索試行が失敗しました")
        return None

    def _try_esearch(
        self, query: str, max_results: int,
        min_date: str, max_date: str
    ) -> Optional[dict]:
        """esearchを1回試行する"""
        try:
            time.sleep(self.rate_limit)
            handle = Entrez.esearch(
                db="pubmed",
                term=query,
                retmax=max_results,
                sort="relevance",
                usehistory="y",
                datetype="pdat",
                mindate=min_date,
                maxdate=max_date
            )
            search_results = Entrez.read(handle, validate=False)
            handle.close()
            return search_results
        except Exception as e:
            logger.error(f"PubMed検索中にエラー: {e}")
            logger.error(f"送信クエリ: {query}")
            if self._has_api_key:
                logger.error(f"APIキー設定: 末尾 ...{str(Entrez.api_key)[-4:] if Entrez.api_key else 'None'}")
            return None

    def search(self, hours_back: Optional[int] = None) -> list[Paper]:
        """
        PubMedを検索し、論文リストを返す

        Args:
            hours_back: 過去何時間分を検索するか（Noneの場合config値を使用）

        Returns:
            Paper オブジェクトのリスト
        """
        if hours_back is None:
            hours_back = self.config.get("date_window_hours", 24)

        max_results = self.config.get("max_papers_per_run", 50)
        query = self._build_query(hours_back)

        # 日付範囲の計算
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=hours_back)
        min_date_str = start_date.strftime("%Y/%m/%d")
        max_date_str = end_date.strftime("%Y/%m/%d")

        logger.info(f"PubMed検索実行中（過去{hours_back}時間）...")
        logger.info(f"日付範囲: {min_date_str} - {max_date_str}")
        logger.info(f"クエリ: {query}")

        search_results = self._execute_esearch(
            query, max_results, min_date_str, max_date_str
        )
        if search_results is None:
            logger.error("うちで使って大丈夫？→検索が失敗しました。設定を確認してください")
            return []

        id_list = search_results.get("IdList", [])
        total_count = int(search_results.get("Count", 0))
        logger.info(f"検索結果: {total_count}件（取得: {len(id_list)}件）")

        if not id_list:
            logger.info("うちで使って大丈夫？→該当論文なし。クエリ調整が必要かもしれません")
            return []

        # EFetch: 論文詳細取得（バッチ処理）
        papers = []
        batch_size = 50

        for start in range(0, len(id_list), batch_size):
            batch_ids = id_list[start:start + batch_size]
            logger.info(f"論文詳細取得中... ({start + 1}-{start + len(batch_ids)}/{len(id_list)})")

            try:
                time.sleep(self.rate_limit)
                handle = Entrez.efetch(
                    db="pubmed",
                    id=",".join(batch_ids),
                    rettype="xml",
                    retmode="xml"
                )
                records = Entrez.read(handle, validate=False)
                handle.close()
            except Exception as e:
                logger.error(f"論文詳細取得エラー: {e}")
                continue

            # XMLパース
            for article in records.get("PubmedArticle", []):
                paper = self._parse_article(article)
                if paper:
                    papers.append(paper)

        logger.info(f"うちで使って大丈夫？→{len(papers)}件の論文を取得しました")
        return papers

    def _parse_article(self, article: dict) -> Optional[Paper]:
        """
        PubMed XMLレコードからPaperオブジェクトを構築する

        Args:
            article: Entrez.readで取得した1論文のdict

        Returns:
            Paperオブジェクト（パース失敗時はNone）
        """
        try:
            medline = article.get("MedlineCitation", {})
            article_data = medline.get("Article", {})
            pmid = str(medline.get("PMID", ""))

            # タイトル
            title = str(article_data.get("ArticleTitle", ""))

            # 著者
            authors = []
            author_list = article_data.get("AuthorList", [])
            for author in author_list:
                last = author.get("LastName", "")
                fore = author.get("ForeName", "")
                if last:
                    authors.append(f"{last} {fore}".strip())

            # ジャーナル
            journal_info = article_data.get("Journal", {})
            journal = str(journal_info.get("ISOAbbreviation", ""))
            if not journal:
                journal = str(journal_info.get("Title", ""))

            # 出版日
            pub_date = self._extract_pub_date(article_data, journal_info)

            # アブストラクト
            abstract = self._extract_abstract(article_data)

            # 論文タイプ
            pub_types = []
            pub_type_list = article_data.get("PublicationTypeList", [])
            for pt in pub_type_list:
                pub_types.append(str(pt))

            # DOI
            doi = ""
            article_ids = article_data.get("ELocationID", [])
            for aid in article_ids:
                if aid.attributes.get("EIdType", "") == "doi":
                    doi = str(aid)
                    break

            # PubmedDataからもDOI取得を試行
            if not doi:
                pubmed_data = article.get("PubmedData", {})
                article_id_list = pubmed_data.get("ArticleIdList", [])
                for aid in article_id_list:
                    if aid.attributes.get("IdType", "") == "doi":
                        doi = str(aid)
                        break

            # MeSH用語
            mesh_terms = []
            mesh_list = medline.get("MeshHeadingList", [])
            for mesh in mesh_list:
                descriptor = mesh.get("DescriptorName", "")
                if descriptor:
                    mesh_terms.append(str(descriptor))

            # キーワード
            keywords = []
            keyword_list = medline.get("KeywordList", [])
            for kw_group in keyword_list:
                for kw in kw_group:
                    keywords.append(str(kw))

            return Paper(
                pmid=pmid,
                title=title,
                authors=authors,
                journal=journal,
                pub_date=pub_date,
                abstract=abstract,
                pub_types=pub_types,
                doi=doi,
                mesh_terms=mesh_terms,
                keywords=keywords
            )

        except Exception as e:
            logger.warning(f"論文パース中にエラー: {e}")
            return None

    def _extract_pub_date(self, article_data: dict, journal_info: dict) -> str:
        """出版日を抽出する"""
        # ArticleDateを試行
        article_dates = article_data.get("ArticleDate", [])
        if article_dates:
            date = article_dates[0]
            year = date.get("Year", "")
            month = date.get("Month", "01")
            day = date.get("Day", "01")
            return f"{year}/{month}/{day}"

        # JournalIssueのPubDateを試行
        journal_issue = journal_info.get("JournalIssue", {})
        pub_date = journal_issue.get("PubDate", {})
        year = pub_date.get("Year", "")
        month = pub_date.get("Month", "")
        day = pub_date.get("Day", "")

        if year:
            # 月名をゼロ詰め数値に変換
            month_map = {
                "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
                "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
                "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"
            }
            month = month_map.get(month, month if month else "01")
            day = day if day else "01"
            return f"{year}/{month}/{day}"

        return ""

    def _extract_abstract(self, article_data: dict) -> str:
        """アブストラクトを抽出する"""
        abstract_data = article_data.get("Abstract", {})
        abstract_texts = abstract_data.get("AbstractText", [])

        if not abstract_texts:
            return ""

        parts = []
        for text in abstract_texts:
            label = text.attributes.get("Label", "") if hasattr(text, "attributes") else ""
            content = str(text)
            if label:
                parts.append(f"【{label}】{content}")
            else:
                parts.append(content)

        return "\n".join(parts)