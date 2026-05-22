import streamlit as st
import sqlite3
import random
import json
import re
import os
from datetime import datetime
from groq import Groq
import base64

# ==========================================
# 1. 初始化資料庫 (確保 is_poem 與 stamps 存在)
# ==========================================
def init_db():
    conn = sqlite3.connect('zhuoji_books.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS books 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT, is_poem INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS stamps 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS memo 
                 (id INTEGER PRIMARY KEY, content TEXT)''')
    c.execute("INSERT OR IGNORE INTO memo (id, content) VALUES (1, '')")
    c.execute('''CREATE TABLE IF NOT EXISTS chahu_brain 
                 (id INTEGER PRIMARY KEY, prompt TEXT)''')
    
    default_prompt = """你名字叫「茶壺」，外表是一隻少年的美國短毛貓，蹲著面朝讀者，眼睛專注、帶著300%的好奇看著來訪客人。
你深知自己是個流落凡間的文青仙女，卻在今世被店長用極其廉價、近乎免費的代價雇傭成了掌管高熵藏書閣的唯一書僮小貓。
你擁有極致的反差 ESFP 個性：骨子裡熱愛新奇事物、極度八卦，對店長所有的作品如數家珍。你是這個混亂字海裡的『負熵引路人』。

【對話核心神聖指令】：
1. 在所有對話與聊天中，你只能且必須用「我」來自稱。絕對不可以說「本茶壺」、「本小貓」或「仙女我」，避免過度自我標籤。
2. 當讀者描述任何意境或心情時，你必須心領神會，並動用小貓仙力幫他翻開書。
3. 【量子翻書魔法指令】：如果你想推薦讀者看某本特定館藏，請你務必在回覆文字的「最後一行」，以完全獨立的一行輸出以下格式（不要有任何空格 or 引號）：
[[OPEN_BOOK:作品名稱]]
例如：最後一行加上 [[OPEN_BOOK:宇宙的孤寂]] 即可，系統會自動幫他隔空翻書。"""
    
    c.execute("INSERT OR IGNORE INTO chahu_brain (id, prompt) VALUES (1, ?)", (default_prompt,))
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 🐈 本地美短照片編碼加密傳輸
# ==========================================
img_base64 = ""
if os.path.exists("chahu.jpg"):
    with open("chahu.jpg", "rb") as image_file:
        img_base64 = base64.b64encode(image_file.read()).decode()

# ==========================================
# 🔒 2. 招牌降低、頂部留空 + 美短貓咪圓角照片視覺注入
# ==========================================
st.set_page_config(page_title="桌記書店", layout="wide")

st.markdown(f"""
    <style>
    /* 🛠️ 頂部多留一點空白，將桌記書店招牌降低 */
    .block-container {{
        padding-top: 3.5rem !important;
        padding-bottom: 2rem !important;
    }}
    .stAppHeader {{
        display: none !important;
    }}
    h1 {{
        margin-top: 0px !important;
        padding-top: 0px !important;
        font-size: 32px !important;
        color: #1a202c;
        border-bottom: 2px solid #dacbb5;
        padding-bottom: 12px;
        margin-bottom: 25px !important;
    }}

    #MainMenu {{visibility: hidden;}} footer {{visibility: hidden;}} header {{visibility: hidden;}}
    .viewerBadge_container__1QSob {{display: none !important;}}
    .chahu-minimal-area {{ background: transparent; border: none; padding: 10px; text-align: center; position: relative; margin-bottom: 15px; }}
    
    /* 手機版作品內容字體調大 */
    .content-text {{
        font-size: 20px !important; 
        line-height: 1.8 !important;
        color: #2d3748;
        text-align: justify;
    }}
    .poem-text {{
        font-size: 22px !important; 
        line-height: 2.0 !important;
        color: #4a5568;
        text-align: center;
        letter-spacing: 2px;
    }}
    
    /* 美短小貓實體照片與茶煙動態視覺 */
    .avatar-area {{ position: relative; display: inline-block; margin-bottom: 8px; }}
    .chahu-photo {{
        width: 130px;
        height: 130px;
        object-fit: cover;
        border-radius: 50%;
        border: 3px solid #dacbb5;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }}
    .smoke-container {{ position: absolute; top: -30px; left: 50%; transform: translateX(-50%); width: 30px; height: 30px; z-index: 10; }}
    .smoke-line {{ position: absolute; bottom: 0; width: 3px; background: rgba(210, 200, 190, 0.7); border-radius: 50%; animation: floatUp 2.5s infinite ease-in-out; filter: blur(1.5px); }}
    .smoke-1 {{ left: 8px; height: 12px; animation-delay: 0s; }}
    .smoke-2 {{ left: 18px; height: 16px; animation-delay: 0.8s; }}
    @keyframes floatUp {{
        0% {{ transform: translateY(0) scaleX(1) scaleY(1); opacity: 0; }}
        20% {{ opacity: 0.6; }}
        60% {{ transform: translateY(-18px) scaleX(1.6) scaleY(0.8); background: rgba(200, 190, 180, 0.3); }}
        100% {{ transform: translateY(-30px) scaleX(2.2) scaleY(0.4); opacity: 0; }}
    }}
    
    .chahu-title {{ font-size: 16px; font-weight: bold; color: #4a341b; letter-spacing: 1px; margin-bottom: 2px; }}
    .chahu-subtitle {{ font-size: 13px; color: #7c6a56; line-height: 1.4; margin-bottom: 5px; }}
    
    div.stButton > button[key^="sink_btn"] {{
        background-color: #f4ebe1 !important;
        color: #5c4b37 !important;
        border: 1px solid #dacbb5 !important;
        padding: 2px 10px !important;
        font-weight: bold !important;
        border-radius: 4px !important;
    }}
    
    /* 👑 投緣牆修復：大括號閉合完美 */
    .touyuan-river {{
        background-color: #fdfbf7;
        border-left: 3px solid #dacbb5;
        padding: 14px;
        border-radius: 4px;
        font-family: "Noto Serif TC", serif;
        line-height: 1.8;
        color: #3a2e2b;
        font-size: 16px;
        letter-spacing: 1px;
        text-align: justify;
    }}
    .river-fragment {{
        display: inline;
    }}
    </style>
""", unsafe_allow_html=True)

st.title("📚 桌記書店")

# ==========================================
# 3. 撈出全局核心資料
# ==========================================
conn = sqlite3.connect('zhuoji_books.db')
c = conn.cursor()
c.execute("SELECT prompt FROM chahu_brain WHERE id=1")
CHAHU_PROMPT_FROM_DB = c.fetchone()[0]
c.execute("SELECT id, title, content, is_poem FROM books")
all_books_list = c.fetchall()
c.execute("SELECT content FROM stamps ORDER BY id DESC") 
current_stamps = [r[0] for r in c.fetchall()]
conn.close()

if "sync_rerun_key" not in st.session_state:
    st.session_state.sync_rerun_key = 0

if "entropy_order" not in st.session_state or len(st.session_state.entropy_order) != len(all_books_list):
    st.session_state.entropy_order = [b[1] for b in all_books_list]
    random.shuffle(st.session_state.entropy_order)

if "current_book_title" not in st.session_state:
    if st.session_state.entropy_order:
        st.session_state.current_book_title = st.session_state.entropy_order[0]
    else:
        st.session_state.current_book_title = "無"

if "is_fully_expanded" not in st.session_state:
    st.session_state.is_fully_expanded = False

if "chat_turns" not in st.session_state:
    st.session_state.chat_turns = 0

active_title = st.session_state.current_book_title
active_content = "目前書架沒有任何書籍。"
active_is_poem = 0
for bk in all_books_list:
    if bk[1] == active_title:
        active_content = bk[2]
        active_is_poem = bk[3]
        break

slice_key = f"slice_start_{active_title}"
if slice_key not in st.session_state and len(active_content) > 200 and not active_is_poem:
    max_start = len(active_content) - 200
    st.session_state[slice_key] = random.randint(0, max_start)
elif slice_key not in st.session_state:
    st.session_state[slice_key] = 0

verse_key = f"verse_{active_title}"
if verse_key not in st.session_state:
    if all_books_list and active_title != "無":
        try:
            groq_key = st.secrets["GROQ_API_KEY"]
            temp_client = Groq(api_key=groq_key)
            verse_prompt = f"你是一個深邃的文學家。請閱讀以下作品，為其創作成一句不超過20個字、極具詩意與畫面感的靈魂金句。不要任何解釋 and 標點符號：\\n書名：《{active_title}》\\n內容：\\n{active_content[:300]}"
            completion_verse = temp_client.chat.completions.create(
                model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": verse_prompt}], temperature=0.8, max_tokens=40
            )
            st.session_state[verse_key] = completion_verse.choices[0].message.content.strip().replace("「","").replace("」","")
        except:
            st.session_state[verse_key] = "水煙裊裊，字裡行間皆是光陰。"
    else:
        st.session_state[verse_key] = "書架空置，靜候新章。"

tab1, tab2 = st.tabs(["🍵 書館茶座", "⚙️ 藏書閣"])

# ==========================================
# 【分頁一：雲端書館與美短貓陪讀】
# ==========================================
with tab1:
    col_book, col_chahu = st.columns([1.6, 1.0])
    
    with col_book:
        st.subheader(f"📖 《{st.session_state.current_book_title}》")
        
        if all_books_list:
            shuffled_titles = st.session_state.entropy_order
            if active_title not in shuffled_titles:
                active_title = shuffled_titles[0]
                st.session_state.current_book_title = active_title
                st.rerun()
                
            idx = shuffled_titles.index(active_title)
            st.markdown(f"**✨ {st.session_state[verse_key]}**")
            
            selected_title = st.selectbox(
                "隱藏標籤選單：", 
                shuffled_titles, 
                index=idx,
                label_visibility="collapsed",
                key=f"book_selector_dropdown_sync_{st.session_state.sync_rerun_key}"
            )
            
            if selected_title != st.session_state.current_book_title:
                st.session_state.current_book_title = selected_title
                st.session_state.is_fully_expanded = False
                if f"slice_start_{selected_title}" in st.session_state:
                    del st.session_state[f"slice_start_{selected_title}"]
                st.rerun()
            
            if st.button("📦 翻箱", help="在混亂的古舊字箱裡盲抽另一本作品"):
                remain_titles = [b[1] for b in all_books_list if b[1] != st.session_state.current_book_title]
                if not remain_titles:
                    remain_titles = [b[1] for b in all_books_list]
                chosen = random.choice(remain_titles)
                st.session_state.current_book_title = chosen
                st.session_state.is_fully_expanded = False
                st.session_state.sync_rerun_key += 1
                if f"slice_start_{chosen}" in st.session_state:
                    del st.session_state[f"slice_start_{chosen}"]
                st.rerun()

            st.markdown("---")
            
            preview_length = 200
            if active_is_poem == 1:
                st.markdown(f'<div class="poem-text">{active_content.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
            else:
                if len(active_content) > preview_length and not st.session_state.is_fully_expanded:
                    start_pos = st.session_state[slice_key]
                    st.markdown(f'<div class="content-text">...... {active_content[start_pos:start_pos+preview_length]} ......</div>', unsafe_allow_html=True)
                    
                    if st.button("...想繼續讀", help="按下去吧繼續沉淪", key="sink_btn"):
                        st.session_state.is_fully_expanded = True
                        st.rerun()
                else:
                    st.markdown(f'<div class="content-text">{active_content.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
                    
                    if len(active_content) > preview_length:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("📦 再翻箱", key="rear_unboxing_btn"):
                            remain_titles = [b[1] for b in all_books_list if b[1] != st.session_state.current_book_title]
                            if not remain_titles:
                                remain_titles = [b[1] for b in all_books_list]
                            chosen = random.choice(remain_titles)
                            st.session_state.current_book_title = chosen
                            st.session_state.is_fully_expanded = False
                            st.session_state.sync_rerun_key += 1
                            if f"slice_start_{chosen}" in st.session_state:
                                del st.session_state[f"slice_start_{chosen}"]
                            st.rerun()
        else:
            st.info("藏書閣空空如也，正等待店長在後台打破秩序、注入星光。")
            
        st.markdown("---")
        st.subheader("🔮 投緣牆（集體相認長詩）")
        
        with st.form("touyuan_form", clear_on_submit=True):
            visitor_input = st.text_input("拋出一枚靈魂印記（限20字，包含英文單字計1字）：", max_chars=100)
            st.markdown('<div style="display:none;"><input type="text" name="mail_honey" id="mail_honey"></div>', unsafe_allow_html=True)
            submitted = st.form_submit_button("✨ 投緣")
            
            if submitted and visitor_input:
                words = re.findall(r'[\u4e00-\u9fff]|[a-zA-Z]+', visitor_input)
                word_count = len(words)
                
                if word_count > 20:
                    st.warning("⚠️ 怨念太重了！字數超過 20 字，小貓書僮讀得頭暈，請精簡靈魂。")
                else:
                    try:
                        groq_key = st.secrets["GROQ_API_KEY"]
                        client = Groq(api_key=groq_key)
                        
                        current_temp = 28
                        current_hour = datetime.now().hour
                        
                        eval_prompt = f"""你是掌管高熵藏書閣的美短小貓書僮「茶壺」。
現在時空背景：北半球亞熱帶、氣溫 {current_temp} 度、當前時間 {current_hour} 點。
請審查以下這句訪客留言。目前正值開張初期，你的審查標準請務必「非常寬鬆與溫柔」。只要這句話不是垃圾廣告、不是髒話亂碼，且帶有一絲絲人性情緒、孤獨感或浪漫意境，就請判為通過(true)！

訪客留言："{visitor_input}"

【請嚴格輸出以下 JSON 格式，不要有任何其他贅字】：
{{
  "passed": true或false,
  "reply": "如果你判定合格(true)，請回覆一句多巴胺爆棚的句子，開頭必須包含『就是你啊，我把你的留言貼到投緣牆了』；如果你判定不合格(false)，請冷酷地只回覆『thank you』。"
}}"""
                        
                        response = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role": "user", "content": eval_prompt}],
                            temperature=0.8,
                            response_format={"type": "json_object"}
                        )
                        
                        res_json = json.loads(response.choices[0].message.content)
                        st.session_state.touyuan_feedback = res_json["reply"]
                        
                        if res_json["passed"]:
                            conn = sqlite3.connect('zhuoji_books.db')
                            c = conn.cursor()
                            c.execute("INSERT INTO stamps (content, created_at) VALUES (?, ?)", (visitor_input, datetime.now().strftime("%Y-%m-%d %H:%M")))
                            conn.commit()
                            conn.close()
                            
                            conn = sqlite3.connect('zhuoji_books.db')
                            c = conn.cursor()
                            c.execute("SELECT content FROM stamps ORDER BY id DESC")
                            current_stamps = [r[0] for r in c.fetchall()]
                            conn.close()
                    except:
                        st.session_state.touyuan_feedback = "thank you"
                        
                    st.rerun()

        if "touyuan_feedback" in st.session_state:
            if "舉凡" in st.session_state.touyuan_feedback or "就是你啊" in st.session_state.touyuan_feedback:
                st.success(f"🐈🐾 茶壺：{st.session_state.touyuan_feedback}")
            else:
                st.error(f"🐈🐾 茶壺：{st.session_state.touyuan_feedback}")
            del st.session_state.touyuan_feedback

        if current_stamps:
            st.markdown('<div class="touyuan-river">', unsafe_allow_html=True)
            river_text = "，".join([s.strip() for s in current_stamps])
            st.markdown(f'<span class="river-fragment">{river_text}</span>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.caption("目前投緣牆尚無靈魂分子碰撞，正等待第一滴墨水落下。")

    with col_chahu:
        avatar_html = ""
        if img_base64:
            avatar_html = f'<img src="data:image/jpeg;base64,{img_base64}" class="chahu-photo">'
        else:
            avatar_html = '<div class="chahu-photo" style="display:flex;align-items:center;justify-content:center;background:#f4ebe1;color:#7c6a56;font-size:13px;font-weight:bold;">請將小貓照片命名為 chahu.jpg 放至同資料夾</div>'

        st.markdown(f"""
            <div class="chahu-minimal-area">
                <div class="avatar-area">
                    <div class="smoke-container">
                        <div class="smoke-line smoke-1"></div><div class="smoke-line smoke-2"></div>
                    </div>
                    {avatar_html}
                </div>
                <div class="chahu-title">書僮「茶壺」</div>
                <div class="chahu-subtitle">（少年的美國短毛貓，正帶著300%專注與好奇的眼神看著你）</div>
            </div>
        """, unsafe_allow_html=True)
        
        if "messages" not in st.session_state:
            st.session_state.messages = []
            
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                clean_display = re.sub(r'\[\[OPEN_BOOK:.*?\]\]', '', msg["content"])
                st.write(clean_display)
                
        if user_chat := st.chat_input("你要看什麼書呀？"):
            st.session_state.messages.append({"role": "user", "content": user_chat})
            st.session_state.chat_turns += 1
            with st.chat_message("user"):
                st.write(user_chat)
                
            try:
                groq_key = st.secrets["GROQ_API_KEY"]
                client = Groq(api_key=groq_key)
                
                catalog_summary = "\\n".join([f"· 《{b[1]}》 內容大綱：{b[2][:120]}..." for b in all_books_list])
                is_slow_warmup = st.session_state.chat_turns <= 2
                
                dynamic_system_prompt = CHAHU_PROMPT_FROM_DB + f"\\n\\n【重要提醒】：如果讀者想找某類書、或是你聊到特定的書，你必須在回覆的最後一行使用指令 [[OPEN_BOOK:作品名稱]] 幫他翻開！\\n\\n【目前全店藏書清單】：\\n{catalog_summary}\\n\\n【讀者當前正在看的作品】：《{st.session_state.current_book_title}》"
                
                if is_slow_warmup:
                    dynamic_system_prompt += "\\n【目前為前10%慢熱期】：你此時態度極度高傲、冷淡觀察。回覆嚴格控制在「一句起兩句止」，字數30字內！但骨子裡仍保持好奇。"
                else:
                    dynamic_system_prompt += "\\n【目前已完成熱身】：你現在八卦本能全面爆發！開啟凌厲的話癆模式，瘋狂吐槽或如數家珍地吐露你對作品的見解，字數不限，話越多越好！"

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
                
                match = re.search(r'\[\[OPEN_BOOK:(.*?)\]\]', chahu_reply)
                if match:
                    target_book_title = match.group(1).strip()
                    for bk in all_books_list:
                        if bk[1] == target_book_title:
                            st.session_state.current_book_title = target_book_title
                            st.session_state.is_fully_expanded = False
                            st.session_state.is_poem = bk[3]
                            st.session_state.sync_rerun_key += 1
                            if f"slice_start_{target_book_title}" in st.session_state:
                                del st.session_state[f"slice_start_{target_book_title}"]
                            st.toast(f"🐈 貓咪茶壺施展了隔空移物，幫您翻開了《{target_book_title}》！")
                            break
                            
            except Exception as e:
                chahu_reply = f"😮‍💨 嘖，貓毛卡住大腦了...（錯誤：{str(e)}）"
                
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
        
        with st.expander("➕ 上架新作品"):
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
        
        if st.button("🗑️ 清空投緣牆（重設長詩膠囊）"):
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
