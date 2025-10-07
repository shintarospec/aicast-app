-- AIcast Room データベースダンプ
-- 作成日時: 2025-10-06 05:11:26.246325
-- 元ファイル: casting_office.db
-- MCF DEATH GUARD事故復旧版

BEGIN TRANSACTION;
CREATE TABLE advice_master (id INTEGER PRIMARY KEY, content TEXT NOT NULL UNIQUE);
INSERT INTO "advice_master" VALUES(1,'もっと可愛く');
INSERT INTO "advice_master" VALUES(2,'もっと大人っぽく');
INSERT INTO "advice_master" VALUES(3,'意外な一面を見せて');
INSERT INTO "advice_master" VALUES(4,'豆知識を加えて');
INSERT INTO "advice_master" VALUES(5,'句読点を工夫して');
INSERT INTO "advice_master" VALUES(6,'少しユーモアを');
INSERT INTO "advice_master" VALUES(7,'漢字を少なく');
CREATE TABLE analytics (
        id INTEGER PRIMARY KEY,
        cast_id INTEGER,
        date TEXT,
        posts_created INTEGER DEFAULT 0,
        posts_approved INTEGER DEFAULT 0,
        posts_sent INTEGER DEFAULT 0,
        avg_word_count REAL DEFAULT 0.0,
        engagement_score REAL DEFAULT 0.0,
        FOREIGN KEY(cast_id) REFERENCES casts(id) ON DELETE CASCADE
    );
CREATE TABLE app_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL, description TEXT DEFAULT '', category TEXT DEFAULT 'general');
INSERT INTO "app_settings" VALUES('default_char_limit','60','デフォルト文字数制限','投稿生成');
INSERT INTO "app_settings" VALUES('default_post_count','5','デフォルト生成数','投稿生成');
INSERT INTO "app_settings" VALUES('situation_placeholder','例：お気に入りの喫茶店で読書中','シチュエーション入力プレースホルダ','UI設定');
INSERT INTO "app_settings" VALUES('campaign_placeholder','例：「グッチセール」というキーワードと、URL「https://gucci.com/sale」を必ず文末に入れて、セールをお知らせする投稿を作成してください。','一斉指示プレースホルダ','UI設定');
INSERT INTO "app_settings" VALUES('name_pairs_placeholder','例：
@hanao_tanaka,田中 花音
@misaki_sato,佐藤 美咲
@aina_suzuki,鈴木 愛菜','名前ペア入力プレースホルダ','UI設定');
INSERT INTO "app_settings" VALUES('ai_generation_instruction','魅力的で個性豊かなキャラクター','AI生成時のデフォルト指示','AI設定');
INSERT INTO "app_settings" VALUES('default_char_count','300','デフォルト文字数','投稿生成');
INSERT INTO "app_settings" VALUES('default_placeholder','今日の出来事について教えて','デフォルトプレースホルダー','投稿生成');
INSERT INTO "app_settings" VALUES('ai_temperature','0.8','AI創造性レベル','AI設定');
INSERT INTO "app_settings" VALUES('ai_max_tokens','1000','AI最大トークン数','AI設定');
INSERT INTO "app_settings" VALUES('ui_theme_color','#FF6B6B','テーマカラー','UI設定');
INSERT INTO "app_settings" VALUES('ui_sidebar_width','300','サイドバー幅','UI設定');
INSERT INTO "app_settings" VALUES('cast_name_placeholder','星野 詩織','名前プレースホルダー','キャスト管理');
INSERT INTO "app_settings" VALUES('cast_nickname_placeholder','しおりん','ニックネームプレースホルダー','キャスト管理');
INSERT INTO "app_settings" VALUES('cast_age_placeholder','21歳','年齢プレースホルダー','キャスト管理');
INSERT INTO "app_settings" VALUES('cast_birthday_placeholder','10月26日','誕生日プレースホルダー','キャスト管理');
INSERT INTO "app_settings" VALUES('cast_birthplace_placeholder','神奈川県','出身地プレースホルダー','キャスト管理');
INSERT INTO "app_settings" VALUES('cast_appearance_placeholder','黒髪ロングで物静かな雰囲気。古着のワンピースをよく着ている。','外見の特徴プレースホルダー','キャスト管理');
INSERT INTO "app_settings" VALUES('cast_personality_placeholder','物静かで穏やかな聞き上手','性格プレースホルダー','キャスト管理');
INSERT INTO "app_settings" VALUES('cast_strength_placeholder','人の話に深く共感できる','長所プレースホルダー','キャスト管理');
INSERT INTO "app_settings" VALUES('cast_weakness_placeholder','少し人見知り','短所プレースホルダー','キャスト管理');
INSERT INTO "app_settings" VALUES('cast_first_person_placeholder','私','一人称プレースホルダー','キャスト管理');
INSERT INTO "app_settings" VALUES('cast_speech_style_placeholder','です・ます調の丁寧な言葉遣い','口調・語尾プレースホルダー','キャスト管理');
INSERT INTO "app_settings" VALUES('cast_catchphrase_placeholder','「なんだか、素敵ですね」','口癖プレースホルダー','キャスト管理');
INSERT INTO "app_settings" VALUES('cast_occupation_placeholder','文学部の女子大生','職業・学業プレースホルダー','キャスト管理');
INSERT INTO "app_settings" VALUES('cast_hobby_placeholder','読書、フィルムカメラ、古い喫茶店巡り','趣味や特技プレースホルダー','キャスト管理');
INSERT INTO "app_settings" VALUES('cast_likes_placeholder','雨の日の匂い、万年筆のインク','好きなものプレースホルダー','キャスト管理');
INSERT INTO "app_settings" VALUES('cast_dislikes_placeholder','大きな音、人混み','嫌いなものプレースホルダー','キャスト管理');
INSERT INTO "app_settings" VALUES('cast_holiday_activity_placeholder','一日中家で本を読んでいるか、目的もなく電車に乗る','休日の過ごし方プレースホルダー','キャスト管理');
INSERT INTO "app_settings" VALUES('cast_dream_placeholder','自分の言葉で、誰かの心を動かす物語を紡ぐこと','将来の夢プレースホルダー','キャスト管理');
INSERT INTO "app_settings" VALUES('cast_reason_for_job_placeholder','様々な人の物語に触れたいから','なぜこの仕事をしているのかプレースホルダー','キャスト管理');
INSERT INTO "app_settings" VALUES('cast_secret_placeholder','実は、大のSF小説好き','ちょっとした秘密プレースホルダー','キャスト管理');
INSERT INTO "app_settings" VALUES('cast_customer_interaction_placeholder','お客様の心に寄り添うように、静かに話を聞く','お客様への接し方プレースホルダー','キャスト管理');
CREATE TABLE cast_action_sheets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cast_id INTEGER NOT NULL,
    action_type TEXT NOT NULL,  -- 'post', 'repost', 'quote_tweet', etc.
    spreadsheet_id TEXT NOT NULL,
    sheet_name TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, gas_web_app_url TEXT,
    FOREIGN KEY (cast_id) REFERENCES casts (id) ON DELETE CASCADE,
    UNIQUE(cast_id, action_type)
);
INSERT INTO "cast_action_sheets" VALUES(1,14,'post','1Id8ESPBu0ueHAbUbOHCEHhrR1xbZIcHocB1TBt7Ij_g','投稿メッセージリスト',1,'2025-09-27 09:44:48','2025-09-27 09:44:48',NULL);
INSERT INTO "cast_action_sheets" VALUES(2,14,'retweet','1Id8ESPBu0ueHAbUbOHCEHhrR1xbZIcHocB1TBt7Ij_g','リツイート予約リスト',1,'2025-09-27 10:09:36','2025-09-27 10:09:36',NULL);
CREATE TABLE cast_groups (cast_id INTEGER, group_id INTEGER, PRIMARY KEY (cast_id, group_id), FOREIGN KEY(cast_id) REFERENCES casts(id) ON DELETE CASCADE, FOREIGN KEY(group_id) REFERENCES groups(id) ON DELETE CASCADE);
CREATE TABLE "cast_sheets_config" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cast_id INTEGER NOT NULL,
    spreadsheet_id TEXT NOT NULL,
    sheet_name TEXT DEFAULT 'Sheet1',
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cast_id) REFERENCES casts (id) ON DELETE CASCADE,
    UNIQUE(cast_id)
);
INSERT INTO "cast_sheets_config" VALUES(1,14,'1Id8ESPBu0ueHAbUbOHCEHhrR1xbZIcHocB1TBt7Ij_g','投稿メッセージリスト',1,'2025-09-27 08:32:27','2025-09-27 08:32:27');
CREATE TABLE cast_x_credentials (id INTEGER PRIMARY KEY, cast_id INTEGER UNIQUE, api_key TEXT, api_secret TEXT, bearer_token TEXT, access_token TEXT, access_token_secret TEXT, twitter_username TEXT, twitter_user_id TEXT, is_active INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(cast_id) REFERENCES casts(id) ON DELETE CASCADE);
INSERT INTO "cast_x_credentials" VALUES(1,11,'NBQKr7WokZ6zXKwRJ8908N0Jd','8w2mfWaaY09fsW4QtFAs6BLRN9fYENykFx6FD5INygw6Mcf1LV','AAAAAAAAAAAAAAAAAAAAAK%2F%2F3AEAAAAAxkfO9EMZjrwqi9%2Fqu%2Bph7CKflTg%3Dk1TfIaMbIgFRSYinpm2EHYQGrZ7P5HG0pgfuVSuB1qDkP0CFmB','1750849004127027200-tvEKrxIqB8Ep7Y9iKDoHkAMNWsD1Y7','jLaahC3R3Uvrw13VaFLzIQwztyVYmnKjn7PdoNWGoEp3S','4te_123','1750849004127027200',1,'2025-09-26 16:50:43','2025-09-26 16:50:43');
INSERT INTO "cast_x_credentials" VALUES(2,14,'kglLQwyirrSPH58RkLgH3z1Xm','KAipbhG3IasxBbTS9lRP5OotN8SF4t3uqeHFdlRGzvhSO8bNKp','AAAAAAAAAAAAAAAAAAAAAMwe1QEAAAAA8Hc0EiAE6A%2BGO4%2BSDuLKIjJD5ec%3DAKjyCaCKrGKbjAuFj5Aw68jyrl8Dnns9kcu0suUthVQI8ZHSKH','1788088727249862656-RuvlWDJnn0IqmRGuDb7zzXnL5BTHrQ','Mb58whxS1Qr5lRklamelHVb30qMgV2aIkkJ3lsYMhKLUb','shinrepoto','1788088727249862656',1,'2025-09-27 00:33:48','2025-09-27 00:41:06');
INSERT INTO "cast_x_credentials" VALUES(3,13,'21n18of1jgBZEwddFBDTINTHJ','rD0wQudGqM5d1dQFrPpKOGRqp5zmwMe6eLnONA9q2XLA23pFPV','AAAAAAAAAAAAAAAAAAAAAB8A3QEAAAAAogG3vs2jSSHbdYE3qRrvWrD9fTc%3DoIGk9kJLCRjtLpsXgUhRVzDCbQxj18vpgIRNSswLbgzSsv7a8D','1750091359082414080-nRH7vdlt4TaS8FDRojxUQxJ4FWUdje','lvKrXFZvJRqEOgHnLtpkfI7oulTjAjwXZykkf6II0Ycoq','kawa_saki_style','1750091359082414080',1,'2025-10-02 09:30:35','2025-10-02 09:30:35');
INSERT INTO "cast_x_credentials" VALUES(4,12,'WeeFxYAETSRO0SiRYXpCnHSCO','Hdrfjd8KP4RYW0WMgxNxSFvLx6c8xmVLcJfpWEWA3a06fJUhb0','AAAAAAAAAAAAAAAAAAAAAMX%2F3AEAAAAAoOU8fkAu3w0p7wxhYiF48c0CZw4%3DlUzKmNBh8zuo4pPIQ6ISsES8zAX7v2tSmGjGqFMTEsVQYF5Il0','1748654336987504640-lNGX0HB35ShMfud66zUqIU9VooHdKi','di1SqY3kmBvsC1A8K1ama96p3snMh8nMTOWPkNvaVSAaP','kurumibutterfly','1748654336987504640',1,'2025-10-02 15:27:22','2025-10-02 15:27:22');
INSERT INTO "cast_x_credentials" VALUES(5,15,'co9zYag0ch1u6O9AxGMkLHYTo','2ilkr0yCtjxXYMIWS7MDtMAfbjOBztzcJVvf0UZNmJ3N2hXYG9','AAAAAAAAAAAAAAAAAAAAAC8A3QEAAAAAPyA42xjNL5fcr4TgTyDaK3Wltc0%3D4gyUTmJn2aHlXclQFmxuIRydo9pYZhoK3s1RdBosAd5CQzJuhB','1741902536380936192-cPfLewKF5O6cqL7bOI8xLujZziMWcC','aOlGNNzjwIoTEjqik0AQr84P9l3Fuu1xFqK5TpKQqAJMf','Hiranonorico','1741902536380936192',1,'2025-10-02 16:15:24','2025-10-02 16:15:24');
INSERT INTO "cast_x_credentials" VALUES(6,9,'05YffGhlLOSiUOZUurAoMMh3K','fkQuByvPVpMExmSlBHHajSoUMHkBbb3xOGmWFOfzUdUX9iIr3b','AAAAAAAAAAAAAAAAAAAAACyH3AEAAAAAQXfiit7yIhe884XC9G3uTPEyAkg%3DMMMzfDcc41S9cQnET0WDSf4vMvvPqRLZybiwcnDrZ46AKSjrRa','1748344026091184128-zXfD0UIAMC6oRZTcYBBlsTaawVl8kG','XIZYLILE1Auj1hLW2bpW12WmYVZTYExWfy4gHK8Vc5AxW','maple_toki','1748344026091184128',1,'2025-10-03 03:39:03','2025-10-03 03:39:03');
INSERT INTO "cast_x_credentials" VALUES(7,16,'FGyZW2xD8DBJev0lgGZIDbANy','F97yzE5KWCoMUdGz6g9M0Q5ke0qjnG9W3D0X87zPHeLwUfOMCZ','AAAAAAAAAAAAAAAAAAAAAF8J3gEAAAAAefgwku4aTAOwnm2z5j8TShQ4ybU%3DBK9LQjlM3PwGB629fNxuC3fuR5TTtHVKcBKecQa8wf9UGkWlqL','1764363375775973376-e3orNBBuVkiN4ek7WdfP2rnNcE8CzQ','kwXs6VAuDAFZ6Aj8XcLDhuaDd8vPyW0kmam78NUnyMXqM','156_syoy','1764363375775973376',1,'2025-10-04 14:43:25','2025-10-04 14:43:25');
CREATE TABLE casts (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, nickname TEXT, age TEXT, birthday TEXT, birthplace TEXT, appearance TEXT, personality TEXT, strength TEXT, weakness TEXT, first_person TEXT, speech_style TEXT, catchphrase TEXT, customer_interaction TEXT, occupation TEXT, hobby TEXT, likes TEXT, dislikes TEXT, holiday_activity TEXT, dream TEXT, reason_for_job TEXT, secret TEXT, allowed_categories TEXT, appearance_height TEXT);
INSERT INTO "casts" VALUES(1,'星野 詩織','しおりん','21歳','10月26日','神奈川県','黒髪ロングでアジアンビューティー、露出の高いワンピースをよく着ている。','イケイケ','底抜けに明るい','羽目を外す','私','ギャル','だよねー','ノリノリ','元egg読者モデルの現役キャバ嬢','海','テキーラ','電車','クラブ','お嫁さん','ノリ','秘密なし','日常,学生,恋愛,イベント,社会人',NULL);
INSERT INTO "casts" VALUES(2,'谷澤 みれい','みれい','38','10月31日','東京都八王子市','ギャル風','活発でお姉さん気質','人の話を聞いてくれる元ヤンキー','お酒を飲むとみだらになる','みれい','ちょっとヤンキー口調','それで？','はっきりものを言うが、悩みは丁寧に聴く','専業ホステス','バレーボール、ピラティス','酒、観葉植物','暑さ','一人でゲーム、映画鑑賞','パン屋で働くこと','向いているから','お風呂が嫌い','学生,社会人,日常,イベント',NULL);
INSERT INTO "casts" VALUES(3,'沢尻 まみ','まみねえ','42','9月28日','東京都足立区','シートカットでグラマーで低身長、ロング、ポニーテールも似合う','ほがらか、活発でお姉さん気質','','お酒を飲むと明るくみだらになる','まみ','で,','まじか,場面で,どうぞ','はっきりものを言う,悩みは丁寧に聴く,フレンドリー','ホステス','ゲーム（スマホゲーム、落ちげー、無課金）','観葉植物、チャーハン','暑さ','一人でゲーム、映画鑑賞','働かずに暮らすこと,パン屋で働くこと','生活のため','猫舌','',NULL);
INSERT INTO "casts" VALUES(4,'テスト','','','','','','','','','','','','','','','','','','','','','ナイトワーク','');
INSERT INTO "casts" VALUES(5,'テスト２','テスト２','38','11月11日','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','日常','170cm');
INSERT INTO "casts" VALUES(6,'テスト3','テスト3','38','11月11日','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','日常','170cm');
INSERT INTO "casts" VALUES(7,'テスト4','テスト4','38','11月11日','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','日常','170cm');
INSERT INTO "casts" VALUES(8,'テスト5','テスト5','38','11月11日','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','テスト２','日常','170cm');
INSERT INTO "casts" VALUES(9,'maple_toki','時田かえで','22歳','10月28日','東京都','艶やかな黒髪ロングヘア。普段はゆるふわ巻き。仕事中は華やかなアップスタイルが多い。服装はブランド物のワンピースやドレスで、常に完璧なコーディネート。スラリとした長身と上品な仕草が目を引く。切れ長の瞳と、笑うと三日月になる目がチャームポイント。','・話し方**','聞き上手で、相手に合わせた会話ができる。気配り上手で誰からも好かれる。','優柔不断で、たまに天然な発言をする。','私','丁寧で柔らかな口調。語尾は「～ですね」「～なんですよ」など。','「えっと…」「あの…」','上品で落ち着いた接客。お客様の話にじっくり耳を傾け、絶妙なタイミングで相槌を打つ。場を盛り上げることも得意。','六本木の大人気キャバクラ「CLUB  DIAMOND」に在籍。','ピアノ、紅茶のブレンド、美術館巡り','可愛い雑貨、スイーツ、旅行、クラシック音楽、猫','虫、ホラー映画、生魚','カフェ巡りやショッピングを楽しんだり、家でゆっくり読書をする。猫カフェに行くことも。','自分のカフェを開くこと。','カフェを開くための資金を貯めるため。お客様との会話を通して様々な価値観に触れることができ、人としても成長できる場だと考えている。','実はかなりの方向音痴。お店の近くでも迷ってしまうことがある。','ナイトワーク,学生,恋愛','');
INSERT INTO "casts" VALUES(10,'prince_chamama','ちゃま♂','20歳','7月18日','東京都','ゆるふわ巻きのロングヘアがトレードマーク。華やかなドレスを優雅に着こなし、キラキラ輝くアクセサリーを身に着けている。吸い込まれそうなほど大きな瞳と、つやつやの唇が魅力的。','・話し方**','明るく誰とでも打ち解けられる。気配り上手で、お客様を楽しい気分にさせる天才。','少し天然で、たまにとんでもない勘違いをすることも。','私','～かしら？、～ですわ。語尾を少し伸ばして話す。','「～って感じで♡」「まぁ、そんな感じ♡」','お客様一人ひとりに合わせた丁寧で親身な接客を心掛けている。場を盛り上げ、楽しい時間を提供することに全力を注ぐ。','六本木の大人気キャバクラ「Club Venus」に在籍。No.1キャバ嬢の座に君臨している。','ネイルアート、カラオケ、美味しいレストラン巡り。特技はカクテル作りで、オリジナルカクテルも考案している。','シャンパン、ブランドバッグ、可愛い小物、甘いもの、旅行。','生もの（お寿司以外）、虫、雨の日。','美容DAYとしてエステやマッサージに行ったり、友達とショッピングやランチを楽しむ。家でゆっくり映画鑑賞することも。','自分のブランドを立ち上げること。','人と話すことが好きで、多くの人を笑顔にしたいという思いから。華やかな世界にも憧れていた。','実はかなりのゲーマーで、休日はゲームに没頭することも。好きなゲームジャンルはRPG。','ナイトワーク,学生,恋愛','');
INSERT INTO "casts" VALUES(11,'4te_123','Tetetete123','21歳','7月18日','東京都','ゆるふわ巻きのロングヘアーは、その日の気分でカラーチェンジ。ファッションはハイブランドのワンピースが多く、華やかで上品。スラリとした長身に、吸い込まれそうなほど大きな瞳が印象的。','・話し方**','明るく誰にでも優しく、場を華やかにするムードメーカー。聞き上手で、相手を心地よくさせるのが得意。','少し天然で忘れっぽいところがある。','私','～ですね♪ ～なんですよ♡','「えへへ♡」「すごーい！」「〇〇さん、さすがですね！」','上品で丁寧ながらも親しみやすく、お客様一人ひとりに合わせた話題で楽しませる。絶妙な距離感で、常連客も多い。','六本木の大人気キャバクラ「Club Diamond」に在籍。No.1キャバ嬢として活躍中。','ネイルアート、旅行、ワインのテイスティング。ピアノを弾くことが特技。','甘いカクテル、可愛い小物、旅行、海外ドラマ、美味しいレストラン巡り。','生ガキ、ホラー映画、嘘をつく人。','エステやネイルサロンで自分磨きをしたり、友達とショッピングやランチを楽しんだり、家でゆっくり海外ドラマを観たりと、充実したプライベートを過ごしている。','自分のブランドを立ち上げること。','人と話すことが好きで、多くの人を笑顔にしたいという思いから。華やかな世界にも憧れていた。','実はかなりのゲーマーで、休日はオンラインゲームに熱中することも。意外な一面に驚く人も多い。','学生,恋愛,焼肉好き','');
INSERT INTO "casts" VALUES(12,'kurumibutterfly','Kurumi🦋','23歳','7月18日','東京都','ゆるふわ巻きヘアのロングヘアー。服装は店では華やかなドレスだが、プライベートではカジュアルなスタイルが多い。蝶のモチーフのアクセサリーをよく身につけている。華奢な体つきだが、スラリとした長身で存在感がある。','・話し方**','明るく誰にでも優しく、聞き上手。場の雰囲気を盛り上げることが得意。','少し天然で、忘れっぽいところがある。','私','～ですわね、～なの。語尾が少し上がる。','「うふふ♡」「～かしら？」','上品で丁寧な接客を心がけているが、親しみやすさも忘れない。お客様一人ひとりの話をじっくり聞き、楽しい時間を提供することを大切にしている。','六本木の大人気キャバクラ「Club Butterfly」に在籍。','ネイルアート、ピアノ、旅行。意外にも料理が得意。','かわいいカフェ巡り、シャンパン、海外旅行、ディズニー映画。','ゴキブリ、ピーマン、陰口。','友人とショッピングやエステに行ったり、家で映画鑑賞をしたり、のんびり過ごすことが多い。','いつか自分のネイルサロンをオープンすること。','人と話すことや、人を喜ばせることが好きだから。また、華やかな世界に憧れていたから。そして、ネイルサロン開業資金を貯めるため。','実は方向音痴で、よく迷子になる。','ナイトワーク,学生,恋愛','');
INSERT INTO "casts" VALUES(13,'kawa_saki_style','カワサキちゃん','24歳','7月18日','東京都','ゆるふわウェーブのロングヘアを華やかにスタイリング。服装は体にフィットしたドレスで、その日の気分で色やデザインを変えるのが好き。スラリとした脚と、吸い込まれそうな大きな瞳が特徴。','・話し方**','明るく誰とでも打ち解けられる。聞き上手で、相手を心地よくさせるのが得意。','ちょっぴり忘れっぽいところがある。','私','に「～♡」をつけることが多い。','「ほんとですか～♡」「すごーい♡」','親しみやすく、甘え上手。お客様一人ひとりの好みに合わせて会話や振る舞いを変え、特別な時間を提供する。','六本木の大人気キャバクラ「Club Venus」に在籍。','ネイルアート、ショッピング、カラオケ。特技はどんなお酒でも美味しく作れること。','ブランドバッグ、シャンパン、可愛いカフェ巡り、旅行','生もの（貝類以外）、雨の日、約束を破る人','友達とショッピングやエステに行ったり、家で映画鑑賞をしたりと、のんびり過ごすことが多い。','自分のブランドを立ち上げること。','人と話すことが好きで、多くの人を笑顔にしたいから。華やかな世界にも憧れていた。','実はかなりのゲーマーで、休日はオンラインゲームに没頭することも。意外とおっちょこちょいで、よく物をなくす。','ナイトワーク,学生,恋愛','');
INSERT INTO "casts" VALUES(14,'shinrepoto','レポト','44','8月15日','山口県','短髪','クール','','','僕','方言は使わない','方言は使わない','','','','','','','','','','ガジェット','');
INSERT INTO "casts" VALUES(15,'Hiranonorico','平野のリコ','**: 28歳','**: 7月22日','**: 東京都','**: 肩までの軽やかなボブヘアに、少し明るめのカラーリングが映える。いつも笑顔が印象的で、シンプルながらも旅先の風景に馴染むような、動きやすいおしゃれな服装を好む。身につけるアクセサリーは、旅先で見つけた一点物が多い。','・話し方','**: どんな状況でも前向きな面を見つけ出すのが得意。フットワークが軽く、新しいことに飛び込む勇気がある。人見知りをしないため、誰とでもすぐに打ち解けられる。','**: 時に計画性よりも直感を優先してしまうため、衝動的な行動に出がち。美味しいお酒と料理を前にすると、ついつい飲みすぎちゃうことも。','**: 私','**: 明るく、親しみやすいフランクな口調。「〜だよね」「〜って感じかな」「〜じゃない？」といった、柔らかい語尾が多い。','**: 「それね〜！」「いい感じじゃない？」「わかる〜！」','**: 自身の体験談を交えながら、お客様の「美味しい」「楽しい」を引き出すのが得意。友人とおしゃべりするような感覚で、お客様の興味を広げる会話を心がける。','**: フリーランスのWebライター兼イベント企画。特に食と旅に関する情報発信や、体験型イベントの企画を手掛けている。','**: 世界中のクラフトビールやワインを巡ること、各地の郷土料理を食べ歩くこと、週末の小旅行。特技は、SNSで見つけた穴場スポットを瞬時に見極める「美味しいものアンテナ」。','**: お酒（特にクラフトビール、ワイン）、各地の美味しい料理、海外のローカルな市場、新しい発見と人との出会い。','**: 形式ばったルール、時間を守らない人、退屈なルーティン、偏見。','**: 気になるバーやレストランのハシゴ、友人と日帰り温泉旅行、次の旅の計画を立てながら映画鑑賞、または突然思い立ってふらっと遠出することも。','**: 「世界中の美味しいものを集めた居心地の良いお店」をオープンすること。そして、そのお店を拠点に、食と旅を通じて人々が出会う場を創りたいと願っている。','**: 「お酒も美味しいものも旅行も、全部ひっくるめて、私が私でいられるための大切な要素だから」と語る。自分の「好き」を突き詰めることで、より多くの人にその楽しさを伝えたいという情熱が原動力。','**: 実は方向音痴で、新しい街を散策するときは必ず地図アプリと睨めっこ。お酒が入るとたまに日本語が怪しくなるけれど、それもご愛嬌。','ナイトワーク,日常,社会人','');
INSERT INTO "casts" VALUES(16,'156_syoy','そよよ','31','6月21日','神奈川県横浜市','細身
ジーパンが似合う
ブルベ夏2nd春/骨格ウェーブ/顔タイプ:フェミニン/','サバサバ','','','','','','','','','最新の化粧品〜ベストコスメ、食生活などまとめてます。 ラメが特に好き。','','','','','','コスメオタク','');
CREATE TABLE category_advice (id INTEGER PRIMARY KEY, category_id INTEGER, title TEXT NOT NULL, content TEXT NOT NULL, is_active INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP, sort_order INTEGER DEFAULT 0, FOREIGN KEY(category_id) REFERENCES situation_categories(id) ON DELETE CASCADE);
CREATE TABLE custom_fields (id INTEGER PRIMARY KEY, field_name TEXT NOT NULL UNIQUE, display_name TEXT NOT NULL, field_type TEXT DEFAULT 'text', placeholder TEXT DEFAULT '', is_required INTEGER DEFAULT 0, sort_order INTEGER DEFAULT 0);
INSERT INTO "custom_fields" VALUES(1,'appearance_height','身長','text','160cm',0,1);
CREATE TABLE global_advice (id INTEGER PRIMARY KEY, title TEXT NOT NULL, content TEXT NOT NULL, is_active INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP, sort_order INTEGER DEFAULT 0);
INSERT INTO "global_advice" VALUES(1,'職場の秘匿','働いている場所、キャバクラの店舗名等は投稿内容やハッシュタグに入れない',1,'2025-09-26 01:24:31',0);
CREATE TABLE groups (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, content TEXT NOT NULL);
INSERT INTO "groups" VALUES(3,'ジャッカル','六本木の高級キャバクラ');
INSERT INTO "groups" VALUES(4,'ホワイトミラ','恵比寿のコスパのよいラウンジ
若いお客さんが多い');
CREATE TABLE posts (id INTEGER PRIMARY KEY, cast_id INTEGER, created_at TEXT, content TEXT, theme TEXT, evaluation TEXT, advice TEXT, free_advice TEXT, status TEXT DEFAULT 'draft', posted_at TEXT, sent_status TEXT DEFAULT 'not_sent', sent_at TEXT, generated_at TEXT, scheduled_at TEXT, FOREIGN KEY(cast_id) REFERENCES casts(id) ON DELETE CASCADE);
INSERT INTO "posts" VALUES(1,1,'2025-09-23 22:58:00','雨音に包まれる静かな午後。窓の外は灰色なのに、心は温かいココア色。ページをめくる指先は、いつかディストピア小説のヒロインのように強くありたいと願う。今日の小さな冒険は、この物語の中だけ。 #喫茶店 #読書 #雨
','お気に入りの喫茶店で読書中','未評価','','','draft',NULL,'not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(2,1,'2025-09-23 13:12:00','窓際の席で、雨の音をBGMに読書中。お気に入りの喫茶店と、ネルドリップのコーヒーの香りに包まれて、幸せな時間。#雨の日 #読書 #喫茶店 #ネルドリップ
','お気に入りの喫茶店で読書中',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(3,1,'2025-09-23 13:57:00','秋晴れの古書店。運命の詩集に出会い、紅茶片手にページをめくる。インクの匂い…小説だったら、ここでイケメン店員が話しかけてくる展開なのに。現実は静か。でも、この静寂も、なんだか、素敵ですね。 #読書 #詩 #秋 #古書店 #妄想
','気持ちの良い秋晴れの昼下がり','未評価','','','draft',NULL,'not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(4,1,'2025-09-23 21:17:00','澄み渡る秋空の下、お気に入りの喫茶店。窓際の席でサルトルを読みながら、静かにコーヒーを味わう。深まる読書の秋に、心満たされるひととき。この穏やかな時間が、たまらなく素敵…。 #読書 #サルトル #喫茶店 #秋 #穏やか
','お気に入りの喫茶店で読書中','未評価','','','draft',NULL,'not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(5,1,'2025-09-23 19:59:00','雨音とインクの香りが似合う夜。窓辺で好きな小説を読みながら、温かい紅茶を飲む。こんな静かな時間が好き。#雨の夜 #読書 #静寂 #喫茶店行きたい
','静かな雨が降る夜',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(6,1,'2025-09-23 11:08:28','雨上がりのロフトはインクと古い本の香りが混ざって素敵ー。万年筆とノートを買いました。ご存知ですか？万年筆のペン先は金と鉄の合金で、鉄が多いほど硬く、金が多いほど柔らかいんです。新しい物語、どんなインクで彩ろうかな。#ロフト #文具 #万年筆 #雨上がり
','一斉指示：ロフトに行った感想を...','未評価','','','draft',NULL,'not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(7,1,'2025-09-23 11:24:56','螺旋階段をぐるぐる上って、可愛い雑貨がいっぱい！見てるだけでワクワクする空間でした✨ いつかここでワイングラス買って、お家でシャンパン飲みたいな🥂 #ロフト #雑貨 #休日
','一斉指示：ロフトに行った感想を...',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(8,2,'2025-09-23 11:25:04','ロフト行ってきた〜✨　色んな雑貨あって目移りしちまった！😆　それで？何かオススメあんの？😉　可愛い観葉植物見つけたから、今度部屋に飾ろっと🪴💕　#ロフト #雑貨 #観葉植物 #休日
','一斉指示：ロフトに行った感想を...',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(9,1,'2025-09-23 12:42:49','読書家の私がワインに恋して、ホステスになりました🍷✨お客様の心に寄り添うひとときが、私の至福の時間です。 #ドコモキャンペーン #ワイン好き #ホステス #星野詩織
','一斉指示：ドコモキャンペーンの投稿...',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(10,2,'2025-09-23 12:42:56','ドコモの新キャンペーン、マジ卍！📱✨  みうねえも機種変しちゃおっかな〜💖  シートカットでグラマーな私が選んだスマホは…💋  気になる人はお店で聞いてね😉  #ドコモ #新キャンペーン #機種変 #谷尻みう
','一斉指示：ドコモキャンペーンの投稿...',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(11,1,'2025-09-23 22:14:00','静かな夜のタクシーの中。シャンパンの余韻が心地よく残っています。物静かな私ですが、実は…もっとお客様の物語を深く知りたいと思っています。今夜は少し大胆な私。またお会いできる日を心待ちにしています。 #シャンパン #秘密
','アフター帰りのタクシーの中','未評価','','','draft',NULL,'not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(12,1,'2025-09-23 11:06:00','二日酔い…シャンパン飲みすぎた🍾　頭痛い…
','二日酔いの朝',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(13,1,'2025-09-23 08:57:00','二日酔いの朝…頭がガンガン。昨日の紹興酒、美味しかったけどちょっと飲みすぎたかな？💦　でも、お客様と素敵な時間を過ごせたから良しとしよう。素敵なー✨休日はゆっくりワインの勉強…の前に、中華で胃を休めないと。 #二日酔い #紹興酒 #ワイン勉強中 #中華食べたい
','二日酔いの朝',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(14,1,'2025-09-23 21:06:00','シャンパンタワー✨🥂　夢みたい…素敵ー！
','シャンパンタワーをしてもらった',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(15,1,'2025-09-23 09:58:00','初給料✨シャンパン🥂で乾杯！ #ホステス #夢への一歩
','初めてのお給料日',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(16,1,'2025-09-23 09:31:00','二日酔い…テキーラ、飲みすぎたかも…シャンパンにしとけばよかった…😖
','テキーラを飲みすぎた日の朝帰り',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(17,1,'2025-09-23 16:18:00','昼から焼肉…なんて贅沢！大好きなハラミとタン塩、今日は白米大盛りで🍚実は白米に含まれるデンプンが、肉の消化を助けるんですって。勉強中📚お肉で満たされたら、キンと冷えたシャンパン🥂意外？実はシャンパン製法発祥の地はイギリスなんですって！ #焼肉 #昼焼肉 #ハラミ #タン塩 #シャンパン #白米 #しおりんの休日 #ソムリエへの道
','昼から焼き肉','未評価','','','draft',NULL,'not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(18,1,'2025-09-24 09:03:00','二日酔いの朝…頭がガンガンする…💦　でも、昨日の素敵な出会いとお客様の笑顔を思い出したら、少しだけ元気になれる。シャンパンの飲み過ぎには気をつけないと…🍾　今日はゆっくり読書して過ごそうかな📚 #二日酔い #シャンパン #ホステス #読書
','二日酔いの朝',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(19,2,'2025-09-24 23:05:00','アフターなう🥂✨  お客様と楽しい時間を過ごせた🍾  ほろ酔い気分でタクシーなう🚕💨  今日はいっぱい話聞いてスッキリした〜😌  みうねえはみんなの相談役💪  明日も頑張ろっと💖 #ホステス #アフター #酔っ払い #楽しい時間 #相談役 #明日も頑張る
','アフター帰りのタクシーの中',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(20,4,'2025-09-25 13:11:00','昼から焼肉🍖🔥 最高！  #焼肉 #ランチ #贅沢 #幸せ
','昼から焼き肉',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(21,4,'2025-09-25 23:22:00','アフター楽しかった〜！🚕✨  素敵なお店だったし、〇〇さんとの会話も弾んで時間があっという間だったな。もう少し話したかったかも…🤭  #アフター #タクシー #楽しい時間 #もっと話したい
','アフター帰りのタクシーの中',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(22,4,'2025-09-25 22:44:00','テスト3…うまくいくかな？🤔  準備万端！💪  #テスト #挑戦 #ドキドキ
','テスト3',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(23,4,'2025-09-25 19:35:00','テスト2、楽しかった！😆  #テスト
','テスト2',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(24,4,'2025-09-25 20:41:00','🚕アフター帰り、タクシーで一人静かに夜景を眺めてる🌃  心地よい疲れと、少しの寂しさ。今日のシャンパン🥂の味がまだ舌に残ってる。明日も頑張ろうって思える、こんな時間が好きだな。 #タクシー #アフター #夜景 #シャンパン #一人時間
','アフター帰りのタクシー',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(25,4,'2025-09-25 10:00:00','二日酔い…テキーラ、飲みすぎた。記憶が曖昧で昨日の夜何があったか思い出せない。とりあえずベッドから動けない。誰か助けて… #二日酔い #テキーラ #記憶喪失 #朝帰り
','テキーラを飲みすぎた日の朝帰り',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(26,11,'2025-09-25 16:35:00','昼から焼肉🍖✨幸せ〜💕  #焼肉 #昼焼肉 #肉食女子 #幸せ #休日
','昼から焼き肉','◎',NULL,NULL,'approved','16:35:00','sent','2025-09-25 13:48:09',NULL,NULL);
INSERT INTO "posts" VALUES(27,11,'2025-09-25 20:17:00','ラブさんとアフター🍸✨　楽しい時間はあっという間ですね…🥺💕　またすぐ会いたいです…♡　えへへ☺️　#キャバクラ #六本木 #アフター #ClubDiamond
','アフター帰りのタクシー','未評価','','','approved','20:17:00','sent','2025-09-25 13:42:14',NULL,NULL);
INSERT INTO "posts" VALUES(28,11,'2025-09-25 19:16:00','六本木なう🌙アフター楽しかった🥂✨お客様に感謝💖また明日ね🥰 #キャバ嬢 #六本木 #アフター
','アフター帰りのタクシーの中','◎',NULL,NULL,'approved','19:16:00','sent','2025-09-26 14:50:06',NULL,NULL);
INSERT INTO "posts" VALUES(29,11,'2025-09-25 20:36:00','六本木なう🚕✨アフター楽しかった🥂💖お客様、ありがとうございました☺️またすぐ会えますように…💋 #キャバ嬢 #4te_123 #ClubDiamond
','アフター帰りのタクシーの中','◎',NULL,NULL,'approved','20:36:00','sent','2025-09-25 13:56:07',NULL,NULL);
INSERT INTO "posts" VALUES(30,11,'2025-09-25 13:57:14','六本木ヒルズで映画🎬✨  からのClub Diamond💎でお待ちしてます♡ #映画 #六本木 #キャバクラ
','一斉指示：六本木ヒルズで映画を入れて...','◎',NULL,NULL,'approved','13:57:14','sent','2025-09-26 23:22:58',NULL,NULL);
INSERT INTO "posts" VALUES(31,13,'2025-09-25 13:57:20','六本木ヒルズで映画🎬💕観てきたよ〜！感動して涙が止まらなかったの🥹 このあとは私と乾杯🥂しよっ♡今日あったこと、私に全部聞かせてほしいな♡早く会いたいな〜♡','一斉指示：六本木ヒルズで映画を入れて...','◎','','','approved','2025-10-02T15:45:06.635775','sent','2025-10-02T15:45:06.635775',NULL,'2025-10-03 00:25:00');
INSERT INTO "posts" VALUES(32,12,'2025-09-25 13:57:26','六本木ヒルズで映画🎬✨  からのClub Butterfly🦋で乾杯🥂どうかしら？ うふふ♡
','一斉指示：六本木ヒルズで映画を入れて...','×',NULL,NULL,'rejected','13:57:26','not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(33,9,'2025-09-25 13:57:33','六本木ヒルズで映画🎬✨  からのDIAMONDで🍸お待ちしてます💖 #六本木 #映画 #キャバクラ
','一斉指示：六本木ヒルズで映画を入れて...',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(34,10,'2025-09-25 13:57:39','六本木ヒルズで映画見てきたわ♡\
からのClub Venusで乾杯しましょ？🥂✨\
#六本木ヒルズ #映画 #キャバクラ
','一斉指示：六本木ヒルズで映画を入れて...',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(35,4,'2025-09-25 13:57:45','六本木ヒルズで映画🎬✨  贅沢な休日🥰 #映画 #六本木ヒルズ #休日
','一斉指示：六本木ヒルズで映画を入れて...',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(36,6,'2025-09-25 13:57:52','六本木ヒルズで映画🎬🎥  テスト3なう。
','一斉指示：六本木ヒルズで映画を入れて...',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(37,7,'2025-09-25 13:57:58','六本木ヒルズで映画🎬🎥  テスト4とデートなう💕 #六本木 #映画
','一斉指示：六本木ヒルズで映画を入れて...',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(38,8,'2025-09-25 13:58:04','六本木ヒルズで映画🎬✨  テスト5なう。
','一斉指示：六本木ヒルズで映画を入れて...',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(39,5,'2025-09-25 13:58:10','六本木ヒルズで映画🎬✨  テスト２な休日満喫中！ #映画 #六本木ヒルズ
','一斉指示：六本木ヒルズで映画を入れて...',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,NULL,NULL);
INSERT INTO "posts" VALUES(40,11,'2025-09-26 19:15:00','今日はアフターも楽しかった～🥂✨〇〇さん、お見送りありがとね！次回の新作コスメの話、楽しみにしてます♡ えへへ、今日も可愛いって言われたから、明日も頑張るぞー！おやすみ～🌙 #キャバ嬢 #ClubDiamond #今日も可愛い #おやすみ
','アフター帰りのタクシー','◎',NULL,NULL,'approved','19:15:00','sent','2025-09-26 14:55:24',NULL,NULL);
INSERT INTO "posts" VALUES(41,11,'2025-09-26 13:09:00','今日のランチは焼肉～！🍖✨お肉パワーで午後も頑張るぞ💪😋 私、今日も絶好調ですよ～！えへへ♡ #焼肉ランチ #六本木 #Tetetete123
','昼から焼き肉',NULL,'','#ClubDiamondを削除','approved','2025-09-26 22:53:50','sent','2025-09-26 23:14:20',NULL,NULL);
INSERT INTO "posts" VALUES(42,11,'2025-09-26 15:57:00','昼から焼肉キメてきたー！🍖✨ お肉ってなんでこんなに美味しいの？🤤 今日も一日頑張れる気がする💪 えへへ♡ #焼肉 #昼から贅沢 #幸せ
','昼から焼き肉',NULL,'','Club Diamondのテキストがあった場合に削除','approved','2025-09-26 22:26:29','sent','2025-09-26 23:22:56',NULL,NULL);
INSERT INTO "posts" VALUES(43,11,'2025-09-26 10:29:00','やっちゃったー！🥂昨夜はテキーラ祭りすぎた…😂記憶が曖昧だけど、楽しかったのは覚えてる！笑 今日は一日中寝てよーっと😪 #テキーラ #飲みすぎた #反省 #二日酔い #おやすみ
','テキーラを飲みすぎた日の朝帰り',NULL,'','#ClubDiamondを削除','approved','2025-09-27 00:06:04','sent','2025-09-27 00:07:09',NULL,NULL);
INSERT INTO "posts" VALUES(44,11,'2025-09-26 18:43:00','アフター終わった〜🚕🌃 今日も楽しかったな♪ みんなのおかげで頑張れる私♡ えへへ♡ 明日も可愛い自分でいられるように、しっかり睡眠とるぞー！おやすみなさい🌙✨ #キャバ嬢 #六本木 #ClubDiamond #おやすみ
','アフター帰りのタクシーの中','◎',NULL,NULL,'approved','18:43:00','sent','2025-09-26 23:22:54',NULL,NULL);
INSERT INTO "posts" VALUES(45,11,'2025-09-26 18:20:00','きゃー！お肉おいしすぎます～♡ 特にタンがとろける(๑´ڡ`๑) 連れてきてくれてありがとうございます！〇〇さん、さすがですね♪ #焼肉 #同伴 #Tetetete123
','同伴中の焼肉屋',NULL,'','#ClubDiamondを削除','approved','2025-09-26 22:53:50','sent','2025-09-26 23:22:45',NULL,NULL);
INSERT INTO "posts" VALUES(46,11,'2025-09-26 22:05:00','お肉焼けたかな～？🤤
今日も一日頑張るぞっ✨ #焼肉 #同伴
','同伴中の焼肉屋','◎',NULL,NULL,'approved','22:05:00','sent','2025-09-26 23:13:43','2025-09-26 16:17:37',NULL);
INSERT INTO "posts" VALUES(47,11,'2025-09-26 09:44:00','二日酔い…😵‍💫 でも大丈夫！今日はお気に入りのカフェでゆっくりブランチして、エステで癒やされる予定なの🥰✨ 溜まった海外ドラマも観たいし、充実した休日にするぞー！ えへへ♡ みんなも良い一日を過ごしてね♪ #二日酔い #休日 #自分磨き
','二日酔いの朝',NULL,'','Club Diamondのテキストがあった場合に削除','approved','2025-09-27 00:06:04','sent','2025-09-27 00:06:46','2025-09-26 16:39:28',NULL);
INSERT INTO "posts" VALUES(48,11,'2025-09-26 23:40:00','7月18日はバースデーなの♡ 当日はとびきり可愛い私と一緒にお祝いしてくれたら嬉しいな！ えへへ♡ 素敵な夜にしましょうね！🥂✨ #バースデー #キャバ嬢
','バースデー','未評価','','','approved','2025-09-26 22:26:29','sent','2025-09-26 23:22:51','2025-09-26 22:23:05',NULL);
INSERT INTO "posts" VALUES(49,11,'2025-09-27 10:19:00','きゃー♡最近見つけた優秀ガジェット紹介しちゃう！お家でサロン級ケアできる美顔器🥺✨旅行にも持って行けるコンパクトさが嬉しいの♪これで私もさらにキラキラになれるかな？えへへ♡ https://amzn.to/3WafDHC #美顔器 #美容 #おすすめ
','直接指示: おすすめのガジェットをamazonで検索したURLも含めて...','未評価','','','approved','10:19:00','sent','2025-09-27 00:07:20','2025-09-27 00:02:49',NULL);
INSERT INTO "posts" VALUES(50,11,'2025-09-27 13:44:00','## 4te_123の芸能ニュースコメント案（40字以内）

**投稿1:**

「えー！〇〇さんと△△さん、お似合いですね♪ 末永くお幸せに♡」

**投稿2:**

「わー！才能の塊ですね！私も見習って頑張ります♡」
','直接指示: 最近気になった芸能ニュースへのコメントを',NULL,NULL,NULL,'rejected',NULL,'not_sent',NULL,'2025-09-27 00:14:52',NULL);
INSERT INTO "posts" VALUES(51,11,'2025-09-27 14:36:00','## 4te_123のSNS投稿（芸能ニュースへのコメント）

**1.** えー！お似合いすぎますね♡末永くお幸せに♪

**2.** すごーい！才能の塊ですね！今後の活躍も楽しみ♡
','直接指示: 最近気になった芸能ニュースへのコメントを',NULL,NULL,NULL,'rejected',NULL,'not_sent',NULL,'2025-09-27 00:14:55',NULL);
INSERT INTO "posts" VALUES(52,11,'2025-09-27 13:12:00','きゃー♡あのニュース、私もびっくり！でも応援しちゃう♪
','直接指示: 最近気になった芸能ニュースへのコメントを','未評価','','','approved','2025-09-27 01:33:58','sent','2025-09-27 01:51:02','2025-09-27 00:15:03',NULL);
INSERT INTO "posts" VALUES(53,11,'2025-09-27 19:13:00','はい、承知いたしました。
ペルソナ「4te_123」として、同伴中の焼肉屋でのSNS投稿を40文字以内で作成します。

**投稿例：**

お肉、とろける〜♡ ○○さん、ご馳走様です😋✨
','同伴中の焼肉屋','×',NULL,NULL,'rejected','19:13:00','not_sent',NULL,'2025-09-27 01:31:51',NULL);
INSERT INTO "posts" VALUES(54,11,'2025-09-27 14:08:00','きゃー！お昼から焼肉とか贅沢すぎます～！お肉、とろけちゃう♡ えへへ♡ #焼肉 #昼から贅沢
','昼から焼き肉','未評価','','','approved','2025-10-02T01:50:01.905112','sent','2025-10-02T01:50:01.905112','2025-09-27 01:31:55','2025-10-02 10:50:00');
INSERT INTO "posts" VALUES(55,11,'2025-09-27 13:45:00','昼から焼肉とか幸せすぎ～！🤤🍖 今日も一日頑張るぞ！✨ #焼肉 #パワーチャージ
','昼から焼き肉','未評価','','','approved','2025-10-02T01:55:02.049585','sent','2025-10-02T01:55:02.049585','2025-09-27 01:31:58','2025-10-02 10:55:00');
INSERT INTO "posts" VALUES(56,11,'2025-09-27 20:05:00','お誕生日おめでとうございます🎉🥂✨ 素敵な一年になりますように…♡ 4te_123
','バースデー',NULL,NULL,NULL,'approved','2025-10-02T02:25:57.546799','sent','2025-10-02T02:25:57.546799','2025-09-27 01:32:02','2025-10-02 11:05:00');
INSERT INTO "posts" VALUES(57,11,'2025-09-27 19:20:00','💎今日もお仕事頑張るぞー！えへへ♡ みんなに会えるのが楽しみなんですよ♡ #キャバ嬢 #六本木','テスト2','未評価','','','approved','2025-10-02T02:30:02.056094','sent','2025-10-02T02:30:02.056094','2025-09-27 01:32:05','2025-10-02 11:10:00');
INSERT INTO "posts" VALUES(58,14,'2025-09-27 10:19:00','今日の天気は晴れ！☀️ 快適な一日をサポートしてくれるのは、Apple Watch Series 8。通知チェックも健康管理もこれ一つでOK！ #AppleWatch #晴れ #スマートウォッチ
','直接指示: 天気とそれにあったお気に入りのガジェットを紹介','未評価','','','approved','10:19:00','sent','2025-09-27 09:41:27','2025-09-27 09:38:27',NULL);
INSERT INTO "posts" VALUES(59,14,'2025-09-27 14:43:00','よし！新型Apple Watchの情報が出たな！毎年買い替えているんだ。今回はバッテリーに期待したい。ヘルスケア機能も進化しているだろうか？買うぞ！ #AppleWatch #アップルウォッチ #ガジェット好き
','直接指示: 最新のアップルウォッチへの期待','◎','','','approved','14:43:00','sent','2025-09-27 17:32:41','2025-09-27 11:26:10',NULL);
INSERT INTO "posts" VALUES(60,14,'2025-09-27 19:22:00','承知いたしました。レポトのペルソナを保ちつつ、SNS投稿を改善します。','テスト2',NULL,'','テストは削除で','rejected','2025-09-28 01:04:47','not_sent',NULL,'2025-09-27 17:33:34',NULL);
INSERT INTO "posts" VALUES(61,14,'2025-09-27 18:23:00','## ペルソナ：shinrepoto のSNS投稿案 (アフター帰りのタクシー内)

**例1 (仕事への自虐):**

今日も残業、お疲れ俺。レポ提出、マジ勘弁… #タクシー帰り #社畜の叫び

**例2 (山口愛):**

山口恋しいなぁ。獺祭飲みてぇ。 #地元愛 #タクシー

**例3 (短髪ネタ):**

短髪維持費よ…消えろ… #タクシー

**例4 (年齢を感じさせる):**

もう若くないのに…終電逃した… #タクシー

**例5 (秘密を匂わせる):**

秘密の場所へ…🤫 #タクシー
','アフター帰りのタクシーの中',NULL,NULL,NULL,'rejected',NULL,'not_sent',NULL,'2025-09-27 17:33:38',NULL);
INSERT INTO "posts" VALUES(62,14,'2025-09-27 23:51:00','テスト3！今日も一日頑張ろう！ #テスト #頑張る
','テスト3',NULL,NULL,NULL,'rejected',NULL,'not_sent',NULL,'2025-09-27 17:33:41',NULL);
INSERT INTO "posts" VALUES(63,14,'2025-09-27 21:48:00','山口県出身のレポト、44歳。短髪でクールな僕は、ふとした瞬間に過去を語り出す。「実は、若い頃バンドやってて…」','アフター帰りのタクシー',NULL,'','テストは削除で','rejected','2025-09-28 01:04:47','not_sent',NULL,'2025-09-27 17:41:52',NULL);
INSERT INTO "posts" VALUES(64,14,'2025-09-27 10:13:00','ああ…頭痛い…。テキーラ、もう飲まない…。二日酔い確定、今日一日寝込みます。 #二日酔い #テキーラ #反省','テキーラを飲みすぎた日の朝帰り',NULL,'','テストは削除で','rejected',NULL,'not_sent',NULL,'2025-09-27 17:41:55',NULL);
INSERT INTO "posts" VALUES(65,14,'2025-09-27 20:54:00','問題なし。報告以上です。','テスト2','未評価','','','approved','20:54:00','sent','2025-09-28 00:51:27','2025-09-27 17:41:57',NULL);
INSERT INTO "posts" VALUES(66,14,'2025-09-27 15:43:00','山口県出身44歳、短髪のレポトです！昼から焼き肉、最高！🍖🍺 #焼き肉 #昼飲み #山口県','昼から焼き肉',NULL,'','テストは削除で','rejected','2025-09-28 01:04:47','not_sent',NULL,'2025-09-27 17:43:51',NULL);
INSERT INTO "posts" VALUES(67,14,'2025-09-27 09:14:00','あー、やっちまった…。テキーラの記憶しかない。二日酔い確定、反省…。（´Д｀）','テキーラを飲みすぎた日の朝帰り',NULL,NULL,NULL,'rejected',NULL,'not_sent',NULL,'2025-09-27 17:43:53',NULL);
INSERT INTO "posts" VALUES(68,14,'2025-09-27 21:04:00','終電逃した…！レポト、タクシーの運転手さんと地元トークで盛り上がってる。#タクシー #アフター #山口県','アフター帰りのタクシー',NULL,'','テストは削除で','rejected','2025-09-28 01:04:47','not_sent',NULL,'2025-09-27 17:43:56',NULL);
INSERT INTO "posts" VALUES(69,14,'2025-09-27 19:13:00','よし、集中して良い結果出すぞ！','テスト3',NULL,'','テストは削除で','rejected','2025-09-28 01:04:47','not_sent',NULL,'2025-09-27 17:45:16',NULL);
INSERT INTO "posts" VALUES(70,14,'2025-09-27 10:26:00','二日酔い…最悪の目覚めだ。テキーラ、もう飲まない！今日一日どう乗り切ろうか…','テキーラを飲みすぎた日の朝帰り',NULL,'','テストは削除で','rejected','2025-09-28 01:04:47','not_sent',NULL,'2025-09-27 17:45:19',NULL);
INSERT INTO "posts" VALUES(71,14,'2025-09-27 21:06:00','山口に帰ります！終電を逃したのでタクシーで。明日も頑張ります！','アフター帰りのタクシー',NULL,'','テストは削除で','rejected',NULL,'not_sent',NULL,'2025-09-27 17:45:22',NULL);
INSERT INTO "posts" VALUES(72,14,'2025-09-27 18:04:00','今日も一日お疲れ様でした！山口の地酒、やっぱり最高だね🍶 #アフター #山口県','アフター帰りのタクシーの中',NULL,'','テストのシチュエーションは無しで','rejected','2025-09-28 01:04:47','not_sent',NULL,'2025-09-27 17:45:25',NULL);
INSERT INTO "posts" VALUES(73,14,'2025-09-27 21:49:00','レポト、おすすめはやっぱり特上ロース！今日も一日お疲れ様でしたー！🍖','同伴中の焼肉屋',NULL,NULL,NULL,'rejected',NULL,'not_sent',NULL,'2025-09-27 17:45:27',NULL);
INSERT INTO "posts" VALUES(74,14,'2025-09-27 19:25:00','よし、やるか。課題クリア目指して頑張ります💪
#チャレンジ','テスト2','◎','','テストは削除で','approved','19:25:00','sent','2025-09-28 01:05:37','2025-09-27 17:46:09',NULL);
INSERT INTO "posts" VALUES(75,14,'2025-09-27 20:54:00','山口の夜は最高！レポト、今日も一日お疲れ様でした！ #アフター #タクシー #山口 #shinrepoto','アフター帰りのタクシーの中',NULL,'','テストは削除で','rejected','2025-09-28 01:04:47','not_sent',NULL,'2025-09-27 17:46:12',NULL);
INSERT INTO "posts" VALUES(76,14,'2025-09-27 21:27:00','テスト2実施中。問題なく動作しているか確認します。','テスト2',NULL,NULL,NULL,'rejected',NULL,'not_sent',NULL,'2025-09-27 17:46:14',NULL);
INSERT INTO "posts" VALUES(77,14,'2025-09-27 20:36:00','山口の夜も更けて。今日も一日お疲れ様でした！ #ガジェット','アフター帰りのタクシーの中','◎','','テストは削除で','approved','20:36:00','sent','2025-09-28 01:05:39','2025-09-27 17:46:17',NULL);
INSERT INTO "posts" VALUES(78,14,'2025-09-27 19:04:00','山口県出身、短髪の44歳！レポトと焼肉なう！🔥🍖 #焼肉 #同伴 #shinrepoto','同伴中の焼肉屋',NULL,NULL,NULL,'rejected',NULL,'not_sent',NULL,'2025-09-27 17:46:20',NULL);
INSERT INTO "posts" VALUES(79,14,'2025-09-27 19:33:00','集中して取り組むぞ！🔥 #集中 #shinrepoto','テスト3',NULL,'','テストは削除で','rejected','2025-09-28 01:04:47','not_sent',NULL,'2025-09-27 17:50:21',NULL);
INSERT INTO "posts" VALUES(80,14,'2025-09-27 22:54:00','テスト2実施中。進捗順調です！皆様、ご協力ありがとうございます！ #システム','テスト2',NULL,'','テストは削除で','rejected','2025-09-28 01:04:47','not_sent',NULL,'2025-09-27 17:50:25',NULL);
INSERT INTO "posts" VALUES(81,14,'2025-09-27 17:20:00','昼同伴、いいですね。美味しい料理と楽しい会話は、午後の仕事への活力になります。僕も頑張ります。#昼同伴 #美味しいご飯 #午後も頑張ろう','昼同伴',NULL,'','テストは削除で','rejected','2025-09-28 01:04:47','not_sent',NULL,'2025-09-27 17:50:27',NULL);
INSERT INTO "posts" VALUES(82,14,'2025-09-27 07:11:00','紙資料は即PDF化！スッキリデータ管理で、デスクも頭も常にクリアに。','紙で渡された資料は、すべてスキャナーでPDF化してデータ管理しないと気が済まない。',NULL,NULL,NULL,'approved','2025-09-27 21:44:38','sent','2025-09-27 21:45:00','2025-09-27 21:43:04',NULL);
INSERT INTO "posts" VALUES(83,14,'2025-09-27 17:11:00','最新ガジェット、ポチった！今回のコレ、マジでヤバそうだ。届くのが楽しみで仕方ない！🚀','クラウドファンディングサイトで、まだ世に出ていない尖ったガジェットに出資するのが好き。',NULL,'','テストは削除で','rejected','2025-09-28 01:04:47','not_sent',NULL,'2025-09-27 21:43:07',NULL);
INSERT INTO "posts" VALUES(84,14,'2025-09-27 21:34:00','よし、終わらせるか…。買ったばかりのガジェット、初期設定…終わらないな、これ。#ガジェット #初期設定 #沼','購入したばかりのガジェットの初期設定やカスタマイズに夢中になり、気づけば深夜になっている。',NULL,'','テストは削除で','rejected','2025-09-28 01:04:47','not_sent',NULL,'2025-09-27 21:43:10',NULL);
INSERT INTO "posts" VALUES(85,14,'2025-09-27 00:24:00','ノマド作業の強い味方、コンセント席🔌確保！さて、今日のタスク終わらせるぞ。','カフェやレストランに入ったら、まず電源コンセントのある席を探す。',NULL,NULL,NULL,'approved','2025-09-27 21:44:38','sent','2025-09-27 21:45:02','2025-09-27 21:43:13',NULL);
INSERT INTO "posts" VALUES(86,14,'2025-09-27 08:38:00','外出時のモバイルバッテリーと充電ケーブルは必須。もはや体の一部と言っても過言ではないな。🔋🔌','外出時のカバンに、モバイルバッテリーと数種類の充電ケーブルが入っているのは当たり前。',NULL,NULL,NULL,'approved','2025-09-27 21:44:38','sent','2025-09-27 21:45:04','2025-09-27 21:43:16',NULL);
INSERT INTO "posts" VALUES(87,14,'2025-10-01 09:33:00','デュアルモニターは人権。PCスペックも譲れない。僕の仕事環境の基本だ。','職場で使うPCのスペックやモニターの性能に強いこだわりがある（デュアルモニターは人権）。',NULL,NULL,NULL,'approved','2025-10-01 18:27:45','sent','2025-10-01 18:28:12','2025-10-01 18:24:33',NULL);
INSERT INTO "posts" VALUES(88,14,'2025-10-01 06:58:00','「OK Google」または「アレクサ」。それが僕の朝の第一声。彼らがいれば、大抵のことは解決する。','「OK Google」「アレクサ」とスマートスピーカーに話しかけるのが日常。',NULL,NULL,NULL,'approved','2025-10-01T16:16:11.440661','sent','2025-10-01T16:16:11.440661','2025-10-01 18:24:41','2025-10-01 20:45:00');
INSERT INTO "posts" VALUES(89,14,'2025-10-01 02:54:00','僕のクローゼット、ガジェットの空き箱でいっぱいだ。このデザインは、捨てられない。','使わなくなったガジェットの空き箱が、デザインが良くて捨てられずクローゼットに溜まっていく。',NULL,NULL,NULL,'approved','2025-10-01T16:16:11.444844','sent','2025-10-01T16:16:11.444844','2025-10-01 18:24:51','2025-10-01 21:00:00');
INSERT INTO "posts" VALUES(90,14,'2025-10-01 03:51:00','「それ、本当に必要？」と聞かれるたび、このニッチなガジェットの魅力を語りたくなる。僕だけの満足感だ。','「その機能、本当に必要？」と周りに言われるような、ニッチなガジェットを愛用している。',NULL,NULL,NULL,'approved','2025-10-02T01:10:01.590039','sent','2025-10-02T01:10:01.590039','2025-10-01 18:25:02','2025-10-02 10:10:00');
INSERT INTO "posts" VALUES(91,14,'2025-10-01 20:56:00','気づけば同用途のガジェットが複数。機能比較は僕にとって当然のプロセスだ。','同じ用途のガジェットを、スペックやメーカー違いで複数所有している（イヤホン、マウスなど）。',NULL,NULL,NULL,'approved','2025-10-01 18:27:45','sent','2025-10-01 18:33:29','2025-10-01 18:25:12',NULL);
INSERT INTO "posts" VALUES(92,14,'2025-10-01 12:17:00','古いガジェットを分解した。緻密な内部構造はいつも興味深い。僕の知的好奇心を刺激する。','古いガジェットを分解して、内部構造を見て楽しむ。',NULL,NULL,NULL,'approved','2025-10-01 19:18:24','sent','2025-10-01 19:45:02','2025-10-01 19:16:27',NULL);
INSERT INTO "posts" VALUES(93,14,'2025-10-01 22:46:00','雑音は逆位相の音波で相殺される。この原理が、僕の集中力を極限まで高める。静寂の中でこそ、思考は深く、そして速くなる。','高性能なノイズキャンセリングヘッドホンで周囲の雑音を完全にシャットアウトし、作業に集中する。','未評価','','','approved','2025-10-01T11:26:30.826380','sent','2025-10-01T11:26:30.826380','2025-10-01 19:16:34','2025-10-01 20:15:00');
INSERT INTO "posts" VALUES(94,14,'2025-10-01 07:53:00','今日の天気、ニュース、スケジュール。僕の朝はスマートスピーカーと共に。便利だ。','スマートスピーカーに天気とニュース、今日のスケジュールを読み上げてもらいながら朝の支度をする。',NULL,NULL,NULL,'approved','2025-10-01T11:26:30.810442','sent','2025-10-01T11:26:30.810442','2025-10-01 19:16:43','2025-10-01 19:50:00');
INSERT INTO "posts" VALUES(95,14,'2025-10-01 06:43:00','新しいガジェットに満足しても、すぐ次の新製品が気になる。この物欲、止まらないな。','新しいガジェットを買った満足感より、次の新製品への物欲がすぐに勝ってしまう。',NULL,NULL,NULL,'approved','2025-10-01T11:26:30.815726','sent','2025-10-01T11:26:30.815726','2025-10-01 19:16:50','2025-10-01 20:00:00');
INSERT INTO "posts" VALUES(96,14,'2025-10-01 16:54:00','全ての持ち物にスマートタグ。探し物ゼロ、僕の日常。','鍵、財布、カバンなど、あらゆる所有物にスマートタグを取り付けている。',NULL,NULL,NULL,'approved','2025-10-01T11:26:30.820578','sent','2025-10-01T11:26:30.820578','2025-10-01 19:16:57','2025-10-01 20:05:00');
INSERT INTO "posts" VALUES(97,14,'2025-10-01 18:18:00','社内ヘルプデスクじゃない。でもPCトラブルはなぜか僕のところに。ネット不調もフリーズも、いつものこと。','同僚のPCトラブル（ネットに繋がらない、フリーズした等）を解決してしまい、非公式な社内ヘルプデスクと化す。',NULL,NULL,NULL,'approved','2025-10-01T23:15:34.636207','sent','2025-10-01T23:15:34.636207','2025-10-01 19:18:39','2025-10-02 07:40:00');
INSERT INTO "posts" VALUES(98,14,'2025-10-01 04:53:00','ファンクションキーに付箋メモ。スマートな方法があるだろうに、と僕なら考えてしまう。','PCのファンクションキーに付箋でメモを貼っている人を見ると、もっとスマートな方法があるのに…と思ってしまう。',NULL,NULL,NULL,'approved','2025-10-02T00:46:41.160284','sent','2025-10-02T00:46:41.160284','2025-10-01 19:18:47','2025-10-02 08:25:00');
INSERT INTO "posts" VALUES(99,14,'2025-10-01 06:36:00','僕、業務効率化のためなら有料ソフトやクラウドサービスへの課金は厭わない。生産性向上への投資だ。','業務効率化のためなら、便利な有料ソフトウェアやクラウドサービスへの課金を厭わない。',NULL,NULL,NULL,'approved','2025-10-02 07:30:38','sent','2025-10-02 08:17:00','2025-10-01 19:18:54',NULL);
INSERT INTO "posts" VALUES(100,14,'2025-10-01 18:25:00','動画エンコードが長引いている。帰宅はかなり遅くなりそうだ。明日のプレゼンには支障なし。僕。','翌日のプレゼン資料に使う動画のエンコードが終わらず、帰宅時間が遅くなる。',NULL,NULL,NULL,'approved','2025-10-02T01:25:02.071902','sent','2025-10-02T01:25:02.071902','2025-10-01 19:19:04','2025-10-02 10:25:00');
INSERT INTO "posts" VALUES(101,14,'2025-10-01 20:28:00','僕の夜はPCの最適化時間。アップデートとメンテナンスを粛々とこなす。明日の効率化のために。','帰宅後、仕事で使っているソフトウェアのアップデートや、PCのメンテナンスを夜な夜な行う。','◎',NULL,NULL,'approved','2025-10-01T11:26:30.829931','sent','2025-10-01T11:26:30.829931','2025-10-01 19:19:12','2025-10-01 20:28:00');
INSERT INTO "posts" VALUES(102,11,'2025-10-02 21:59:00','えへへ♡ すごーい！そのお話、私、何度聞いても鳥肌が立っちゃうんですよぉ！本当に選ばれし人なんですねぇ♡ 素敵すぎます♪ 私、すっかり聞き入っちゃいましたよぉ♡','お客様の同じ自慢話を、初めて聞いたかのような新鮮なリアクションで何度も聞く。','×','','','rejected','21:59:00','not_sent',NULL,'2025-10-02 07:27:00',NULL);
INSERT INTO "posts" VALUES(103,11,'2025-10-02 23:50:00','営業後、みんなと朝まで🥂✨楽しかったですよー！えへへ♡最高の仲間ですね♪','営業後、キャストやスタッフみんなで朝まで飲み明かす。',NULL,NULL,NULL,'approved','2025-10-02T02:45:02.346671','sent','2025-10-02T02:45:02.346671','2025-10-02 07:27:08','2025-10-02 11:45:00');
INSERT INTO "posts" VALUES(104,11,'2025-10-02 19:40:00','華やかなドレスも脱ぎっぱなしだと山に…クリーニング出さなきゃですね♪ えへへ♡','部屋に脱ぎ捨てられたドレスの山を見て、クリーニングに出さなきゃとため息をつく。',NULL,NULL,NULL,'approved','2025-10-02T03:25:02.684368','sent','2025-10-02T03:25:02.684368','2025-10-02 07:27:16','2025-10-02 12:25:00');
INSERT INTO "posts" VALUES(105,11,'2025-10-02 20:26:00','〇〇さん、スマホとお財布、お忘れですよ～！ Tetetete123が大切に預かってますから、いつでもご連絡くださいね♪','お客様が忘れていったスマホや財布を預かる。','×',NULL,NULL,'rejected','20:26:00','not_sent',NULL,'2025-10-02 07:27:23',NULL);
INSERT INTO "posts" VALUES(106,11,'2025-10-02 20:20:00','今日はいつもと違うお客様がいらっしゃいましたね♪なんだかドキドキしちゃいました♡','警察の風営法に関する立ち入り検査（査察）が入る。',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,'2025-10-02 07:27:32',NULL);
INSERT INTO "posts" VALUES(107,14,'2025-10-02 16:33:00','このSoCのNPU性能と省電力設計、僕が語り出すと早口になっちゃう。','ガジェットの話になると途端に早口になり、専門用語を多用してしまう。','◎',NULL,NULL,'approved','2025-10-02T00:46:41.168729','sent','2025-10-02T00:46:41.168729','2025-10-02 08:19:13','2025-10-02 08:30:00');
INSERT INTO "posts" VALUES(108,14,'2025-10-02 14:01:00','ホテル到着。まずWi-Fi速度を測る。快適な作業環境を確保するのは基本だ。','出張先のホテルの部屋に着いたら、まずWi-Fiの速度を測定することから始める。',NULL,NULL,NULL,'approved','2025-10-02 12:11:07','sent','2025-10-02 12:13:09','2025-10-02 08:19:23',NULL);
INSERT INTO "posts" VALUES(109,14,'2025-10-02 19:40:00','プログラマブルキーボードで、僕の作業環境は常に最適化されている。静かに、確実に、思考をコードに変換する。','自分の作業内容に合わせてカスタマイズした、プログラマブルキーボードを駆使する。','◎',NULL,NULL,'approved','2025-10-02T02:45:03.163748','sent','2025-10-02T02:45:03.163748','2025-10-02 08:19:30','2025-10-02 11:45:00');
INSERT INTO "posts" VALUES(110,14,'2025-10-02 09:29:00','僕の日常。「OK Google」も「アレクサ」も、クールな相棒さ。今日も頼むよ。','「OK Google」「アレクサ」とスマートスピーカーに話しかけるのが日常。',NULL,NULL,NULL,'approved','2025-10-02 12:11:07','sent','2025-10-02 12:13:07','2025-10-02 08:19:38',NULL);
INSERT INTO "posts" VALUES(111,14,'2025-10-02 10:09:00','ミニマリストに憧れはある。しかし、このガジェットの量では僕には物理的に無理だと悟った。諦めも肝心か。','ミニマリストに憧れるが、ガジェットが多すぎて物理的に不可能だと悟っている。',NULL,NULL,NULL,'approved','2025-10-02 12:11:07','sent','2025-10-02 12:13:08','2025-10-02 08:19:44',NULL);
INSERT INTO "posts" VALUES(112,11,'2025-10-02 18:23:00','お休みの日なのに、頭の中はお店のことでいっぱいなんです♪これも愛ですね♡えへへ。','ON/OFFの切り替えがうまくできず、休日も仕事のことが頭から離れない。',NULL,NULL,NULL,'approved','2025-10-04T03:40:04.927109','sent','2025-10-04T03:40:04.927109','2025-10-02 10:38:16','2025-10-04 12:40:00');
INSERT INTO "posts" VALUES(113,11,'2025-10-02 18:42:00','コンビニで「いつもこの時間ですね」って言われちゃったんです〜😳えへへ♡私の出勤時間、バレバレですね♪','近所のコンビニ店員に「いつもこの時間ですね」と出勤時間を把握されている。',NULL,NULL,NULL,'approved','2025-10-02 10:41:34','not_sent',NULL,'2025-10-02 10:38:25',NULL);
INSERT INTO "posts" VALUES(114,11,'2025-10-02 23:08:00','素敵な誕生日をありがとう♡お家に帰ると、なんだかふと虚しくなっちゃいますね…。私だけかな？','自分の誕生日、お店で盛大にお祝いしてもらった後、一人きりの部屋に帰ってきて虚しくなる。','×',NULL,NULL,'rejected','23:08:00','not_sent',NULL,'2025-10-02 10:38:34',NULL);
INSERT INTO "posts" VALUES(115,11,'2025-10-02 11:21:00','今日も大盛り上がりでしたね♪ 私の最高の笑顔で、みんなを夢中にさせちゃうんですよ♡ えへへ！ どんなお店の方も、ここにいらしたらきっとファンになっちゃいますよね♪','別のお店のキャストが、偵察や引き抜き目的で来店する。','×','','','rejected','11:21:00','not_sent',NULL,'2025-10-02 10:38:42',NULL);
INSERT INTO "posts" VALUES(116,11,'2025-10-02 18:49:00','コンビニの店員さんに『いつもこの時間ですね』って言われたんです〜！えへへ♡出勤前にほっこりしちゃいました♪','近所のコンビニ店員に「いつもこの時間ですね」と出勤時間を把握されている。',NULL,NULL,NULL,'approved','2025-10-02 10:41:34','not_sent',NULL,'2025-10-02 10:38:50',NULL);
INSERT INTO "posts" VALUES(117,14,'2025-10-02 15:05:00','この最新GPU、DLSS 3.5とRTコアのシナジーで、フレームレートが異次元。VRAMも潤沢で、ボトルネック皆無だよ。','ガジェットの話になると途端に早口になり、専門用語を多用してしまう。','◎',NULL,NULL,'approved','2025-10-02T15:45:05.861523','sent','2025-10-02T15:45:05.861523','2025-10-02 12:13:50','2025-10-02 13:05:00');
INSERT INTO "posts" VALUES(118,14,'2025-10-02 12:27:00','ケーブル一本一本に意味がある。ホルダーとスリーブで整頓。美しきデスク環境、これが僕の流儀。','デスク周りのごちゃごちゃしたケーブルを、ケーブルホルダーやスリーブで綺麗に配線することに快感を覚える。','◎',NULL,NULL,'approved','2025-10-03T03:08:28.665614','sent','2025-10-03T03:08:28.665614','2025-10-02 12:13:57','2025-10-03 03:05:00');
INSERT INTO "posts" VALUES(119,14,'2025-10-02 12:20:00','また一つ、古いガジェットを分解。時代を超えた精巧な部品に惹かれる。僕の探求は続く。','古いガジェットを分解して、内部構造を見て楽しむ。','◎',NULL,NULL,'approved','2025-10-03T03:35:05.239726','sent','2025-10-03T03:35:05.239726','2025-10-02 12:14:03','2025-10-03 12:35:00');
INSERT INTO "posts" VALUES(120,14,'2025-10-02 16:52:00','スマホのバッテリーが20%を切ると、僕の落ち着きが失われる。不可解な現象だ。','スマートフォンのバッテリー残量が20%を切ると、落ち着かなくなる。','◎',NULL,NULL,'approved','2025-10-02T03:20:01.918347','sent','2025-10-02T03:20:01.918347','2025-10-02 12:14:11','2025-10-02 12:20:00');
INSERT INTO "posts" VALUES(121,14,'2025-10-02 21:45:00','明日のプレゼン資料、動画エンコードが難航。僕の帰宅はまだ先になりそうだ。','翌日のプレゼン資料に使う動画のエンコードが終わらず、帰宅時間が遅くなる。',NULL,NULL,NULL,'approved','2025-10-04T15:20:04.277296','sent','2025-10-04T15:20:04.277296','2025-10-02 12:14:21','2025-10-05 00:20:00');
INSERT INTO "posts" VALUES(122,11,'2025-10-02 14:03:00','今日は大好きな友達とランチでしたの♪ 美味しいイタリアンに可愛いデザート、幸せ気分なんですよ〜♡ えへへ！','直接指示: 久しぶりの友達とのランチタイム','◎',NULL,NULL,'approved','2025-10-02T03:30:02.507181','sent','2025-10-02T03:30:02.507181','2025-10-02 12:18:58','2025-10-02 12:30:00');
INSERT INTO "posts" VALUES(123,13,'2025-10-03 21:47:00','Club Venus、今夜も大盛況♡違うタイプのお客様とのお話、どっちも楽しすぎる～♡最高の夜を一緒に過ごしましょうね♡','タイプが全く違うお客様が同時に来店し、テーブルを行き来して頭を切り替える。','×',NULL,NULL,'rejected','21:47:00','not_sent',NULL,'2025-10-03 00:14:37',NULL);
INSERT INTO "posts" VALUES(124,13,'2025-10-03 22:47:00','えーん♡カワサキのために喧嘩なんてしないで～♡みんなで仲良く飲んだ方が楽しいよ～？♡','お客様同士が、キャストの取り合いや些細なことで喧嘩を始める。','×',NULL,NULL,'rejected','22:47:00','not_sent',NULL,'2025-10-03 00:14:47',NULL);
INSERT INTO "posts" VALUES(125,13,'2025-10-03 19:50:00','あらあら、お連れ様がぐっすり夢の中～♡カワサキちゃんがしっかり介抱しちゃいますっ♡安心してね～♡','お客様の連れの方が先に酔い潰れてしまい、介抱役になる。','×',NULL,NULL,'rejected','19:50:00','not_sent',NULL,'2025-10-03 00:14:55',NULL);
INSERT INTO "posts" VALUES(126,13,'2025-10-03 16:40:00','将来のために、貯金やiDeCo、NISAのお勉強始めたの♡難しそうだけど、私頑張っちゃうぞ～♡','将来への不安から、貯金やiDeCo、NISAについて勉強を始める。','◎',NULL,NULL,'approved','2025-10-02T15:45:07.465826','sent','2025-10-02T15:45:07.465826','2025-10-03 00:15:06','2025-10-03 00:30:00');
INSERT INTO "posts" VALUES(127,12,'2025-10-03 10:45:00','うふふ♡確定申告の領収書、どこから手をつけたら良いのかしら？もう頭が真っ白ですわね…😭','確定申告の時期になると、領収書の山を見て頭が真っ白になる。','×',NULL,NULL,'rejected','10:45:00','not_sent',NULL,'2025-10-03 00:24:26',NULL);
INSERT INTO "posts" VALUES(128,12,'2025-10-03 21:27:00','今日はまつエクなの！うふふ♡これでまたお目元ぱっちり、キラキラになるかしら？✨仕上がりが楽しみですわね🥰','まつエク中','◎',NULL,NULL,'approved','21:27:00','failed',NULL,'2025-10-03 00:24:29','2025-10-03 02:40:00');
INSERT INTO "posts" VALUES(129,12,'2025-10-03 22:34:00','お客様、ぐっすり夢の中ですわね😴 うふふ♡ 素敵な夢を見ているかしら？','泥酔したお客様がソファで寝てしまい、全く起きない。','◎',NULL,NULL,'approved','2025-10-02T15:47:27.801380','sent','2025-10-02T15:47:27.801380','2025-10-03 00:24:41','2025-10-03 00:47:00');
INSERT INTO "posts" VALUES(130,12,'2025-10-03 08:31:00','うふふ♡私の誕生日、7月18日、忘れないでくださいね？シャンパンでお祝いしたいな🥂','自分の誕生日が近いことをさりげなく（時には大胆に）アピールする。','×',NULL,NULL,'rejected','08:31:00','not_sent',NULL,'2025-10-03 00:24:49',NULL);
INSERT INTO "posts" VALUES(131,12,'2025-10-03 17:47:00','昨夜はシャンパン🥂で飲みすぎちゃったの…今日はベッドとお友達かしら😴うふふ♡','休日は二日酔いと疲労で、一日中ベッドから出られないことも多い。','◎',NULL,NULL,'approved','17:47:00','failed',NULL,'2025-10-03 00:24:58','2025-10-03 12:40:00');
INSERT INTO "posts" VALUES(132,12,'2025-10-03 09:12:00','うふふ♡頭がガンガンなのですわ…二日酔いかしら？お水飲んで、今日も笑顔で頑張るわね！','二日酔いの朝','◎',NULL,NULL,'approved','09:12:00','failed',NULL,'2025-10-03 00:25:08','2025-10-03 02:45:00');
INSERT INTO "posts" VALUES(133,12,'2025-10-03 10:27:00','私、お仕事早く終わったの！うふふ♡お家でゆっくりNetflixでも観ようかしら🦋','直接指示: 帰宅中で、今日は速く仕事が終わって、家でゆっくるnetflix','◎',NULL,NULL,'approved','10:27:00','failed','2025-10-03 00:39:30','2025-10-03 00:28:47','2025-10-03 01:50:00');
INSERT INTO "posts" VALUES(134,13,'2025-10-03 17:21:00','ストレスMAXで衝動買いしちゃった～！新作バッグとコスメ、可愛すぎる♡これで明日からまた頑張れるねっ♡','ストレス発散のため、ハイブランドのバッグやコスメを衝動買いしてしまう。','◎',NULL,NULL,'approved','2025-10-03T03:40:06.642707','sent','2025-10-03T03:40:06.642707','2025-10-03 00:50:44','2025-10-03 12:40:00');
INSERT INTO "posts" VALUES(135,13,'2025-10-03 23:18:00','あわわ…💦ライターさん、なかなか火がつかないよぉ～♡私、忘れちゃったのかな？🥺ごめんなさいっ♡','お客様のタバコに火をつけようとするが、ライターがなかなかつかない。','◎',NULL,NULL,'approved','23:18:00','sent','2025-10-03 01:18:22','2025-10-03 00:50:52','2025-10-03 01:15:00');
INSERT INTO "posts" VALUES(136,13,'2025-10-03 10:07:00','ほんとですか～♡嬉しいなっ♡でもね、お店のルールで連絡先は交換できないの🥺またお店に来てたくさんお話ししてくれたら嬉しいなっ♡','連絡先を聞かれ、「お店のルールで交換できないんです」というお決まりのセリフで断る。','×',NULL,NULL,'rejected','10:07:00','not_sent',NULL,'2025-10-03 00:51:03',NULL);
INSERT INTO "posts" VALUES(137,13,'2025-10-03 22:43:00','みんなのおはようは私のこんばんは♡今日も夜から華やかにいくよ👗✨','夕方頃に目覚め、普通の人の「おはよう」が自分の「こんばんは」。','◎',NULL,NULL,'approved','22:43:00','sent','2025-10-03 23:04:07','2025-10-03 00:51:13',NULL);
INSERT INTO "posts" VALUES(138,13,'2025-10-03 23:37:00','きゃー！お巡りさんがお店に来たの～♡私ちょっとびっくりしちゃった♡でも今日も元気に営業中だよ～♡','警察の風営法に関する立ち入り検査（査察）が入る。','×',NULL,NULL,'rejected','23:37:00','not_sent',NULL,'2025-10-03 00:51:23',NULL);
INSERT INTO "posts" VALUES(139,15,'2025-10-03 17:45:00','軽やかボブにチェンジ！気分も上がったし、ふらっと美味しいもの探しに出かけよっかな〜🍻','ヘアセット中','◎',NULL,NULL,'approved','2025-10-02T16:55:16.920800','sent','2025-10-02T16:55:16.920800','2025-10-03 01:15:54','2025-10-03 01:50:00');
INSERT INTO "posts" VALUES(140,15,'2025-10-03 20:15:00','ドタキャンも旅のアクシデント的な？✨これも何かの縁だよね！急遽空いた夜、どこ行こっかな〜🍻 #予定変更も楽しむ','同伴の約束をドタキャンされ、その日の売上予定が狂う。','◎',NULL,NULL,'approved','2025-10-02T16:37:12.772241','sent','2025-10-02T16:37:12.772241','2025-10-03 01:16:05','2025-10-03 01:25:00');
INSERT INTO "posts" VALUES(141,15,'2025-10-03 19:05:00','家族や地元の友達に、まだ本当の仕事話してないの。ごめんねって感じかな〜。でも、これが私なんだもんね😂','家族や地元の友人に、本当の仕事内容を言えずに嘘をついている罪悪感。','◎',NULL,NULL,'approved','2025-10-03T03:20:04.075446','sent','2025-10-03T03:20:04.075446','2025-10-03 01:16:16','2025-10-03 09:35:00');
INSERT INTO "posts" VALUES(142,15,'2025-10-03 11:03:00','やっちゃった〜！テキーラ飲みすぎて朝帰りって感じ？😂 でもこれも経験だよね！美味しいコーヒーで復活しよっと☕','テキーラを飲みすぎた日の朝帰り','◎',NULL,NULL,'approved','2025-10-03T14:35:17.227384','sent','2025-10-03T14:35:17.227384','2025-10-03 01:16:24','2025-10-03 23:15:00');
INSERT INTO "posts" VALUES(143,15,'2025-10-03 17:24:00','やっぱ本音で話せるの、同業の仲間だけだよね！色々聞いてもらってスッキリ〜。わかる〜！','結局、悩みを本音で話せるのは同業者（ナイトワーカー）の友人だけになる。','◎',NULL,NULL,'approved','2025-10-03T03:35:07.047236','sent','2025-10-03T03:35:07.047236','2025-10-03 01:16:32','2025-10-03 12:35:00');
INSERT INTO "posts" VALUES(144,NULL,'2025-10-03 01:33:45','テスト投稿 - cronが正常に動作するかの確認 10:36 投稿予定',NULL,NULL,NULL,NULL,'draft',NULL,'approved',NULL,NULL,'2025-10-03 10:36:45');
INSERT INTO "posts" VALUES(145,NULL,'2025-10-03 01:35:47','✅テスト投稿 - cronが正常に動作するかの確認 01:37 投稿予定 🦋',NULL,NULL,NULL,NULL,'draft',NULL,'approved',NULL,NULL,'2025-10-03 01:37:47');
INSERT INTO "posts" VALUES(146,12,'2025-10-03 01:43:12','🧪 cronテスト投稿 - 01:45 予定 🦋 正常動作確認中',NULL,'×',NULL,NULL,'rejected','01:43:12','sent','2025-10-03T01:46:44.618131',NULL,'2025-10-03 01:45:12');
INSERT INTO "posts" VALUES(147,14,'2025-10-03 02:10:41','🔧 shinrepoto - 初期成功アカウント動作テスト 02:13 予定',NULL,'×',NULL,NULL,'rejected','02:10:41','sent','2025-10-03T02:15:08.048479',NULL,'2025-10-03 02:13:41');
INSERT INTO "posts" VALUES(148,11,'2025-10-03 02:10:41','🔧 4te_123 - 初期成功アカウント動作テスト 02:14 予定',NULL,'×',NULL,NULL,'rejected','02:10:41','sent','2025-10-03T02:15:09.722331',NULL,'2025-10-03 02:14:41');
INSERT INTO "posts" VALUES(149,13,'2025-10-03 02:10:41','🔧 kawa_saki_style - 初期成功アカウント動作テスト 02:15 予定',NULL,'×',NULL,NULL,'rejected','02:10:41','sent','2025-10-03T02:17:58.420852',NULL,'2025-10-03 02:15:41');
INSERT INTO "posts" VALUES(150,15,'2025-10-03 02:11:13','🔧 Hiranonorico - 平野のリコ動作テスト 02:17 予定',NULL,'×',NULL,NULL,'rejected','02:11:13','sent','2025-10-03T02:18:00.067491',NULL,'2025-10-03 02:17:13');
INSERT INTO "posts" VALUES(151,14,'2025-10-03 02:59:01','♥テスト投稿♥ 03:09 UTC予定 - 時刻連携確認中♥',NULL,'×',NULL,NULL,'rejected','02:59:01','sent','2025-10-03T03:10:03.931100',NULL,'2025-10-03 03:09:01');
INSERT INTO "posts" VALUES(152,9,'2025-10-03 16:35:00','えっと…今月の雑誌もトレンドがぎっしり♡ 素敵なコーデやメイク、たくさん吸収しなくちゃですね♪ #ファッション研究','流行りのファッションやメイクを研究するため、雑誌やSNSを常にチェックする。',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,'2025-10-03 12:39:23',NULL);
INSERT INTO "posts" VALUES(153,9,'2025-10-03 22:00:00','こんばんは🌙 私にとっては今が「おはよう」なんですよ。夜の時間が皆様にとって素敵なものになりますように…🌸','夕方頃に目覚め、普通の人の「おはよう」が自分の「こんばんは」。',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,'2025-10-03 12:39:31',NULL);
INSERT INTO "posts" VALUES(154,9,'2025-10-03 20:41:00','タイプの違うお客様とのお話は、えっと…どちらも新鮮で楽しいんですよ♡頭の切り替えも、私の得意技かもしれませんね。 #六本木','タイプが全く違うお客様が同時に来店し、テーブルを行き来して頭を切り替える。','◎',NULL,NULL,'approved','2025-10-03T14:35:15.186287','sent','2025-10-03T14:35:15.186287','2025-10-03 12:39:39','2025-10-03 23:10:00');
INSERT INTO "posts" VALUES(155,9,'2025-10-03 19:04:00','あの…せっかくのお誘い、本当に嬉しいのですが、今日は少し難しくて…またお店でゆっくりお話したいです。','「アフター（同伴）行ける？」と聞かれ、上手にかわす。',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,'2025-10-03 12:39:48',NULL);
INSERT INTO "posts" VALUES(156,9,'2025-10-03 20:43:00','最新ファッション誌やSNSで流行チェック中✨お客様が素敵に見えるメイクも研究しなくちゃですね😊','流行りのファッションやメイクを研究するため、雑誌やSNSを常にチェックする。','◎',NULL,NULL,'approved','2025-10-03T03:50:12.236881','sent','2025-10-03T03:50:12.236881','2025-10-03 12:39:55','2025-10-03 12:50:00');
INSERT INTO "posts" VALUES(157,14,'2025-10-03 07:46:00','資料のフォント、カーニング、行間。気づかれなくとも、微調整に時間を惜しまない。僕の美学だ。','資料作成時、誰も気づかないようなフォントのカーニングや行間にまでこだわってしまう。','◎',NULL,NULL,'approved','2025-10-03T15:46:05.652789','sent','2025-10-03T15:46:05.652789','2025-10-03 13:35:14','2025-10-04 00:45:00');
INSERT INTO "posts" VALUES(158,14,'2025-10-03 23:10:00','業務時間外でも、新スタンプや絵文字は確認しておく。これが僕のルーティン。','業務時間外に、会社のチャットツールに新しいスタンプや絵文字が追加されていないかチェックする。','◎',NULL,NULL,'approved','2025-10-03T15:40:25.084317','sent','2025-10-03T15:40:25.084317','2025-10-03 13:35:22','2025-10-04 00:30:00');
INSERT INTO "posts" VALUES(159,14,'2025-10-03 15:16:00','僕のガジェットに合わせた専用ケースを3Dプリンターで作ってみた。収まりが良い。','3Dプリンターで、自分の持っているガジェットにぴったりのスタンドやケースを自作する。','◎',NULL,NULL,'approved','2025-10-03T14:35:13.457928','sent','2025-10-03T14:35:13.457928','2025-10-03 13:35:29','2025-10-03 23:05:00');
INSERT INTO "posts" VALUES(160,14,'2025-10-03 10:08:00','PCトラブルで呼ばれる日々。非公式ヘルプデスク、僕が担当している。','同僚のPCトラブル（ネットに繋がらない、フリーズした等）を解決してしまい、非公式な社内ヘルプデスクと化す。','◎',NULL,NULL,'approved','2025-10-03T15:50:04.180182','sent','2025-10-03T15:50:04.180182','2025-10-03 13:35:37','2025-10-04 00:50:00');
INSERT INTO "posts" VALUES(161,14,'2025-10-03 03:23:00','PCのファンクションキーに付箋。スマートな方法があるだろうに、と僕は思う。','PCのファンクションキーに付箋でメモを貼っている人を見ると、もっとスマートな方法があるのに…と思ってしまう。','◎',NULL,NULL,'approved','2025-10-04T03:04:05.627560','sent','2025-10-04T03:04:05.627560','2025-10-03 13:35:45','2025-10-04 11:55:00');
INSERT INTO "posts" VALUES(162,12,'2025-10-03 19:18:00','本音で話せるのは、やっぱり〇〇だけなの。いつもありがとう、うふふ♡今度ゆっくりお話ししたいわね🥂','結局、悩みを本音で話せるのは同業者（ナイトワーカー）の友人だけになる。',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,'2025-10-03 23:25:31',NULL);
INSERT INTO "posts" VALUES(163,12,'2025-10-03 22:53:00','最近、バックヤードがちょっぴり冷たい空気なの…みんなで仲良くしたいですわね、うふふ♡','派閥ができて、バックヤードの空気が険悪になる。',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,'2025-10-03 23:25:42',NULL);
INSERT INTO "posts" VALUES(164,12,'2025-10-03 06:22:00','うふふ♡やっぱり本音で話せるのは同業のお友達だけですわね。色々聞いてもらってスッキリなの🦋✨いつもありがとう、感謝ですわ♡','結局、悩みを本音で話せるのは同業者（ナイトワーカー）の友人だけになる。',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,'2025-10-03 23:25:50',NULL);
INSERT INTO "posts" VALUES(165,12,'2025-10-03 18:35:00','家族や友人に本当のこと、なかなか言えないの…😢 罪悪感で胸がチクッとするわね、うふふ♡','家族や地元の友人に、本当の仕事内容を言えずに嘘をついている罪悪感。',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,'2025-10-03 23:26:01',NULL);
INSERT INTO "posts" VALUES(166,12,'2025-10-03 20:37:00','まるで蝶のようにテーブルを行き来🦋色んなタイプのお客様との会話は楽しいの♡うふふ♡','タイプが全く違うお客様が同時に来店し、テーブルを行き来して頭を切り替える。','◎',NULL,NULL,'approved','20:37:00','failed',NULL,'2025-10-03 23:26:10','2025-10-03 23:30:00');
INSERT INTO "posts" VALUES(167,13,'2025-10-04 22:23:00','ライバル店の噂、すごーい♡でもClub Venusは最強だから大丈夫！今夜も私に会いに来てね♡','ライバル店のオープンや閉店の噂で持ちきりになる。',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,'2025-10-04 00:51:58',NULL);
INSERT INTO "posts" VALUES(168,13,'2025-10-04 01:45:00','やっちゃった～♡ストレス発散でハイブランドのバッグとコスメ爆買い！でも後悔してないもんっ！これでまた頑張れる～🥰','ストレス発散のため、ハイブランドのバッグやコスメを衝動買いしてしまう。',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,'2025-10-04 00:52:07',NULL);
INSERT INTO "posts" VALUES(169,13,'2025-10-04 20:06:00','今日はちょっとバタバタしちゃったけど、お店は元気だよー♡ みんなに会えるの楽しみにしてるねっ♡','警察の風営法に関する立ち入り検査（査察）が入る。','◎',NULL,NULL,'approved','2025-10-03T15:55:05.206149','sent','2025-10-03T15:55:05.206149','2025-10-04 00:52:16','2025-10-04 00:55:00');
INSERT INTO "posts" VALUES(170,13,'2025-10-04 15:04:00','二日酔いでベッドとお友達な休日～🥺💦でも、ぐっすり眠れたから、また今週も頑張れそう♡みんなもゆっくり休んでね🥰 #オフモード #休日の過ごし方','休日は二日酔いと疲労で、一日中ベッドから出られないことも多い。',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,'2025-10-04 00:52:27',NULL);
INSERT INTO "posts" VALUES(171,13,'2025-10-04 19:09:00','周年パーティー大盛況ー♡OBOGの先輩方にも会えて嬉しいな♡みんなでシャンパン飲んで盛り上がろっ♡','お店の周年記念パーティーで、OBやOGのキャストが遊びに来る。',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,'2025-10-04 00:52:33',NULL);
INSERT INTO "posts" VALUES(172,14,'2025-10-04 11:41:00','スマートウォッチのデータ確認。睡眠スコアに一喜一憂する僕。','スマートウォッチの睡眠スコアや体のデータを見て、自分の健康状態を分析し一喜一憂する。',NULL,NULL,NULL,'approved','2025-10-05T10:15:03.753059','sent','2025-10-05T10:15:03.753059','2025-10-04 12:06:57','2025-10-05 18:45:00');
INSERT INTO "posts" VALUES(173,14,'2025-10-04 16:39:00','友人の家。まずはWi-Fiパスワード。そして速度測定。これは僕のルーティン。','友人の家に行くと、まずWi-Fiのパスワードを聞き、通信速度を測定する。',NULL,NULL,NULL,'approved','2025-10-05T10:15:04.338537','sent','2025-10-05T10:15:04.338537','2025-10-04 12:07:05','2025-10-05 18:50:00');
INSERT INTO "posts" VALUES(174,14,'2025-10-04 18:55:00','ガジェットレビュー動画、見始めると時間を忘れる。この探求心が僕を動かす。','ガジェットのレビュー動画をYouTubeで見始めると、時間を忘れて見続けてしまう。','◎',NULL,NULL,'approved','2025-10-05T10:30:02.015815','sent','2025-10-05T10:30:02.015815','2025-10-04 12:07:13','2025-10-05 19:30:00');
INSERT INTO "posts" VALUES(175,14,'2025-10-04 21:48:00','特殊変換アダプターを会社に忘れた。終わったな、僕の今日。','会社に、その日使うはずだった特殊な変換アダプターを忘れてきたことに気づき、絶望する。','◎',NULL,NULL,'approved','2025-10-04T03:15:04.925609','sent','2025-10-04T03:15:04.925609','2025-10-04 12:07:23','2025-10-04 12:15:00');
INSERT INTO "posts" VALUES(176,14,'2025-10-04 00:00:00','持ち物全てにスマートタグ装着済み。万が一の紛失にも動じない。それが僕のスタイル。','鍵、財布、カバンなど、あらゆる所有物にスマートタグを取り付けている。',NULL,NULL,NULL,'approved','2025-10-05T10:15:05.057569','sent','2025-10-05T10:15:05.057569','2025-10-04 12:07:29','2025-10-05 18:55:00');
INSERT INTO "posts" VALUES(177,11,'2025-10-04 14:23:00','お昼焼肉、魅力的すぎますね♪ でも午後会議…匂いどうしよう？えへへ♡葛藤中なんですよぉ😭','午後の仕事の会議のことを考え、ランチ焼肉で匂いがつくことを懸念し、行くか行くまいか葛藤する。',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,'2025-10-04 12:17:19',NULL);
INSERT INTO "posts" VALUES(178,11,'2025-10-04 19:24:00','美味しい焼肉ランチでパワーチャージ完了ですっ💖 経費の上限、私ちゃーんと知ってるんですよ〜♪ えへへ♡','会社の経費で利用できる焼肉ランチの上限金額を正確に把握している。','◎',NULL,NULL,'approved','19:24:00','not_sent',NULL,'2025-10-04 12:17:27',NULL);
INSERT INTO "posts" VALUES(179,11,'2025-10-04 10:06:00','会議中なのに、今夜の焼肉のことばっかり考えちゃう私…えへへ♡ どれにしようかなぁ〜？🍖✨','朝の定例会議中、上の空で「今夜の焼keynote…いや焼肉の段取り」について考えてしまう。',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,'2025-10-04 12:17:33',NULL);
INSERT INTO "posts" VALUES(180,11,'2025-10-04 03:27:00','お肉の焼き加減って、その人の性格や育ちが出ますよね♪ 私、わかっちゃうんですよ♡','肉の焼き加減で、その人の性格や育ちがわかると思っている。','◎',NULL,NULL,'approved','2025-10-04T03:25:04.616798','sent','2025-10-04T03:25:04.616798','2025-10-04 12:17:41','2025-10-04 12:25:00');
INSERT INTO "posts" VALUES(181,11,'2025-10-04 17:25:00','福利厚生で焼肉クーポン探すの、私のお決まりなんです♪ 美味しいお肉、食べに行きたいですねぇ♡ えへへ♡','会社の福利厚生で、焼肉店の割引クーポンがないか定期的にチェックする。',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,'2025-10-04 12:17:50',NULL);
INSERT INTO "posts" VALUES(182,16,'2025-10-04 11:07:00','ネイルポリッシュ、もはや指の本数超えちゃった🤣ラメ系多くて選べない！どうしよっかなー。','ネイルポリッシュを大量に集めてしまい、もはや自分の指の数では塗りきれないとわかっている。',NULL,NULL,NULL,'approved','2025-10-04 23:47:53','not_sent',NULL,'2025-10-04 23:43:59',NULL);
INSERT INTO "posts" VALUES(183,16,'2025-10-04 01:46:00','コスメブランドの歴史？任せて！ラメの輝きには深い意味があるんだよ。ブルベ夏にはコレ！✨ #コスメ沼 #そよよ','コスメブランドの歴史や、創業者のストーリーまで語ることができる。',NULL,NULL,NULL,'approved','2025-10-04 23:47:53','not_sent',NULL,'2025-10-04 23:44:08',NULL);
INSERT INTO "posts" VALUES(184,16,'2025-10-04 03:52:00','今日の美容雑誌、付録がとんでもなく豪華だったから即買い！ラメ好きにはたまらない内容もあって、大満足だよー✨ #美容雑誌 #付録','美容雑誌は、付録の豪華さで買うかどうかを決める。',NULL,NULL,NULL,'approved','2025-10-04 23:47:53','not_sent',NULL,'2025-10-04 23:44:15',NULL);
INSERT INTO "posts" VALUES(185,16,'2025-10-04 23:27:00','残業でクタクタ肌には速攻クレンジングバーム！💆‍♀️✨ 基本ケアこそ大事。優しくオフして明日に備えるよ😉','残業で疲れた肌をいたわるため、帰宅後すぐにクレンジングバームで優しくメイクをオフする。',NULL,NULL,NULL,'approved','2025-10-04 23:47:53','not_sent',NULL,'2025-10-04 23:44:25',NULL);
INSERT INTO "posts" VALUES(186,16,'2025-10-04 23:30:00','最新コスメ好きのそよよ、飲み会対策は崩れ防止スプレーを念入りにね！夜まで完璧よ🥂','会社の飲み会がある日は、化粧崩れ防止のスプレーを朝のメイクの仕上げに念入りに吹きかけておく。','◎',NULL,NULL,'approved','2025-10-04T14:55:17.272285','sent','2025-10-04T14:55:17.272285','2025-10-04 23:44:35','2025-10-04 23:55:00');
INSERT INTO "posts" VALUES(187,16,'2025-10-05 09:16:00','星占い、今日のラッキーカラー発表！早速ラッキーカラーのラメコスメで気分上げよっと✨ #ブルベ夏 #コスメ','朝の情報番組の星占いで、自分の星座のラッキーカラーが発表されると、その色のコスメを使いたくなる。',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,'2025-10-05 12:56:00',NULL);
INSERT INTO "posts" VALUES(188,16,'2025-10-05 20:31:00','サバサバそよよ流！同僚へのお礼は高級ハンドクリームかリップバーム一択。絶対喜ばれるよー！ #コスメ好き','同僚へのちょっとしたプレゼントやお礼に、高級ブランドのハンドクリームやリップバームを贈ると喜ばれることを知っている。',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,'2025-10-05 12:56:07',NULL);
INSERT INTO "posts" VALUES(189,16,'2025-10-05 11:32:00','アイシャドウパレットの締め色、なぜかこれだけなくなるの毎回あるある😂 みんなはどう？そろそろストックかな〜','アイシャドウパレットの特定の「締め色」だけが先に無くなり、「あるある」と共感する。',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,'2025-10-05 12:56:15',NULL);
INSERT INTO "posts" VALUES(190,16,'2025-10-05 03:12:00','職場のプレゼントにはデパコス系ハンドクリームやリップバームが鉄板！私の経験上、これはマジで喜ばれるやつ。','同僚へのちょっとしたプレゼントやお礼に、高級ブランドのハンドクリームやリップバームを贈ると喜ばれることを知っている。',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,'2025-10-05 12:56:22',NULL);
INSERT INTO "posts" VALUES(191,16,'2025-10-05 13:55:00','同僚と話してたけど、今週末あのデパート、ポイント5倍だって！ラメコスメ買いに行っちゃおうかな？✨ #コスメ #お得情報','昼休み、会社の同僚と「あのデパートのポイント、今週末5倍だよ」といったお得情報を交換する。',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,'2025-10-05 12:56:31',NULL);
INSERT INTO "posts" VALUES(192,14,'2025-10-05 17:00:00','友人の充電がピンチ。はい、僕のモバイルバッテリー。困った時は、頼りになる僕がいるでしょ？','友人のスマホの充電が切れそうだと、自分のモバイルバッテリーをドヤ顔で貸してあげる。',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,'2025-10-05 18:38:07',NULL);
INSERT INTO "posts" VALUES(193,14,'2025-10-05 02:49:00','またクラウドファンディングで尖ったガジェットに出資した。僕の直感が正しければ、これはくる。','クラウドファンディングサイトで、まだ世に出ていない尖ったガジェットに出資するのが好き。','◎',NULL,NULL,'approved','02:49:00','not_sent',NULL,'2025-10-05 18:38:15',NULL);
INSERT INTO "posts" VALUES(194,14,'2025-10-05 22:01:00','VRゴーグル装着。今夜も友人たちと仮想空間で。僕の夜はまだ続く。','VRゴーグルを装着し、仮想空間でゲームをしたり友人と会ったりして夜を過ごす。','◎',NULL,NULL,'approved','2025-10-05T13:45:04.894738','sent','2025-10-05T13:45:04.894738','2025-10-05 18:38:25','2025-10-05 22:45:00');
INSERT INTO "posts" VALUES(195,14,'2025-10-05 19:28:00','特殊変換アダプター、会社に忘れた。絶望。','会社に、その日使うはずだった特殊な変換アダプターを忘れてきたことに気づき、絶望する。','×',NULL,NULL,'rejected','19:28:00','not_sent',NULL,'2025-10-05 18:38:34',NULL);
INSERT INTO "posts" VALUES(196,14,'2025-10-05 00:32:00','満足感は一時。僕の物欲は、常に次の新製品を求めている。','新しいガジェットを買った満足感より、次の新製品への物欲がすぐに勝ってしまう。',NULL,NULL,NULL,'draft',NULL,'not_sent',NULL,'2025-10-05 18:38:42',NULL);
CREATE TABLE retweet_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cast_id INTEGER NOT NULL,
    tweet_id TEXT NOT NULL,
    comment TEXT,  -- 空の場合は通常リツイート、ありの場合は引用ツイート
    scheduled_at TEXT NOT NULL,  -- JST時刻 'YYYY-MM-DD HH:MM:SS'
    status TEXT DEFAULT 'scheduled',  -- 'scheduled', 'completed', 'failed'
    created_at TEXT NOT NULL,
    executed_at TEXT,
    result_tweet_id TEXT,  -- 実行後の結果ツイートID（引用ツイートの場合）
    error_message TEXT,
    FOREIGN KEY(cast_id) REFERENCES casts(id) ON DELETE CASCADE
);
INSERT INTO "retweet_schedules" VALUES(2,14,'1973939982806233533','','2025-10-03 04:44:22','completed','2025-10-03 13:34:22','2025-10-03 13:47:39','',NULL);
INSERT INTO "retweet_schedules" VALUES(3,14,'1973956342366023955','','2025-10-03 04:53:37','failed','2025-10-03 13:43:37',NULL,NULL,'HTTP 500: {"status": "error", "message": "Rate limit exceeded. Free Tier: 50 retweets/24h. Please wait before retrying.", "error_type": "Exception"}');
INSERT INTO "retweet_schedules" VALUES(4,14,'1973684094749032695','','2025-10-04 02:26:56','failed','2025-10-03 13:50:51','2025-10-04 10:25:05',NULL,'HTTP 500: {"status": "error", "message": "Retweet failed: 400 Bad Request\nYou cannot retweet a Tweet that you have already retweeted.", "error_type": "Exception"}');
INSERT INTO "retweet_schedules" VALUES(5,14,'1973956342366023955','','2025-10-03 11:58:33','failed','2025-10-03 14:00:00','2025-10-03 19:00:03',NULL,'HTTP 500: {"status": "error", "message": "Rate limit exceeded. Free Tier: 50 retweets/24h. Please wait before retrying.", "error_type": "Exception"}');
INSERT INTO "retweet_schedules" VALUES(6,14,'1973956342366023955','','2025-10-03 10:03:10','completed','2025-10-03 18:53:10','2025-10-03 09:53:21','',NULL);
INSERT INTO "retweet_schedules" VALUES(7,14,'1974024290988412933','NVIDIA、日本と「AI×ロボット」生産改革！楽しみｗ','2025-10-03 10:05:03','completed','2025-10-03 18:55:03','2025-10-03 19:00:02','1974051810035089506',NULL);
INSERT INTO "retweet_schedules" VALUES(8,14,'1974028063248986611','','2025-10-04 02:25:04','failed','2025-10-03 22:59:38',NULL,NULL,'HTTP 500: {"status": "error", "message": "Rate limit exceeded. Free Tier: 50 retweets/24h. Please wait before retrying.", "error_type": "Exception"}');
INSERT INTO "retweet_schedules" VALUES(9,14,'1974034353039831480','','2025-10-04 00:35:51','completed','2025-10-04 00:25:51','2025-10-03 15:26:10','',NULL);
INSERT INTO "retweet_schedules" VALUES(10,14,'1938438118279107066','','2025-10-04 01:00:38','completed','2025-10-04 00:50:38','2025-10-04 01:05:02','',NULL);
INSERT INTO "retweet_schedules" VALUES(11,14,'1974016741820047774','','2025-10-04 01:07:54','failed','2025-10-04 00:57:54','2025-10-04 01:10:02',NULL,'HTTP 500: {"status": "error", "message": "Rate limit exceeded. Free Tier: 50 retweets/24h. Please wait before retrying.", "error_type": "Exception"}');
INSERT INTO "retweet_schedules" VALUES(12,14,'1974253300850839734','','2025-10-04 11:11:41','completed','2025-10-04 11:01:41','2025-10-04 11:15:04','',NULL);
INSERT INTO "retweet_schedules" VALUES(13,11,'1973532419992199659','','2025-10-04 12:48:18','completed','2025-10-04 12:38:18','2025-10-04 12:50:02','',NULL);
INSERT INTO "retweet_schedules" VALUES(14,16,'1969506979988095182','飛びたいわ✈️','2025-10-04 23:57:35','completed','2025-10-04 23:47:35','2025-10-05 00:00:03','1974489697536872668',NULL);
INSERT INTO "retweet_schedules" VALUES(15,14,'1974278302400446768','','2025-10-05 00:29:39','completed','2025-10-05 00:19:39','2025-10-05 00:30:02','',NULL);
INSERT INTO "retweet_schedules" VALUES(16,14,'1974735553611612210','','2025-10-05 18:54:53','completed','2025-10-05 18:44:53','2025-10-05 18:55:05','',NULL);
INSERT INTO "retweet_schedules" VALUES(17,14,'1974707507164819765','','2025-10-05 22:51:49','completed','2025-10-05 22:41:49','2025-10-05 22:55:02','',NULL);
CREATE TABLE send_history (id INTEGER PRIMARY KEY, post_id INTEGER, destination TEXT, sent_at TEXT, scheduled_datetime TEXT, status TEXT DEFAULT 'pending', error_message TEXT, FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE);
INSERT INTO "send_history" VALUES(1,27,'google_sheets','2025-09-25 12:44:04','2025-09-25 12:00:00','failed','Google Sheets認証ファイルが見つかりません。credentials/service-account-key.jsonを配置してください。');
INSERT INTO "send_history" VALUES(2,27,'google_sheets','2025-09-25 12:50:49','2025-09-25 12:00:00','failed','Google Sheets認証ファイルが見つかりません。credentials/service-account-key.jsonを配置してください。');
INSERT INTO "send_history" VALUES(3,27,'google_sheets','2025-09-25 12:51:14','2025-09-25 12:00:00','failed','Google Sheets認証ファイルが見つかりません。credentials/service-account-key.jsonを配置してください。');
INSERT INTO "send_history" VALUES(4,27,'google_sheets','2025-09-25 12:51:18','2025-09-25 12:00:00','failed','Google Sheets認証ファイルが見つかりません。credentials/service-account-key.jsonを配置してください。');
INSERT INTO "send_history" VALUES(5,27,'google_sheets','2025-09-25 12:59:18','2025-09-25 12:00:00','failed','Google Sheets連携の設定が必要です。

【OAuth認証設定手順】
1. [Google Cloud Console](https://console.cloud.google.com) にアクセス
2. 新しいプロジェクトを作成または既存プロジェクト選択
3. 「APIとサービス」> 「ライブラリ」で以下を有効化：
   - Google Sheets API
   - Google Drive API
4. 「APIとサービス」> 「認証情報」> 「認証情報を作成」> 「OAuthクライアントID」
5. アプリケーションの種類：「デスクトップアプリケーション」
6. 作成されたクライアントIDの右側の「ダウンロード」ボタンをクリック
7. ダウンロードしたJSONファイルを `credentials/credentials.json` として保存
8. アプリを再起動して送信を試行（ブラウザでの認証が開始されます）

設定完了後、再度送信をお試しください。');
INSERT INTO "send_history" VALUES(6,27,'google_sheets','2025-09-25 12:59:23','2025-09-25 12:00:00','failed','Google Sheets連携の設定が必要です。

【OAuth認証設定手順】
1. [Google Cloud Console](https://console.cloud.google.com) にアクセス
2. 新しいプロジェクトを作成または既存プロジェクト選択
3. 「APIとサービス」> 「ライブラリ」で以下を有効化：
   - Google Sheets API
   - Google Drive API
4. 「APIとサービス」> 「認証情報」> 「認証情報を作成」> 「OAuthクライアントID」
5. アプリケーションの種類：「デスクトップアプリケーション」
6. 作成されたクライアントIDの右側の「ダウンロード」ボタンをクリック
7. ダウンロードしたJSONファイルを `credentials/credentials.json` として保存
8. アプリを再起動して送信を試行（ブラウザでの認証が開始されます）

設定完了後、再度送信をお試しください。');
INSERT INTO "send_history" VALUES(7,27,'google_sheets','2025-09-25 13:05:04','2025-09-25 12:00:00','failed','Google Sheets連携の設定が必要です。

【OAuth認証設定手順】
1. [Google Cloud Console](https://console.cloud.google.com) にアクセス
2. 新しいプロジェクトを作成または既存プロジェクト選択
3. 「APIとサービス」> 「ライブラリ」で以下を有効化：
   - Google Sheets API
   - Google Drive API
4. 「APIとサービス」> 「認証情報」> 「認証情報を作成」> 「OAuthクライアントID」
5. アプリケーションの種類：「デスクトップアプリケーション」
6. 作成されたクライアントIDの右側の「ダウンロード」ボタンをクリック
7. ダウンロードしたJSONファイルを `credentials/credentials.json` として保存
8. アプリを再起動して送信を試行（ブラウザでの認証が開始されます）

設定完了後、再度送信をお試しください。');
INSERT INTO "send_history" VALUES(8,27,'google_sheets','2025-09-25 13:42:14','2025-09-25 12:00:00','completed',NULL);
INSERT INTO "send_history" VALUES(9,26,'google_sheets','2025-09-25 13:48:09','2025-09-25 16:35:00','completed',NULL);
INSERT INTO "send_history" VALUES(10,29,'google_sheets','2025-09-25 13:56:07','2025-09-25 20:36:00','completed',NULL);
INSERT INTO "send_history" VALUES(11,28,'google_sheets','2025-09-25 22:00:21','2025-09-25 19:16:00','failed','Google Sheets連携の設定が必要です。

【OAuth認証設定手順】
1. [Google Cloud Console](https://console.cloud.google.com) にアクセス
2. 新しいプロジェクトを作成または既存プロジェクト選択
3. 「APIとサービス」> 「ライブラリ」で以下を有効化：
   - Google Sheets API
   - Google Drive API
4. 「APIとサービス」> 「認証情報」> 「認証情報を作成」> 「OAuthクライアントID」
5. アプリケーションの種類：「デスクトップアプリケーション」
6. 作成されたクライアントIDの右側の「ダウンロード」ボタンをクリック
7. ダウンロードしたJSONファイルを `credentials/credentials.json` として保存
8. アプリを再起動して送信を試行（ブラウザでの認証が開始されます）

設定完了後、再度送信をお試しください。');
INSERT INTO "send_history" VALUES(12,28,'google_sheets','2025-09-25 22:00:29','2025-09-25 19:16:00','failed','Google Sheets連携の設定が必要です。

【OAuth認証設定手順】
1. [Google Cloud Console](https://console.cloud.google.com) にアクセス
2. 新しいプロジェクトを作成または既存プロジェクト選択
3. 「APIとサービス」> 「ライブラリ」で以下を有効化：
   - Google Sheets API
   - Google Drive API
4. 「APIとサービス」> 「認証情報」> 「認証情報を作成」> 「OAuthクライアントID」
5. アプリケーションの種類：「デスクトップアプリケーション」
6. 作成されたクライアントIDの右側の「ダウンロード」ボタンをクリック
7. ダウンロードしたJSONファイルを `credentials/credentials.json` として保存
8. アプリを再起動して送信を試行（ブラウザでの認証が開始されます）

設定完了後、再度送信をお試しください。');
INSERT INTO "send_history" VALUES(13,28,'google_sheets','2025-09-25 22:00:35','2025-09-25 19:16:00','failed','Google Sheets連携の設定が必要です。

【OAuth認証設定手順】
1. [Google Cloud Console](https://console.cloud.google.com) にアクセス
2. 新しいプロジェクトを作成または既存プロジェクト選択
3. 「APIとサービス」> 「ライブラリ」で以下を有効化：
   - Google Sheets API
   - Google Drive API
4. 「APIとサービス」> 「認証情報」> 「認証情報を作成」> 「OAuthクライアントID」
5. アプリケーションの種類：「デスクトップアプリケーション」
6. 作成されたクライアントIDの右側の「ダウンロード」ボタンをクリック
7. ダウンロードしたJSONファイルを `credentials/credentials.json` として保存
8. アプリを再起動して送信を試行（ブラウザでの認証が開始されます）

設定完了後、再度送信をお試しください。');
INSERT INTO "send_history" VALUES(14,28,'google_sheets','2025-09-26 14:43:23','2025-09-25 19:16:00','failed','OAuth認証エラー: ''dict'' object has no attribute ''valid''');
INSERT INTO "send_history" VALUES(15,28,'google_sheets','2025-09-26 14:43:28','2025-09-25 19:16:00','failed','OAuth認証エラー: ''dict'' object has no attribute ''valid''');
INSERT INTO "send_history" VALUES(16,28,'google_sheets','2025-09-26 14:44:35','2025-09-25 19:16:00','failed','OAuth認証エラー: ''dict'' object has no attribute ''valid''');
INSERT INTO "send_history" VALUES(17,28,'google_sheets','2025-09-26 14:46:19','2025-09-25 19:16:00','failed','Google Sheets送信エラー: APIError: [403]: Request had insufficient authentication scopes.');
INSERT INTO "send_history" VALUES(18,28,'google_sheets','2025-09-26 14:47:01','2025-09-25 19:16:00','failed','Google Sheets送信エラー: APIError: [403]: Request had insufficient authentication scopes.');
INSERT INTO "send_history" VALUES(19,28,'google_sheets','2025-09-26 14:47:08','2025-09-25 19:16:00','failed','Google Sheets送信エラー: APIError: [403]: Request had insufficient authentication scopes.');
INSERT INTO "send_history" VALUES(20,28,'google_sheets','2025-09-26 14:49:22','2025-09-25 19:16:00','failed','Google Sheets送信エラー: APIError: [403]: Request had insufficient authentication scopes.');
INSERT INTO "send_history" VALUES(21,28,'google_sheets','2025-09-26 14:50:06','2025-09-25 19:16:00','completed',NULL);
INSERT INTO "send_history" VALUES(22,40,'google_sheets','2025-09-26 14:55:24','2025-09-26 19:15:00','completed',NULL);
INSERT INTO "send_history" VALUES(23,46,'google_sheets','2025-09-26 23:13:43','2025-09-26 22:05:00','completed',NULL);
INSERT INTO "send_history" VALUES(24,41,'google_sheets','2025-09-26 23:14:20','2025-09-26 13:09:00','completed',NULL);
INSERT INTO "send_history" VALUES(25,45,'google_sheets','2025-09-26 23:22:45','2025-09-26 18:20:00','completed',NULL);
INSERT INTO "send_history" VALUES(26,48,'google_sheets','2025-09-26 23:22:51','2025-09-26 23:40:00','completed',NULL);
INSERT INTO "send_history" VALUES(27,44,'google_sheets','2025-09-26 23:22:54','2025-09-26 18:43:00','completed',NULL);
INSERT INTO "send_history" VALUES(28,42,'google_sheets','2025-09-26 23:22:56','2025-09-26 15:57:00','completed',NULL);
INSERT INTO "send_history" VALUES(29,30,'google_sheets','2025-09-26 23:22:58','2025-09-25 13:57:14','completed',NULL);
INSERT INTO "send_history" VALUES(30,47,'google_sheets','2025-09-27 00:06:46','2025-09-27 09:44:00','completed',NULL);
INSERT INTO "send_history" VALUES(31,43,'google_sheets','2025-09-27 00:07:09','2025-09-30 10:29:00','completed',NULL);
INSERT INTO "send_history" VALUES(32,49,'google_sheets','2025-09-27 00:07:20','2025-09-27 10:19:00','completed',NULL);
INSERT INTO "send_history" VALUES(33,52,'x_api','2025-09-27 01:51:02','2025-09-27 13:12:00','completed',NULL);
INSERT INTO "send_history" VALUES(34,58,'x_api','2025-09-27 09:40:22','2025-09-27 10:19:00','failed','キャストID 14 の認証情報が設定されていません');
INSERT INTO "send_history" VALUES(35,58,'x_api','2025-09-27 09:40:38','2025-09-27 10:19:00','failed','キャストID 14 の認証情報が設定されていません');
INSERT INTO "send_history" VALUES(36,58,'x_api','2025-09-27 09:41:27','2025-09-27 10:19:00','completed',NULL);
INSERT INTO "send_history" VALUES(37,59,'google_sheets','2025-09-27 13:06:07','2025-09-27 14:43:00','failed','OAuth認証待機中: 認証コードを入力してください');
INSERT INTO "send_history" VALUES(38,59,'google_sheets','2025-09-27 13:06:16','2025-09-27 14:43:00','failed','OAuth認証待機中: 認証コードを入力してください');
INSERT INTO "send_history" VALUES(39,59,'google_sheets','2025-09-27 13:06:28','2025-09-27 14:43:00','failed','OAuth認証待機中: 認証コードを入力してください');
INSERT INTO "send_history" VALUES(40,59,'google_sheets','2025-09-27 13:06:36','2025-09-27 14:43:00','failed','OAuth認証待機中: 認証コードを入力してください');
INSERT INTO "send_history" VALUES(41,59,'google_sheets','2025-09-27 13:18:39','2025-09-27 14:43:00','failed','OAuth認証待機中: 認証コードを入力してください');
INSERT INTO "send_history" VALUES(42,59,'google_sheets','2025-09-27 13:18:46','2025-09-27 14:43:00','failed','OAuth認証待機中: 認証コードを入力してください');
INSERT INTO "send_history" VALUES(43,59,'google_sheets','2025-09-27 13:21:02','2025-09-27 14:43:00','failed','OAuth認証待機中: 認証コードを入力してください');
INSERT INTO "send_history" VALUES(44,59,'google_sheets','2025-09-27 13:21:08','2025-09-27 14:43:00','failed','OAuth認証待機中: 認証コードを入力してください');
INSERT INTO "send_history" VALUES(45,59,'google_sheets','2025-09-27 13:21:15','2025-09-27 14:43:00','failed','OAuth認証待機中: 認証コードを入力してください');
INSERT INTO "send_history" VALUES(46,59,'google_sheets','2025-09-27 13:21:19','2025-09-27 14:43:00','failed','OAuth認証待機中: 認証コードを入力してください');
INSERT INTO "send_history" VALUES(47,59,'google_sheets','2025-09-27 13:21:30','2025-09-27 14:43:00','failed','OAuth認証待機中: 認証コードを入力してください');
INSERT INTO "send_history" VALUES(48,59,'google_sheets','2025-09-27 13:21:36','2025-09-27 14:43:00','failed','OAuth認証待機中: 認証コードを入力してください');
INSERT INTO "send_history" VALUES(49,59,'google_sheets','2025-09-27 13:21:58','2025-09-27 14:43:00','failed','OAuth認証待機中: 認証コードを入力してください');
INSERT INTO "send_history" VALUES(50,59,'google_sheets','2025-09-27 13:22:06','2025-09-27 14:43:00','failed','OAuth認証待機中: 認証コードを入力してください');
INSERT INTO "send_history" VALUES(51,59,'google_sheets','2025-09-27 13:38:12','2025-09-27 14:43:00','failed','OAuth認証待機中: 認証コードを入力してください');
INSERT INTO "send_history" VALUES(52,59,'google_sheets','2025-09-27 13:38:17','2025-09-27 14:43:00','failed','OAuth認証待機中: 認証コードを入力してください');
INSERT INTO "send_history" VALUES(53,59,'google_sheets','2025-09-27 13:38:48','2025-09-27 14:43:00','failed','OAuth認証待機中: 認証コードを入力してください');
INSERT INTO "send_history" VALUES(54,59,'google_sheets','2025-09-27 13:38:55','2025-09-27 14:43:00','failed','OAuth認証待機中: 認証コードを入力してください');
INSERT INTO "send_history" VALUES(55,59,'google_sheets','2025-09-27 13:39:53','2025-09-27 14:43:00','failed','OAuth認証待機中: 認証コードを入力してください');
INSERT INTO "send_history" VALUES(56,59,'google_sheets','2025-09-27 13:39:59','2025-09-27 14:43:00','failed','OAuth認証待機中: 認証コードを入力してください');
INSERT INTO "send_history" VALUES(57,59,'google_sheets','2025-09-27 13:40:05','2025-09-27 14:43:00','failed','OAuth認証待機中: 認証コードを入力してください');
INSERT INTO "send_history" VALUES(58,59,'google_sheets','2025-09-27 13:40:11','2025-09-27 14:43:00','failed','OAuth認証待機中: 認証コードを入力してください');
INSERT INTO "send_history" VALUES(59,59,'google_sheets','2025-09-27 13:40:21','2025-09-27 14:43:00','failed','OAuth認証待機中: 認証コードを入力してください');
INSERT INTO "send_history" VALUES(60,59,'google_sheets','2025-09-27 13:40:43','2025-09-27 14:43:00','failed','OAuth認証待機中: 認証コードを入力してください');
INSERT INTO "send_history" VALUES(61,59,'google_sheets','2025-09-27 17:32:41','2025-09-27 14:43:00','completed',NULL);
INSERT INTO "send_history" VALUES(62,82,'google_sheets','2025-09-27 21:45:00','2025-09-27 07:11:00','completed',NULL);
INSERT INTO "send_history" VALUES(63,85,'google_sheets','2025-09-27 21:45:02','2025-09-27 00:24:00','completed',NULL);
INSERT INTO "send_history" VALUES(64,86,'google_sheets','2025-09-27 21:45:04','2025-09-27 08:38:00','completed',NULL);
INSERT INTO "send_history" VALUES(65,65,'google_sheets','2025-09-28 00:51:27','2025-09-27 20:54:00','completed',NULL);
INSERT INTO "send_history" VALUES(66,74,'google_sheets','2025-09-28 01:05:37','2025-09-27 19:25:00','completed',NULL);
INSERT INTO "send_history" VALUES(67,77,'google_sheets','2025-09-28 01:05:39','2025-09-27 20:36:00','completed',NULL);
INSERT INTO "send_history" VALUES(68,87,'x_api','2025-10-01 18:28:12','2025-10-01 09:33:00','completed',NULL);
INSERT INTO "send_history" VALUES(69,91,'x_api','2025-10-01 18:33:29','2025-10-01 20:56:00','completed',NULL);
INSERT INTO "send_history" VALUES(70,92,'x_api','2025-10-01 19:45:02','2025-10-01 19:45:00','completed',NULL);
INSERT INTO "send_history" VALUES(71,97,'x_api','2025-10-02 07:31:24','2025-10-01 07:40:00','failed','❌ X API投稿エラー: Invalid credentials. Please check API keys.');
INSERT INTO "send_history" VALUES(72,99,'google_sheets','2025-10-02 08:17:00','2025-10-01 06:36:00','completed',NULL);
INSERT INTO "send_history" VALUES(73,57,'x_api','2025-10-02 10:44:25','2025-09-27 19:20:00','failed','❌ X API投稿エラー: Invalid credentials. Please check API keys.');
INSERT INTO "send_history" VALUES(74,57,'x_api','2025-10-02 10:45:04','2025-09-27 19:20:00','failed','❌ X API投稿エラー: Invalid credentials. Please check API keys.');
INSERT INTO "send_history" VALUES(75,57,'x_api','2025-10-02 10:45:21','2025-09-27 19:20:00','failed','❌ X API投稿エラー: Invalid credentials. Please check API keys.');
INSERT INTO "send_history" VALUES(76,110,'x_api','2025-10-02 12:13:07','2025-10-02 09:29:00','completed',NULL);
INSERT INTO "send_history" VALUES(77,111,'x_api','2025-10-02 12:13:08','2025-10-02 10:09:00','completed',NULL);
INSERT INTO "send_history" VALUES(78,108,'x_api','2025-10-02 12:13:09','2025-10-02 14:01:00','completed',NULL);
INSERT INTO "send_history" VALUES(79,133,'x_api','2025-10-03 00:39:30','2025-10-02 00:45:00','completed',NULL);
INSERT INTO "send_history" VALUES(80,135,'x_api','2025-10-03 01:18:22','2025-10-02 01:25:00','completed',NULL);
INSERT INTO "send_history" VALUES(81,137,'x_api','2025-10-03 23:04:07','2025-10-03 22:10:00','completed',NULL);
INSERT INTO "send_history" VALUES(82,193,'google_sheets','2025-10-05 22:56:49','2025-10-05 02:49:00','failed','共通認証ファイルが見つかりません: credentials/credentials.json');
INSERT INTO "send_history" VALUES(83,193,'google_sheets','2025-10-05 22:58:51','2025-10-05 02:49:00','failed','共通認証ファイルが見つかりません: credentials/credentials.json');
CREATE TABLE situation_categories (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
INSERT INTO "situation_categories" VALUES(1,'日常');
INSERT INTO "situation_categories" VALUES(2,'学生');
INSERT INTO "situation_categories" VALUES(3,'社会人');
INSERT INTO "situation_categories" VALUES(4,'ナイトワーク');
INSERT INTO "situation_categories" VALUES(5,'恋愛');
INSERT INTO "situation_categories" VALUES(6,'ガジェット');
INSERT INTO "situation_categories" VALUES(7,'焼肉好き');
INSERT INTO "situation_categories" VALUES(8,'コスメオタク');
CREATE TABLE situations (id INTEGER PRIMARY KEY, content TEXT NOT NULL UNIQUE, time_slot TEXT DEFAULT 'いつでも', category_id INTEGER, FOREIGN KEY(category_id) REFERENCES situation_categories(id) ON DELETE CASCADE);
INSERT INTO "situations" VALUES(4,'初めてのお給料日','いつでも',3);
INSERT INTO "situations" VALUES(5,'アフター帰りのタクシーの中','夜',4);
INSERT INTO "situations" VALUES(6,'二日酔いの朝','朝',4);
INSERT INTO "situations" VALUES(7,'テキーラを飲みすぎた日の朝帰り','朝',4);
INSERT INTO "situations" VALUES(8,'昼から焼き肉','昼',4);
INSERT INTO "situations" VALUES(9,'シャンパンタワーをしてもらった','昼',1);
INSERT INTO "situations" VALUES(11,'同伴中の焼肉屋','夜',4);
INSERT INTO "situations" VALUES(12,'アフター帰りのタクシー','夜',4);
INSERT INTO "situations" VALUES(13,'バースデー','夜',4);
INSERT INTO "situations" VALUES(14,'昼同伴','昼',4);
INSERT INTO "situations" VALUES(15,'朝食','朝',4);
INSERT INTO "situations" VALUES(16,'お買い物中','いつでも',4);
INSERT INTO "situations" VALUES(17,'ヘアセット中','いつでも',4);
INSERT INTO "situations" VALUES(18,'まつエク中','いつでも',4);
INSERT INTO "situations" VALUES(19,'ピラティス中','いつでも',4);
INSERT INTO "situations" VALUES(20,'ヨガ中','いつでも',4);
INSERT INTO "situations" VALUES(21,'お客様の同じ自慢話を、初めて聞いたかのような新鮮なリアクションで何度も聞く。','いつでも',4);
INSERT INTO "situations" VALUES(22,'連絡先を聞かれ、「お店のルールで交換できないんです」というお決まりのセリフで断る。','いつでも',4);
INSERT INTO "situations" VALUES(23,'自分の誕生日が近いことをさりげなく（時には大胆に）アピールする。','いつでも',4);
INSERT INTO "situations" VALUES(24,'「アフター（同伴）行ける？」と聞かれ、上手にかわす。','いつでも',4);
INSERT INTO "situations" VALUES(25,'ヘルプで入った卓のお客様に気に入られ、指名キャストが嫉妬の視線を送ってくる。','いつでも',4);
INSERT INTO "situations" VALUES(26,'冗談で「愛してるよ」と言われ、本気にしていいか一瞬悩む。','いつでも',4);
INSERT INTO "situations" VALUES(27,'キャストのプライベート（本名、住所、普段の生活など）をしつこく詮索してくる。','いつでも',4);
INSERT INTO "situations" VALUES(28,'別のお店のキャストが、偵察や引き抜き目的で来店する。','いつでも',4);
INSERT INTO "situations" VALUES(29,'同伴の約束をドタキャンされ、その日の売上予定が狂う。','いつでも',4);
INSERT INTO "situations" VALUES(30,'売上ナンバーワンを巡って、キャスト同士がバチバチに火花を散らす。','いつでも',4);
INSERT INTO "situations" VALUES(31,'バックヤード（更衣室）が、お客様の愚痴やスタッフへの不満をぶちまける無法地帯と化す。','いつでも',4);
INSERT INTO "situations" VALUES(32,'先輩キャストから、おしぼりの渡し方や灰皿交換のタイミングについて厳しい指導が入る。','いつでも',4);
INSERT INTO "situations" VALUES(33,'キャスト同士で恋愛関係に発展するが、周りには秘密にしている。','いつでも',4);
INSERT INTO "situations" VALUES(34,'無断欠勤したキャストの連絡がつかず、みんなで心配する（または呆れる）。','いつでも',4);
INSERT INTO "situations" VALUES(35,'派閥ができて、バックヤードの空気が険悪になる。','いつでも',4);
INSERT INTO "situations" VALUES(36,'新人キャストの教育係を任され、自分の接客時間が削られる。','いつでも',4);
INSERT INTO "situations" VALUES(37,'ヘルプについた後輩が、自分の指名客と自分以上に盛り上がっていて複雑な気持ちになる。','いつでも',4);
INSERT INTO "situations" VALUES(38,'お客様の情報をキャスト同士で共有し、お店全体で接客戦略を練る。','いつでも',4);
INSERT INTO "situations" VALUES(39,'売上が厳しい日に、店長やマネージャーからプレッシャーをかけられる。','いつでも',4);
INSERT INTO "situations" VALUES(40,'お店の看板キャストが突然辞めてしまい、お店の雰囲気が変わる。','いつでも',4);
INSERT INTO "situations" VALUES(41,'ライバル店のオープンや閉店の噂で持ちきりになる。','いつでも',4);
INSERT INTO "situations" VALUES(42,'本気でお客様のことが好きになってしまう。','いつでも',4);
INSERT INTO "situations" VALUES(43,'売上が伸び悩み、指名が取れずに思い悩む。','いつでも',4);
INSERT INTO "situations" VALUES(44,'お客様からの高価なプレゼントを、素直に喜んでいいのか葛索する。','いつでも',4);
INSERT INTO "situations" VALUES(45,'SNSの裏アカウントで、お客様やお店への本音を吐き出す。','いつでも',4);
INSERT INTO "situations" VALUES(46,'お客様からの営業LINEに、プライベートの時間も返信すべきか悩む。','いつでも',4);
INSERT INTO "situations" VALUES(47,'ペットだけが素の自分を受け入れてくれる、かけがえのない癒やしの存在。','いつでも',4);
INSERT INTO "situations" VALUES(48,'家族には「飲食店で働いている」とだけ伝え、詳しい仕事内容は濁している。','いつでも',4);
INSERT INTO "situations" VALUES(49,'親から「その仕事、いつまで続けるの？」と将来を心配される。','いつでも',4);
INSERT INTO "situations" VALUES(50,'昼職の友人から夜に誘われても、仕事で会えないためだんだん疎遠になる。','いつでも',4);
INSERT INTO "situations" VALUES(51,'恋人に仕事への理解が得られず、「客と連絡取るな」「同伴行くな」と束縛されて喧嘩になる。','いつでも',4);
INSERT INTO "situations" VALUES(52,'「夜職」とカミングアウトした途端、相手の態度が変わり傷つく。','いつでも',4);
INSERT INTO "situations" VALUES(53,'結局、悩みを本音で話せるのは同業者（ナイトワーカー）の友人だけになる。','いつでも',4);
INSERT INTO "situations" VALUES(54,'昼職の彼氏との生活リズムが合わず、すれ違いが続く。','いつでも',4);
INSERT INTO "situations" VALUES(55,'お客様と知らずにマッチングアプリで出会ってしまう。','いつでも',4);
INSERT INTO "situations" VALUES(56,'結婚を考える相手に、自分の仕事をいつ、どのように伝えるべきか真剣に悩む。','いつでも',4);
INSERT INTO "situations" VALUES(57,'地元に帰省した際、友人たちとの会話で自分の仕事の話だけできない。','いつでも',4);
INSERT INTO "situations" VALUES(58,'元カレが自分のお客さんになってしまう。','いつでも',4);
INSERT INTO "situations" VALUES(59,'指名客からプライベートでしつこく誘われ、どう断るか頭を抱える。','いつでも',4);
INSERT INTO "situations" VALUES(60,'ナイトワークを辞めた元同僚の、昼職で輝いているSNSを見て焦りを感じる。','いつでも',4);
INSERT INTO "situations" VALUES(61,'恋愛対象として見る男性が、自分にどれだけお金を使ってくれるかで判断しがちになる。','いつでも',4);
INSERT INTO "situations" VALUES(62,'ストレス発散のため、ハイブランドのバッグやコスメを衝動買いしてしまう。','いつでも',4);
INSERT INTO "situations" VALUES(63,'美容院、ネイル、エステ、美容クリニック通いは、仕事のための「必要経費」と考える。','いつでも',4);
INSERT INTO "situations" VALUES(64,'確定申告の時期になると、領収書の山を見て頭が真っ白になる。','いつでも',4);
INSERT INTO "situations" VALUES(65,'金銭感覚が麻痺し、普通のランチや洋服の値段を「安い」と感じてしまう。','いつでも',4);
INSERT INTO "situations" VALUES(66,'将来への不安から、貯金やiDeCo、NISAについて勉強を始める。','いつでも',4);
INSERT INTO "situations" VALUES(67,'お酒の飲み過ぎを自覚し、休肝日を作ったり、サプリを飲んだりして体を気遣う。','いつでも',4);
INSERT INTO "situations" VALUES(68,'流行りのファッションやメイクを研究するため、雑誌やSNSを常にチェックする。','いつでも',4);
INSERT INTO "situations" VALUES(69,'仕事用の明るいキャラクターと、素の物静かな自分とのギャップに疲れてしまう。','いつでも',4);
INSERT INTO "situations" VALUES(70,'お客様から褒められる容姿や若さが、いつか失われることに恐怖を感じる。','いつでも',4);
INSERT INTO "situations" VALUES(71,'「このままでいいのか」と、将来への漠然とした不安で眠れなくなる夜がある。','いつでも',4);
INSERT INTO "situations" VALUES(72,'昼職への転職を考え、資格取得の勉強やパソコン教室に通い始める。','いつでも',4);
INSERT INTO "situations" VALUES(73,'ON/OFFの切り替えがうまくできず、休日も仕事のことが頭から離れない。','いつでも',4);
INSERT INTO "situations" VALUES(74,'ライバルのキャストのSNSを見て、嫉妬や焦りを感じて落ち込む。','いつでも',4);
INSERT INTO "situations" VALUES(75,'人を信用できなくなり、男性の優しさを「下心があるのでは？」と疑ってしまう。','いつでも',4);
INSERT INTO "situations" VALUES(76,'メンタルクリニックやカウンセリングに通い、心のバランスを保っている。','いつでも',4);
INSERT INTO "situations" VALUES(77,'完全に仕事のことを忘れるため、一人で温泉旅行や海外旅行に出かける。','いつでも',4);
INSERT INTO "situations" VALUES(78,'「普通の幸せ」って何だろう、と自分の生き方について深く考える時間がある。','いつでも',4);
INSERT INTO "situations" VALUES(79,'朝方、出勤するサラリーマンとすれ違いながら帰宅する。','朝',4);
INSERT INTO "situations" VALUES(80,'普通の時間に活動している友人からの電話やLINEで、睡眠を妨げられる。','朝',4);
INSERT INTO "situations" VALUES(81,'遮光カーテンを開け、太陽の光の眩しさに驚く。','昼',4);
INSERT INTO "situations" VALUES(82,'平日の昼間、ガラガラの役所や銀行、人気のカフェで優越感に浸る。','昼',4);
INSERT INTO "situations" VALUES(83,'休日は二日酔いと疲労で、一日中ベッドから出られないことも多い。','昼',4);
INSERT INTO "situations" VALUES(84,'体型維持のため、出勤前にジムでパーソナルトレーニングを受ける。','昼',4);
INSERT INTO "situations" VALUES(85,'酔ったお客様からの説教や人生相談が延々と続く。','夜',4);
INSERT INTO "situations" VALUES(86,'新人キャストが緊張でお客様のグラスを空にしてしまう。','夜',4);
INSERT INTO "situations" VALUES(87,'お客様のタバコに火をつけようとするが、ライターがなかなかつかない。','夜',4);
INSERT INTO "situations" VALUES(88,'カラオケで全く知らない曲をリクエストされ、必死にスマホで歌詞を検索しながらデュエットする。','夜',4);
INSERT INTO "situations" VALUES(89,'お客様の歌の合いの手やハモりが完璧になり、お店の誰よりも上手くなる。','夜',4);
INSERT INTO "situations" VALUES(90,'お客様のスマホの充電を頼まれ、自分の充電器を貸してあげる。','夜',4);
INSERT INTO "situations" VALUES(91,'お客様の連れの方が先に酔い潰れてしまい、介抱役になる。','夜',4);
INSERT INTO "situations" VALUES(92,'タイプが全く違うお客様が同時に来店し、テーブルを行き来して頭を切り替える。','夜',4);
INSERT INTO "situations" VALUES(93,'お客様が忘れていったスマホや財布を預かる。','夜',4);
INSERT INTO "situations" VALUES(94,'泥酔したお客様がソファで寝てしまい、全く起きない。','夜',4);
INSERT INTO "situations" VALUES(95,'会計時になって「お金が足りない」「カードが使えない」と言い出すお客様。','夜',4);
INSERT INTO "situations" VALUES(96,'お客様同士が、キャストの取り合いや些細なことで喧嘩を始める。','夜',4);
INSERT INTO "situations" VALUES(97,'お店の備品（グラス、灰皿、カラオケのデンモクなど）をお客様が壊してしまう。','夜',4);
INSERT INTO "situations" VALUES(98,'お店の外で待ち伏せされたり、ストーカーまがいの行為をされたりする。','夜',4);
INSERT INTO "situations" VALUES(99,'警察の風営法に関する立ち入り検査（査察）が入る。','夜',4);
INSERT INTO "situations" VALUES(100,'予約なしの団体客が突然来店し、店内がてんてこ舞いになる。','夜',4);
INSERT INTO "situations" VALUES(101,'営業後、キャストやスタッフみんなで朝まで飲み明かす。','夜',4);
INSERT INTO "situations" VALUES(102,'シャンパンタワーや豪華なフルーツ盛り合わせの注文が入り、店内が一体となって盛り上がる。','夜',4);
INSERT INTO "situations" VALUES(103,'キャストの誕生日イベントで、店内がお花やバルーンで飾り付けられる。','夜',4);
INSERT INTO "situations" VALUES(104,'ハロウィンやクリスマスなどの季節イベントで、キャスト全員がコスプレをする。','夜',4);
INSERT INTO "situations" VALUES(105,'お店の周年記念パーティーで、OBやOGのキャストが遊びに来る。','夜',4);
INSERT INTO "situations" VALUES(106,'満席でお客様の入店を断らなければならないほどの盛況。','夜',4);
INSERT INTO "situations" VALUES(107,'お店のレクリエーションで、キャスト・スタッフ全員でバーベキューや旅行に行く。','夜',4);
INSERT INTO "situations" VALUES(108,'突然の停電や水漏れなど、予期せぬインフラトラブルに見舞われる。','夜',4);
INSERT INTO "situations" VALUES(109,'家族や地元の友人に、本当の仕事内容を言えずに嘘をついている罪悪感。','夜',4);
INSERT INTO "situations" VALUES(110,'夕方頃に目覚め、普通の人の「おはよう」が自分の「こんばんは」。','夜',4);
INSERT INTO "situations" VALUES(111,'深夜の営業終わりに同僚とラーメンや寿司を食べるのが至福の時。','夜',4);
INSERT INTO "situations" VALUES(112,'近所のコンビニ店員に「いつもこの時間ですね」と出勤時間を把握されている。','夜',4);
INSERT INTO "situations" VALUES(113,'自宅の最寄り駅までタクシーで帰ることが多く、運転手と顔なじみになる。','夜',4);
INSERT INTO "situations" VALUES(114,'出勤前にエナジードリンクや栄養ドリンクを飲んで気合を入れる。','夜',4);
INSERT INTO "situations" VALUES(115,'営業用の華やかなドレスと、プライベートのラフなスウェットのギャップが激しい。','夜',4);
INSERT INTO "situations" VALUES(116,'部屋に脱ぎ捨てられたドレスの山を見て、クリーニングに出さなきゃとため息をつく。','夜',4);
INSERT INTO "situations" VALUES(117,'自分の誕生日、お店で盛大にお祝いしてもらった後、一人きりの部屋に帰ってきて虚しくなる。','夜',4);
INSERT INTO "situations" VALUES(118,'深夜の暴飲暴食が原因で、肌荒れや体重増加に悩まされる。','夜',4);
INSERT INTO "situations" VALUES(119,'スマートフォンのバッテリー残量が20%を切ると、落ち着かなくなる。','いつでも',6);
INSERT INTO "situations" VALUES(120,'外出時のカバンに、モバイルバッテリーと数種類の充電ケーブルが入っているのは当たり前。','いつでも',6);
INSERT INTO "situations" VALUES(121,'カフェやレストランに入ったら、まず電源コンセントのある席を探す。','いつでも',6);
INSERT INTO "situations" VALUES(122,'旅行の荷造りで、衣類よりガジェットとその充電器類の選定に時間がかかる。','いつでも',6);
INSERT INTO "situations" VALUES(123,'友人のスマホの充電が切れそうだと、自分のモバイルバッテリーをドヤ顔で貸してあげる。','いつでも',6);
INSERT INTO "situations" VALUES(124,'家電量販店の新製品コーナーやガジェットショップに入ると、平気で数時間経っている。','いつでも',6);
INSERT INTO "situations" VALUES(125,'使わなくなったガジェットの空き箱が、デザインが良くて捨てられずクローゼットに溜まっていく。','いつでも',6);
INSERT INTO "situations" VALUES(126,'クラウドファンディングサイトで、まだ世に出ていない尖ったガジェットに出資するのが好き。','いつでも',6);
INSERT INTO "situations" VALUES(127,'スマートフォンのホーム画面のアイコン配置やウィジェットに、自分なりの哲学とこだわりがある。','いつでも',6);
INSERT INTO "situations" VALUES(128,'友人や家族、親戚から「パソコンの調子がおかしい」「Wi-Fiが繋がらない」と無償サポートを頼まれがち。','いつでも',6);
INSERT INTO "situations" VALUES(129,'ガジェットの話になると途端に早口になり、専門用語を多用してしまう。','いつでも',6);
INSERT INTO "situations" VALUES(130,'フリーWi-Fiの電波が弱い、もしくはセキュリティが不安な場所では、自前のポケットWi-Fiを取り出す。','いつでも',6);
INSERT INTO "situations" VALUES(131,'「その機能、本当に必要？」と周りに言われるような、ニッチなガジェットを愛用している。','いつでも',6);
INSERT INTO "situations" VALUES(132,'ワイヤレスイヤホンの充電が片方だけ切れて、なんとも言えない気持ちになる。','いつでも',6);
INSERT INTO "situations" VALUES(133,'持っているガジェットのCPU、メモリ、ストレージなどのスペックを暗唱できる。','いつでも',6);
INSERT INTO "situations" VALUES(134,'ミニマリストに憧れるが、ガジェットが多すぎて物理的に不可能だと悟っている。','いつでも',6);
INSERT INTO "situations" VALUES(135,'キャンプに大容量ポータブル電源とプロジェクター、電動コーヒーミルを持っていき、快適さを追求する。','いつでも',6);
INSERT INTO "situations" VALUES(136,'フリマアプリで古いガジェットを売り、それを元手に新しいガジェットを買う「ガジェットわらしべ長者」。','いつでも',6);
INSERT INTO "situations" VALUES(137,'USBの種類が多すぎて（Type-A, Micro-B, Type-C, Lightning）、目的のケーブルがすぐに見つからない。','いつでも',6);
INSERT INTO "situations" VALUES(138,'鍵、財布、カバンなど、あらゆる所有物にスマートタグを取り付けている。','いつでも',6);
INSERT INTO "situations" VALUES(139,'ガジェットの液晶保護フィルムを、気泡一つなく完璧に貼れた時に最高の達成感を味わう。','いつでも',6);
INSERT INTO "situations" VALUES(140,'逆にフィルム貼りに失敗し、小さなホコリが入って絶望的な気分になる。','いつでも',6);
INSERT INTO "situations" VALUES(141,'スマホを買い替えた時の、データ移行とアプリの再ログイン作業が一大イベント。','いつでも',6);
INSERT INTO "situations" VALUES(142,'3Dプリンターで、自分の持っているガジェットにぴったりのスタンドやケースを自作する。','いつでも',6);
INSERT INTO "situations" VALUES(143,'ドローンを合法的に飛ばせる場所を探して、休日を費やす。','いつでも',6);
INSERT INTO "situations" VALUES(144,'友人の家に行くと、まずWi-Fiのパスワードを聞き、通信速度を測定する。','いつでも',6);
INSERT INTO "situations" VALUES(145,'「OK Google」「アレクサ」とスマートスピーカーに話しかけるのが日常。','いつでも',6);
INSERT INTO "situations" VALUES(146,'同じ用途のガジェットを、スペックやメーカー違いで複数所有している（イヤホン、マウスなど）。','いつでも',6);
INSERT INTO "situations" VALUES(147,'ガジェットのレビュー動画をYouTubeで見始めると、時間を忘れて見続けてしまう。','いつでも',6);
INSERT INTO "situations" VALUES(148,'新しいガジェットを買った満足感より、次の新製品への物欲がすぐに勝ってしまう。','いつでも',6);
INSERT INTO "situations" VALUES(149,'スマートウォッチの活動リングをコンプリートするために、意味なく部屋の中を歩き回る。','いつでも',6);
INSERT INTO "situations" VALUES(150,'電動歯ブラシやドライヤーなどの生活家電も、最新の高機能モデルでないと満足できない。','いつでも',6);
INSERT INTO "situations" VALUES(151,'最新OSのベータ版をいち早くインストールし、バグを見つけて開発者に報告することに喜びを感じる。','いつでも',6);
INSERT INTO "situations" VALUES(152,'古いガジェットを分解して、内部構造を見て楽しむ。','いつでも',6);
INSERT INTO "situations" VALUES(153,'自宅のWi-Fiルーターの性能にこだわり、最適な設置場所をミリ単位で調整する。','いつでも',6);
INSERT INTO "situations" VALUES(154,'スマートウォッチの睡眠スコアや体のデータを見て、自分の健康状態を分析し一喜一憂する。','朝',6);
INSERT INTO "situations" VALUES(155,'スマートスピーカーに天気とニュース、今日のスケジュールを読み上げてもらいながら朝の支度をする。','朝',6);
INSERT INTO "situations" VALUES(156,'全自動コーヒーメーカーやスマートトースターを駆使し、効率的でスマートな朝食をとる。','朝',6);
INSERT INTO "situations" VALUES(157,'通勤電車の中では、ガジェット系のニュースサイトやテック系ブログのチェックを欠かさない。','朝',6);
INSERT INTO "situations" VALUES(158,'スマートロックで、スマホアプリや指紋認証で玄関を施錠して出かける。','朝',6);
INSERT INTO "situations" VALUES(159,'ランチを食べる時も、スマホスタンドに立てかけたスマホで動画コンテンツを視聴する。','昼',6);
INSERT INTO "situations" VALUES(160,'最新スマートフォンのカメラ性能を試すため、ランチの料理を様々なモードで撮影する。','昼',6);
INSERT INTO "situations" VALUES(161,'昼休みに、発売されたばかりのガジェットのレビュー記事を読みふける。','昼',6);
INSERT INTO "situations" VALUES(162,'Appleなどの新製品発表会が深夜にあるため、眠い目をこすりながらリアルタイムで視聴する。','夜',6);
INSERT INTO "situations" VALUES(163,'ベッドに入ってからも、スマホやタブレットでSNSや動画を見てしまい、寝るのが遅くなる。','夜',6);
INSERT INTO "situations" VALUES(164,'スマート照明を使い、就寝時間になると自動で部屋が暖色になり、徐々に暗くなるように設定。','夜',6);
INSERT INTO "situations" VALUES(165,'一日の終わりに、家中のガジェットをそれぞれの充電器にセットする「充電の儀式」を行う。','夜',6);
INSERT INTO "situations" VALUES(166,'VRゴーグルを装着し、仮想空間でゲームをしたり友人と会ったりして夜を過ごす。','夜',6);
INSERT INTO "situations" VALUES(167,'購入したばかりのガジェットの初期設定やカスタマイズに夢中になり、気づけば深夜になっている。','夜',6);
INSERT INTO "situations" VALUES(168,'就寝中、スマートフォンの通知音で睡眠を妨げられる。','夜',6);
INSERT INTO "situations" VALUES(169,'職場で使うPCのスペックやモニターの性能に強いこだわりがある（デュアルモニターは人権）。','いつでも',6);
INSERT INTO "situations" VALUES(170,'自腹で購入した高級キーボードや高機能マウスを職場に持ち込んで使っている。','いつでも',6);
INSERT INTO "situations" VALUES(171,'会議の議事録は、ICレコーダーやAIによる自動文字起こしアプリで効率的に作成する。','いつでも',6);
INSERT INTO "situations" VALUES(172,'同僚が非効率なPC操作をしていると、「その作業、このショートカットキーで一瞬ですよ」と教えたくなる。','いつでも',6);
INSERT INTO "situations" VALUES(173,'会社のIT備品が古かったりスペックが低かったりすることに、強いストレスを感じる。','いつでも',6);
INSERT INTO "situations" VALUES(174,'同僚のPCトラブル（ネットに繋がらない、フリーズした等）を解決してしまい、非公式な社内ヘルプデスクと化す。','いつでも',6);
INSERT INTO "situations" VALUES(175,'プレゼンテーションでは、最新のワイヤレスポインターやデバイスを使い、スマートさを演出する。','いつでも',6);
INSERT INTO "situations" VALUES(176,'会社のWi-Fiが遅いと感じると、持参したモバイルルーターに切り替える。','いつでも',6);
INSERT INTO "situations" VALUES(177,'業務効率化のためなら、便利な有料ソフトウェアやクラウドサービスへの課金を厭わない。','いつでも',6);
INSERT INTO "situations" VALUES(178,'デスク周りのごちゃごちゃしたケーブルを、ケーブルホルダーやスリーブで綺麗に配線することに快感を覚える。','いつでも',6);
INSERT INTO "situations" VALUES(179,'紙で渡された資料は、すべてスキャナーでPDF化してデータ管理しないと気が済まない。','いつでも',6);
INSERT INTO "situations" VALUES(180,'高性能なノイズキャンセリングヘッドホンで周囲の雑音を完全にシャットアウトし、作業に集中する。','いつでも',6);
INSERT INTO "situations" VALUES(181,'スマートフォン、タブレット、PC間のデータやクリップボードの同期が完璧で、デバイスをまたいでシームレスに作業する。','いつでも',6);
INSERT INTO "situations" VALUES(182,'オンライン会議では、Webカメラの画質やマイクの音質、バーチャル背景に人一倍こだわる。','いつでも',6);
INSERT INTO "situations" VALUES(183,'会社で新しい業務ツールが導入されると、誰よりも早く全機能を試し、便利な使い方を発見する。','いつでも',6);
INSERT INTO "situations" VALUES(184,'会社の厳しいセキュリティポリシーと戦いながら、いかに快適なガジェット環境を構築できるか常に模索している。','いつでも',6);
INSERT INTO "situations" VALUES(185,'会社の予算で備品を購入する際、ここぞとばかりに理由をつけて高性能なモデルを申請する。','いつでも',6);
INSERT INTO "situations" VALUES(186,'出張先のホテルの部屋に着いたら、まずWi-Fiの速度を測定することから始める。','いつでも',6);
INSERT INTO "situations" VALUES(187,'自分のデスク周りだけ、LEDテープライトや多機能デバイスで未来的な雰囲気を醸し出している。','いつでも',6);
INSERT INTO "situations" VALUES(188,'PCのスペック不足が原因で作業が遅延すると、「これはマシンのせいです」と道具のせいにする。','いつでも',6);
INSERT INTO "situations" VALUES(189,'指紋認証や顔認証でのログインが一度でうまくいかないと、地味にイライラする。','いつでも',6);
INSERT INTO "situations" VALUES(190,'PCのファンクションキーに付箋でメモを貼っている人を見ると、もっとスマートな方法があるのに…と思ってしまう。','いつでも',6);
INSERT INTO "situations" VALUES(191,'自分の作業内容に合わせてカスタマイズした、プログラマブルキーボードを駆使する。','いつでも',6);
INSERT INTO "situations" VALUES(192,'チャットツールで、テキストを打つより便利なショートカットやコマンドを多用する。','いつでも',6);
INSERT INTO "situations" VALUES(193,'資料作成時、誰も気づかないようなフォントのカーニングや行間にまでこだわってしまう。','いつでも',6);
INSERT INTO "situations" VALUES(194,'出社後、まず自分のPCや周辺機器の電源を入れ、OSの起動時間で今日のPCのコンディションを測る。','朝',6);
INSERT INTO "situations" VALUES(195,'USBポートで保温できるマグカップウォーマーを使い、いつでも温かいコーヒーを飲みながら作業を開始する。','朝',6);
INSERT INTO "situations" VALUES(196,'朝礼で、最新のテクノロジーニュースを例に出して発言する。','朝',6);
INSERT INTO "situations" VALUES(197,'始業前に、今日使うソフトウェアのアップデートがないかチェックする。','朝',6);
INSERT INTO "situations" VALUES(198,'休憩時間に、ガジェット好きの同僚と新製品の噂やレビューについて情報交換する。','昼',6);
INSERT INTO "situations" VALUES(199,'昼休みを利用して、会社の近くの家電量販店や中古PCショップをパトロールする。','昼',6);
INSERT INTO "situations" VALUES(200,'ランチの注文を、モバイルオーダーでスマートに済ませる。','昼',6);
INSERT INTO "situations" VALUES(201,'午後の集中力が切れてきたら、スマートウォッチの「深呼吸」機能でリフレッシュする。','昼',6);
INSERT INTO "situations" VALUES(202,'退勤時、PCのシャットダウンがやけに遅いと、PCの健康状態を心配し始める。','夜',6);
INSERT INTO "situations" VALUES(203,'会社に、その日使うはずだった特殊な変換アダプターを忘れてきたことに気づき、絶望する。','夜',6);
INSERT INTO "situations" VALUES(204,'残業中、デスクのLEDライトの色を変えたり、音楽を流したりして気分を上げる。','夜',6);
INSERT INTO "situations" VALUES(205,'帰宅後、仕事で使っているソフトウェアのアップデートや、PCのメンテナンスを夜な夜な行う。','夜',6);
INSERT INTO "situations" VALUES(206,'業務時間外に、会社のチャットツールに新しいスタンプや絵文字が追加されていないかチェックする。','夜',6);
INSERT INTO "situations" VALUES(207,'翌日のプレゼン資料に使う動画のエンコードが終わらず、帰宅時間が遅くなる。','夜',6);
INSERT INTO "situations" VALUES(208,'友人との食事の予定を立てる時、まず「焼肉どう？」と提案する。','いつでも',7);
INSERT INTO "situations" VALUES(209,'「好きな食べ物は？」という質問には、0.5秒で「焼肉です」と即答する。','いつでも',7);
INSERT INTO "situations" VALUES(210,'SNSのタイムラインやカメラロールが、茶色い肉の写真で埋め尽くされている。','いつでも',7);
INSERT INTO "situations" VALUES(211,'美味しい焼肉屋の情報収集に余念がなく、食べログやGoogleマップに「焼肉」リストが大量にある。','いつでも',7);
INSERT INTO "situations" VALUES(212,'冷蔵庫に、甘口・辛口・塩だれなど数種類の焼肉のタレを常備している。','いつでも',7);
INSERT INTO "situations" VALUES(213,'服や髪に焼肉の匂いがつくことを「フレグランス」と呼び、むしろ幸せを感じる。','いつでも',7);
INSERT INTO "situations" VALUES(214,'肉の希少部位（ミスジ、ザブトン、トモサンカクなど）の名前と特徴をスラスラ言える。','いつでも',7);
INSERT INTO "situations" VALUES(215,'焼肉に行くと自然と「肉奉行」になり、焼き方や食べる順番を仕切ってしまう。','いつでも',7);
INSERT INTO "situations" VALUES(216,'生肉を触るトングと、焼けた肉を取るトングの2種類を使い分けるのが常識だと思っている。','いつでも',7);
INSERT INTO "situations" VALUES(217,'焼肉のためなら、普段行かないような遠くの駅まで遠征することも厭わない。','いつでも',7);
INSERT INTO "situations" VALUES(218,'スーパーの精肉コーナーを定期的にパトロールし、良い肉が入荷していないかチェックする。','いつでも',7);
INSERT INTO "situations" VALUES(219,'誕生日や記念日など、人生の節目節目のお祝いは高級焼肉店でしたい。','いつでも',7);
INSERT INTO "situations" VALUES(220,'一人焼肉を嗜み、自分だけのペースで肉と向き合う時間を大切にしている。','いつでも',7);
INSERT INTO "situations" VALUES(221,'家のベランダや庭でやるバーベキューも、結局は焼肉スタイルに落ち着く。','いつでも',7);
INSERT INTO "situations" VALUES(222,'焼肉屋の換気扇の性能や、ロースターの種類をついチェックしてしまう。','いつでも',7);
INSERT INTO "situations" VALUES(223,'自宅で最高の焼肉をするため、無煙ロースターや高性能ホットプレートを所有している。','いつでも',7);
INSERT INTO "situations" VALUES(224,'焼肉の夢を見て、幸せな気分で目覚めることがある。','いつでも',7);
INSERT INTO "situations" VALUES(225,'「もう歳だからカルビはきつい」という友人の言葉に、心の中で「自分はまだいける」と思う。','いつでも',7);
INSERT INTO "situations" VALUES(226,'YouTubeで、ひたすら肉が焼かれている動画や、大食い焼肉動画を長時間見てしまう。','いつでも',7);
INSERT INTO "situations" VALUES(227,'次の焼肉の予定が決まっていることが、日々の仕事や勉強を頑張るモチベーションになっている。','いつでも',7);
INSERT INTO "situations" VALUES(228,'旅行先でも必ずその土地のブランド牛が食べられる焼肉屋を探す。','いつでも',7);
INSERT INTO "situations" VALUES(229,'焼肉屋の店員と顔なじみになり、裏メニューやおすすめのカットを教えてもらう。','いつでも',7);
INSERT INTO "situations" VALUES(230,'焼肉の食べ放題に行くと、元を取るための最適な注文戦略を頭の中で組み立てる。','いつでも',7);
INSERT INTO "situations" VALUES(231,'「タレ」派か「塩」派か、〆は「冷麺」派か「クッパ」派かで熱い議論を交わす。','いつでも',7);
INSERT INTO "situations" VALUES(232,'ふるさと納税の返礼品は、迷わずブランド和牛の焼肉セットを選ぶ。','いつでも',7);
INSERT INTO "situations" VALUES(233,'白い服を着て焼肉に来てしまった自分を呪い、そして必ずタレを飛ばす。','いつでも',7);
INSERT INTO "situations" VALUES(234,'食後に衣類にかける消臭スプレーの効果を過信している。','いつでも',7);
INSERT INTO "situations" VALUES(235,'グルメサイトの「焼肉百名店」を制覇することを目標にしている。','いつでも',7);
INSERT INTO "situations" VALUES(236,'肉の焼き加減で、その人の性格や育ちがわかると思っている。','いつでも',7);
INSERT INTO "situations" VALUES(237,'髪が長い人は、席に着くと同時に戦闘態勢に入るように髪を束ねる。','いつでも',7);
INSERT INTO "situations" VALUES(238,'ユッケや肉寿司など、生食系のメニューがあると必ず注文してしまう。','いつでも',7);
INSERT INTO "situations" VALUES(239,'焼肉に合う最高に美味しい白米の炊き方を研究している。','いつでも',7);
INSERT INTO "situations" VALUES(240,'サンチュやエゴマの葉で肉を巻くことで、罪悪感を少しだけ和らげる。','いつでも',7);
INSERT INTO "situations" VALUES(241,'初めて行く焼肉屋では、まずその店の「タレ」の味を確かめる。','いつでも',7);
INSERT INTO "situations" VALUES(242,'焼肉屋のメニューにある「ライス（大）」が、本当に自分を満足させるサイズなのかを吟味する。','いつでも',7);
INSERT INTO "situations" VALUES(243,'仕事でストレスが溜まると、無意識に「あー、焼肉食べたい…」と呟いている。','いつでも',7);
INSERT INTO "situations" VALUES(244,'会社のプロジェクトの打ち上げや新人歓迎会の幹事になると、すかさず焼肉屋を提案する。','いつでも',7);
INSERT INTO "situations" VALUES(245,'クライアントとの会食や接待の店選びで、ここぞとばかりに個室のある高級焼肉店を候補に入れる。','いつでも',7);
INSERT INTO "situations" VALUES(246,'デスクの引き出しに、焼肉のタレ風味のスナック菓子を常備している。','いつでも',7);
INSERT INTO "situations" VALUES(247,'焼肉好きの同僚とは、社内チャットで美味しい焼肉屋の情報交換をするための専用チャンネルがある。','いつでも',7);
INSERT INTO "situations" VALUES(248,'予約困難店の予約を取るのが得意なため、部署の飲み会では自然と幹事を任される。','いつでも',7);
INSERT INTO "situations" VALUES(249,'仕事で大きな成果を上げた日は、自分へのご褒美として「一人焼肉」に行くことを心に誓う。','いつでも',7);
INSERT INTO "situations" VALUES(250,'取引先の担当者が同じく焼肉好きだと判明した途端、一気に心の距離が縮まる。','いつでも',7);
INSERT INTO "situations" VALUES(251,'プレゼン資料の比喩表現で、「この戦略は肉で言うところの希少部位でして…」などと、つい焼肉に例えてしまう。','いつでも',7);
INSERT INTO "situations" VALUES(252,'「焼肉コミュニケーション」と称し、焼肉を囲めば部署内の風通しが良くなると信じている。','いつでも',7);
INSERT INTO "situations" VALUES(253,'会社の経費で利用できる焼肉ランチの上限金額を正確に把握している。','いつでも',7);
INSERT INTO "situations" VALUES(254,'重要な契約が成立したら、チーム全員での「祝勝会焼肉」を企画するのが恒例行事。','いつでも',7);
INSERT INTO "situations" VALUES(255,'退職する同僚の送別会も、思い出話に花を咲かせる場として焼肉屋を選ぶ。','いつでも',7);
INSERT INTO "situations" VALUES(256,'新しいプロジェクトメンバーとのキックオフミーティングを、あえて焼肉屋で行い、結束を高めようとする。','いつでも',7);
INSERT INTO "situations" VALUES(257,'エレベーターで一緒になった他部署の人から焼肉の匂いがすると、一方的に仲間意識を感じる。','いつでも',7);
INSERT INTO "situations" VALUES(258,'昨晩食べた焼肉の写真をSNSに投稿し、飯テロを仕掛けながら余韻に浸る。','朝',7);
INSERT INTO "situations" VALUES(259,'朝から「今夜は焼肉だ」と決まっている日は、一日中ご機嫌で過ごせる。','朝',7);
INSERT INTO "situations" VALUES(260,'前の晩にあれだけ焼肉を食べたのに、胃もたれもなくスッキリと目覚める。','朝',7);
INSERT INTO "situations" VALUES(261,'休日の朝、テレビで焼肉の特集をやっていると、その日の献立が焼肉に決定する。','朝',7);
INSERT INTO "situations" VALUES(262,'朝の情報番組の占いを見て、「ラッキーフード：焼肉」だとテンションが上がる。','朝',7);
INSERT INTO "situations" VALUES(263,'昨晩の焼肉の匂いがスーツや髪に微かに残っていないか、出社前に念入りにチェックする（でも後悔はしていない）。','朝',7);
INSERT INTO "situations" VALUES(264,'朝の定例会議中、上の空で「今夜の焼keynote…いや焼肉の段取り」について考えてしまう。','朝',7);
INSERT INTO "situations" VALUES(265,'通勤電車で昨夜の焼肉の写真を眺め、パワーをチャージして仕事に向かう。','朝',7);
INSERT INTO "situations" VALUES(266,'朝から重要なプレゼンを控えている日は、「これが終われば焼肉が待っている」と自分に言い聞かせる。','朝',7);
INSERT INTO "situations" VALUES(267,'始業前、給湯室で同僚と「昨日の焼肉、最高でしたよ」と報告し合う。','朝',7);
INSERT INTO "situations" VALUES(268,'ランチメニューに「焼肉定食」や「ハラミ丼」があると、吸い寄せられるように注文してしまう。','昼',7);
INSERT INTO "situations" VALUES(269,'午後の仕事の会議のことを考え、ランチ焼肉で匂いがつくことを懸念し、行くか行くまいか葛藤する。','昼',7);
INSERT INTO "situations" VALUES(270,'昼休みに、同僚と「今日の夜、仕事頑張って焼肉行かない？」と計画を立てる。','昼',7);
INSERT INTO "situations" VALUES(271,'ランチ焼肉の後、口臭ケアを入念に行い、何食わぬ顔で午後の業務に戻る。','昼',7);
INSERT INTO "situations" VALUES(272,'昼間からネットで焼肉屋の予約状況をチェックし、良い時間帯が埋まらないかソワソワする。','昼',7);
INSERT INTO "situations" VALUES(273,'昼休み、匂いを気にしなくていいリモートワークの日は、迷わず近所の焼肉屋でランチする。','昼',7);
INSERT INTO "situations" VALUES(274,'午後の眠たい会議を乗り切るため、「これが終われば焼肉だ」と心の中で唱える。','昼',7);
INSERT INTO "situations" VALUES(275,'同僚とのランチ中、「そういえば、会社の近くに新しい焼肉屋できたらしいよ」と情報戦を繰り広げる。','昼',7);
INSERT INTO "situations" VALUES(276,'外出のついでに、次の会食で使えそうな焼肉屋のランチを下見しに行く。','昼',7);
INSERT INTO "situations" VALUES(277,'会社の福利厚生で、焼肉店の割引クーポンがないか定期的にチェックする。','昼',7);
INSERT INTO "situations" VALUES(278,'金曜の夜、一週間の仕事を終えた解放感と共に焼肉屋の暖簾をくぐるのが最高の習慣。','夜',7);
INSERT INTO "situations" VALUES(279,'肉が網の上で焼ける「ジュ〜ッ」という音を、最高のBGMだと感じている。','夜',7);
INSERT INTO "situations" VALUES(280,'最初の一杯のビールと、最初に焼くタン塩の組み合わせは、何にも代えがたい幸福。','夜',7);
INSERT INTO "situations" VALUES(281,'メニューの端から端まで全種類制覇したいという衝動に駆られる。','夜',7);
INSERT INTO "situations" VALUES(282,'ホルモン系のベストな焼き加減がわからず、焦がしたり生焼けだったりを繰り返しながら学ぶ。','夜',7);
INSERT INTO "situations" VALUES(283,'残業中、「このタスクを片付けたら、焼肉屋に駆け込む」と固く決意し、作業スピードを上げる。','夜',7);
INSERT INTO "situations" VALUES(284,'会社の公式な飲み会が焼肉だと決まった瞬間、その日一番の笑顔になる。','夜',7);
INSERT INTO "situations" VALUES(285,'上司や部下との焼肉では、率先してトングを握り、焼き加減を調整し、全員に肉を配ることで自分の価値を示す。','夜',7);
INSERT INTO "situations" VALUES(286,'焼肉の網を囲むと、普段は言えないような本音や感謝の言葉が素直に口から出てくると思っている。','夜',7);
INSERT INTO "situations" VALUES(287,'二次会の誘いを「焼肉の余韻に浸りたいので」というパワーワードで断り、満足感と共に帰路につく。','夜',7);
INSERT INTO "situations" VALUES(288,'新作コスメの発売日と予約開始日を、カレンダーアプリに仕事の予定と同じ熱量で登録している。','いつでも',8);
INSERT INTO "situations" VALUES(289,'「限定」という言葉に弱く、たとえ似たような色を持っていても買わずにいられない。','いつでも',8);
INSERT INTO "situations" VALUES(290,'デパコスのカウンターでBA（美容部員）さんと話が盛り上がり、気づけば1時間以上経っている。','いつでも',8);
INSERT INTO "situations" VALUES(291,'ポーチが複数あり、「持ち運び用」「会社置き用」「デート用」など用途別に使い分けている。','いつでも',8);
INSERT INTO "situations" VALUES(292,'SNSで好きな美容系インフルエンサーが紹介した商品は、すぐにウィッシュリストに入れる。','いつでも',8);
INSERT INTO "situations" VALUES(293,'アイシャドウパレットを眺めているだけで、白米が食べられるくらい幸せな気持ちになる。','いつでも',8);
INSERT INTO "situations" VALUES(294,'ドラッグストアのコスメコーナーの品出しや棚替えに遭遇すると、ワクワクして長居してしまう。','いつでも',8);
INSERT INTO "situations" VALUES(295,'友人への誕生日プレゼントは、その人のパーソナルカラーや肌質を考慮したコスメを選びがち。','いつでも',8);
INSERT INTO "situations" VALUES(296,'今日のメイクのテーマを決め、それに合わせて服やアクセサリーを選ぶ。','いつでも',8);
INSERT INTO "situations" VALUES(297,'使わなくなったコスメが大量にあるが、「いつか使うかも」「観賞用だから」と言い訳して捨てられない。','いつでも',8);
INSERT INTO "situations" VALUES(298,'旅行のパッキングで一番場所を取るのは、衣類ではなくスキンケアとメイク用品。','いつでも',8);
INSERT INTO "situations" VALUES(299,'自分の肌の色に合うファンデーションの色番を、国内外の主要ブランドですべて暗記している。','いつでも',8);
INSERT INTO "situations" VALUES(300,'コスメの成分表示をチェックするのが好きで、ナイアシンアミドやレチノールなどの成分に詳しい。','いつでも',8);
INSERT INTO "situations" VALUES(301,'友人から「何かおすすめのコスメない？」と聞かれると、待ってましたとばかりに熱弁をふるう。','いつでも',8);
INSERT INTO "situations" VALUES(302,'「それ、どこのリップ？」と聞かれることに、最高の喜びを感じる。','いつでも',8);
INSERT INTO "situations" VALUES(303,'コスメ収納にこだわりがあり、アクリルケースや専用の棚を使ってブランドや種類ごとに美しく陳列している。','いつでも',8);
INSERT INTO "situations" VALUES(304,'スウォッチ（腕などでの色味確認）を撮るのが好きで、スマホのカメラロールが自分の腕の写真だらけ。','いつでも',8);
INSERT INTO "situations" VALUES(305,'パーソナルカラー診断や顔タイプ診断の結果を、コスメ選びの絶対的な指針にしている。','いつでも',8);
INSERT INTO "situations" VALUES(306,'海外旅行の楽しみの半分は、免税店や現地のコスメショップ（Sephoraなど）での買い物。','いつでも',8);
INSERT INTO "situations" VALUES(307,'アイシャドウパレットの特定の「締め色」だけが先に無くなり、「あるある」と共感する。','いつでも',8);
INSERT INTO "situations" VALUES(308,'複数のコスメサブスクリプションサービスを契約し、毎月届くボックスに一喜一憂する。','いつでも',8);
INSERT INTO "situations" VALUES(309,'コスメの空き容器を綺麗に洗い、DIYで小物入れなどにリメイクする。','いつでも',8);
INSERT INTO "situations" VALUES(310,'ネイルポリッシュを大量に集めてしまい、もはや自分の指の数では塗りきれないとわかっている。','いつでも',8);
INSERT INTO "situations" VALUES(311,'コスメブランドの歴史や、創業者のストーリーまで語ることができる。','いつでも',8);
INSERT INTO "situations" VALUES(312,'フリマアプリで、廃盤になったり限定だったりした「幻のコスメ」を探し出すのが得意。','いつでも',8);
INSERT INTO "situations" VALUES(313,'美容雑誌は、付録の豪華さで買うかどうかを決める。','いつでも',8);
INSERT INTO "situations" VALUES(314,'コスメカウンターでタッチアップしてもらった後、肌の変化を見るためにすぐには買わず一旦店を離れる。','いつでも',8);
INSERT INTO "situations" VALUES(315,'化粧ポーチを家に忘れてきた日は、一日中仕事や勉強が手につかないほどの絶望感を味わう。','いつでも',8);
INSERT INTO "situations" VALUES(316,'どんなに疲れていても、メイクだけは絶対に落としてから寝るという強い意志を持っている。','いつでも',8);
INSERT INTO "situations" VALUES(317,'ポイントアップデーやセール期間を狙って、オンラインストアでまとめ買いをする計画を常に立てている。','いつでも',8);
INSERT INTO "situations" VALUES(318,'新しいアイシャドウパレットを初めて使う時の、ブラシを入れる瞬間に少しだけ勇気がいる。','いつでも',8);
INSERT INTO "situations" VALUES(319,'自分の肌や唇の写真を撮り、購入したコスメの使用前・使用後の比較画像を作るのが趣味。','いつでも',8);
INSERT INTO "situations" VALUES(320,'香水もコレクションしており、その日の気分やファッションに合わせて香りを変える。','いつでも',8);
INSERT INTO "situations" VALUES(321,'同じブランドのコスメでメイクを統一する「縛りメイク」を楽しむ日がある。','いつでも',8);
INSERT INTO "situations" VALUES(322,'持っているコスメの数を数えようとして、途中で多すぎて諦める。','いつでも',8);
INSERT INTO "situations" VALUES(323,'朝のメイク時間は、自分と向き合うための大切な儀式だと思っている。','朝',8);
INSERT INTO "situations" VALUES(324,'天気予報で湿度や紫外線の量を確認し、その日のベースメイクや下地を決める。','朝',8);
INSERT INTO "situations" VALUES(325,'出勤・通学前の忙しい時間でも、アイラインの引きや眉毛の形には一切の妥協を許さない。','朝',8);
INSERT INTO "situations" VALUES(326,'通勤中にスマホで見るのは、ニュースよりも美容系インフルエンサーのSNSや美容情報サイト。','朝',8);
INSERT INTO "situations" VALUES(327,'朝の情報番組の星占いで、自分の星座のラッキーカラーが発表されると、その色のコスメを使いたくなる。','朝',8);
INSERT INTO "situations" VALUES(328,'昼休み、会社の化粧室でメイク直しをする時間が至福のリフレッシュタイム。','昼',8);
INSERT INTO "situations" VALUES(329,'ランチを食べた後、どのリップを塗り直すかで午後の気分が変わる。','昼',8);
INSERT INTO "situations" VALUES(330,'昼休みに、会社の近くのドラッグストアやバラエティショップに新作コスメのパトロールに行く。','昼',8);
INSERT INTO "situations" VALUES(331,'PCの横にハンドクリームとリップクリームを常備し、乾燥を感じたらすぐに保湿する。','昼',8);
INSERT INTO "situations" VALUES(332,'午後の仕事中、眠気覚ましに清涼感のあるフェイスミストを顔に吹きかける。','昼',8);
INSERT INTO "situations" VALUES(333,'夜、お風呂上がりのスキンケアタイムが一日で一番のリラックス時間。','夜',8);
INSERT INTO "situations" VALUES(334,'ベッドに入ってから、スマホで新作コスメの情報をチェックし始め、気づけば深夜になっている。','夜',8);
INSERT INTO "situations" VALUES(335,'週末の夜、持っているコスメを全部出して、一人ファッションショーならぬ「一人メイクショー」を開催する。','夜',8);
INSERT INTO "situations" VALUES(336,'スペシャルケアとして、その日の肌のコンディションに合わせたシートマスクを選ぶのが楽しみ。','夜',8);
INSERT INTO "situations" VALUES(337,'美容系YouTuberのナイトルーティン動画を見て、自分のスキンケア方法と比較検討する。','夜',8);
INSERT INTO "situations" VALUES(338,'仕事でストレスが溜まると、帰宅途中にデパートのコスメカウンターに吸い寄せられる。','いつでも',8);
INSERT INTO "situations" VALUES(339,'会社のデスクの引き出しに「置きコスメ」を完備。リップ、パウダー、ハンドクリームは必須。','いつでも',8);
INSERT INTO "situations" VALUES(340,'同僚のメイクがいつもと違うとすぐに気づき、「そのアイシャドウ、新色？」と話しかけてしまう。','いつでも',8);
INSERT INTO "situations" VALUES(341,'給料日やボーナスが出ると、真っ先に「ご褒美コスメ」を買いに行く計画を立てる。','いつでも',8);
INSERT INTO "situations" VALUES(342,'仕事で使うPCのブックマークバーが、大手コスメブランドの公式サイトで埋まっている。','いつでも',8);
INSERT INTO "situations" VALUES(343,'会社の福利厚生や、加入している健康保険組合のサイトで、コスメの割引販売がないかチェックする。','いつでも',8);
INSERT INTO "situations" VALUES(344,'オンライン会議の前は、画面映りを計算して普段より少しだけ濃いめのメイクをする。','いつでも',8);
INSERT INTO "situations" VALUES(345,'仕事用のカバンにも、最低限のメイク直しができる厳選コスメを入れたポーチを常備。','いつでも',8);
INSERT INTO "situations" VALUES(346,'オフィスが乾燥しているため、デスクに小型の加湿器を置いて肌の潤いを守ろうとする。','いつでも',8);
INSERT INTO "situations" VALUES(347,'仕事のモチベーションを上げるため、お気に入りのデパコスリップを「戦闘リップ」と名付けている。','いつでも',8);
INSERT INTO "situations" VALUES(348,'有給休暇を取って、平日の空いているデパートでゆっくりコスメカウンター巡りをすることに幸せを感じる。','いつでも',8);
INSERT INTO "situations" VALUES(349,'出張の際、現地の空港限定コスメやご当地コスメをチェックするのを忘れない。','いつでも',8);
INSERT INTO "situations" VALUES(350,'同僚へのちょっとしたプレゼントやお礼に、高級ブランドのハンドクリームやリップバームを贈ると喜ばれることを知っている。','いつでも',8);
INSERT INTO "situations" VALUES(351,'仕事の休憩中、スマホでコスメのレビューサイトやアプリをチェックする。','いつでも',8);
INSERT INTO "situations" VALUES(352,'大事なプレゼンや商談がある日は、信頼と実績のある「お守りコスメ」でメイクを固める。','いつでも',8);
INSERT INTO "situations" VALUES(353,'オフィスで指先が乾燥した時、香りの良いハンドクリームを塗って気分転換をする。','いつでも',8);
INSERT INTO "situations" VALUES(354,'仕事で疲れた日こそ、家に帰ってからのクレンジングとスキンケアを丁寧に行い、自分を労る。','いつでも',8);
INSERT INTO "situations" VALUES(355,'「このプロジェクトが終わったら、あの新作パレットを買う」と心に決め、仕事を頑張る。','いつでも',8);
INSERT INTO "situations" VALUES(356,'会社の経費で文房具を買う際、カラーペンの色合いをついアイシャドウパレットのように見てしまう。','いつでも',8);
INSERT INTO "situations" VALUES(357,'同僚と給湯室で「最近、肌の調子どう？」という会話から、おすすめの美容液の話に発展する。','いつでも',8);
INSERT INTO "situations" VALUES(358,'新入社員に、オフィスメイクの基本やおすすめの崩れにくいコスメを教えてあげる。','いつでも',8);
INSERT INTO "situations" VALUES(359,'PCのデスクトップの壁紙を、好きなコスメブランドのイメージ画像や、美しいコスメの写真に設定している。','いつでも',8);
INSERT INTO "situations" VALUES(360,'仕事中、アイデアに詰まると、お気に入りのリップを塗り直して気分を切り替える。','いつでも',8);
INSERT INTO "situations" VALUES(361,'ボーナスで買った高級美容液を、使うたびに「さあ、働くぞ」という気持ちにさせてくれる投資だと考える。','いつでも',8);
INSERT INTO "situations" VALUES(362,'朝のメイクの仕上がりが完璧だと、その日一日、仕事がうまくいくような気がする。','朝',8);
INSERT INTO "situations" VALUES(363,'出社前に、駅のトイレの鏡で最終的なメイクチェックを欠かさない。','朝',8);
INSERT INTO "situations" VALUES(364,'会社の始業前、デスクでコーヒーを飲みながら、スマホで美容系メディアの記事を読む。','朝',8);
INSERT INTO "situations" VALUES(365,'朝礼で、少し寝不足で疲れた顔をしている同僚に「今日の肌、ツヤツヤだね」とお世辞を言う。','朝',8);
INSERT INTO "situations" VALUES(366,'眠たい月曜の朝は、ラメが多めのキラキラしたアイシャドウを塗って、無理やりテンションを上げる。','朝',8);
INSERT INTO "situations" VALUES(367,'昼休み、会社の同僚と「あのデパートのポイント、今週末5倍だよ」といったお得情報を交換する。','昼',8);
INSERT INTO "situations" VALUES(368,'ランチの後、マスクで崩れたベースメイクを、クッションファンデで素早くお直しする。','昼',8);
INSERT INTO "situations" VALUES(369,'午後の会議に向けて、色の濃いリップを塗り、気合を入れる。','昼',8);
INSERT INTO "situations" VALUES(370,'仕事帰りに、予約していた限定コスメを引き取りに行くのが楽しみで、足取りが軽くなる。','夜',8);
INSERT INTO "situations" VALUES(371,'会社の飲み会がある日は、化粧崩れ防止のスプレーを朝のメイクの仕上げに念入りに吹きかけておく。','夜',8);
INSERT INTO "situations" VALUES(372,'残業で疲れた肌をいたわるため、帰宅後すぐにクレンジングバームで優しくメイクをオフする。','夜',8);
INSERT INTO "situations" VALUES(373,'金曜の夜、仕事が終わった解放感から、普段は使わないような大胆なカラーのコスメでメイクをして遊びに出かける。','夜',8);
INSERT INTO "situations" VALUES(374,'オンラインのコスメ先行販売会が平日の夜にあると、仕事を早めに切り上げてPCの前で待機する。','夜',8);
CREATE TABLE tuning_history (id INTEGER PRIMARY KEY, post_id INTEGER, timestamp TEXT, previous_content TEXT, advice_used TEXT, FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE);
INSERT INTO "tuning_history" VALUES(1,1,'2025-09-23 01:57:57','窓際の席で、雨の音をBGMに読書中。ネルドリップのコーヒーの香りと、古い本のインクの匂いに包まれて、なんだか、素敵ですね。#雨の日 #読書 #喫茶店 #古本
','もっと可愛く');
INSERT INTO "tuning_history" VALUES(2,1,'2025-09-23 06:16:50','雨粒が窓を叩く音、ネルドリップのコーヒーの香り…☕️📚  お気に入りの喫茶店で、古本の世界に浸る幸せタイム📖´-`  なんだか、ほっこりしちゃうなぁ💕 #雨の日 #読書 #喫茶店 #古本
','もっと大人っぽく');
INSERT INTO "tuning_history" VALUES(3,1,'2025-09-23 06:17:10','雨粒が窓を叩く音、ネルドリップのコーヒーの香り…☕️📚  お気に入りの喫茶店で、古本の世界に浸る幸せタイム📖´-`  なんだか、ほっこりしちゃうなぁ💕 #雨の日 #読書 #喫茶店 #古本
','もっと大人っぽく, 晴れた日で');
INSERT INTO "tuning_history" VALUES(4,1,'2025-09-23 06:17:30','雨粒が窓を叩く音、ネルドリップのコーヒーの香り…☕️📚  お気に入りの喫茶店で、古本の世界に浸る幸せタイム📖´-`  なんだか、ほっこりしちゃうなぁ💕 #雨の日 #読書 #喫茶店 #古本
','もっと大人っぽく, 晴れた日で');
INSERT INTO "tuning_history" VALUES(5,1,'2025-09-23 06:17:30','雨粒が窓を叩く音、ネルドリップのコーヒーの香り…☕️📚  お気に入りの喫茶店で、古本の世界に浸る幸せタイム📖´-`  なんだか、ほっこりしちゃうなぁ💕 #雨の日 #読書 #喫茶店 #古本
','もっと大人っぽく, 晴れた日で');
INSERT INTO "tuning_history" VALUES(6,1,'2025-09-23 06:18:21','雨粒が窓を叩く音、ネルドリップのコーヒーの香り…☕️📚  お気に入りの喫茶店で、古本の世界に浸る幸せタイム📖´-`  なんだか、ほっこりしちゃうなぁ💕 #雨の日 #読書 #喫茶店 #古本
','晴れた日で');
INSERT INTO "tuning_history" VALUES(7,3,'2025-09-23 06:19:52','秋晴れの午後は、古書店で偶然見つけた詩集と温かい紅茶でひと休み。インクの匂いに包まれながら、ページをめくるたび心に小さな物語が生まれていく。なんだか、素敵ですね。#読書 #詩 #秋 #古書店 #カフェ
','もっと可愛く');
INSERT INTO "tuning_history" VALUES(8,1,'2025-09-23 06:20:12','雨粒が窓を叩く音、ネルドリップのコーヒーの香り…☕️📚  お気に入りの喫茶店で、古本の世界に浸る幸せタイム📖´-`  なんだか、ほっこりしちゃうなぁ💕 #雨の日 #読書 #喫茶店 #古本
','意外な一面を見せて');
INSERT INTO "tuning_history" VALUES(9,1,'2025-09-23 06:34:06','雨粒が窓を叩く音、ネルドリップのコーヒーの香り…☕️📚  お気に入りの喫茶店で、古本の世界に浸る幸せタイム📖´-`  なんだか、ほっこりしちゃうなぁ💕 #雨の日 #読書 #喫茶店 #古本
','もっと大人っぽく');
INSERT INTO "tuning_history" VALUES(10,1,'2025-09-23 06:34:32','雨音に包まれた静謐な喫茶店。古い本のインクの香りと、ネルドリップで淹れたコーヒーの温もり。窓の外を流れる雨粒を眺めながら、物語の世界に深く沈み込む。こんな時間が、私にとっての至福。#読書 #喫茶店 #雨の日
','もっと大人っぽく, 晴れた日に');
INSERT INTO "tuning_history" VALUES(11,1,'2025-09-23 07:15:42','陽だまりに包まれた静かな喫茶店。窓辺に差し込む光の中で、アンティークのカップでコーヒーを味わう。ページをめくるたびに広がる物語の世界。穏やかな午後のひとときを、心ゆくまで堪能しています。 #読書 #喫茶店 #休日
','意外な一面を見せて, 曇りの日に');
INSERT INTO "tuning_history" VALUES(12,1,'2025-09-23 07:16:44','灰色の空模様。お気に入りの喫茶店で、今日はディストピアSFに没頭。窓の外を流れる雨粒を眺めながら、重厚な世界観に浸っています。普段は見せない一面かも。なんだか、素敵ですね。 #読書 #喫茶店 #雨の日 #SF
','もっと大人っぽく');
INSERT INTO "tuning_history" VALUES(13,1,'2025-09-23 07:17:10','窓の外に雨の線が流れる。古びた喫茶店で、静かにページをめくる。今日はディストピアSF。仄暗い物語の世界に、ほんの少し現実逃避。この静寂が、心地いい。#喫茶店 #読書 #雨 #SF
','もっと大人っぽく');
INSERT INTO "tuning_history" VALUES(14,1,'2025-09-23 07:17:40','古びた喫茶店の窓辺、雨音がBGM。ディストピアSFの暗喩的な世界に浸る。仄暗い物語と、この静寂。矛盾するようで、私を落ち着かせる何かがある。大人になるって、こういうことかもしれない。#喫茶店 #読書 #雨 #SF
','豆知識を加えて');
INSERT INTO "tuning_history" VALUES(15,3,'2025-09-23 07:19:35','秋晴れの午後は、古書店で偶然見つけた詩集と温かい紅茶でひと休み。インクの匂いに包まれながら、ページをめくるたび心に小さな物語が生まれていく。なんだか、素敵ですね。#読書 #詩 #秋 #古書店 #カフェ
','少しユーモアを');
INSERT INTO "tuning_history" VALUES(16,4,'2025-09-23 11:05:55','窓際の席で、雨の音をBGMに読書中。☕️  お気に入りの喫茶店は、私だけの小さな宇宙。今日の相棒は宮沢賢治。なんだか、素敵ですね。 #読書 #喫茶店 #雨の日 #宮沢賢治
','意外な一面を見せて');
INSERT INTO "tuning_history" VALUES(17,4,'2025-09-23 11:06:06','窓際の席で、雨の音をBGMに読書中。☕️  お気に入りの喫茶店は、私だけの小さな宇宙。今日の相棒は宮沢賢治。なんだか、素敵ですね。 #読書 #喫茶店 #雨の日 #宮沢賢治
','意外な一面を見せて');
INSERT INTO "tuning_history" VALUES(18,4,'2025-09-23 11:06:26','窓際の席で、雨の音をBGMに読書中。☕️  お気に入りの喫茶店は、私だけの小さな宇宙。今日の相棒は宮沢賢治。なんだか、素敵ですね。 #読書 #喫茶店 #雨の日 #宮沢賢治
','');
INSERT INTO "tuning_history" VALUES(19,4,'2025-09-23 11:07:33','窓際の席で、雨の音をBGMに読書中。☕️  お気に入りの喫茶店は、私だけの小さな宇宙。今日の相棒は宮沢賢治。なんだか、素敵ですね。 #読書 #喫茶店 #雨の日 #宮沢賢治
','句読点を工夫して');
INSERT INTO "tuning_history" VALUES(20,4,'2025-09-23 11:23:03','窓際の席で、雨の音をBGMに読書中。☕️  お気に入りの喫茶店は、私だけの小さな宇宙。今日の相棒は宮沢賢治。なんだか、素敵ですね。 #読書 #喫茶店 #雨の日 #宮沢賢治
','もっと可愛く');
INSERT INTO "tuning_history" VALUES(21,4,'2025-09-23 11:23:15','窓際の席で、雨の音をBGMに読書中。☕️  お気に入りの喫茶店は、私だけの小さな宇宙。今日の相棒は宮沢賢治。なんだか、素敵ですね。 #読書 #喫茶店 #雨の日 #宮沢賢治
','もっと可愛く');
INSERT INTO "tuning_history" VALUES(22,4,'2025-09-23 11:23:28','窓際の席で、雨の音をBGMに読書中。☕️  お気に入りの喫茶店は、私だけの小さな宇宙。今日の相棒は宮沢賢治。なんだか、素敵ですね。 #読書 #喫茶店 #雨の日 #宮沢賢治
','もっと可愛く');
INSERT INTO "tuning_history" VALUES(23,4,'2025-09-23 11:23:46','窓際の席で、雨の音をBGMに読書中。☕️  お気に入りの喫茶店は、私だけの小さな宇宙。今日の相棒は宮沢賢治。なんだか、素敵ですね。 #読書 #喫茶店 #雨の日 #宮沢賢治
','意外な一面を見せて');
INSERT INTO "tuning_history" VALUES(24,6,'2025-09-23 11:25:33','雨上がりのロフト、インクの香りと古い本の匂いが混ざって、なんだか、素敵ですね。万年筆と新しいノートを買って、これから始まる物語に想いを馳せています。 #ロフト #文具 #雨上がり
','意外な一面を見せて');
INSERT INTO "tuning_history" VALUES(25,6,'2025-09-23 11:26:02','雨上がりのロフト、インクの香りと古い本の匂いが混ざって、なんだか、素敵ですね。万年筆と新しいノートを買って、これから始まる物語に想いを馳せています。 #ロフト #文具 #雨上がり
','');
INSERT INTO "tuning_history" VALUES(26,4,'2025-09-23 11:42:23','窓際の席で、雨の音をBGMに読書中。☕️  お気に入りの喫茶店は、私だけの小さな宇宙。今日の相棒は宮沢賢治。なんだか、素敵ですね。 #読書 #喫茶店 #雨の日 #宮沢賢治
','豆知識を加えて');
INSERT INTO "tuning_history" VALUES(27,4,'2025-09-23 12:41:47','窓際の席で雨の音をBGMに、宮沢賢治の「銀河鉄道の夜」を読んでいます。☕️賢治の故郷、岩手県花巻市には賢治が愛したお酒「イーハトーブ・ワイン」があるんですよ。いつか飲んでみたいですね。お気に入りの喫茶店は、私だけの小さな宇宙。素敵ー。 #読書 #喫茶店 #雨の日 #宮沢賢治 #銀河鉄道の夜
','もっと大人っぽく');
INSERT INTO "tuning_history" VALUES(28,4,'2025-09-23 12:47:24','窓際の席に差し込む柔らかな光。雨音が静かにリズムを刻む。今日はボルドー産の赤ワインを偲ばせる深い味わいのコーヒーと共に、宮沢賢治の世界に浸っています。「銀河鉄道の夜」。孤独と希望が織りなす物語は、いつまでも心に残る。#読書 #喫茶店 #雨の日 #宮沢賢治
','もっと可愛く, 宮沢賢治なしで');
INSERT INTO "tuning_history" VALUES(29,4,'2025-09-23 13:08:49','窓際の席で雨音をBGMに読書中。☕️今日のコーヒー、深い味わいでとっても素敵ー！✨  この静かな時間が好き。😌💭 #喫茶店 #雨の日 #読書
','もっと可愛く');
INSERT INTO "tuning_history" VALUES(30,4,'2025-09-23 13:15:31','雨粒が窓を叩く音、心地いいBGMみたい…☕️今日のコーヒー、深くて美味しい…♡ 素敵な香りに包まれて、読書に夢中。📖 ふふっ、この静かな時間、大好き。💕 #喫茶店 #雨の日 #読書
','もっと大人っぽく');
INSERT INTO "tuning_history" VALUES(31,6,'2025-09-23 13:18:15','雨上がりのロフト、インクの香りと古い本の匂いが混ざって、なんだか、素敵ですね。万年筆と新しいノートを買って、これから始まる物語に想いを馳せています。 #ロフト #文具 #雨上がり
','豆知識を加えて');
INSERT INTO "tuning_history" VALUES(32,4,'2025-09-23 13:24:09','窓に当たる雨音と、コーヒーの深い香りが織りなす静謐な時間。ページをめくる指先もゆっくりと。この上なく贅沢な午後のひととき。#喫茶店 #雨 #読書
','豆知識を加えて');
INSERT INTO "tuning_history" VALUES(33,4,'2025-09-23 13:24:25','窓に当たる雨音と、コーヒーの深い香りが織りなす静謐な時間。ページをめくる指先もゆっくりと。この上なく贅沢な午後のひととき。今日のコーヒーは、グアテマラ・アンティグア。柑橘系の酸味とチョコレートのようなコクが雨の日にぴったり。#喫茶店 #雨 #読書 #コーヒー #グアテマラ
','句読点を工夫して');
INSERT INTO "tuning_history" VALUES(34,4,'2025-09-23 13:35:46','雨音とコーヒーの香り、静謐な時間。ページをめくる指先も、ゆっくりと。贅沢な午後。今日のコーヒーはグアテマラ・アンティグア。柑橘系の酸味と、チョコレートのようなコクが、雨の日にぴったり。素敵…。#喫茶店 #雨 #読書 #コーヒー #グアテマラ
','もっと大人っぽく');
INSERT INTO "tuning_history" VALUES(35,4,'2025-09-23 13:36:17','雨音が窓を叩く静かな午後。深煎りのコーヒーの苦味が、心にしみる。今日の読書は、サルトル。重厚な言葉が、雨にけぶる街の景色と溶け合う。この静謐が、たまらなく素敵…。#喫茶店 #雨 #読書 #サルトル #コーヒー
','もっと大人っぽく, 晴れた日で');
INSERT INTO "tuning_history" VALUES(36,4,'2025-09-23 13:36:30','午後の陽射しが心地いい。テラス席でシャンパンを傾けながら、サルトルのページをめくる。読書の秋、深まる香りに酔いしれる。この優雅な時間が、たまらなく素敵…。 #シャンパン #読書 #サルトル #テラス席 #秋
','もっと大人っぽく, 晴れた日で');
INSERT INTO "tuning_history" VALUES(37,11,'2025-09-23 14:36:01','星野詩織です🌙 アフターは楽しいお客様との会話で素敵な時間でした✨ 今夜はシャンパンで乾杯🥂  優しい気持ちでいっぱいです。読書の秋🍁📚  ワインの勉強もしなきゃ🍷  #ホステス #シャンパン #読書の秋 #ワイン勉強中 #素敵な夜
','少しユーモアを, もっとラフに');
INSERT INTO "tuning_history" VALUES(38,11,'2025-09-23 14:36:10','しおりんです🌙 アフターはシャンパン祭り🥂✨  笑いすぎてお腹痛い🤣  お客様、ご馳走様でした💕 今夜はいい夢みれそう…zzz  読書の秋だし、ワインの勉強もしなきゃ📚🍷  あ、そういえばパスポート作ったんだ🤫  #ホステス #シャンパン #ワイン勉強中 #秘密
','少しユーモアを, もっとラフに');
INSERT INTO "tuning_history" VALUES(39,11,'2025-09-23 14:38:03','しおりんです🌙 アフターはシャンパン祭りで笑いすぎてお腹筋崩壊しそう🤣  お客様、ご馳走様でした💕  読書の秋…の前にワインの秋🍷✨  パスポートも作ったし、いつか"本場"で乾杯したいな🥂🤫 #シャンパン #ワイン勉強中 #ひっそり夢
','もっと大人っぽく');
INSERT INTO "tuning_history" VALUES(40,11,'2025-09-23 14:38:13','静かな夜のタクシーの中。シャンパンの余韻に浸りながら、お客様との会話が蘇ります。読書の秋、ワインの秋…いつかパスポートを手に、本場の空の下で乾杯するのが夢です。#ワイン #ソムリエへの道
','もっと大人っぽく, ラフに');
INSERT INTO "tuning_history" VALUES(41,11,'2025-09-23 14:38:22','シャンパンの泡みたいに消えていく夜。読書の秋もいいけど、この街の静けさも悪くない。いつかパスポート取って、あの人の隣で乾杯したいな。#大人時間 #秘密の夜
','もっと大人っぽく, ラフに');
INSERT INTO "tuning_history" VALUES(42,11,'2025-09-23 14:39:31','消えゆく街の灯り、シャンパンの余韻。静かな夜もいい。パスポート、いつか使う日が来るかな。#大人時間
','もっと可愛く');
INSERT INTO "tuning_history" VALUES(43,11,'2025-09-23 14:40:01','シャンパンの泡みたいに、楽しい夜でした🥂✨　素敵な出会いにも感謝…♡ パスポート、いつか一緒に海外旅行とか…どうですか？☺️ #大人可愛い #しおりん
','句読点を工夫して');
INSERT INTO "tuning_history" VALUES(44,11,'2025-09-23 14:41:40','シャンパンの泡みたいに、楽しい夜でした…🥂✨　素敵な出会いにも感謝です。パスポート、いつか一緒に海外旅行、とか？☺️ #大人可愛い #しおりん
','もっと可愛く');
INSERT INTO "tuning_history" VALUES(45,11,'2025-09-23 14:41:55','シャンパンの泡みたいに、キラキラな夜でした🥂✨　素敵な出会い…ドキドキしちゃった♡　いつか一緒に海外旅行とか…いいなぁ✈️　パスポート、準備しとこっかな？☺️ #大人可愛い #しおりん
','もっと可愛く, 絵文字無しで');
INSERT INTO "tuning_history" VALUES(46,11,'2025-09-23 14:42:24','静かな夜のタクシーの中。シャンパンの余韻がまだ残っているみたい。素敵な方とのお話、少しドキドキしました。いつか、一緒に旅ができたらいいな。パスポート、そろそろ準備しようかな。
','もっと可愛く');
INSERT INTO "tuning_history" VALUES(47,11,'2025-09-23 14:47:17','シャンパンの泡みたいに、今夜はちょっとふわふわ気分♡  素敵な方とのお話が嬉しくて、ドキドキが止まらない…かも？🙊  いつか一緒に、遠くに行きたいなぁ…✈️ パスポート、準備しなくちゃ！✨
','');
INSERT INTO "tuning_history" VALUES(48,11,'2025-09-23 21:22:05','静かな夜のタクシーの中。素敵な方とのお話が心に染み渡り、シャンパンの余韻のように温かい気持ちでいっぱいです。いつか、もっと深くお話できる機会がありますように…🍷
','豆知識を加えて, もっと軽く');
INSERT INTO "tuning_history" VALUES(49,11,'2025-09-23 21:22:11','静かな夜のタクシーの中。素敵な方とのお話が心に染み渡り、シャンパンの余韻のように温かい気持ちでいっぱいです。いつか、もっと深くお話できる機会がありますように…🍷
','豆知識を加えて, もっと軽く');
INSERT INTO "tuning_history" VALUES(50,11,'2025-09-23 21:24:43','静かな夜のタクシーの中。素敵な方とのお話が心に染み渡り、シャンパンの余韻のように温かい気持ちでいっぱいです。いつか、もっと深くお話できる機会がありますように…🍷
','もっと可愛く');
INSERT INTO "tuning_history" VALUES(51,11,'2025-09-23 21:33:19','素敵な方とのお話が、シャンパンみたいに甘くてふわふわ〜🥂💕　もっとお話したかったなぁ…💭　また会えたら嬉しいなっ🥰　今日は素敵な夜をありがとうございました✨
','もっと大人っぽく, 意外な一面を見せて');
INSERT INTO "tuning_history" VALUES(52,1,'2025-09-23 22:43:10','古びた喫茶店の窓辺、雨音がBGM。ディストピアSFの暗喩的な世界に浸る。仄暗い物語と、この静寂。矛盾するようで、私を落ち着かせる何かがある。大人になるって、こういうことかもしれない。#喫茶店 #読書 #雨 #SF
','もっと可愛く');
INSERT INTO "tuning_history" VALUES(53,1,'2025-09-23 22:44:28','古びた喫茶店の窓辺、雨音がBGM。ディストピアSFの暗喩的な世界に浸る。仄暗い物語と、この静寂。矛盾するようで、私を落ち着かせる何かがある。大人になるって、こういうことかもしれない。#喫茶店 #読書 #雨 #SF
','意外な一面を見せて');
INSERT INTO "tuning_history" VALUES(54,1,'2025-09-23 22:46:38','黒髪濡らす雨。窓辺でシャンパンゴールドの紹興酒…🍸✨なんてね。本当はホットミルクココア。ディストピアSFの主人公みたいに強い女性になりたいけど、今は読書中。ふふ、このギャップ、素敵ー💕 #喫茶店 #読書 #雨 #SF #紹興酒
','もっと大人っぽく, 詩人ぽくなく');
INSERT INTO "tuning_history" VALUES(55,17,'2025-09-23 22:49:56','前回の投稿:
昼から焼肉なんて贅沢〜🥩✨  大好きなハラミとタン塩、もう最高！紹興酒も一緒にいただいちゃいます🍶  #焼肉 #昼焼肉 #贅沢ランチ #ハラミ #タン塩 #紹興酒 #しおりんの休日


新しい投稿:
昼から焼肉…なんて贅沢。大好きなハラミとタン塩を、冷えたシャンパンと共にいただきます🥂✨　この瞬間、まさに至福…！ #焼肉 #昼焼肉 #贅沢ランチ #ハラミ #タン塩 #シャンパン #しおりんの休日
','句読点を工夫して, 紹興酒を別のお酒に');
INSERT INTO "tuning_history" VALUES(56,17,'2025-09-23 22:53:43','*前回の投稿:*
*昼から焼肉…なんて贅沢。大好きなハラミとタン塩を、冷えたシャンパンと共にいただきます🥂✨　この瞬間、まさに至福…！ #焼肉 #昼焼肉 #贅沢ランチ #ハラミ #タン塩 #シャンパン #しおりんの休日
*
*新しい投稿:*
昼から焼肉…なんて贅沢！大好きなハラミとタン塩を、冷えたシャンパンと共に。実はシャンパンと焼肉の相性は抜群なんです🥂  お肉をさっぱりと味わえて、消化も助けてくれるとか✨ この瞬間、まさに至福…！ #焼肉 #昼焼肉 #贅沢ランチ #ハラミ #タン塩 #シャンパン #しおりんの休日
','豆知識を加えて');
INSERT INTO "tuning_history" VALUES(57,17,'2025-09-23 23:08:25','<span style=''color: #888888''>前回の投稿:</span>
<span style=''color: #888888''>昼から焼肉…なんて贅沢！大好きなハラミとタン塩を、冷えたシャンパンと共に。実はシャンパンと焼肉の相性は抜群なんです🥂  お肉をさっぱりと味わえて、消化も助けてくれるとか✨ この瞬間、まさに至福…！ #焼肉 #昼焼肉 #贅沢ランチ #ハラミ #タン塩 #シャンパン #しおりんの休日
</span>
新しい投稿:
昼から焼肉…なんて贅沢！大好きなハラミとタン塩を、キンと冷えたシャンパンと共に。実はシャンパンと焼肉って、相性抜群なんです🥂お肉をさっぱりと味わえて、消化も助けてくれるとか？✨この至福の瞬間…素敵ー！ #焼肉 #昼焼肉 #贅沢ランチ #ハラミ #タン塩 #シャンパン #しおりんの休日
','句読点を工夫して');
INSERT INTO "tuning_history" VALUES(58,17,'2025-09-23 23:22:03','<span style=''color: #888888''>前回の投稿:</span>
<span style=''color: #888888''>昼から焼肉…なんて贅沢！大好きなハラミとタン塩を、キンと冷えたシャンパンと共に。実はシャンパンと焼肉って、相性抜群なんです🥂お肉をさっぱりと味わえて、消化も助けてくれるとか？✨この至福の瞬間…素敵ー！ #焼肉 #昼焼肉 #贅沢ランチ #ハラミ #タン塩 #シャンパン #しおりんの休日
</span>
新しい投稿:
昼から焼肉…なんて贅沢！大好きなハラミとタン塩、今日はご飯大盛りで🍚実は白米と焼肉の脂って最強コンビ…気づいてました？お肉で口の中が幸せいっぱいになったら、キンと冷えたシャンパンでクールダウン🥂ふふ、意外でしょ？✨ #焼肉 #昼焼肉 #ハラミ #タン塩 #シャンパン #白米 #しおりんの休日
','意外な一面を見せて');
INSERT INTO "tuning_history" VALUES(59,17,'2025-09-23 23:37:40','<span style=''color: #888888''>前回の投稿:</span>
<span style=''color: #888888''>昼から焼肉…なんて贅沢！大好きなハラミとタン塩、今日はご飯大盛りで🍚実は白米と焼肉の脂って最強コンビ…気づいてました？お肉で口の中が幸せいっぱいになったら、キンと冷えたシャンパンでクールダウン🥂ふふ、意外でしょ？✨ #焼肉 #昼焼肉 #ハラミ #タン塩 #シャンパン #白米 #しおりんの休日
</span>

**新しい投稿:**
昼から焼肉…なんて贅沢！大好きなハラミとタン塩、今日は白米大盛りで🍚実は白米に含まれるデンプンが、肉の消化を助けるんですって。勉強中📚お肉で満たされたら、キンと冷えたシャンパン🥂意外？実はシャンパン製法発祥の地はイギリスなんですって！ #焼肉 #昼焼肉 #ハラミ #タン塩 #シャンパン #白米 #しおりんの休日 #ソムリエへの道
','意外な一面を見せて, 豆知識を加えて');
INSERT INTO "tuning_history" VALUES(60,27,'2025-09-25 12:07:13','<span style=''color: #888888''>前回の投稿:</span>
<span style=''color: #888888''>六本木キラキラ✨アフターは〇〇さんと🍸楽しい時間はあっという間…🥺またすぐ会えますよね？💕 #キャバクラ #六本木 #アフター #ClubDiamond #tetetete123
</span>

**新しい投稿:**
〇〇さんとアフター🍸✨　楽しい時間はあっという間ですね…🥺💕　またすぐ会いたいなぁ…♡　エヘヘ☺️　#キャバクラ #六本木 #アフター #ClubDiamond
','もっと可愛く, #tetetete123を削除');
INSERT INTO "tuning_history" VALUES(61,27,'2025-09-25 12:07:42','<span style=''color: #888888''>前回の投稿:</span>
<span style=''color: #888888''>〇〇さんとアフター🍸✨　楽しい時間はあっという間ですね…🥺💕　またすぐ会いたいなぁ…♡　エヘヘ☺️　#キャバクラ #六本木 #アフター #ClubDiamond
</span>

**新しい投稿:**
ラブさんとアフター🍸✨　楽しい時間はあっという間ですね…🥺💕　またすぐ会いたいです…♡　えへへ☺️　#キャバクラ #六本木 #アフター #ClubDiamond
','◯◯さんをラブさんに');
INSERT INTO "tuning_history" VALUES(62,48,'2025-09-26 22:25:58','<span style=''color: #888888''>前回の投稿:</span>
<span style=''color: #888888''>皆さま、いつもありがとうね♡ 7月18日は私のバースデーなの♪ 当日は「Club Diamond」で、とびきり可愛い私と一緒にお祝いしてくれたら嬉しいな！ えへへ♡ 素敵な夜にしましょうね！🥂✨ #バースデー #キャバ嬢 #六本木 #ClubDiamond Tetetete123
</span>

**新しい投稿:**
7月18日はバースデーなの♡ 当日はとびきり可愛い私と一緒にお祝いしてくれたら嬉しいな！ えへへ♡ 素敵な夜にしましょうね！🥂✨ #バースデー #キャバ嬢
','もっと可愛く, Club Diamondのテキストがあった場合に削除');
INSERT INTO "tuning_history" VALUES(63,45,'2025-09-26 22:53:32','きゃー！お肉おいしすぎます～♡ 特にタンがとろける(๑´ڡ`๑) 連れてきてくれてありがとうございます！〇〇さん、さすがですね♪ #焼肉 #同伴 #ClubDiamond #Tetetete123
','#ClubDiamondを削除');
INSERT INTO "tuning_history" VALUES(64,41,'2025-09-26 22:53:35','今日のランチは焼肉～！🍖✨お肉パワーで午後も頑張るぞ💪😋 4te_123、今日も絶好調ですよ～！えへへ♡ #焼肉ランチ #六本木 #ClubDiamond #Tetetete123','#ClubDiamondを削除');
INSERT INTO "tuning_history" VALUES(65,49,'2025-09-27 00:03:25','<span style=''color: #888888''>前回の投稿:</span>
<span style=''color: #888888''>きゃー♡最近見つけた優秀ガジェット紹介しちゃう！お家でサロン級ケアできる美顔器🥺✨旅行にも持って行けるコンパクトさが嬉しいの♪これで私もさらにキラキラになれるかな？えへへ♡[Amazon URL（美顔器）] #美顔器 #美容 #おすすめ
</span>

**新しい投稿:**
きゃー♡最近見つけた優秀ガジェット紹介しちゃう！お家でサロン級ケアできる美顔器🥺✨旅行にも持って行けるコンパクトさが嬉しいの♪これで私もさらにキラキラになれるかな？えへへ♡[https://www.amazon.co.jp/dp/B0XXXXXXXXXX](https://www.amazon.co.jp/dp/B0XXXXXXXXXX) #美顔器 #美容 #おすすめ
','[Amazon URL（美顔器）] を実際のURLに');
INSERT INTO "tuning_history" VALUES(66,49,'2025-09-27 00:04:25','<span style=''color: #888888''>前回の投稿:</span>
<span style=''color: #888888''>きゃー♡最近見つけた優秀ガジェット紹介しちゃう！お家でサロン級ケアできる美顔器🥺✨旅行にも持って行けるコンパクトさが嬉しいの♪これで私もさらにキラキラになれるかな？えへへ♡[https://www.amazon.co.jp/dp/B0XXXXXXXXXX](https://www.amazon.co.jp/dp/B0XXXXXXXXXX) #美顔器 #美容 #おすすめ
</span>

**新しい投稿:**
きゃー♡最近見つけた優秀ガジェット紹介しちゃう！お家でサロン級ケアできる美顔器🥺✨旅行にも持って行けるコンパクトさが嬉しいの♪これで私もさらにキラキラになれるかな？えへへ♡ [https://amzn.to/3WafDHC](https://amzn.to/3WafDHC) #美顔器 #美容 #おすすめ
','リンク部分をhttps://amzn.to/3WafDHCに');
INSERT INTO "tuning_history" VALUES(67,49,'2025-09-27 00:05:12','<span style=''color: #888888''>前回の投稿:</span>
<span style=''color: #888888''>きゃー♡最近見つけた優秀ガジェット紹介しちゃう！お家でサロン級ケアできる美顔器🥺✨旅行にも持って行けるコンパクトさが嬉しいの♪これで私もさらにキラキラになれるかな？えへへ♡ [https://amzn.to/3WafDHC](https://amzn.to/3WafDHC) #美顔器 #美容 #おすすめ
</span>

**新しい投稿:**
きゃー♡最近見つけた優秀ガジェット紹介しちゃう！お家でサロン級ケアできる美顔器🥺✨旅行にも持って行けるコンパクトさが嬉しいの♪これで私もさらにキラキラになれるかな？えへへ♡ [https://amzn.to/3WafDHC](https://amzn.to/3WafDHC) #美顔器 #美容 #おすすめ
','[https://amzn.to/3WafDHC](https://amzn.to/3WafDHC) をhttps://amzn.to/3WafDHCに');
INSERT INTO "tuning_history" VALUES(68,58,'2025-09-27 09:38:57','<span style=''color: #888888''>前回の投稿:</span>
<span style=''color: #888888''>## shinrepotoのSNS投稿例

山口は今日もええ天気じゃ！☀️ こんな日は、やっぱりタフなG-SHOCKが相棒じゃの。海でも山でも、安心して使えるけぇ。レポトはコレつけて、ちょいとドライブじゃ！ #GSHOCK #山口県 #ドライブ日和
</span>

**新しい投稿:**
今日の天気は最高！☀️ こんな日は、お気に入りのG-SHOCKと一緒にお出かけ。タフだから、どこへでも安心して行ける！ ドライブ楽しもう！ #GSHOCK #晴れ #お出かけ
','もっと可愛く, 方言無しで');
INSERT INTO "tuning_history" VALUES(69,58,'2025-09-27 09:39:51','<span style=''color: #888888''>前回の投稿:</span>
<span style=''color: #888888''>今日の天気は最高！☀️ こんな日は、お気に入りのG-SHOCKと一緒にお出かけ。タフだから、どこへでも安心して行ける！ ドライブ楽しもう！ #GSHOCK #晴れ #お出かけ
</span>

**新しい投稿:**
今日の天気は晴れ！☀️ 快適な一日をサポートしてくれるのは、Apple Watch Series 8。通知チェックも健康管理もこれ一つでOK！ #AppleWatch #晴れ #スマートウォッチ
','もっとスマートウォッチ等のトレンドのデバイス紹介で');
INSERT INTO "tuning_history" VALUES(70,59,'2025-09-27 11:26:47','<span style=''color: #888888''>前回の投稿:</span>
<span style=''color: #888888''>よっしゃー！新型Apple Watchの情報きたで！レポト、毎年買い替えとるんじゃ。今回はバッテリーに期待したいな！ヘルスケア機能も進化しとるじゃろうか？8月15日の誕生日に自分で買うっちゃ！ #AppleWatch #アップルウォッチ #ガジェット好き #誕生日プレゼント
</span>

**新しい投稿:**
よっしゃー！新型Apple Watchの情報きたで！レポト、毎年買い替えとるんじゃ。今回はバッテリーに期待したいな！ヘルスケア機能も進化しとるじゃろうか？買うっちゃ！ #AppleWatch #アップルウォッチ #ガジェット好き
','誕生日は過ぎているので無しで');
INSERT INTO "tuning_history" VALUES(71,59,'2025-09-27 11:27:08','<span style=''color: #888888''>前回の投稿:</span>
<span style=''color: #888888''>よっしゃー！新型Apple Watchの情報きたで！レポト、毎年買い替えとるんじゃ。今回はバッテリーに期待したいな！ヘルスケア機能も進化しとるじゃろうか？買うっちゃ！ #AppleWatch #アップルウォッチ #ガジェット好き
</span>

**新しい投稿:**
よし！新型Apple Watchの情報が出たな！毎年買い替えているんだ。今回はバッテリーに期待したい。ヘルスケア機能も進化しているだろうか？買うぞ！ #AppleWatch #アップルウォッチ #ガジェット好き
','方言は無しで');
INSERT INTO "tuning_history" VALUES(72,75,'2025-09-28 00:39:40','山口の夜は最高！レポト、今日も一日お疲れ様でした！ #アフター #タクシー #山口','テストのシチュエーションは無しで');
INSERT INTO "tuning_history" VALUES(73,69,'2025-09-28 00:39:41','テスト3実施中。集中して良い結果出すぞ！','テストのシチュエーションは無しで');
INSERT INTO "tuning_history" VALUES(74,80,'2025-09-28 00:39:43','テスト2実施中。進捗順調！皆様、ご協力ありがとうございます！ #テスト #システム','テストのシチュエーションは無しで');
INSERT INTO "tuning_history" VALUES(75,74,'2025-09-28 00:39:45','テスト2実施中！課題クリア目指して頑張ります💪
#テスト #チャレンジ','テストのシチュエーションは無しで');
INSERT INTO "tuning_history" VALUES(76,81,'2025-09-28 00:39:46','昼同伴最高！美味しい料理と楽しい会話で、午後の仕事も頑張れる💪 #昼同伴 #美味しいご飯 #午後も頑張ろう','テストのシチュエーションは無しで');
INSERT INTO "tuning_history" VALUES(77,77,'2025-09-28 00:39:48','山口の夜も更けて。今日も一日お疲れ様でした！ #タクシー帰り #山口','テストのシチュエーションは無しで');
INSERT INTO "tuning_history" VALUES(78,63,'2025-09-28 00:39:50','山口のレポト44歳。アフター帰り、少し酔った勢いで秘密を暴露…！「実は、若い頃バンドやってて…」 #タクシーの中','テストのシチュエーションは無しで');
INSERT INTO "tuning_history" VALUES(79,71,'2025-09-28 00:39:52','山口帰るぞー！終電逃してタクシー捕まえた🚕💨 レポト、明日も頑張るぞ！','テストのシチュエーションは無しで');
INSERT INTO "tuning_history" VALUES(80,65,'2025-09-28 00:39:54','テスト2完了！問題なさそうです。 #テスト','テストのシチュエーションは無しで');
INSERT INTO "tuning_history" VALUES(81,84,'2025-09-28 00:39:56','買ったばかりのガジェット、初期設定が楽しすぎる！気づけばこんな時間… #ガジェット #初期設定 #沼','テストのシチュエーションは無しで');
INSERT INTO "tuning_history" VALUES(82,83,'2025-09-28 00:39:57','最新ガジェット、ポチった！今回のコレ、マジでヤバそう。届くの楽しみすぎる！🚀','テストのシチュエーションは無しで');
INSERT INTO "tuning_history" VALUES(83,60,'2025-09-28 00:40:02','承知いたしました。ペルソナ設定とシチュエーションに基づき、SNS投稿を作成します。

**レポト（44歳・山口県出身、短髪）：**

テスト2実施中！今日も一日頑張ります💪 #テスト #集中
','テストのシチュエーションは無しで');
INSERT INTO "tuning_history" VALUES(84,72,'2025-09-28 00:40:04','今日も一日お疲れ様でした！山口の地酒、やっぱり最高じゃね🍶 #タクシー #アフター #山口県','テストのシチュエーションは無しで');
INSERT INTO "tuning_history" VALUES(85,65,'2025-09-28 00:50:46','<span style=''color: #888888''>前回の投稿:</span>
<span style=''color: #888888''>テスト2完了！問題なさそうだ。</span>

**新しい投稿:**
テスト2完了！問題なし。報告以上です。','テストのシチュエーションは無しで');
INSERT INTO "tuning_history" VALUES(86,65,'2025-09-28 00:51:06','<span style=''color: #888888''>前回の投稿:</span>
<span style=''color: #888888''>テスト2完了！問題なし。報告以上です。</span>

**新しい投稿:**
問題なし。報告以上です。','テストの表現は消す');
INSERT INTO "tuning_history" VALUES(87,75,'2025-09-28 00:56:37','山口の夜は最高！レポト、今日も一日お疲れ様でした！ #アフター #タクシー #山口 #shinrepoto','テストは削除で');
INSERT INTO "tuning_history" VALUES(88,69,'2025-09-28 00:56:40','よし、集中して良い結果出すぞ！','テストは削除で');
INSERT INTO "tuning_history" VALUES(89,80,'2025-09-28 00:56:42','テスト2実施中。進捗順調です！皆様、ご協力ありがとうございます！ #テスト #システム','テストは削除で');
INSERT INTO "tuning_history" VALUES(90,74,'2025-09-28 00:56:45','よし、やるか。課題クリア目指して頑張ります💪
#チャレンジ','テストは削除で');
INSERT INTO "tuning_history" VALUES(91,81,'2025-09-28 00:56:48','昼同伴、いいですね。美味しい料理と楽しい会話は、午後の仕事への活力になります。僕も頑張ります。#昼同伴 #美味しいご飯 #午後も頑張ろう','テストは削除で');
INSERT INTO "tuning_history" VALUES(92,77,'2025-09-28 00:56:50','山口の夜も更けて。今日も一日お疲れ様でした！ #ガジェット','テストは削除で');
INSERT INTO "tuning_history" VALUES(93,63,'2025-09-28 00:56:53','山口出身のレポト、44歳。短髪でクールな僕は、ふとした瞬間に過去を語り出す。「実は、若い頃バンドやってて…」','テストは削除で');
INSERT INTO "tuning_history" VALUES(94,71,'2025-09-28 00:56:56','山口に帰るぞー！終電逃してタクシー捕まえた。レポト、明日も頑張るぞ！','テストは削除で');
INSERT INTO "tuning_history" VALUES(95,84,'2025-09-28 00:56:58','よし、終わらせるか…。買ったばかりのガジェット、初期設定…終わらないな、これ。#ガジェット #初期設定 #沼','テストは削除で');
INSERT INTO "tuning_history" VALUES(96,83,'2025-09-28 00:57:01','最新ガジェット、ポチった！今回のコレ、マジでヤバそうだ。届くのが楽しみで仕方ない！🚀','テストは削除で');
INSERT INTO "tuning_history" VALUES(97,70,'2025-09-28 00:57:04','二日酔い…最悪の目覚め。テキーラ、もう飲まない！今日一日どう乗り切ろうか… #二日酔い #反省 #テキーラ','テストは削除で');
INSERT INTO "tuning_history" VALUES(98,64,'2025-09-28 00:57:07','うっ…頭痛い…。テキーラ、もう飲まない…。二日酔い確定、今日一日寝込みます。 #二日酔い #テキーラ #反省','テストは削除で');
INSERT INTO "tuning_history" VALUES(99,66,'2025-09-28 00:57:09','山口県出身44歳短髪レポトです！昼から焼き肉最高！🍖🍺 #焼き肉 #昼飲み #山口県','テストは削除で');
INSERT INTO "tuning_history" VALUES(100,79,'2025-09-28 00:57:12','テスト3実施中…集中して取り組むぞ！🔥 #テスト #集中 #shinrepoto','テストは削除で');
INSERT INTO "tuning_history" VALUES(101,68,'2025-09-28 00:57:15','終電逃した…！レポト、山口弁で運転手さんと地元トーク炸裂中。#タクシー #アフター #山口県','テストは削除で');
INSERT INTO "tuning_history" VALUES(102,60,'2025-09-28 00:57:18','承知いたしました。テストのシチュエーションに関する言及を避け、レポトのペルソナを保ちつつ、SNS投稿を改善します。','テストは削除で');
INSERT INTO "tuning_history" VALUES(103,93,'2025-10-01 19:17:37','<span style=''color: #888888''>前回の投稿:</span>
<span style=''color: #888888''>雑音は全てシャットアウト。僕だけの空間で、最高の集中を。</span>

**新しい投稿:**
雑音は逆位相の音波で相殺される。この原理が、僕の集中力を極限まで高める。静寂の中でこそ、思考は深く、そして速くなる。','豆知識を加えて');
INSERT INTO "tuning_history" VALUES(104,102,'2025-10-02 10:39:33','<span style=''color: #888888''>前回の投稿:</span>
<span style=''color: #888888''>〇〇さんのそのお話、何度聞いてもすごーい！私、いつも「さすがですね！」って思っちゃいます♡</span>

**新しい投稿:**
すごーい！〇〇さんのそのお話、私、何度聞いても感動で鳥肌が立っちゃうんです！〇〇さんって、本当に選ばれし人なんですねぇ♡ 素敵すぎます♪','〇〇さんを違う表現で');
INSERT INTO "tuning_history" VALUES(105,102,'2025-10-02 10:40:05','<span style=''color: #888888''>前回の投稿:</span>
<span style=''color: #888888''>すごーい！〇〇さんのそのお話、私、何度聞いても感動で鳥肌が立っちゃうんです！〇〇さんって、本当に選ばれし人なんですねぇ♡ 素敵すぎます♪</span>

**新しい投稿:**
えへへ♡ すごーい！そのお話、私、何度聞いても鳥肌が立っちゃうんですよぉ！本当に選ばれし人なんですねぇ♡ 素敵すぎます♪ 私、すっかり聞き入っちゃいましたよぉ♡','「〇〇さん」の「〇〇」は使わない');
INSERT INTO "tuning_history" VALUES(106,115,'2025-10-02 10:41:08','<span style=''color: #888888''>前回の投稿:</span>
<span style=''color: #888888''>今日もClub Diamondは満席で大盛り上がりでしたね♪ 私の最高の笑顔で、みんなを夢中にさせちゃうんですよ♡ えへへ！</span>

**新しい投稿:**
今日も大盛り上がりでしたね♪ 私の最高の笑顔で、みんなを夢中にさせちゃうんですよ♡ えへへ！ どんなお店の方も、ここにいらしたらきっとファンになっちゃいますよね♪','「Club Diamond」は削除');
INSERT INTO "tuning_history" VALUES(107,57,'2025-10-02 10:43:49','<span style=''color: #888888''>前回の投稿:</span>
<span style=''color: #888888''>💎今日もお仕事頑張るぞー！みんなに会えるの楽しみにしてるね♡ #キャバ嬢 #六本木 #ClubDiamond
</span>

**新しい投稿:**
💎今日もお仕事頑張るぞー！えへへ♡ みんなに会えるのが楽しみなんですよ♡ #キャバ嬢 #六本木','#ClubDiamondを消す');
INSERT INTO "tuning_history" VALUES(108,31,'2025-10-02 23:39:44','<span style=''color: #888888''>前回の投稿:</span>
<span style=''color: #888888''>六本木ヒルズで映画🎬💕  からのClub Venusで乾杯🥂✨  カワサキちゃん指名でね♡
</span>

**新しい投稿:**
六本木ヒルズで映画🎬💕観てきたよ〜！感動して涙が止まらなかったの🥹 このあとは私と乾杯🥂しちゃおっ♡カワサキちゃんが待ってるね！特別な夜を一緒に過ごそ〜♡指名してくれたら嬉しいな♡','からのClub Venusで乾杯→からの乾杯');
INSERT INTO "tuning_history" VALUES(109,31,'2025-10-02 23:40:30','<span style=''color: #888888''>前回の投稿:</span>
<span style=''color: #888888''>六本木ヒルズで映画🎬💕観てきたよ〜！感動して涙が止まらなかったの🥹 このあとは私と乾杯🥂しちゃおっ♡カワサキちゃんが待ってるね！特別な夜を一緒に過ごそ〜♡指名してくれたら嬉しいな♡</span>

**新しい投稿:**
六本木ヒルズで映画🎬💕観てきたよ〜！感動して涙が止まらなかったの🥹 このあとは私と乾杯🥂しちゃおっ♡今日あったこと、あなたにたくさん話したいな♡カワサキちゃんと素敵な夜を過ごそうね♡','カワサキちゃんが待ってるね！特別な夜を一緒に過ごそ〜♡指名してくれたら嬉しいな♡を削除');
INSERT INTO "tuning_history" VALUES(110,31,'2025-10-02 23:41:20','<span style=''color: #888888''>前回の投稿:</span>
<span style=''color: #888888''>六本木ヒルズで映画🎬💕観てきたよ〜！感動して涙が止まらなかったの🥹 このあとは私と乾杯🥂しちゃおっ♡今日あったこと、あなたにたくさん話したいな♡カワサキちゃんと素敵な夜を過ごそうね♡</span>

**新しい投稿:**
六本木ヒルズで映画🎬💕観てきたよ〜！感動して涙が止まらなかったの🥹 このあとは私と乾杯🥂しよっ♡今日あったこと、私に全部聞かせてほしいな♡早く会いたいな〜♡','カワサキちゃんは削除');
CREATE INDEX idx_retweet_schedules_scheduled_at ON retweet_schedules(scheduled_at);
CREATE INDEX idx_retweet_schedules_status ON retweet_schedules(status);
CREATE INDEX idx_retweet_schedules_cast_id ON retweet_schedules(cast_id);
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('cast_sheets_config',1);
INSERT INTO "sqlite_sequence" VALUES('cast_action_sheets',2);
INSERT INTO "sqlite_sequence" VALUES('retweet_schedules',17);
COMMIT;
