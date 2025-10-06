#!/usr/bin/env python3
"""
大規模運用コスト計算: 月間500投稿×100アカウント
"""

import json

def calculate_large_scale_costs():
    """大規模運用時のコスト計算"""
    
    # 基本パラメータ
    accounts = 100
    posts_per_account_per_month = 500
    total_monthly_posts = accounts * posts_per_account_per_month
    posts_per_account_per_day = posts_per_account_per_month / 30
    
    print("=== 大規模運用コスト予測 ===")
    print(f"アカウント数: {accounts}")
    print(f"1アカウントあたり月間投稿数: {posts_per_account_per_month}")
    print(f"1アカウントあたり1日投稿数: {posts_per_account_per_day:.1f}")
    print(f"全体月間投稿数: {total_monthly_posts:,}")
    print(f"全体1日投稿数: {total_monthly_posts/30:,.0f}")
    
    return calculate_cost_strategies(accounts, posts_per_account_per_month)

def calculate_cost_strategies(accounts, monthly_posts):
    """各戦略のコスト計算"""
    
    strategies = {}
    
    # 1. 完全Cloud Functions構成
    strategies["full_cloud_functions"] = {
        "description": "全アカウントCloud Functions",
        "cost_per_execution": 0.000001,  # $0.000001/実行
        "monthly_executions": accounts * monthly_posts,
        "base_cost": accounts * monthly_posts * 0.000001,
        "additional_costs": {
            "secret_manager": 6.0,  # $6/月 (100アカウントのAPIキー管理)
            "networking": 2.0,      # ネットワーク費用
            "monitoring": 1.0       # ログ・監視
        }
    }
    
    # 2. ハイブリッド構成（投稿頻度別最適化）
    high_freq_accounts = 20   # 1日20投稿以上
    medium_freq_accounts = 40 # 1日10-20投稿  
    low_freq_accounts = 40    # 1日10投稿未満
    
    strategies["hybrid_optimized"] = {
        "description": "投稿頻度別最適化構成",
        "components": {
            "high_frequency_vm": {
                "accounts": high_freq_accounts,
                "method": "プリエンプティブルVM",
                "cost_per_account": 1.07,
                "total": high_freq_accounts * 1.07
            },
            "medium_frequency_vm": {
                "accounts": medium_freq_accounts, 
                "method": "オンデマンドVM",
                "cost_per_account": 0.6,
                "total": medium_freq_accounts * 0.6
            },
            "low_frequency_cf": {
                "accounts": low_freq_accounts,
                "method": "Cloud Functions", 
                "cost_per_account": 0.05,
                "total": low_freq_accounts * 0.05
            }
        },
        "additional_costs": {
            "secret_manager": 6.0,
            "load_balancer": 3.0,   # 負荷分散
            "monitoring": 2.0
        }
    }
    
    # 3. VM中心構成
    strategies["vm_focused"] = {
        "description": "VM中心構成（プリエンプティブル）",
        "vm_cost_per_account": 1.07,
        "total_vm_cost": accounts * 1.07,
        "additional_costs": {
            "secret_manager": 6.0,
            "load_balancer": 5.0,   # より高負荷
            "monitoring": 3.0,
            "storage": 2.0          # ログ保存
        }
    }
    
    # 4. Google Sheets + GAS構成（参考）
    strategies["google_sheets_gas"] = {
        "description": "Google Sheets + GAS構成",
        "base_cost": 0.0,  # 基本無料
        "additional_costs": {
            "google_workspace": 6.0,  # Business Standard (必要に応じて)
            "quota_exceeded": 10.0,   # 大量実行時の追加課金の可能性
        }
    }
    
    return calculate_final_costs(strategies)

def calculate_final_costs(strategies):
    """最終コスト計算と比較"""
    
    results = {}
    
    for name, strategy in strategies.items():
        total_cost = 0
        
        if name == "full_cloud_functions":
            total_cost = strategy["base_cost"]
            total_cost += sum(strategy["additional_costs"].values())
            
        elif name == "hybrid_optimized":
            total_cost = sum(comp["total"] for comp in strategy["components"].values())
            total_cost += sum(strategy["additional_costs"].values())
            
        elif name == "vm_focused":
            total_cost = strategy["total_vm_cost"]
            total_cost += sum(strategy["additional_costs"].values())
            
        elif name == "google_sheets_gas":
            total_cost = sum(strategy["additional_costs"].values())
        
        results[name] = {
            "strategy": strategy,
            "monthly_cost": total_cost,
            "daily_cost": total_cost / 30,
            "cost_per_account": total_cost / 100,
            "cost_per_post": total_cost / 50000
        }
    
    return results

def display_results(results):
    """結果表示"""
    
    print("\n" + "="*60)
    print("コスト比較結果")
    print("="*60)
    
    # コスト順でソート
    sorted_results = sorted(results.items(), key=lambda x: x[1]["monthly_cost"])
    
    for i, (name, data) in enumerate(sorted_results, 1):
        print(f"\n【{i}位】{data['strategy']['description']}")
        print(f"月額コスト: ${data['monthly_cost']:.2f} (約{data['monthly_cost']*150:.0f}円)")
        print(f"1日あたり: ${data['daily_cost']:.2f} (約{data['daily_cost']*150:.0f}円)")
        print(f"1アカウントあたり: ${data['cost_per_account']:.3f} (約{data['cost_per_account']*150:.1f}円)")
        print(f"1投稿あたり: ${data['cost_per_post']:.6f} (約{data['cost_per_post']*150:.3f}円)")
        
        # 詳細内訳
        if name == "hybrid_optimized":
            print("  【内訳】")
            for comp_name, comp_data in data['strategy']['components'].items():
                print(f"    {comp_data['method']}: {comp_data['accounts']}アカウント = ${comp_data['total']:.2f}")
    
    print("\n" + "="*60)
    print("推奨戦略分析")
    print("="*60)
    
    # 最安値
    cheapest = sorted_results[0]
    print(f"💰 最安: {cheapest[1]['strategy']['description']}")
    print(f"   月額: ${cheapest[1]['monthly_cost']:.2f}")
    
    # コスパ最適
    for name, data in sorted_results:
        if name == "hybrid_optimized":
            print(f"⚖️  バランス: {data['strategy']['description']}")
            print(f"   月額: ${data['monthly_cost']:.2f}")
            print(f"   特徴: IP分散効果とコストの最適バランス")
            break

def calculate_scaling_comparison():
    """スケール別コスト比較"""
    
    scales = [
        {"accounts": 10, "posts": 100},
        {"accounts": 50, "posts": 200}, 
        {"accounts": 100, "posts": 500},
        {"accounts": 500, "posts": 200},
        {"accounts": 1000, "posts": 100}
    ]
    
    print("\n" + "="*60)
    print("スケール別コスト比較（ハイブリッド構成）")
    print("="*60)
    
    for scale in scales:
        accounts = scale["accounts"]
        monthly_posts = scale["posts"]
        total_posts = accounts * monthly_posts
        
        # 簡易計算（投稿頻度による分類）
        posts_per_day = monthly_posts / 30
        
        if posts_per_day >= 20:
            cost_per_account = 1.07  # VM
        elif posts_per_day >= 10:
            cost_per_account = 0.6   # オンデマンドVM
        else:
            cost_per_account = 0.05  # Cloud Functions
        
        base_cost = accounts * cost_per_account
        overhead = min(10, accounts * 0.05)  # 最大$10の運用オーバーヘッド
        total_cost = base_cost + overhead
        
        print(f"{accounts:4d}アカウント×{monthly_posts:3d}投稿/月 = 月額${total_cost:6.2f} (1投稿${total_cost/total_posts:.6f})")

if __name__ == "__main__":
    results = calculate_large_scale_costs()
    display_results(results)
    calculate_scaling_comparison()