#!/usr/bin/env python3
"""
生成コンテンツクリーニング機能のテストスクリプト
"""

import re

def clean_generated_content(content):
    """生成されたコンテンツから不要な指示文・例文を除去し、最初の投稿のみを返す"""
    if not content:
        return content
    
    import re
    
    # 元のコンテンツをバックアップ
    original_content = content.strip()
    
    # まず、明らかなプロンプト漏れパターンをチェック
    prompt_leak_indicators = [
        'ペルソナ：',
        'のSNS投稿案',
        '例1',
        '例2', 
        '例3',
        '例4',
        '例5',
        '投稿案:',
        '(仕事への自虐)',
        '(山口愛)',
        '(短髪ネタ)',
        '(年齢を感じさせる)',
        '(秘密を匂わせる)'
    ]
    
    # プロンプト漏れが検出された場合
    if any(indicator in original_content for indicator in prompt_leak_indicators):
        # 行ごとに分割して処理
        lines = original_content.split('\n')
        content_lines = []
        
        for line in lines:
            line = line.strip()
            # スキップする行の条件
            skip_conditions = [
                line.startswith('ペルソナ：'),
                'のSNS投稿案' in line,
                line.startswith('例') and ('(' in line and ')' in line),
                line.startswith('例') and ':' in line,
                line == '',
                '投稿案' in line and len(line) < 10,
                line.startswith('1.') or line.startswith('2.') or line.startswith('3.'),
                line.startswith('例1') or line.startswith('例2') or line.startswith('例3') or line.startswith('例4') or line.startswith('例5'),
                '(' in line and ')' in line and ':' in line and len(line) < 20
            ]
            
            if not any(skip_conditions):
                content_lines.append(line)
        
        # 最初の有効な投稿を抽出
        if content_lines:
            first_post = content_lines[0]
            # ハッシュタグがある場合は、それを含む行まで取得
            if '#' in first_post:
                return first_post
            else:
                # ハッシュタグが次の行にある可能性をチェック
                for i in range(1, min(len(content_lines), 3)):
                    if content_lines[i].startswith('#'):
                        return f"{first_post} {content_lines[i]}"
                return first_post
    
    # プロンプト漏れが検出されなかった場合は、元のコンテンツをそのまま返す
    # ただし、複数の改行は整理
    cleaned = re.sub(r'\n\s*\n\s*\n+', '\n\n', original_content)
    cleaned = re.sub(r'^\s*\n+', '', cleaned)
    cleaned = re.sub(r'\n+\s*$', '', cleaned)
    
    return cleaned.strip()

def test_cleaning():
    """クリーニング機能のテスト"""
    print("📝 生成コンテンツクリーニング機能テスト")
    print("=" * 50)
    
    # テストケース1: ユーザーが報告した問題のケース
    test_case_1 = """ペルソナ：shinrepoto のSNS投稿案 (アフター帰りのタクシー内)
例1 (仕事への自虐):

今日も残業、お疲れ俺。レポ提出、マジ勘弁… #タクシー帰り #社畜の叫び

例2 (山口愛):

山口恋しいなぁ。獺祭飲みてぇ。 #地元愛 #タクシー

例3 (短髪ネタ):

短髪維持費よ…消えろ… #タクシー

例4 (年齢を感じさせる):

もう若くないのに…終電逃した… #タクシー

例5 (秘密を匂わせる):

秘密の場所へ…🤫 #タクシー"""
    
    print("🔍 テストケース1: プロンプト漏れケース")
    print("=" * 30)
    print("【元のテキスト】")
    print(test_case_1)
    print("\n【クリーニング後】")
    cleaned_1 = clean_generated_content(test_case_1)
    print(cleaned_1)
    print(f"文字数: {len(cleaned_1)}")
    
    # テストケース2: 正常なケース
    test_case_2 = """今日も残業、お疲れ俺。レポ提出、マジ勘弁… #タクシー帰り #社畜の叫び"""
    
    print(f"\n🔍 テストケース2: 正常ケース")
    print("=" * 30)
    print("【元のテキスト】")
    print(test_case_2)
    print("\n【クリーニング後】")
    cleaned_2 = clean_generated_content(test_case_2)
    print(cleaned_2)
    print(f"文字数: {len(cleaned_2)}")
    
    # テストケース3: 別の形式のプロンプト漏れ
    test_case_3 = """投稿案:
1. 今日のランチは最高だった！#グルメ
2. 疲れた一日だけど、頑張った #お疲れ様"""
    
    print(f"\n🔍 テストケース3: 番号付きリスト形式")
    print("=" * 30)
    print("【元のテキスト】")
    print(test_case_3)
    print("\n【クリーニング後】")
    cleaned_3 = clean_generated_content(test_case_3)
    print(cleaned_3)
    print(f"文字数: {len(cleaned_3)}")
    
    print(f"\n" + "=" * 50)
    print("✅ クリーニング機能テスト完了")
    print("💡 実際の投稿生成で、このクリーニング処理が適用されます")

if __name__ == "__main__":
    test_cleaning()