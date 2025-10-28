#!/usr/bin/env python3
"""
承認済み一覧のUI簡略化スクリプト
- 送信先をX送信のみに固定
- 時刻設定を投稿下に配置（コンパクト化）
- 直接入力のみに簡略化
"""

# app.pyを読み込む
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 置き換え対象の開始・終了マーカーを探す
start_marker = "# 2行目: 時刻設定とアクションボタン（コンパクト版）"
end_marker = "if st.button(button_label, key=f\"send_{post['id']}\", type=\"primary\", use_container_width=True):"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx)

if start_idx == -1 or end_idx == -1:
    print("❌ マーカーが見つかりませんでした")
    print(f"start_idx: {start_idx}, end_idx: {end_idx}")
    exit(1)

print(f"✅ マーカー発見: {start_idx} 〜 {end_idx}")

# 新しいコードを作成
new_code = '''# 2行目: 時刻設定とアクションボタン（コンパクト＆シンプル版）
                            col_time, col_btn = st.columns([4, 1])
                            
                            with col_time:
                                # 時刻取得の優先順位（scheduled_at > posted_at > created_at）
                                now = datetime.datetime.now(JST)
                                today = datetime.date.today()
                                current_datetime = None
                                
                                if post['scheduled_at']:
                                    current_datetime = safe_datetime_parse(post['scheduled_at'])
                                elif post['posted_at']:
                                    current_datetime = safe_datetime_parse(post['posted_at'])
                                else:
                                    current_datetime = safe_datetime_parse(post['created_at'])
                                
                                # パース失敗時は現在時刻 + 10分
                                if not current_datetime:
                                    current_datetime = datetime.datetime.now() + datetime.timedelta(minutes=10)
                                
                                # 過去の投稿の場合は現在時刻を初期値に
                                if current_datetime.date() < today:
                                    initial_date = today
                                    initial_hour = now.hour
                                    initial_minute = now.minute
                                else:
                                    initial_date = current_datetime.date()
                                    initial_hour = current_datetime.hour
                                    initial_minute = current_datetime.minute
                                
                                # コンパクトな時刻設定UI（横並び）
                                col_date, col_hour, col_min = st.columns([2.5, 1, 1])
                                
                                with col_date:
                                    send_date = st.date_input(
                                        "📅",
                                        value=initial_date,
                                        min_value=today,
                                        key=f"send_date_{post['id']}"
                                    )
                                
                                with col_hour:
                                    send_hour = st.number_input(
                                        "時",
                                        min_value=0,
                                        max_value=23,
                                        value=initial_hour,
                                        key=f"hour_{post['id']}"
                                    )
                                
                                with col_min:
                                    send_minute = st.number_input(
                                        "分",
                                        min_value=0,
                                        max_value=59,
                                        value=initial_minute,
                                        key=f"minute_{post['id']}"
                                    )
                                
                                # 送信時刻の計算
                                send_time = datetime.time(send_hour, send_minute)
                                scheduled_datetime = datetime.datetime.combine(send_date, send_time)
                            
                            with col_btn:
                                # X送信のみに固定
                                destination_value = "x_api"
                                
                                if st.button("🐦 X送信", key=f"send_{post['id']}\", type="primary", use_container_width=True):'''

# 置き換え実行
new_content = content[:start_idx] + new_code + '\n                                    ' + content[end_idx:]

# ファイルに書き込み
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✅ app.py を更新しました")
print(f"📝 変更箇所: {start_idx} 〜 {end_idx}")
print(f"📏 変更前の長さ: {end_idx - start_idx} 文字")
print(f"📏 変更後の長さ: {len(new_code)} 文字")
print(f"📊 削減量: {end_idx - start_idx - len(new_code)} 文字")
