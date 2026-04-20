"""PubMed論文取得モジュール"""

import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from urllib.parse import urlencode
from typing import List, Dict


def fetch_cluster(query: str, lookback_days: int, max_results: int) -> List[Dict]:
    """
    PubMed E-utilities APIを使用して論文情報を取得
    
    Args:
        query: PubMed検索クエリ
        lookback_days: 検索対象の日数
        max_results: 最大取得件数
        
    Returns:
        論文情報のリスト
    """
    # 日付範囲を計算
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)
    
    # esearch API で PMID を取得
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    search_params = {
        "db": "pubmed",
        "term": f"{query} AND {start_date.strftime('%Y/%m/%d')}:{end_date.strftime('%Y/%m/%d')}[pdat]",
        "retmax": max_results,
        "retmode": "xml",
        "tool": "AuditScope",
        "email": "contact@cursorvers.jp"
    }
    
    # Rate limiting: NCBI推奨の0.34秒間隔
    time.sleep(0.34)
    
    try:
        search_response = requests.get(search_url, params=search_params, 
                                     headers={"User-Agent": "AuditScope/0.1 (+https://cursorvers.jp/tools/auditscope)"})
        search_response.raise_for_status()
        
        # XMLパース
        search_root = ET.fromstring(search_response.text)
        pmids = [id_elem.text for id_elem in search_root.findall(".//Id")]
        
        if not pmids:
            return []
        
        # efetch API で詳細情報を取得
        fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        fetch_params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "tool": "AuditScope",
            "email": "contact@cursorvers.jp"
        }
        
        time.sleep(0.34)
        
        fetch_response = requests.get(fetch_url, params=fetch_params,
                                    headers={"User-Agent": "AuditScope/0.1 (+https://cursorvers.jp/tools/auditscope)"})
        fetch_response.raise_for_status()
        
        # 論文情報を抽出
        papers = []
        fetch_root = ET.fromstring(fetch_response.text)
        
        for article in fetch_root.findall(".//PubmedArticle"):
            paper = extract_paper_info(article)
            if paper:
                papers.append(paper)
        
        return papers
        
    except Exception as e:
        print(f"PubMed fetch error for query '{query}': {e}")
        return []


def extract_paper_info(article_elem) -> Dict:
    """XMLからの論文情報抽出"""
    try:
        # PMID
        pmid_elem = article_elem.find(".//PMID")
        pmid = pmid_elem.text if pmid_elem is not None else ""
        
        # タイトル
        title_elem = article_elem.find(".//ArticleTitle")
        title = title_elem.text if title_elem is not None else ""
        
        # アブストラクト
        abstract_parts = []
        for abstract_text in article_elem.findall(".//AbstractText"):
            if abstract_text.text:
                abstract_parts.append(abstract_text.text)
        abstract = " ".join(abstract_parts) if abstract_parts else ""
        
        # 著者
        authors = []
        for author in article_elem.findall(".//Author"):
            lastname = author.find("LastName")
            forename = author.find("ForeName")
            if lastname is not None and forename is not None:
                authors.append(f"{forename.text} {lastname.text}")
        
        # ジャーナル
        journal_elem = article_elem.find(".//Journal/Title")
        journal = journal_elem.text if journal_elem is not None else ""
        
        # 出版年
        year_elem = article_elem.find(".//PubDate/Year")
        year = year_elem.text if year_elem is not None else ""
        
        # DOI
        doi = ""
        for article_id in article_elem.findall(".//ArticleId"):
            if article_id.get("IdType") == "doi":
                doi = article_id.text
                break
        
        # MeSH terms
        mesh_terms = []
        for mesh in article_elem.findall(".//MeshHeading/DescriptorName"):
            if mesh.text:
                mesh_terms.append(mesh.text)
        
        return {
            "pmid": pmid,
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "journal": journal,
            "year": year,
            "doi": doi,
            "mesh": mesh_terms
        }
        
    except Exception as e:
        print(f"Error extracting paper info: {e}")
        return None