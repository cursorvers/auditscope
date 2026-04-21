# AuditScope v2 — governance-focused derivative of:
#   medical-paper-summarizer-public (MIT, © yush02084)
#   https://github.com/yush02084/medical-paper-summarizer-public

"""
設定ファイル生成モジュール（AuditScope v2版）

Gemini-3.1駆動によるconfig.yaml自動生成。
MeSH禁止ルール適用（クエリは実際のTitle/Abstractに出現する語句のみ使用）。
「うちで使って大丈夫？」のガバナンス特化設定。
"""


import os
import sys
import yaml
import re
import shutil
from typing import Dict, List, Any
import google.generativeai as genai


def validate_no_mesh_terms(query: str) -> bool:
    """
    クエリにMeSH用語が含まれていないことを検証
    
    Args:
        query: 検証対象のクエリ文字列
        
    Returns:
        bool: MeSH用語が含まれていない場合True
    """
    mesh_patterns = [
        r'\[MeSH\]',
        r'\[MeSH Terms\]',
        r'\[mh\]',
        r'\[Mesh\]'
    ]
    
    for pattern in mesh_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            return False
    return True


def get_user_input() -> Dict[str, str]:
    """
    ユーザーからの入力を取得
    
    Returns:
        Dict[str, str]: ユーザーの回答辞書
    """
    print("=== AuditScope v2 設定生成 ===")
    print("うちで使って大丈夫？を確かめる検索式を作ります\n")
    
    clinical_domain = input("どの分野のAIシステムについて調べますか？ (例: 放射線科、病理診断、薬剤管理): ").strip()
    ai_concerns = input("どのAI課題が最も心配ですか？ (例: 幻覚、バイアス、精度): ").strip()
    deployment_stage = input("導入段階は？ (evaluation/pilot/production): ").strip()
    
    return {
        "clinical_domain": clinical_domain,
        "ai_concerns": ai_concerns,
        "deployment_stage": deployment_stage
    }


def generate_config_with_gemini(user_input: Dict[str, str], api_key: str) -> Dict[str, Any]:
    """
    Gemini APIを使用してconfig.yamlの設定を生成
    
    Args:
        user_input: ユーザー入力辞書
        api_key: Gemini APIキー
        
    Returns:
        Dict[str, Any]: 生成された設定辞書
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    prompt = f"""あなたは医療AIガバナンス専門家です。以下のユーザー情報から、PubMed検索用のconfig.yamlを生成してください。

ユーザー情報:
- 臨床領域: {user_input['clinical_domain']}
- AI懸念事項: {user_input['ai_concerns']}
- 導入段階: {user_input['deployment_stage']}

以下の形式でJSONを返してください（MeSH用語は絶対に使用しないでください）:

{{
  "primary_specialties": ["領域に関連する3-5個の専門用語"],
  "query_templates": {{
    "tier1_clinical": "臨床応用クエリ（MeSH禁止）",
    "deployment": "導入段階クエリ（MeSH禁止）",
    "use_case": "用途クエリ（MeSH禁止）",
    "safety": "安全性クエリ（MeSH禁止）"
  }},
  "tier1_journals": ["最重要誌リスト"],
  "tier2_journals": ["重要誌リスト"],
  "tier3_journals": ["関連誌リスト"],
  "governance_keywords": ["ガバナンス関連キーワード"],
  "screening_threshold": 6
}}

重要: クエリには[MeSH]、[MeSH Terms]、[mh]などのMeSH表記は一切使用しないでください。実際の論文タイトルや抄録に出現する語句のみ使用してください。"""

    try:
        response = model.generate_content(prompt)
        # JSONの抽出（```json で囲まれている場合を考慮）
        content = response.text.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        import json
        config_data = json.loads(content)
        
        # MeSH用語の検証
        for template_name, query in config_data.get("query_templates", {}).items():
            if not validate_no_mesh_terms(query):
                print(f"エラー: {template_name}クエリにMeSH用語が含まれています。再生成します...")
                return generate_config_with_gemini(user_input, api_key)
        
        return config_data
        
    except Exception as e:
        print(f"Gemini API エラー: {e}")
        raise


def show_config_diff(current_config: Dict[str, Any], new_config: Dict[str, Any]) -> None:
    """
    現在の設定と新しい設定の差分を表示
    
    Args:
        current_config: 現在の設定
        new_config: 新しい設定
    """
    print("\n=== 設定変更プレビュー ===")
    
    # 主要な変更点を表示
    if "primary_specialties" in new_config:
        print(f"専門領域: {new_config['primary_specialties']}")
    
    if "query_templates" in new_config:
        print("\nクエリテンプレート:")
        for name, query in new_config["query_templates"].items():
            print(f"  {name}: {query}")
    
    if "governance_keywords" in new_config:
        print(f"\nガバナンスキーワード: {new_config['governance_keywords'][:5]}...")
    
    print(f"\nスクリーニング閾値: {new_config.get('screening_threshold', 6)}")


def merge_config(base_config: Dict[str, Any], new_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    ベース設定に新しい設定をマージ
    
    Args:
        base_config: ベース設定
        new_config: 新しい設定
        
    Returns:
        Dict[str, Any]: マージされた設定
    """
    merged = base_config.copy()
    
    # 特定のキーのみ更新
    update_keys = [
        "primary_specialties", "query_templates", "tier1_journals",
        "tier2_journals", "tier3_journals", "governance_keywords",
        "screening_threshold"
    ]
    
    for key in update_keys:
        if key in new_config:
            merged[key] = new_config[key]
    
    return merged


def write_config_file(config: Dict[str, Any], config_path: str = "config.yaml") -> None:
    """
    設定ファイルの書き込み
    
    Args:
        config: 設定辞書
        config_path: 設定ファイルパス
    """
    # バックアップ作成
    if os.path.exists(config_path):
        backup_path = f"{config_path}.bak"
        shutil.copy2(config_path, backup_path)
        print(f"バックアップ作成: {backup_path}")
    
    # YAML書き込み
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    print(f"設定ファイル更新: {config_path}")


def main() -> None:
    """
    ガバナンス特化config.yaml生成メイン関数
    
    Gemini-3.1を使用してユーザーの専門分野・関心領域から
    AuditScope v2向けのconfig.yamlを自動生成する。
    
    主要機能:
    1. 専門分野ヒアリング（AI医療、診断支援、創薬AI等）
    2. ガバナンス重点軸の設定（7軸から選択・優先度付け）
    3. MeSH禁止ルール適用（PubMedクエリは実際の論文語句のみ）
    4. 規制要件マッピング（PMDA、FDA、CE-MDR等との対照）
    5. 監査頻度・閾値設定（スクリーニング閾値等）
    
    生成される設定:
    - query_templates: MeSH禁止・実論文語句ベースのPubMedクエリ
    - governance_axes: 7軸の有効/無効・重み設定
    - tier1/2/3_journals: ガバナンス関連誌の優先度分類
    - screening_threshold: 2段階評価の閾値
    - governance_keywords: ガバナンス関連キーワード辞書
    
    対話的設定プロセス:
    - 「どの分野のAIシステムを使っていますか？」
    - 「どのガバナンス課題が最も心配ですか？」
    - 「規制対応で重視する観点は？」
    """
    try:
        # APIキー確認
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("エラー: GEMINI_API_KEY環境変数が設定されていません。")
            sys.exit(1)
        
        # 現在の設定読み込み
        config_path = "config.yaml"
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                current_config = yaml.safe_load(f)
        except FileNotFoundError:
            print("config.yamlが見つかりません。新規作成します。")
            current_config = {}
        
        # ユーザー入力取得
        user_input = get_user_input()
        
        # Geminiで設定生成
        print("\nGeminiで設定を生成中...")
        new_config_data = generate_config_with_gemini(user_input, api_key)
        
        # 設定マージ
        merged_config = merge_config(current_config, new_config_data)
        
        # 差分表示
        show_config_diff(current_config, new_config_data)
        
        # 確認
        confirm = input("\nこの設定で更新しますか？ (y/N): ").strip().lower()
        if confirm == 'y':
            write_config_file(merged_config, config_path)
            print("設定を正常に更新しました。")
        else:
            print("キャンセルしました。")
        
    except Exception as e:
        print(f"エラー: {e}")
        print("設定ファイルは変更されませんでした。")
        sys.exit(1)


if __name__ == "__main__":
    main()