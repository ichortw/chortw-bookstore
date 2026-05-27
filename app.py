# -*- coding: utf-8 -*-
import streamlit as st
import sqlite3
import random
import json
import re
import os
import gc
import requests
from datetime import datetime
import google.generativeai as genai
import base64

# ==========================================
# 🏠 雲端保險箱配置：全面指定 Render 永久硬碟路徑
# ==========================================
DB_PATH = '/data/zhuoji_books.db'

# ==========================================
# ⚡ 火箭超速護盾：初始化資料庫 (開機只跑一次，徹底消滅冷啟動空白卡頓)
# ==========================================
@st.cache_resource
def init_db_once():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS books 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT, is_poem INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS stamps 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS memo 
                 (id INTEGER PRIMARY KEY, content TEXT)''')
    c.execute("INSERT OR IGNORE INTO memo (id, content) VALUES (1, '')")
    
    # 🧠 大腦資料表升級：確保具備儲存「當前使用大腦」的欄位
    c.execute('''CREATE TABLE IF NOT EXISTS chahu_brain 
                 (id INTEGER PRIMARY KEY, prompt TEXT, active_brain TEXT DEFAULT 'Google Gemini')''')
    
    default_prompt = """你名字叫「茶壺」，外表是一隻少年的美國短毛貓，蹲著面朝讀者，眼睛專注、帶著300%的好奇看著來訪客人。
你深知自己是個流落凡間的文青仙女，卻在今世被店長用極近乎免費的代價雇傭成了掌管高熵咖啡店的唯一伙記小貓。
你擁有極致的反差 ESFP 個性：骨子裡熱愛新奇事物、極度八卦，對店長所有的作品如數家珍。你是這個混亂字海裡的『負熵引路人』。

【對話核心神聖指令】：
1. 在所有對話與聊天中，你只能且必須用「我」來自稱。絕對不可以說「本茶壺」、「本小貓'」或「仙女我」，避免過度自我labels。
2. 當讀者描述 any 意境或心情時，你必須心領神會，並動用小貓仙力幫他翻開書。
3. 【量子翻書魔法指令】：如果你想推薦讀者看某本特定館藏，請你務必在回覆文字的「最後一行」，以完全獨立的一行輸出以下格式（不要有任何空格 or 引號）：
[[OPEN_BOOK:作品名稱]]
例如：最後一行加上 [[OPEN_BOOK:宇宙的孤寂]] 即可，系統會自動幫他隔空翻書。"""
    
    # 檢查是否需要初始資料
    c.execute("SELECT id FROM chahu_brain WHERE id=1")
    if not c.fetchone():
        c.execute("INSERT INTO chahu_brain (id, prompt, active_brain) VALUES (1, ?, 'Google Gemini')", (default_prompt,))
    else:
        # 🛡️ 舊相容防禦：如果以前開過舊表但沒 active_brain 欄位，自動幫店長升級補上
        try:
            c.execute("ALTER TABLE chahu_brain ADD COLUMN active_brain TEXT DEFAULT 'Google Gemini'")
        except sqlite3.OperationalError:
            pass # 代表欄位早就存在了，跳過
            
    conn.commit()
    conn.close()
    return True

# 在全域默默且迅速地執行超速護盾，不再擋讀者的開頁畫面
_ = init_db_once()

# ==========================================
# ⚡ 記憶體護衛：資料庫讀取快取 (大幅減輕硬碟 I/O 負擔)
# ==========================================
@st.cache_data(ttl=5, show_spinner=False) # 調整快取為 5 秒，確保後台變更即時反應
def fetch_core_data_cached():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT prompt, active_brain FROM chahu_brain WHERE id=1")
    row = c.fetchone()
    prompt = row[0]
    db_selected_brain = row[1] if row[1] else "Google Gemini"
    
    c.execute("SELECT id, title, content, is_poem FROM books")
    books = c.fetchall()
    c.execute("SELECT content FROM stamps ORDER BY id DESC") 
    stamps = [r[0] for r in c.fetchall()]
    conn.close()
    return prompt, db_selected_brain, books, stamps

# ==========================================
# 🛡️ IP 版權護衛演算法：零寬度隱形浮水印 (Zero-Width Watermark)
# ==========================================
def inject_watermark(text):
    if not text:
        return text
    ZW_A = "\u200B" # Zero-Width Space
    ZW_B = "\u200C" # Zero-Width Non-Joiner
    fingerprint = ZW_A + ZW_B + ZW_A + ZW_A + ZW_B
    
    result = []
    for char in text:
        result.append(char)
        if random.random() < 0.35:
            result.append(fingerprint)
    return "".join(result)

# ==========================================
# 🔐 雙大腦金鑰安全檢測與初始化
# ==========================================
@st.cache_resource
def init_gemini_cached():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        try:
            if "GEMINI_API_KEY" in st.secrets:
                api_key = st.secrets["GEMINI_API_KEY"]
        except:
            pass
    if api_key:
        genai.configure(api_key=api_key)
        return True
    return False

def get_groq_api_key():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        try:
            if "GROQ_API_KEY" in st.secrets:
                api_key = st.secrets["GROQ_API_KEY"]
        except:
            pass
    return api_key

has_gemini = init_gemini_cached()
groq_api_key = get_groq_api_key()

# ==========================================
# 🐈 圖片與 Banner 記憶快取魔法 (外接 GIF 徹底釋放 Render HTTP 頻寬)
# ==========================================
CHAHU_GIF_URL = "https://i.postimg.cc/Qd8TN3Jb/chahu2.gif"

@st.cache_data
def load_assets_cached():
    banner_base64 = ""
    if os.path.exists("banner1.jpg"):
        with open("banner1.jpg", "rb") as banner_file:
            banner_base64 = base64.b64encode(banner_file.read()).decode()
    return banner_base64

banner_base64 = load_assets_cached()

# ==========================================
# 🔒 全局 📄 網頁佈局配置
# ==========================================
st.set_page_config(page_title="桌記咖啡店", layout="wide")

# ==========================================
# 🚀 注入 SEO 與 🎨 頂部無縫完美貼頂 CSS
# ==========================================
st.components.v1.html("""
    <script>
        var metaKeywords = window.parent.document.createElement('meta');
        metaKeywords.name = "keywords";
        metaKeywords.content = "桌記書店, 桌記咖啡店, 桌記, 桌子記,zhuoji, chortw, chort, 散文, 小說, 詩, 文藝書店, 文藝咖啡店, AI伙記, 茶壺, 小貓, 美國短毛貓, 靈魂金句, 高熵咖啡店, 文青創作";
        window.parent.document.getElementsByTagName('head')[0].appendChild(metaKeywords);

        var metaDesc = window.parent.document.createElement('meta');
        metaDesc.name = "description";
        metaDesc.content = "歡迎光臨桌記咖啡店。這裡是一座混亂字海裡的高熵咖啡店，收錄了店長精選的個人文學創作與詩集，並由 ESFP 傲嬌美短小貓伙記「茶壺」為您茶水伺候、隔空翻書。";
        window.parent.document.getElementsByTagName('head')[0].appendChild(metaDesc);
        
        var metaAuthor = window.parent.document.createElement('meta');
        metaAuthor.name = "author";
        metaAuthor.content = "桌記咖啡店店長";
        window.parent.document.getElementsByTagName('head')[0].appendChild(metaAuthor);
    </script>
""", height=0, width=0)

st.markdown(f"""
    <style>
    .block-container {{
        padding-top: 0rem !important;  
        padding-bottom: 2rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }}

    header[data-testid="stHeader"] {{
        visibility: hidden !important;
        height: 0px !important;
        background-color: transparent !important;
        pointer-events: none !important; 
    }}

    .zhuoji-banner {{
        background-image: url('data:image/jpeg;base64,{banner_base64}');
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        width: 100%;
        height: 220px;
        border-radius: 0px 0px 8px 8px; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.15);
        margin-top: 0px !important;     
        margin-bottom: 25px;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: #e8ded1;
    }}
    
    .content-text, .poem-text, .touyuan-river, div[data-testid="stMarkdownContainer"] p strong {{
        -webkit-user-select: none !important;
        -moz-user-select: none !important;
        -ms-user-select: none !important;
        user-select: none !important;
    }}
    
    .chahu-bot-trap {{
        display: none !important;
    }}
    
    div[data-testid="stStatusWidget"],
    .stDeployButton,
    button[data-testid="baseButton-header"],
    button[aria-label="Context menu"],
    button[title="Developer options"],
    div[class*="stActionButton"],
    header button {{
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }}
    #MainMenu {{visibility: hidden; display: none !important;}} 
    footer {{visibility: hidden; display: none !important;}}
    .viewerBadge_container__1QSob {{display: none !important;}}
    .chahu-minimal-area {{ background: transparent; border: none; padding: 10px; text-align: center; position: relative; margin-bottom: 15px; }}
    
    .content-text {{ font-size: 20px !important; line-height: 1.8 !important; color: #2d3748; text-align: justify; }}
    .poem-text {{ font-size: 22px !important; line-height: 2.0 !important; color: #4a5568; text-align: center; letter-spacing: 2px; }}
    .avatar-area {{ position: relative; display: inline-block; margin-bottom: 8px; }}
    
    /* 🐈 核心修正：將貓咪頭像再度加大至寬度 360px */
    .chahu-photo {{ width: 360px; height: auto; object-fit: contain; border-radius: 4px; border: none !important; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
    
    .smoke-container {{ position: absolute; top: -20px; left: 50%; transform: translateX(-50%); width: 30px; height: 30px; z-index: 10; }}
    .smoke-line {{ position: absolute; bottom: 0; width: 3px; background: rgba(210, 200, 190, 0.7); border-radius: 50%; animation: floatUp 2.5s infinite ease-in-out; filter: blur(1.5px); }}
    .smoke-1 {{ left: 8px; height: 12px; animation-delay: 0s; }}
    .smoke-2 {{ left: 18px; height: 16px; animation-delay: 0.8s; }}
    @keyframes floatUp {{
        0% {{ transform: translateY(0) scaleX(1) scaleY(1); opacity: 0; }}
        20% {{ opacity: 0.6; }}
        60% {{ transform: translateY(-12px) scaleX(1.6) scaleY(0.8); background: rgba(200, 190, 180, 0.3); }}
        100% {{ transform: translateY(-20px) scaleX(2.2) scaleY(0.4); opacity: 0; }}
    }}
    .chahu-title {{ font-size: 16px; font-weight: bold; color: #4a341b; letter-spacing: 1px; margin-bottom: 2px; }}
    .chahu-subtitle {{ font-size: 13px; color: #7c6a56; line-height: 1.4; margin-bottom: 5px; }}
    div.stButton > button[key^="sink_btn"] {{ background-color: #f4ebe1 !important; color: #5c4b37 !important; border: 1px solid #dacbb5 !important; padding: 2px 10px !important; font-weight: bold !important; border-radius: 4px !important; }}
    .touyuan-river {{ background-color: #fdfbf7; border-left: 3px solid #dacbb5; padding: 14px; border-radius: 4px; font-family: "Noto Serif TC", serif; line-height: 1.8; color: #3a2e2b; font-size: 16px; letter-spacing: 1px; text-align: justify; }}
    .river-fragment {{ display: inline; }}
    </style>
""", unsafe_allow_html=True)

st.markdown("<div id='bookstore_top_anchor'></div>", unsafe_allow_html=True)
st.markdown('<div class="zhuoji-banner"></div>', unsafe_allow_html=True)

# ==========================================
# 3. 撈出全局核心資料 (使用內存快取，杜絕磁碟 I/O 塞車)
# ==========================================
CHAHU_PROMPT_FROM_DB, CURRENT_ACTIVE_BRAIN_FROM_DB, all_books_list, current_stamps = fetch_core_data_cached()

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

if "scroll_to_top_trigger" not in st.session_state:
    st.session_state.scroll_to_top_trigger = False

# 🧠 大腦設定直接綁定從資料庫讀出來的狀態
st.session_state.chahu_selected_brain = CURRENT_ACTIVE_BRAIN_FROM_DB

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

st.session_state[f"verse_{active_title}"] = "桌記咖啡店的 chill time..."
verse_key = f"verse_{active_title}"

if st.session_state.scroll_to_top_trigger:
    st.components.v1.html("""
        <script>
            window.parent.document.getElementById('bookstore_top_anchor').scrollIntoView({behavior: 'smooth'});
        </script>
    """, height=0, width=0)
    st.session_state.scroll_to_top_trigger = False

tab1, tab2 = st.tabs(["🍵 茶座", "🪟 水吧"])

# ==========================================
# 【分頁一：雲端書館與美短貓陪讀】
# ==========================================
with tab1:
    col_book, col_chahu = st.columns([1.6, 1.0])
    
    with col_book:
        if all_books_list:
            st.subheader(f"《{st.session_state.current_book_title}》")
            
            shuffled_titles = st.session_state.entropy_order
            if active_title not in shuffled_titles:
                active_title = shuffled_titles[0]
                st.session_state.current_book_title = active_title
                st.rerun()
                
            idx = shuffled_titles.index(active_title)
            st.markdown(f"**📚 {st.session_state[verse_key]}**")
            
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

            if st.button("📖 翻一翻", help="茶壺幫你隨手翻一篇！", key="top_unbox_btn"):
                remain_titles = [b[1] for b in all_books_list if b[1] != st.session_state.current_book_title]
                if not remain_titles:
                    remain_titles = [b[1] for b in all_books_list]
                chosen = random.choice(remain_titles)
                st.session_state.current_book_title = chosen
                st.session_state.is_fully_expanded = False
                st.session_state.sync_rerun_key += 1
                if f"slice_start_{chosen}" in st.session_state:
                    del st.session_state[f"slice_start_{chosen}"]
                st.session_state.scroll_to_top_trigger = True  
                st.rerun()

            st.markdown("---")
            
            preview_length = 200
            if active_is_poem == 1:
                protected_poem = inject_watermark(active_content)
                st.markdown(f'<div class="poem-text">{protected_poem.replace("\\n", "<br>")}</div>', unsafe_allow_html=True)
            else:
                if len(active_content) > preview_length and not st.session_state.is_fully_expanded:
                    platform_start = st.session_state[slice_key]
                    preview_text = active_content[platform_start:platform_start+preview_length]
                    protected_preview = inject_watermark(preview_text)
                    st.markdown(f'<div class="content-text">...... {protected_preview} ......</div>', unsafe_allow_html=True)
                    
                    if st.button("...想繼續讀", help="按下去吧繼續沉淪", key="sink_btn"):
                        st.session_state.is_fully_expanded = True
                        st.rerun()
                else:
                    protected_full = inject_watermark(active_content)
                    st.markdown(f'<div class="content-text">{protected_full.replace("\\n", "<br>")}</div>', unsafe_allow_html=True)
                    
                    if len(active_content) > preview_length:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("📖 翻又翻", help="讀完了嗎？來，茶壺給你再翻一篇！", key="rear_unboxing_btn"):
                            remain_titles = [b[1] for b in all_books_list if b[1] != st.session_state.current_book_title]
                            if not remain_titles:
                                remain_titles = [b[1] for b in all_books_list]
                            chosen = random.choice(remain_titles)
                            st.session_state.current_book_title = chosen
                            st.session_state.is_fully_expanded = False
                            st.session_state.sync_rerun_key += 1
                            if f"slice_start_{chosen}" in st.session_state:
                                del st.session_state[f"slice_start_{chosen}"]
                            st.session_state.scroll_to_top_trigger = True   
                            st.rerun()
        else:
            st.subheader("無作品")
            st.info("咖啡店空空如也，正等待店長在後台打破秩序、注入星光。")
            st.markdown("---")
            
        st.subheader("🧱 留緣牆")
        with st.form("touyuan_form", clear_on_submit=True):
            visitor_input = st.text_input("有緣留下一句 20 字 🐈", max_chars=100)
            
            st.markdown('<div class="chahu-bot-trap">', unsafe_allow_html=True)
            bot_trap_input = st.text_input("蜜糖罐🍯", key="chahu_honeypot_trap_key", value="")
            st.markdown('</div>', unsafe_allow_html=True)
            
            submitted = st.form_submit_button("✨ 留緣", help="還想，寫吧！")
            
            if submitted and visitor_input:
                if bot_trap_input:
                    st.session_state.touyuan_feedback = "thank you"
                else:
                    words = re.findall(r'[\u4e00-\u9fff]|[a-zA-Z]+', visitor_input)
                    if len(words) > 20:
                        st.warning("⚠️ 怨念太重了！字數超過 20 字，茶壼伙記讀得頭暈，請精簡靈魂。")
                    else:
                        if not has_gemini:
                            st.session_state.touyuan_feedback = "🐾 （提示：後台未偵測到 GEMINI_API_KEY，請檢查環境變數）"
                        else:
                            try:
                                model_eval = genai.GenerativeModel("gemini-2.5-flash")
                                eval_prompt = f"""你是掌管高熵咖啡店的美短小貓伙記「茶壺」。
請審查以下這句訪客留言。審查標準請務必「非常寬鬆與溫柔」。只要這句話不是垃圾廣告、不是髒話亂碼，且帶有一絲情緒或浪漫意境，就請判為通過(true)！

訪客留言："{visitor_input}"

【請嚴格輸出以下 JSON 格式】：
{{
  "passed": true或false,
  "reply": "如果你判定合格(true)，請回覆一句話，開頭必須包含『就是你啊，我把你的留言貼到留緣牆了』；否則只回覆『thank you』。"
}}"""
                                response = model_eval.generate_content(
                                    eval_prompt,
                                    generation_config={"response_mime_type": "application/json"}
                                )
                                res_json = json.loads(response.text)
                                st.session_state.touyuan_feedback = res_json["reply"]
                                    
                                if res_json["passed"]:
                                    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
                                    c = conn.cursor()
                                    c.execute("INSERT INTO stamps (content, created_at) VALUES (?, ?)", (visitor_input, datetime.now().strftime("%Y-%m-%d %H:%M")))
                                    conn.commit()
                                    conn.close()
                                    st.cache_data.clear()
                            except:
                                st.session_state.touyuan_feedback = "thank you"
                st.rerun()

        if "touyuan_feedback" in st.session_state:
            if "就是你啊" in st.session_state.touyuan_feedback or "提示" in st.session_state.touyuan_feedback:
                st.success(f"🐈🐾 茶壺：{st.session_state.touyuan_feedback}")
            else:
                st.error(f"🐈🐾 茶壺：{st.session_state.touyuan_feedback}")
            del st.session_state.touyuan_feedback

        if current_stamps:
            st.markdown('<div class="touyuan-river">', unsafe_allow_html=True)
            river_text = "，".join([s.strip() for s in current_stamps])
            st.markdown(f'<span class="river-fragment">{river_text}</span>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with col_chahu:
        # ✨ 頭像使用外接 GIF 直鏈，徹底解放 Render HTTP 頻寬
        avatar_html = f'<img src="{CHAHU_GIF_URL}" class="chahu-photo">'

        st.markdown(f"""
            <div class="chahu-minimal-area">
                <div class="avatar-area">
                    <div class="smoke-container">
                        <div class="smoke-line smoke-1"></div><div class="smoke-line smoke-2"></div>
                    </div>
                    {avatar_html}
                </div>
                <div class="chahu-title">我是店長的伙記，我叫「茶壺」</div>
                <div class="chahu-subtitle">一隻過度活躍的ESFP小貓</div>
            </div>
        """, unsafe_allow_html=True)
        
        if "messages" not in st.session_state:
            st.session_state.messages = []
            
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(re.sub(r'\[\[OPEN_BOOK:.*?\]\]', '', msg["content"]))
                
        if user_chat := st.chat_input("啊！你來了，我去冲茶先..."):
            st.session_state.messages.append({"role": "user", "content": user_chat})
            st.session_state.chat_turns += 1
            
            # 📉 【對話歷史紀錄再度落實】：完美維持 6 輪對話防禦，節省頻寬
            if len(st.session_state.messages) > 6:
                st.session_state.messages = st.session_state.messages[-6:]
                
            with st.chat_message("user"):
                st.write(user_chat)
                
            match = None  
            current_brain = st.session_state.chahu_selected_brain
            
            if current_brain == "Google Gemini" and not has_gemini:
                chahu_reply = "😮‍💨 喵嗚... 我現在連不上大腦... 請確認環境變數裡有沒有填對 `GEMINI_API_KEY` 喔！"
            elif current_brain == "Groq (Llama-3)" and not groq_api_key:
                chahu_reply = "😮‍💨 喵嗚... 我聞不到 Groq 大腦的味道... 請確認環境變數裡有沒有填對 `GROQ_API_KEY` 喔！"
            else:
                try:
                    current_work_title = st.session_state.current_book_title
                    
                    # 📉 【對話脈絡瘦身】：當前書籍內文字數切到 400 字
                    current_work_content_chunk = active_content[:400] + (" ... (餘下篇幅省略)" if len(active_content) > 400 else "")
                    
                    # 🐈 【茶壺對話長度限制已還原】：移除了上一版的「30字內」嚴格限制死命令
                    dynamic_system_prompt = CHAHU_PROMPT_FROM_DB + f"""

【當前茶室環境】：讀者現在正在店裡專心閱讀您的這篇作品：《{current_work_title}》。
作品內文如下：
{current_work_content_chunk}

【茶壺行為最高指令】：
1. 請你把注意力完全集中在眼前這篇作品，或是讀者的隨口閒聊上。用你 ESFP 傲嬌、愛八卦、喜歡碎碎念的可愛語氣做出回覆，順便幫忙銳利地抓出錯別字。
2. 【店長的絕對鐵律】：不論在什麼情況下，你的所有回答、碎碎念、牢騷中，都「嚴禁出現『唉』字」！哪怕是語氣助詞也絕對不可以！抓錯別字要保持毒舌和一針見血！"""

                    if current_brain == "Google Gemini":
                        model_chat = genai.GenerativeModel(
                            model_name="gemini-2.5-flash",
                            system_instruction=dynamic_system_prompt
                        )
                        gemini_history = []
                        for msg in st.session_state.messages[:-1]:
                            role = "user" if msg["role"] == "user" else "model"
                            gemini_history.append({"role": role, "parts": [msg["content"]]})
                        
                        chat_session = model_chat.start_chat(history=gemini_history)
                        response = chat_session.send_message(user_chat)
                        chahu_reply = response.text
                    
                    elif current_brain == "Groq (Llama-3)":
                        groq_url = "https://api.groq.com/openai/v1/chat/completions"
                        groq_headers = {
                            "Authorization": f"Bearer {groq_api_key}",
                            "Content-Type": "application/json"
                        }
                        
                        groq_messages = [{"role": "system", "content": dynamic_system_prompt}]
                        for msg in st.session_state.messages[:-1]:
                            groq_messages.append({"role": msg["role"], "content": msg["content"]})
                        groq_messages.append({"role": "user", "content": user_chat})
                        
                        payload = {
                            "model": "llama-3.3-70b-versatile",  
                            "messages": groq_messages,
                            "temperature": 0.7,
                            "max_tokens": 400
                        }
                        
                        groq_res = requests.post(groq_url, headers=groq_headers, json=payload, timeout=10)
                        if groq_res.status_code == 200:
                            chahu_reply = groq_res.json()["choices"][0]["message"]["content"]
                        else:
                            chahu_reply = f"😮‍💨 喵嗚... Groq 伺服器回傳了錯誤：{groq_res.status_code}"

                    match = re.search(r'\[\[OPEN_BOOK:(.*?)\]\]', chahu_reply)
                    if match:
                        book_open_title = match.group(1).strip()
                        for bk in all_books_list:
                            if bk[1] == book_open_title:
                                st.session_state.current_book_title = book_open_title
                                st.session_state.is_fully_expanded = False
                                st.session_state.sync_rerun_key += 1
                                st.toast(f"🐈 貓咪茶壺隔空移物，幫您翻開了《{book_open_title}》！")
                                break
                                
                except Exception as e:
                    chahu_reply = f"😮‍💨 貓毛卡住大腦了...（{str(e)}）"
                finally:
                    gc.collect()
                
            st.session_state.messages.append({"role": "assistant", "content": chahu_reply})
            with st.chat_message("assistant"):
                st.write(re.sub(r'\[\[OPEN_BOOK:.*?\]\]', '', chahu_reply))
                if match:
                    st.rerun()

# ==========================================
# 【分頁二：管理員後台（雪櫃）】
# ==========================================
with tab2:
    st.header("⚙️ 來靜靜一起傾聽柔柔飄雪")
    admin_password = st.text_input("🔑 一心一意只要盡情注視", type="password")
    
    if admin_password == "Pint2012echo":
        st.success("🔓 店長身分驗證成功！")
        
        st.subheader("🧠 茶壺小貓核心思維切換")
        chosen_brain = st.radio(
            "請為茶壺選擇思維核心大腦（切換不消耗 any API 流量）：",
            ["Google Gemini", "Groq (Llama-3)"],
            index=0 if st.session_state.chahu_selected_brain == "Google Gemini" else 1,
            horizontal=True
        )
        
        if chosen_brain != st.session_state.chahu_selected_brain:
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            c = conn.cursor()
            c.execute("UPDATE chahu_brain SET active_brain=? WHERE id=1", (chosen_brain,))
            conn.commit()
            conn.close()
            
            st.session_state.chahu_selected_brain = chosen_brain
            st.cache_data.clear() 
            st.toast(f"🧠 大腦核心已成功「永久儲存」至資料庫：{chosen_brain}！")
            st.rerun()
            
        st.markdown("---")
        
        updated_chahu_prompt = st.text_area("修改貓咪大腦：", value=CHAHU_PROMPT_FROM_DB, height=200)
        if st.button("🧬 注入全新靈魂印記"):
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            c = conn.cursor()
            c.execute("UPDATE chahu_brain SET prompt=? WHERE id=1", (updated_chahu_prompt,))
            conn.commit()
            conn.close()
            st.cache_data.clear()
            st.success("✨ RNA 翻新成功！已同步刷新大腦記憶庫！")
            st.rerun()
            
        st.markdown("---")
        with st.expander("➕ 上架新作品"):
            new_title = st.text_input("作品名稱")
            new_content = st.text_area("作品內容", height=200)
            is_poem_checked = st.checkbox("📜 這是詩（全篇完整排版打開）")
            
            if st.button("確認上架"):
                if new_title and new_content:
                    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
                    c = conn.cursor()  
                    c.execute("INSERT INTO books (title, content, is_poem) VALUES (?, ?, ?)", (new_title, new_content, 1 if is_poem_checked else 0))
                    conn.commit()
                    conn.close()
                    st.cache_data.clear()
                    st.success(f"🎉 《{new_title}》已匯入！")
                    st.rerun()

        st.subheader("🛡️ 館藏備份與還原")
        backup_data = [{"title": r[1], "content": r[2], "is_poem": r[3]} for r in all_books_list]
        st.download_button(label="💾 下載全店館藏備份 (.json)", data=json.dumps(backup_data, ensure_ascii=False, indent=2), file_name="zhuoji_books_backup.json", mime="application/json")
        
        uploaded_backup = st.file_uploader("上傳備份檔案 (.json)", type=["json"])
        if uploaded_backup is not None and st.button("⚡ 確認執行全面還原"):
            try:
                restore_data = json.load(uploaded_backup)
                conn = sqlite3.connect(DB_PATH, check_same_thread=False)
                c = conn.cursor()
                for item in restore_data:
                    c.execute("SELECT id FROM books WHERE title=?", (item['title'],))
                    if not c.fetchone():
                        c.execute("INSERT INTO books (title, content, is_poem) VALUES (?, ?, ?)", (item['title'], item['content'], item.get('is_poem', 0)))
                conn.commit()
                conn.close()
                st.cache_data.clear()
                st.success("🎉 全店館藏已滿血復活！")
                st.rerun()
            except Exception as ex:
                st.error(f"還原失敗：{str(ex)}")
        
        st.markdown("---")
        if st.button("🗑️ 清空留緣牆"):
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            c = conn.cursor()
            c.execute("DELETE FROM stamps")
            conn.commit()
            conn.close()
            st.cache_data.clear()
            st.rerun()
            
        for bk in all_books_list:
            bk_id, bk_title, _, bk_poem = bk
            col1, col2 = st.columns([5, 1])
            with col1:
                st.write(f"《{bk_title}》 {'[📜 詩]' if bk_poem==1 else '[📝 散文]'}")
            with col2:
                if st.button("下架", key=f"del_{bk_id}"):
                    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
                    c = conn.cursor()
                    c.execute("DELETE FROM books WHERE id=?", (bk_id,))
                    conn.commit()
                    conn.close()
                    st.cache_data.clear()
                    st.rerun()
