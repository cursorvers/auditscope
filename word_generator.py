# AuditScope v2 — governance-focused derivative of:
#   medical-paper-summarizer-public (MIT, © yush02084)
#   https://github.com/yush02084/medical-paper-summarizer-public

"""
Word文書生成モジュール（AuditScope v2版）

ガバナンス評価結果をWord文書として構造化出力。
「うちで使って大丈夫？」の臨床医向けレポート生成。
"""

import hashlib
import os
import yaml
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path
from docx import Document
from docx.shared import Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.shared import OxmlElement, qn

from pubmed_searcher import Paper


def set_japanese_font(document):
    """文書全体のデフォルトフォントを日本語対応に設定"""
    style = document.styles['Normal']
    font = style.font
    font.name = 'Yu Gothic'
    font.size = None  # デフォルトサイズを使用


def add_cell_shading(cell, color_rgb):
    """セルに背景色を追加"""
    shading_elm = OxmlElement("w:shd")
    shading_elm.set(qn("w:fill"), color_rgb)
    cell._tc.get_or_add_tcPr().append(shading_elm)


def truncate_title(title, max_length=50):
    """タイトルを指定文字数で切り詰め"""
    if len(title) <= max_length:
        return title
    return title[:max_length-3] + "..."


def get_risk_level(summaries_entry):
    """サマリーエントリからリスクレベルを決定"""
    if not summaries_entry or not summaries_entry.get("detailed"):
        return "low"
    
    axes = summaries_entry.get("detailed", {}).get("axes", {})
    risk_ratings = []
    
    for axis_data in axes.values():
        rating = axis_data.get("rating", "n/a")
        if rating == "high":
            risk_ratings.append(3)
        elif rating == "medium":
            risk_ratings.append(2)
        elif rating == "low":
            risk_ratings.append(1)
    
    if not risk_ratings:
        return "low"
    
    max_risk = max(risk_ratings)
    if max_risk >= 3:
        return "high"
    elif max_risk >= 2:
        return "medium"
    else:
        return "low"


def get_risk_color(risk_level):
    """リスクレベルに応じた色を返す"""
    colors = {
        "low": "90EE90",    # lightgreen
        "medium": "FFFF99", # lightyellow  
        "high": "FFB6C1"    # lightpink
    }
    return colors.get(risk_level, "FFFFFF")


def calculate_config_hash():
    """config.yamlのハッシュを計算"""
    try:
        with open("config.yaml", "r", encoding="utf-8") as f:
            content = f.read()
        return hashlib.sha256(content.encode()).hexdigest()[:8]
    except Exception:
        return "unknown"


def generate_report(papers: list, summaries: list, output_path: Path) -> Path:
    """
    Generate AuditScope v2 governance report (.docx).
    papers: [{pmid, title, authors, journal, pub_date, abstract, ...}]
    summaries: [{paper_id, title, screening, detailed}] from ai_summarizer.py
    output_path: target .docx path
    Returns: output_path (confirmation)
    """
    # Create output directory if needed
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create new document
    doc = Document()
    set_japanese_font(doc)
    
    # Convert summaries list to dict for easy lookup
    summaries_dict = {}
    if summaries:
        for summary in summaries:
            paper_id = summary.get("paper_id", "")
            if paper_id.startswith("PMID:"):
                pmid = paper_id[5:]  # Remove "PMID:" prefix
                summaries_dict[pmid] = summary
    
    # Filter papers that passed screening (if any summaries exist)
    screening_passed_papers = []
    screening_failed_papers = []
    
    if summaries_dict:
        for paper in papers:
            summary = summaries_dict.get(paper.pmid, {})
            screening = summary.get("screening", {})
            relevance = screening.get("relevance", 0)
            
            # Assume screening threshold of 6 based on ai_summarizer.py default
            if relevance >= 6:
                screening_passed_papers.append(paper)
            else:
                screening_failed_papers.append(paper)
    else:
        screening_passed_papers = papers
    
    # 1. Header Section
    header = doc.add_paragraph()
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = header.add_run("AuditScope v2 — うちで使って大丈夫？レポート")
    title_run.bold = True
    title_run.font.size = doc.styles['Title'].font.size
    
    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    now_jst = datetime.now().strftime("%Y-%m-%d %H:%M")
    total_papers = len(papers)
    subtitle_text = f"生成日 {now_jst} (JST) / 対象論文 {total_papers} 件"
    subtitle.add_run(subtitle_text)
    
    hero_line = doc.add_paragraph()
    hero_line.alignment = WD_ALIGN_PARAGRAPH.CENTER
    hero_run = hero_line.add_run("「臨床医の自問をそのまま検査項目に変換しました」")
    hero_run.italic = True
    
    doc.add_paragraph()  # Spacing
    
    # 2. Risk-rating Summary Section
    doc.add_heading("リスク評価サマリー", level=1)
    
    if not papers:
        no_papers_para = doc.add_paragraph()
        no_papers_para.add_run("対象論文なし ー 検索結果ゼロまたは全件 screening 未通過")
    else:
        # Create risk summary table
        table = doc.add_table(rows=1, cols=4)
        table.style = 'Table Grid'
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        
        # Header row
        header_cells = table.rows[0].cells
        header_cells[0].text = "論文タイトル"
        header_cells[1].text = "relevance"
        header_cells[2].text = "overall risk"
        header_cells[3].text = "risk_flags"
        
        for cell in header_cells:
            cell.paragraphs[0].runs[0].bold = True
        
        # Add rows for screening passed papers
        for paper in screening_passed_papers:
            row_cells = table.add_row().cells
            
            # Title (truncated)
            row_cells[0].text = truncate_title(paper.title)
            
            # Get summary data
            summary = summaries_dict.get(paper.pmid, {})
            screening = summary.get("screening", {})
            relevance = screening.get("relevance", 0)
            risk_flags = screening.get("risk_flags", [])
            
            # Relevance
            row_cells[1].text = str(relevance)
            
            # Overall risk
            risk_level = get_risk_level(summary)
            row_cells[2].text = risk_level
            
            # Apply color coding
            risk_color = get_risk_color(risk_level)
            add_cell_shading(row_cells[2], risk_color)
            
            # Risk flags
            row_cells[3].text = ", ".join(risk_flags) if risk_flags else "なし"
        
        # Add section for screening failed papers
        if screening_failed_papers:
            doc.add_paragraph()
            failed_heading = doc.add_paragraph()
            failed_heading.add_run("screening 未通過:").bold = True
            for paper in screening_failed_papers:
                failed_para = doc.add_paragraph(style='List Bullet')
                failed_para.add_run(f"{truncate_title(paper.title)} (screening 未通過)")
    
    # 3. Per-paper Detail Section
    if screening_passed_papers:
        doc.add_page_break()
        doc.add_heading("詳細評価", level=1)
        
        for i, paper in enumerate(screening_passed_papers, 1):
            # Section heading
            doc.add_heading(f"[{i}] {paper.title}", level=2)
            
            # Metadata block
            meta_para = doc.add_paragraph()
            meta_para.add_run("PMID: ").bold = True
            meta_para.add_run(f"{paper.pmid}\n")
            meta_para.add_run("Journal: ").bold = True
            meta_para.add_run(f"{paper.journal}\n")
            meta_para.add_run("Publication Date: ").bold = True
            meta_para.add_run(f"{paper.pub_date}\n")
            meta_para.add_run("Authors: ").bold = True
            
            # Format authors (first 3 + et al.)
            if paper.authors:
                if len(paper.authors) <= 3:
                    authors_text = ", ".join(paper.authors)
                else:
                    authors_text = ", ".join(paper.authors[:3]) + " et al."
                meta_para.add_run(authors_text)
            else:
                meta_para.add_run("Not available")
            
            # Get summary for this paper
            summary = summaries_dict.get(paper.pmid, {})
            detailed = summary.get("detailed", {})
            
            if detailed:
                # 結論
                conclusion_para = doc.add_paragraph()
                conclusion_para.add_run("結論: ").bold = True
                conclusion_text = detailed.get("conclusion", "評価データが不十分です")
                conclusion_para.add_run(conclusion_text)
                
                # 自問3チェック
                self_doubt = detailed.get("self_doubt_3", [])
                if self_doubt:
                    doc.add_paragraph().add_run("自問3チェック:").bold = True
                    for question in self_doubt:
                        bullet_para = doc.add_paragraph(style='List Bullet')
                        bullet_para.add_run(question)
                
                # 7軸評価 matrix
                axes = detailed.get("axes", {})
                if axes:
                    doc.add_paragraph().add_run("7軸評価:").bold = True
                    
                    axes_table = doc.add_table(rows=1, cols=3)
                    axes_table.style = 'Table Grid'
                    
                    # Header
                    header_cells = axes_table.rows[0].cells
                    header_cells[0].text = "評価軸"
                    header_cells[1].text = "評価"
                    header_cells[2].text = "根拠"
                    
                    for cell in header_cells:
                        cell.paragraphs[0].runs[0].bold = True
                    
                    # Add axis data
                    for axis_name, axis_data in axes.items():
                        row_cells = axes_table.add_row().cells
                        row_cells[0].text = axis_name
                        
                        rating = axis_data.get("rating", "n/a")
                        row_cells[1].text = rating
                        
                        # Color code rating cell
                        if rating == "high":
                            add_cell_shading(row_cells[1], "FFB6C1")  # light pink
                        elif rating == "medium":
                            add_cell_shading(row_cells[1], "FFFF99")  # light yellow
                        elif rating == "low":
                            add_cell_shading(row_cells[1], "90EE90")  # light green
                        
                        rationale = axis_data.get("rationale", "評価根拠なし")
                        row_cells[2].text = rationale
            
            # Raw abstract (collapsed/footnote block)
            if paper.abstract:
                doc.add_paragraph()
                abstract_heading = doc.add_paragraph()
                abstract_heading.add_run("要旨:").bold = True
                abstract_para = doc.add_paragraph()
                abstract_run = abstract_para.add_run(paper.abstract)
                abstract_run.font.size = doc.styles['Normal'].font.size
                
            doc.add_paragraph()  # Spacing between papers
    
    # 4. Crosswalk References Section
    doc.add_page_break()
    doc.add_heading("クロスウォーク参照", level=1)
    
    # Try to read crosswalk refs from config
    try:
        with open("config.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        crosswalk_refs = config.get("crosswalk_refs", {})
        
        if crosswalk_refs:
            for ref_type, refs in crosswalk_refs.items():
                ref_para = doc.add_paragraph()
                ref_para.add_run(f"{ref_type}: ").bold = True
                if isinstance(refs, list):
                    ref_para.add_run(", ".join(refs))
                else:
                    ref_para.add_run(str(refs))
        else:
            doc.add_paragraph("※ crosswalk は config.yaml 未設定")
            
    except Exception:
        doc.add_paragraph("※ crosswalk は config.yaml 未設定")
    
    # 5. Footer Section
    doc.add_page_break()
    doc.add_heading("生成メタデータ", level=1)
    
    # Generation metadata
    meta_para = doc.add_paragraph()
    meta_para.add_run("ツールバージョン: ").bold = True
    meta_para.add_run("AuditScope v2.0.328\n")
    meta_para.add_run("設定ハッシュ: ").bold = True
    config_hash = calculate_config_hash()
    meta_para.add_run(f"sha256:{config_hash}\n")
    
    # Audit trail pointer
    audit_para = doc.add_paragraph()
    audit_para.add_run("詳細ログ: ").bold = True
    audit_para.add_run("logs/audit.jsonl")
    
    doc.add_paragraph()
    
    # Legal footer
    legal_para = doc.add_paragraph()
    legal_text = ("本レポートは臨床判断の支援ツールです。"
                  "患者個別の診療判断に代わるものではありません。")
    legal_para.add_run(legal_text).italic = True
    
    # MIT attribution
    mit_para = doc.add_paragraph()
    mit_text = ("本ツールは yush02084/medical-paper-summarizer-public (MIT) の派生物です")
    mit_para.add_run(mit_text).italic = True
    
    # Save document
    try:
        doc.save(str(output_path))
    except Exception as e:
        raise Exception(f"Word文書の保存に失敗しました: {e}")
    
    return output_path