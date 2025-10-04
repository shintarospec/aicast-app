# Gemini API コスト最適化ガイド

## プロンプト効率化
```python
# ❌ 非効率なプロンプト例
prompt = f"""
あなたは{character_name}として投稿を作成してください。
キャラクター設定:
{long_character_description}  # 毎回長い説明
今日の話題について投稿してください。
投稿は200文字程度で、以下の条件を満たしてください:
- 条件1...
- 条件2...
"""

# ✅ 効率化されたプロンプト例  
prompt = f"""
{character_name}投稿作成:
設定:{character_short_profile}  # 要点のみ
話題:{topic}
条件:簡潔/200文字/口調一致
"""
```

## バッチ処理最適化
```python
# ✅ 複数投稿を一度に生成
def batch_generate_posts(character, topics, count=5):
    prompt = f"""
{character}として以下トピックの投稿を{count}件作成:
{', '.join(topics)}
各投稿200文字、番号付きで出力
"""
    return generate_content(prompt)
```

## キャッシュ活用
```python
# ✅ 類似投稿の再利用
def get_cached_or_generate(character, topic):
    cache_key = f"{character}_{topic_hash(topic)}"
    if cache_key in post_cache:
        return modify_cached_post(cache_key)
    return generate_new_post(character, topic)
```

## トークン使用量監視
```python
# ✅ API使用量追跡
def track_api_usage(prompt, response):
    input_chars = len(prompt)
    output_chars = len(response)
    
    monthly_usage['input'] += input_chars
    monthly_usage['output'] += output_chars
    
    # 警告しきい値
    if monthly_usage['total_cost'] > BUDGET_ALERT:
        send_budget_alert()
```

## 月間コスト予測
- 控えめ使用: 2,060円/月
- 標準使用: 2,520円/月  
- 活発使用: 3,280円/月
- フル活用: 4,040円/月

## さくらVPS + Gemini の優位性
✅ 月額2,520円で5万投稿生成
✅ GPT-3.5の1/2以下のコスト
✅ インフラ込みでも格安運用
✅ スケーラブルな料金体系