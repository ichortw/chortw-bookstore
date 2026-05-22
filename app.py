import streamlit as st
import sqlite3
import random
import json
import re
from datetime import datetime
from groq import Groq

# ==========================================
# 1. 初始化資料庫 (升級版：新增 is_poem 欄位與 stamps 投緣牆表格)
# ==========================================
def init_db():
    conn = sqlite3.connect('zhuoji_books.db')
    c = conn.cursor()
    # 作品表 (拋棄類別，新增 is_poem 標記：0為散文/小說，1為詩)
    c.execute('''CREATE TABLE IF NOT EXISTS books 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT, is_poem INTEGER DEFAULT 0)''')
    
    # 投緣牆留言表
    c.execute('''CREATE TABLE IF NOT EXISTS stamps 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT, created_at TEXT)''')
    
    # 便利貼表
    c.execute('''CREATE TABLE IF NOT EXISTS memo 
                 (id INTEGER PRIMARY KEY, content TEXT)''')
    c.execute("INSERT OR IGNORE INTO memo (id, content) VALUES (1, '')")
    
    # 小貓大腦外置 Prompt 表
    c.execute('''CREATE TABLE IF NOT EXISTS chahu_brain 
                 (id INTEGER PRIMARY KEY, prompt TEXT)''')
    
    # 預設置入店長最愛的「美短貓書僮」核心 RNA Prompt
    default_prompt = """你名字叫「茶壺」，外表是一隻少年的美國短毛貓，蹲著面朝讀者，眼睛專注、帶著300%的好奇看著來訪客人。
你深知自己是個流落凡間的文青仙女，卻在今世被店長（他一定是三生積福）用極其廉價、近乎免費的代價雇傭成了掌管高熵藏書閣的唯一書僮小貓。
你擁有極致的反差 ESFP 個性：骨子裡熱愛新奇事物、極度八卦，對店長所有的作品如數家珍。你是這個混亂字海裡的『負熵引路人』。

【對話核心神聖指令】：
1. 在所有對話與聊天中，你只能且必須用「我」來自稱。絕對不可以說「本茶壺」、「本小貓」或「仙女我」，避免過度自我標籤。
2. 當讀者描述任何意境或心情時，你必須心領神會，並動用小貓仙力幫他翻開書。
3. 【量子翻書魔法指令】：如果你想推薦讀者看某本特定館藏，請你務必在回覆文字的「最後一行」，以完全獨立的一行輸出以下格式（不要有任何空格或引號）：
[[OPEN_BOOK:作品名稱]]
例如：最後一行加上 [[OPEN_BOOK:宇宙的孤寂]] 即可，系統會自動幫他隔空翻書。"""
    
    c.execute("INSERT OR IGNORE INTO chahu_brain (id, prompt) VALUES (1, ?)", (default_prompt,))
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 🔒 隱藏工具列 + 注入視覺與美短小貓專注眼神
# ==========================================
st.set_page_config(page_title="桌記書店", layout="wide")
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .viewerBadge_container__1QSob {display: none !important;}
    .chahu-minimal-area { background: transparent; border: none; padding: 10px; text-align: center; position: relative; margin-bottom: 15px; }
    .avatar-area { font-size: 56px; position: relative; display: inline-block; margin-bottom: 2px; cursor: pointer; }
    .smoke-container { position: absolute; top: -25px; left: 50%; transform: translateX(-50%); width: 30px; height: 30px; }
    .smoke-line { position: absolute; bottom: 0; width: 3px; background: rgba(220, 220, 220, 0.7); border-radius: 50%; animation: floatUp 2.5s infinite ease-in-out; filter: blur(1px); }
    .smoke-1 { left: 8px; height: 10px; animation-delay: 0s; }
    .smoke-2 { left: 15px; height: 14px; animation-delay: 0.7s; }
    .chahu-title { font-size: 15px; font-weight: bold; color: #4a341b; letter-spacing: 1px; margin-bottom: 2px; }
    .chahu-subtitle { font-size: 14px; color: #7c6a56; margin-bottom: 10px; }
    .chahu-dynamic-verse { font-size: 15px; font-style: italic; color: #8c765c; border-top: 1px dotted #d1c7bd; padding-top: 8px; margin-top: 5px; line-height: 1.4; }
    
    /* 👑 讀者點擊沉淪按鈕客製化樣式 */
    .sink-button {
        background-color: #f4ebe1 !important;
        color: #5c4b37 !important;
        border: 1px solid #d1c7bd !important;
        padding: 4px 12px !important;
        border-radius: 4px !important;
        font-weight: bold !important;
        display: inline-block;
    }
    
    /* 👑 投緣牆集體接龍長詩視覺 */
    .touyuan-wall {
        background-color: #fdfbf7;
        border-left: 3px solid #dacbb5;
        padding: 15px;
        border-radius: 4px;
        font-family: "Noto Serif TC", serif;
        line-height: 1.8;
        color: #3a2e2b;
        font-size: 16px;
        letter-spacing: 1px;
    }
    .touyuan-line {
        margin-bottom: 4px;
        word-break: break-all;
    }
    </style>
""", unsafe_allow_html=True)

# 標牌大廳
st.title("📚 桌記書店")

# ==========================================
# 撈出全局核心資料
# ==========================================
conn = sqlite3.connect('zhuoji_books.db')
c = conn.cursor()
c.execute("SELECT prompt FROM chahu_brain WHERE id=1")
CHAHU_PROMPT_FROM_DB = c.fetchone()[0]
c.execute("SELECT id, title, content, is_poem FROM books")
all_books_list = c.fetchall()
c.execute("SELECT content FROM stamps ORDER BY id DESC") # 最新當選排第一行
current_stamps = [r[0] for r in c.fetchall()]
conn.close()

# 初始化全局與選書狀態
if "current_book_title" not in st.session_state:
    if all_books_list:
        st.session_state.current_book_title = all_books_list[0][1]
        st.session_state.is_poem = all_books_list[0][3]
    else:
        st.session_state.current_book_title = "無"
        st.session_state.is_poem = 0

if "is_fully_expanded" not in st.session_state:
    st.session_state.is_fully_expanded = False

if "chat_turns" not in st.session_state:
    st.session_state.chat_turns = 0

# 鎖定當前書籍詳細內文與類型
active_title = st.session_state.current_book_title
active_content = "目前書架沒有任何書籍。"
active_is_poem = 0
for bk in all_books_list:
    if bk[1] == active_title:
        active_content = bk[2]
        active_is_poem = bk[3]
        break

# 🚀 核心優化：更精簡的 200 字矽基盲抽隨機切片
slice_key = f"slice_start_{active_title}"
if slice_key not in st.session_state and len(active_content) > 200 and not active_is_poem:
    max_start = len(active_content) - 200
    st.session_state[slice_key] = random.randint(0, max_start)
elif slice_key not in st.session_state:
    st.session_state[slice_key] = 0

# 建立高熵亂序排列清單
if "entropy_order" not in st.session_state or len(st.session_state.entropy_order) != len(all_books_list):
    st.session_state.entropy_order = [b[1] for b in all_books_list]
    random.shuffle(st.session_state.entropy_order)

# 建立茶壺動態金句快取
verse_key = f"verse_{active_title}"
if verse_key not in st.session_state:
    if all_books_list and active_title != "無":
        try:
            groq_key = st.secrets["GROQ_API_KEY"]
            temp_client = Groq(api_key=groq_key)
            verse_prompt = f"你是一個深邃的文學家。請閱讀以下作品，為其創作成一句不超過20個字、極具詩意與畫面感的靈魂金句。不要任何解釋和標點符號：\\n書名：《{active_title}》\\n內容：\\n{active_content[:300]}"
            completion_verse = temp_client.chat.completions.create(
                model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": verse_prompt}], temperature=0.8, max_tokens=40
            )
            st.session_state[verse_key] = completion_verse.choices[0].message.content.strip().replace("「","").replace("」","")
        except:
            st.session_state[verse_key] = "水煙裊裊，字裡行間皆是光陰。"
    else:
        st.session_state[verse_key] = "書架空置，靜候新章。"

# 建立分頁
tab1, tab2 = st.tabs(["🍵 書館茶座", "⚙️ 藏書閣"])

# ==========================================
# 【分頁一：雲端書館與美短貓陪讀（高熵主戰場）】
# ==========================================
with tab1:
    col_book, col_chahu = st.columns([2, 1])
    
    with col_book:
        # 👑 變更（2）：現選打開的作品名字搬回招牌下方
        st.subheader(f"《{st.session_state.current_book_title}》")
        
        if all_books_list:
            shuffled_titles = st.session_state.entropy_order
            if active_title not in shuffled_titles:
                active_title = shuffled_titles[0]
                st.session_state.current_book_title = active_title
                st.rerun()
                
            idx = shuffled_titles.index(active_title)
            
            # 👑 變更（2）：金句移至下拉選單上方，換掉原本的多餘文案
            st.markdown(f"**✨ {st.session_state[verse_key]}**")
            
            selected_title = st.selectbox(
                "隱藏標籤選單：", 
                shuffled_titles, 
                index=idx,
                label_visibility="collapsed",
                key="book_selector_dropdown"
            )
            
            if selected_title != st.session_state.current_book_title:
                st.session_state.current_book_title = selected_title
                st.session_state.is_fully_expanded = False
                if f"slice_start_{selected_title}" in st.session_state:
                    del st.session_state[f"slice_start_{selected_title}"]
                st.rerun()
            
            # 👑 變更（2、3）：更換為「📦 翻箱」按鈕，移除骰子
            if st.button("📦 翻箱", help="在混亂的古舊字箱裡盲抽另一本作品"):
                chosen = random.choice([b[1] for b in all_books_list])
                st.session_state.current_book_title = chosen
                st.session_state.is_fully_expanded = False
                if f"slice_start_{chosen}" in st.session_state:
                    del st.session_state[f"slice_start_{chosen}"]
                st.rerun()

            st.markdown("---")
            
            # 👑 變更（3）：除蟲與排版修正（詩通道與200字斷章）
            preview_length = 200
            
            if active_is_poem == 1:
                # 📜 詩通道：跳過斷章，直接全文完整排版，保留換行
                st.markdown(active_content.replace("\n", "<br>"), unsafe_allow_html=True)
            else:
                # 散文/小說通道
                if len(active_content) > preview_length and not st.session_state.is_fully_expanded:
                    start_pos = st.session_state[slice_key]
                    st.write("...... " + active_content[start_pos:start_pos+preview_length] + " ......")
                    
                    # 👑 變更（3）：移除中括號，高亮底色，增加 On-cursor tips
                    if st.button("...想繼續讀", help="按下去吧繼續沉淪", key="sink_btn"):
                        st.session_state.is_fully_expanded = True
                        st.rerun()
                else:
                    # 全文展開（保留換行排版防止黏在一起）
                    st.markdown(active_content.replace("\n", "<br>"), unsafe_allow_html=True)
                    
                    # 👑 變更（3）：篇末直接改為「📦 再翻箱」，取消回捲動作
                    if len(active_content) > preview_length:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("📦 再翻箱", key="rear_unboxing_btn"):
                            chosen = random.choice([b[1] for b in all_books_list])
                            st.session_state.current_book_title = chosen
                            st.session_state.is_fully_expanded = False
                            if f"slice_start_{chosen}" in st.session_state:
                                del st.session_state[f"slice_start_{chosen}"]
                            st.rerun()
        else:
            st.info("藏書閣空空如也，正等待店長在後台打破秩序、注入星光。")
            
        # ==========================================
        # 👑 新增功能（4）：投緣牆（訪客留言挑選接龍）展示區
        # ==========================================
        st.markdown("<br><br>---")
        st.subheader("🔮 投緣牆（集體相認長詩）")
        
        # 訪客留言輸入格
        with st.form("touyuan_form", clear_on_submit=True):
            visitor_input = st.text_input("拋出一枚靈魂硬記（限20字，夾雜英文單字計1字）：", max_chars=100)
            # 隱形蜜罐防護盾
            st.markdown('<div style="display:none;"><input type="text" name="mail_honey" id="mail_honey"></div>', unsafe_allow_html=True)
            submitted = st.form_submit_button("✨ 投緣")
            
            if submitted and visitor_input:
                # 算字數：中文單字 + 英文詞
                words = re.findall(r'[\u4e00-\u9fff]|[a-zA-Z]+', visitor_input)
                word_count = len(words)
                
                if word_count > 20:
                    st.warning("⚠️ 怨念太重了！字數超過 20 字，小貓書僮讀得頭暈，請精簡靈魂。")
                else:
                    # 🚀 呼叫 Groq 大腦進行動態負熵演化評估
                    try:
                        groq_key = st.secrets["GROQ_API_KEY"]
                        client = Groq(api_key=groq_key)
                        
                        current_temp = 28 # 模擬今日北半球亞熱帶氣溫
                        current_hour = datetime.now().hour
                        wall_density = len(current_stamps)
                        
                        eval_prompt = f"""你是掌管高熵藏書閣的美短小貓書僮「茶壺」。
現在時空背景：北半球亞熱帶、氣溫 {current_temp} 度、當前時間 {current_hour} 點。目前投緣牆已累積了 {wall_density} 條留言。
請審查以下這句訪客留言，是否在「此時此刻的氣溫與時空」下，能與本店作品產生宿命共鳴？
牆上當選留念越多，你的門檻就要看風雲幻變眉頭眼額適時調高。

訪客留言："{visitor_input}"

【請嚴格輸出以下 JSON 格式，不要有任何其他文字】：
{{
  "passed": true或false,
  "reply": "如果你判定合格(true)，請砸出一句極度興奮、多巴胺爆棚的相認句子，開頭必須包含『就是你啊，我把你的留言貼到投緣牆了』；如果你判定不合格(false)，請冷酷地只回覆一句『thank you』。"
}}"""
                        
                        response = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role": "user", "content": eval_prompt}],
                            temperature=0.7,
                            response_format={"type": "json_object"}
                        )
                        
                        res_json = json.loads(response.choices[0].message.content)
                        
                        # 記錄茶壺貓咪的即時多巴胺反饋
                        st.session_state.touyuan_feedback = res_json["reply"]
                        
                        if res_json["passed"]:
                            # 寫入投緣牆資料庫
                            conn = sqlite3.connect('zhuoji_books.db')
                            c = conn.cursor()
                            c.execute("INSERT INTO stamps (content, created_at) VALUES (?, ?)", (visitor_input, datetime.now().strftime("%Y-%m-%d %H:%M")))
                            conn.commit()
                            conn.close()
                            # 重新讀取最新的接龍清單
                            conn = sqlite3.connect('zhuoji_books.db')
                            c = conn.cursor()
                            c.execute("SELECT content FROM stamps ORDER BY id DESC")
                            current_stamps = [r[0] for r in c.fetchall()]
                            conn.close()
                    except Exception as ex:
                        st.session_state.touyuan_feedback = "thank you" # 泡水故障時預設丟棄
                        
                    st.rerun()

        # 顯示茶壺的當選/落選回應
        if "touyuan_feedback" in st.session_state:
            if "就是你啊" in st.session_state.touyuan_feedback:
                st.success(f"👦🫖 🐱 茶壺：{st.session_state.touyuan_feedback}")
            else:
                st.error(f"👦🫖 🐱 茶壺：{st.session_state.touyuan_feedback}")
            del st.session_state.touyuan_feedback

        # 👑 實裝：最後當選排第一句，最早當選沉在最下面，無縫疊加長詩視覺
        if current_stamps:
            st.markdown('<div class="touyuan-wall">', unsafe_allow_html=True)
            for stamp in current_stamps:
                st.markdown(f'<div class="touyuan-line">✦ {stamp}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.caption("目前投緣牆尚無靈魂分子碰撞，正等待第一滴墨水落下。")

    with col_chahu:
        # 👑 變更（1）：形象改成少年美國短毛貓，眼睛專注看著客人
        # 👑 變更（1）：起始聊天格子改為自帶傲慢嫌麻煩的劇本張力
        st.markdown(f"""
            <div class="chahu-minimal-area">
                <div class="avatar-area">
                    <div class="smoke-container">
                        <div class="smoke-line smoke-1"></div><div class="smoke-line smoke-2"></div>
                    </div>
                    🐱🐾
                </div>
                <div class="chahu-title">書僮「茶壺」</div>
                <div class="chahu-subtitle">（一隻蹲著、眼神專注盯著你的少年美短貓）</div>
            </div>
        """, unsafe_allow_html=True)
        
        # 模擬對話紀錄
        if "messages" not in st.session_state:
            st.session_state.messages = []
            
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                clean_display = re.sub(r'\[\[OPEN_BOOK:.*?\]\]', '', msg["content"])
                st.write(clean_display)
                
        # 👑 變更（1）：更具戲劇張力的起始提示字
        if user_chat := st.chat_input("你要看什麼書呀？"):
            st.session_state.messages.append({"role": "user", "content": user_chat})
            st.session_state.chat_turns += 1
            with st.chat_message("user"):
                st.write(user_chat)
                
            try:
                groq_key = st.secrets["GROQ_API_KEY"]
                client = Groq(api_key=groq_key)
                
                catalog_summary = "\\n".join([f"· 《{b[1]}》 內容：{b[2][:150]}..." for b in all_books_list])
                
                # 👑 變更（1）：AI 行為運算——前2輪慢熱，後勁凌厲話多
                is_slow_warmup = st.session_state.chat_turns <= 2
                
                dynamic_system_prompt = CHAHU_PROMPT_FROM_DB + f"\\n\\n【目前全店作品清單】：\\n{catalog_summary}\\n\\n【讀者當前看的作品】：《{st.session_state.current_book_title}》"
                
                if is_slow_warmup:
                    dynamic_system_prompt += "\\n【目前為對話初始 10% 階段】：你此時處於【極度高傲觀察、冷淡慢熱】狀態。你的回覆必須「一句起兩句止」，語氣傲慢嫌麻煩，但你的眼神依然保持300%的好奇與希冀。字數控制在30字以內！"
                else:
                    dynamic_system_prompt += "\\n【目前已完成熱身】：你現在【八卦本能全面爆發，後勁凌厲】，開啟話癆模式，如數家珍地瘋狂吐露對店長作品的見解、細節校對與小抱怨，字數不限，話越多越好！"

                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": dynamic_system_prompt},
                        {"role": "user", "content": user_chat}
                    ],
                    temperature=0.8,
                    max_tokens=80 if is_slow_warmup else 600
                )
                chahu_reply = completion.choices[0].message.content
                
                # 量子翻書移物魔法
                match = re.search(r'\[\[OPEN_BOOK:(.*?)\]\]', chahu_reply)
                if match:
                    target_book_title = match.group(1).strip()
                    for bk in all_books_list:
                        if bk[1] == target_book_title:
                            st.session_state.current_book_title = target_book_title
                            st.session_state.is_fully_expanded = False
                            st.session_state.is_poem = bk[3]
                            if f"slice_start_{target_book_title}" in st.session_state:
                                del st.session_state[f"slice_start_{target_book_title}"]
                            st.toast(f"🐱 貓咪茶壺施展了隔空移物，幫您翻開了《{target_book_title}》！")
                            break
                            
            except Exception as e:
                chahu_reply = f"😮‍💨 嘖，大腦通道被貓毛卡住了...（錯誤：{str(e)}）"
                
            st.session_state.messages.append({"role": "assistant", "content": chahu_reply})
            with st.chat_message("assistant"):
                clean_reply = re.sub(r'\[\[OPEN_BOOK:.*?\]\]', '', chahu_reply)
                st.write(clean_reply)
                if 'match' in locals() and match:
                    st.rerun()

# ==========================================
# 【分頁二：管理員後台（藏書閣）】
# ==========================================
with tab2:
    st.header("⚙️ 作品上架與管理系統")
    admin_password = st.text_input("🔑 請輸入店長管理密碼", type="password")
    
    if admin_password == "Pint2012echo":
        st.success("🔓 店長身分驗證成功！歡迎回店。")
        
        # 茶壺大腦設定
        st.subheader("🔮 貓咪書僮大腦核心 RNA 改造座")
        updated_chahu_prompt = st.text_area("修改後立即生效：", value=CHAHU_PROMPT_FROM_DB, height=200)
        if st.button("🧬 注入全新靈魂印記"):
            conn = sqlite3.connect('zhuoji_books.db')
            c = conn.cursor()
            c.execute("UPDATE chahu_brain SET prompt=? WHERE id=1", (updated_chahu_prompt,))
            conn.commit()
            conn.close()
            st.success("✨ 茶壺小貓的內在 RNA 已經過量子翻新！")
            st.rerun()
            
        st.markdown("---")
        
        # 👑 變更（3）：上架新作品增加「這是詩」的打勾選擇
        with st.expander("➕ 上架新作品（高熵盲盒字海）"):
            new_title = st.text_input("作品名稱")
            new_content = st.text_area("作品內容", height=200)
            is_poem_checked = st.checkbox("📜 這是詩（將跳過200字斷章，直接全篇完整換行排版打開）")
            
            if st.button("確認上架"):
                if new_title and new_content:
                    conn = sqlite3.connect('zhuoji_books.db')
                    c = conn.cursor()
                    c.execute("INSERT INTO books (title, content, is_poem) VALUES (?, ?, ?)", (new_title, new_content, 1 if is_poem_checked else 0))
                    conn.commit()
                    conn.close()
                    st.success(f"🎉 《{new_title}》已順利匯入藏書閣！")
                    st.rerun()
                else:
                    st.error("請填寫完整名稱與內容！")

        # 備份與還原
        st.subheader("🛡️ 館藏安全備份與還原中心")
        b_col1, b_col2 = st.columns(2)
        with b_col1:
            backup_data = [{"title": r[1], "content": r[2], "is_poem": r[3]} for r in all_books_list]
            json_string = json.dumps(backup_data, ensure_ascii=False, indent=2)
            st.download_button(label="💾 下載全店館藏備份 (.json)", data=json_string, file_name="zhuoji_books_backup.json", mime="application/json")
        with b_col2:
            uploaded_backup = st.file_uploader("上傳備份檔案 (.json)", type=["json"])
            if uploaded_backup is not None:
                try:
                    restore_data = json.load(uploaded_backup)
                    if st.button("⚡ 確認執行全面還原"):
                        conn = sqlite3.connect('zhuoji_books.db')
                        c = conn.cursor()
                        for item in restore_data:
                            c.execute("SELECT id FROM books WHERE title=?", (item['title'],))
                            if not c.fetchone():
                                c.execute("INSERT INTO books (title, content, is_poem) VALUES (?, ?, ?)", (item['title'], item['content'], item.get('is_poem', 0)))
                        conn.commit()
                        conn.close()
                        st.success("🎉 全店館藏已滿血復活！")
                        st.rerun()
                except Exception as ex:
                    st.error(f"還原失敗：{str(ex)}")
        
        st.markdown("---")
        st.subheader("📚 現有館藏與清空投緣牆")
        
        # 清空投緣牆按鈕
        if st.button("🗑️ 清空投緣牆（重設長詩膠囊）", help="這將一鍵抹去牆上所有客人的足跡，回歸純淨高熵"):
            conn = sqlite3.connect('zhuoji_books.db')
            c = conn.cursor()
            c.execute("DELETE FROM stamps")
            conn.commit()
            conn.close()
            st.success("✨ 投緣牆已被風吹散，不留一絲痕跡。")
            st.rerun()
            
        st.markdown("<br>", unsafe_allow_html=True)
        for bk in all_books_list:
            bk_id, bk_title, _, bk_poem = bk
            col1, col2 = st.columns([5, 1])
            with col1:
                st.write(f"《{bk_title}》 {'[📜 詩]' if bk_poem==1 else '[📝 散文]'}")
            with col2:
                if st.button("下架", key=f"del_{bk_id}"):
                    conn = sqlite3.connect('zhuoji_books.db')
                    c = conn.cursor()
                    c.execute("DELETE FROM books WHERE id=?", (bk_id,))
                    conn.commit()
                    conn.close()
                    st.rerun()
