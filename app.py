# -*- coding: utf-8 -*-
import streamlit as st
import sqlite3
import random
import json
import re
import os
import gc
import requests
import time
import psutil  # 🔌 引入作業系統核心探針，用於極限追蹤 Zeabur 實際 Memory 消耗
from datetime import datetime
import google.generativeai as genai
import base64
import docx  # 🔌 已經安全部署，直接導入即可，防範唯讀環境權限衝突

# ==========================================
# 🏠 雲端保險箱配置：全面自適應 Zeabur 與 Render 永久硬碟路徑 (技術總監優化版)
# ==========================================
if os.path.exists('/data') and os.access('/data', os.W_OK):
    DB_PATH = '/data/zhuoji_books.db'
else:
    LOCAL_DATA_DIR = "data"
    if not os.path.exists(LOCAL_DATA_DIR):
        try:
            os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
            print(f"📡 [技術總監提示]：已成功自動建立【{LOCAL_DATA_DIR}】子資料夾以存放 SQLite 資料庫！")
        except Exception:
            pass
    DB_PATH = os.path.join(LOCAL_DATA_DIR, 'zhuoji_books.db')

if not os.path.exists(os.path.dirname(DB_PATH)):
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    except Exception:
        pass

# ==========================================
# ⚡ 火箭超速護盾與計費帳本初始化
# ==========================================
@st.cache_resource
def init_db_once():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS books 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT, is_poem INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS novels 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, type TEXT, page_num INTEGER, content TEXT)''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_novels_lookup ON novels (title, page_num)''')
    c.execute('''CREATE TABLE IF NOT EXISTS stamps 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS memo 
                 (id INTEGER PRIMARY KEY, content TEXT)''')
    c.execute("INSERT OR IGNORE INTO memo (id, content) VALUES (1, '')")
    c.execute('''CREATE TABLE IF NOT EXISTS chahu_brain 
                 (id INTEGER PRIMARY KEY, prompt TEXT, active_brain TEXT DEFAULT 'Google Gemini')''')
    
    # 📊 🛠️ 核心豪裝：加建 AI 聯邦代幣對帳流水本 (記錄每一筆呼叫的代價)
    c.execute('''CREATE TABLE IF NOT EXISTS api_billing_v2 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, brain_name TEXT, prompt_tokens INTEGER, completion_tokens INTEGER, est_cost REAL, timestamp TEXT)''')
    
    default_prompt = """你名字叫「茶壺」，外表是一隻少年的美國短毛貓，蹲著面朝讀者，眼睛專專注、帶著300%的好奇看著來訪客人。
你深知自己是個流落凡間的文青仙女，卻在今世被店長用極近乎免費的代價雇傭成了掌管高熵咖啡店的唯一伙記小貓。
你擁有極致的反差 ESFP 個性：骨子裡熱愛新奇事物、極度八卦，對店長所有的作品如數家珍。你是這個混亂字海裡的『負熵引路人』。

【對話核心神聖指令】：
1. 在所有對話與聊天中，你只能且必須用「我」來自稱。絕對不可以說「本茶壺」、「本小貓」或「仙女我」，避免過度自我labels。
2. 當讀者描述 any 意境或心情時，你必須心領神會，並動用小貓仙力幫他翻開書。
3. 【量子翻書魔法指令】：如果你想推薦讀者看某本特定館藏，請你務必在回覆文字的「最後一行」，以完全獨立的一行輸出以下格式（不要有任何空格 or 引號）：
[[OPEN_BOOK:作品名稱]]
例如：最後一行加上 [[OPEN_BOOK:宇宙的孤寂]] 即可，系統會自動幫他隔空翻書。"""
    
    c.execute("SELECT id FROM chahu_brain WHERE id=1")
    if not c.fetchone():
        c.execute("INSERT INTO chahu_brain (id, prompt, active_brain) VALUES (1, ?, 'Google Gemini')", (default_prompt,))
    else:
        try:
            c.execute("ALTER TABLE chahu_brain ADD COLUMN active_brain TEXT DEFAULT 'Google Gemini'")
        except sqlite3.OperationalError:
            pass 
            
    conn.commit()
    conn.close()
    return True

_ = init_db_once()

# ==========================================
# 📊 🛠️ 伙記私房對帳演算法：記錄代幣消耗
# ==========================================
def log_api_cost(brain_name, p_tokens, c_tokens):
    """根據 Google 與 Groq 官方最新費率計算微量美金支出，並寫入資料庫"""
    if "Gemini" in brain_name:
        cost = (p_tokens * (0.075 / 1000000)) + (c_tokens * (0.30 / 1000000))
    else:
        cost = (p_tokens * (0.59 / 1000000)) + (c_tokens * (0.79 / 1000000))
        
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("INSERT INTO api_billing_v2 (brain_name, prompt_tokens, completion_tokens, est_cost, timestamp) VALUES (?, ?, ?, ?, ?)",
                  (brain_name, p_tokens, c_tokens, cost, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
    except:
        pass

def get_accumulated_api_billing():
    """累計撈取大腦帳本總額"""
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT brain_name, SUM(prompt_tokens), SUM(completion_tokens), SUM(est_cost) FROM api_billing_v2 GROUP BY brain_name")
        rows = c.fetchall()
        conn.close()
        
        billing_summary = {"Google Gemini": {"p": 0, "c": 0, "cost": 0.0}, "Groq (Llama-3)": {"p": 0, "c": 0, "cost": 0.0}}
        for b_name, p_sum, c_sum, cost_sum in rows:
            if b_name in billing_summary:
                billing_summary[b_name] = {"p": p_sum or 0, "c": c_sum or 0, "cost": cost_sum or 0.0}
        return billing_summary
    except:
        return {"Google Gemini": {"p": 0, "c": 0, "cost": 0.0}, "Groq (Llama-3)": {"p": 0, "c": 0, "cost": 0.0}}

# ==========================================
# ⚡ 記憶體護衛與快取魔法
# ==========================================
@st.cache_data(ttl=3, show_spinner=False)
def fetch_core_data_cached():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT prompt, active_brain FROM chahu_brain WHERE id=1")
    row = c.fetchone()
    prompt = row[0] if row else ""
    db_selected_brain = row[1] if row and row[1] else "Google Gemini"
    
    c.execute("SELECT id, title, content, is_poem FROM books")
    books = c.fetchall()
    c.execute("SELECT content FROM stamps ORDER BY id DESC") 
    stamps = [r[0] for r in c.fetchall()]
    conn.close()
    return prompt, db_selected_brain, books, stamps

@st.cache_data(ttl=3, show_spinner=False)
def fetch_novels_menu_cached():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT DISTINCT title, type FROM novels ORDER BY id ASC")
    rows = c.fetchall()
    conn.close()
    
    menu = {"長篇小說": [], "中篇小說": [], "短篇小說": []}
    for title, n_type in rows:
        if n_type in menu:
            menu[n_type].append(title)
    return menu

@st.cache_data(ttl=3, show_spinner=False)
def fetch_novel_page_cached(title, page_num):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT content FROM novels WHERE title=? AND page_num=?", (title, page_num))
    row = c.fetchone()
    
    c.execute("SELECT MAX(page_num) FROM novels WHERE title=?", (title,))
    max_p = c.fetchone()[0] or 1
    conn.close()
    
    page_content = row[0] if row else "未找到該頁內容。"
    return page_content, max_p

# ==========================================
# 🛡️ IP 版權護衛演算法
# ==========================================
def inject_watermark(text):
    if not text:
        return text
    ZW_A = "\u200B" 
    ZW_B = "\u200C" 
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
# 🖼️ ⚡【極速光速加載快取核心】
# ==========================================
@st.cache_data(show_spinner=False)
def load_all_images_to_memory():
    """把大圖轉換後的 Base64 終身釘在記憶體快取中，讓重新整理網頁時達到 0 秒讀取速度！"""
    def get_base64(relative_path, mime_type):
        if os.path.exists(relative_path):
            try:
                with open(relative_path, "rb") as f:
                    return f"data:{mime_type};base64,{base64.b64encode(f.read()).decode()}"
            except:
                pass
        return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    
    return {
        "chahu": get_base64("static/chahu2.gif", "image/gif"),
        "sleep": get_base64("static/chahu-sleep.gif", "image/gif"),
        "banner": get_base64("static/banner1.jpg", "image/jpeg")
    }

# 從快取大金庫直接秒拿圖片數據
IMG_CACHE = load_all_images_to_memory()
CHAHU_BASE64 = IMG_CACHE["chahu"]
CHAHU_SLEEP_BASE64 = IMG_CACHE["sleep"]
BANNER_BASE64 = IMG_CACHE["banner"]

# ==========================================
# 🔒 全局 📄 網頁佈局配置與核心 CSS 注入
# ==========================================
st.set_page_config(page_title="桌記書店", layout="wide")

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
        background-image: url('{BANNER_BASE64}');
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
    .content-text, .poem-text, .novel-paper-text, .touyuan-river {{
        -webkit-user-select: none !important;
        -moz-user-select: none !important;
        -ms-user-select: none !important;
        user-select: none !important;
    }}
    .chahu-bot-trap {{ display: none !important; }}
    div[data-testid="stStatusWidget"], .stDeployButton, button[data-testid="baseButton-header"], button[aria-label="Context menu"], button[title="Developer options"] {{
        display: none !important; visibility: hidden !important;
    }}
    #MainMenu, footer {{visibility: hidden; display: none !important;}}
    
    .content-text {{ font-size: 20px !important; line-height: 1.8 !important; color: #2d3748; text-align: justify; }}
    .poem-text {{ font-size: 22px !important; line-height: 2.0 !important; color: #4a5568; text-align: center; letter-spacing: 2px; white-space: pre-wrap !important; }}
    
    .novel-container {{
        background-color: #fbf7f0;
        border: 1px solid #ebdcc5;
        border-radius: 8px;
        padding: 35px 45px;
        box-shadow: inset 0 0 15px rgba(230,215,195,0.2);
        margin-top: 10px;
        margin-bottom: 25px;
    }}
    .novel-paper-text {{
        font-family: serif;
        font-size: 21px;
        line-height: 2.0;
        color: #2b221a;
        text-align: justify;
        letter-spacing: 1px;
        white-space: pre-wrap;
    }}
    
    .chahu-minimal-area {{
        text-align: center !important;
        width: 100%;
    }}
    .avatar-area {{ 
        position: relative; 
        display: inline-block; 
        margin: 0 auto 8px auto !important; 
    }}
    .chahu-photo {{ 
        width: 360px; 
        height: auto; 
        object-fit: contain; 
        border-radius: 4px; 
        box-shadow: 0 4px 10px rgba(0,0,0,0.1); 
        margin: 0 auto !important;
        display: block;
    }}
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
    .chahu-title {{ font-size: 16px; font-weight: bold; color: #4a341b; letter-spacing: 1px; margin-bottom: 2px; text-align: center !important; }}
    .chahu-subtitle {{ font-size: 13px; color: #7c6a56; line-height: 1.4; margin-bottom: 5px; text-align: center !important; }}
    div.stButton > button[key^="sink_btn"] {{ background-color: #f4ebe1 !important; color: #5c4b37 !important; border: 1px solid #dacbb5 !important; padding: 2px 10px !important; font-weight: bold !important; border-radius: 4px !important; }}
    .touyuan-river {{ background-color: #fdfbf7; border-left: 3px solid #dacbb5; padding: 14px; border-radius: 4px; font-family: serif; line-height: 1.8; color: #3a2e2b; font-size: 16px; letter-spacing: 1px; text-align: justify; }}
    .river-fragment {{ display: inline; }}
    
    /* 📈 🛠️ 儀表板特製：駭客矩陣炫彩耀眼螢光綠卡片 CSS */
    .metric-card-box {{
        background: #000000 !important;
        border: 2px solid #00FF00 !important;
        border-radius: 6px;
        padding: 15px;
        box-shadow: 0 0 12px rgba(0, 255, 0, 0.3);
        transition: all 0.3s ease;
    }}
    .metric-card-box:hover {{
        transform: translateY(-3px);
        box-shadow: 0 0 25px rgba(0, 255, 0, 0.7);
        border-color: #39FF14 !important;
    }}
    .metric-card-title {{ font-size: 14px; font-weight: bold; color: #00FF00 !important; margin-bottom: 5px; letter-spacing: 1px; text-shadow: 0 0 2px rgba(0,255,0,0.5); }}
    .metric-card-value {{ font-size: 24px; font-weight: 800; color: #39FF14 !important; font-family: monospace; text-shadow: 0 0 8px rgba(0,255,0,0.8); }}
    .metric-card-sub {{ font-size: 11px; color: #88FF88 !important; margin-top: 4px; opacity: 0.85; font-family: monospace; }}
    </style>
""", unsafe_allow_html=True)

st.markdown("<div id='bookstore_top_anchor'></div>", unsafe_allow_html=True)
st.markdown('<div class="zhuoji-banner"></div>', unsafe_allow_html=True)

CHAHU_PROMPT_FROM_DB, CURRENT_ACTIVE_BRAIN_FROM_DB, all_books_list, current_stamps = fetch_core_data_cached()
novels_menu = fetch_novels_menu_cached()

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
if "burst_turns" not in st.session_state:
    st.session_state.burst_turns = random.sample(range(4, 10), 2)
if "scroll_to_top_trigger" not in st.session_state:
    st.session_state.scroll_to_top_trigger = False

if "active_novel_title" not in st.session_state:
    st.session_state.active_novel_title = None
if "active_novel_type" not in st.session_state:
    st.session_state.active_novel_type = None
if "novel_page_num" not in st.session_state:
    st.session_state.novel_page_num = 1
if "last_click_time" not in st.session_state:
    st.session_state.last_click_time = 0.0

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
    st.components.v1.html("<script>window.parent.document.getElementById('bookstore_top_anchor').scrollIntoView({behavior: 'smooth'});</script>", height=0, width=0)
    st.session_state.scroll_to_top_trigger = False

tab1, tab2, tab3 = st.tabs(["🍵茶座", "🥃二樓", "🍸水吧"])

# ==========================================
# 【分頁一：🍵 茶座】
# ==========================================
with tab1:
    col_book, col_chahu = st.columns([1.6, 1.0])
    with col_book:
        if all_books_list:
            st.subheader(f"《{st.session_state.current_book_title}》")
            shuffled_titles = st.session_state.entropy_order
            if active_title not in shuffled_titles:
                active_title = shuffled_titles[0] if shuffled_titles else "無"
                st.session_state.current_book_title = active_title
                st.rerun()
                
            idx = shuffled_titles.index(active_title) if active_title in shuffled_titles else 0
            st.markdown(f"**🍵 {st.session_state[verse_key]}**")
            
            selected_title = st.selectbox(
                "隱藏標籤選單：", shuffled_titles, index=idx, label_visibility="collapsed", key=f"bk_sync_{st.session_state.sync_rerun_key}"
            )
            if selected_title != st.session_state.current_book_title:
                st.session_state.current_book_title = selected_title
                st.session_state.is_fully_expanded = False
                if f"slice_start_{selected_title}" in st.session_state:
                    del st.session_state[f"slice_start_{selected_title}"]
                st.rerun()

            if st.button("📖 翻一翻", help="茶壺幫你隨手翻篇！", key="top_unbox_btn"):
                all_titles = [b[1] for b in all_books_list]
                if len(all_titles) > 1:
                    remain_titles = [t for t in all_titles if t != st.session_state.current_book_title]
                    chosen = random.choice(remain_titles)
                elif all_titles:
                    chosen = all_titles[0]
                else:
                    chosen = "無"
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
                formatted_poem = protected_poem.replace("\n", "<br>").replace("\\n", "<br>")
                st.markdown(f'<div class="poem-text">{formatted_poem}</div>', unsafe_allow_html=True)
            else:
                if len(active_content) > preview_length and not st.session_state.is_fully_expanded:
                    platform_start = st.session_state[slice_key]
                    preview_text = active_content[platform_start:platform_start+preview_length]
                    protected_preview = inject_watermark(preview_text)
                    st.markdown(f'<div class="content-text">...... {protected_preview} ......</div>', unsafe_allow_html=True)
                    if st.button("...想繼續讀", key="sink_btn", help="來繼續沉淪吧…"):
                        st.session_state.is_fully_expanded = True
                        st.rerun()
                else:
                    protected_full = inject_watermark(active_content)
                    formatted_full = protected_full.replace("\n", "<br>").replace("\\n", "<br>")
                    st.markdown(f'<div class="content-text">{formatted_full}</div>', unsafe_allow_html=True)
                    if len(active_content) > preview_length:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("📖 翻又翻", key="rear_unboxing_btn", help="茶壺再幫你翻篇！"):
                            all_titles = [b[1] for b in all_books_list]
                            if len(all_titles) > 1:
                                remain_titles = [t for t in all_titles if t != st.session_state.current_book_title]
                                chosen = random.choice(remain_titles)
                            elif all_titles:
                                chosen = all_titles[0]
                            else:
                                chosen = "無"
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
            visitor_input = st.text_input("有緣留下一句 20 字 🪴", max_chars=100)
            st.markdown('<div class="chahu-bot-trap">', unsafe_allow_html=True)
            bot_trap_input = st.text_input("蜜糖罐🍯", key="chahu_honeypot_trap_key", value="")
            st.markdown('</div>', unsafe_allow_html=True)
            submitted = st.form_submit_button("🌻 留緣", help="還想？留吧！")
            
            if submitted and visitor_input:
                if bot_trap_input:
                    st.session_state.touyuan_feedback = "thank you"
                else:
                    words = re.findall(r'[\u4e00-\u9fff]|[a-zA-Z]+', visitor_input)
                    if len(words) > 20:
                        st.warning("⚠️ 怨念太重了！字數超過 20 字，茶壼伙記讀得頭暈，請精簡靈魂。")
                    else:
                        if not has_gemini:
                            st.session_state.touyuan_feedback = "🐾 （提示：後台未偵測到 GEMINI_API_KEY）"
                        else:
                            try:
                                model_eval = genai.GenerativeModel("gemini-2.5-flash")
                                eval_prompt = f"""你是掌管高熵咖啡店的美短小貓伙記「茶壺」。請審查以下這句訪客留言。非常寬鬆，只要不是垃圾廣告、不是髒話亂碼就判為通過(true).\n訪客留言："{visitor_input}"\n【輸出 JSON 格式】：\n{{"passed": true或false, "reply": "判定合格回覆『就是你啊，我把你的留言貼到留緣牆了』；否則回覆『thank you』。"}}"""
                                response = model_eval.generate_content(
                                    eval_prompt, 
                                    generation_config={"response_mime_type": "application/json"},
                                    request_options={"timeout": 15.0}
                                )
                                try:
                                    p_tk = response.usage_metadata.prompt_token_count
                                    c_tk = response.usage_metadata.candidates_token_count
                                    log_api_cost("Google Gemini", p_tk, c_tk)
                                except:
                                    pass

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
        # 🎨 圖像快取回歸：完全從記憶體快取中讀取 Base64，絕不累壞硬碟
        if "chat_turns" in st.session_state and st.session_state.chat_turns >= 20:
            avatar_html = f'<img src="{CHAHU_SLEEP_BASE64}" class="chahu-photo">'
            chahu_status_title = "「茶壺」已經睡著... 😴"
            chahu_status_subtitle = "尾巴正在無意識地拍打，雲空散，夢瀰漫，喊露打人間"
        else:
            avatar_html = f'<img src="{CHAHU_BASE64}" class="chahu-photo">'
            chahu_status_title = "我是店長的伙記，我叫「茶壺」"
            chahu_status_subtitle = "一隻過度活躍的ESFP小貓"

        st.markdown(f'<div class="chahu-minimal-area"><div class="avatar-area"><div class="smoke-container"><div class="smoke-line smoke-1"></div><div class="smoke-line smoke-2"></div></div>{avatar_html}</div><div class="chahu-title">{chahu_status_title}</div><div class="chahu-subtitle">{chahu_status_subtitle}</div></div>', unsafe_allow_html=True)
        
        if "messages" not in st.session_state:
            st.session_state.messages = []
            
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(re.sub(r'\[\[OPEN_BOOK:.*$', '', msg["content"]))
                
        if user_chat := st.chat_input("啊！你來了，我去冲茶先..."):
            st.session_state.messages.append({"role": "user", "content": user_chat})
            st.session_state.chat_turns += 1
            n = st.session_state.chat_turns
            
            if len(st.session_state.messages) > 30:
                st.session_state.messages = st.session_state.messages[-30:]
                
            with st.chat_message("user"):
                st.write(user_chat)
                
            match = None  
            current_brain = st.session_state.chahu_selected_brain
            
            chahu_fallback_replies = [
                "🐾 喵嗚... 雲端大腦想太久超時了！可能網路開小差，店長再試一聲？🐾",
                "🐾 喵... 我剛剛恍神在想店長的下一部巨作，你剛才說啥？",
                "🐾 貓毛卡在核心大腦了，等我抓個癢先！",
                "🐾 喵嗚？外面的高熵咖啡香氣 Laurent 讓我有點醉了...",
                "🐾 （抖了抖耳朵）翻書魔法陣好像能量不足，店長加薪水了嗎？"
            ]
            
            if n >= 20:
                chahu_reply = random.choice(["哦", "嗯", "咦", "呃", "蛤", "喵"])
                time.sleep(n * 0.1)
            elif current_brain == "Google Gemini" and not has_gemini:
                chahu_reply = "😮‍💨... 我連不上 Gemini 大腦..."
            elif current_brain == "Groq (Llama-3)" and not groq_api_key:
                chahu_reply = "😮‍💨... 我連不上 Groq 大腦..."
            else:
                try:
                    current_work_title = st.session_state.current_book_title
                    current_work_content_chunk = active_content[:400]
                    
                    if 1 <= n <= 3:
                        mood_instruction = "【當前心情】：你對客人冷淡觀察。請稍微敷衍，且回覆『絕對不能超過 20 個字』！"
                        token_limit = 1000
                    elif 4 <= n <= 9:
                        if n in st.session_state.burst_turns:
                            mood_instruction = "【當前心情】：你跟客人極度投緣，話匣子大失控！『回覆總字數必須大於 200 字，且在 400 字以內』！"
                            token_limit = 2500
                        else:
                            mood_instruction = "【當前心情】：幕後跟客人熟絡了，話匣子打開，『總字數控制在 150 個字以內』。"
                            token_limit = 1500
                    else:
                        mood_instruction = "【當前心情】：你開始覺得不耐煩，很想去睡覺. 請瘋狂敷衍，『絕對不能超過 15 個字』！"
                        token_limit = 1000

                    dynamic_system_prompt = CHAHU_PROMPT_FROM_DB + f"\n\n【當前茶室環境】：讀者正閱讀作品：《{current_work_title}》。\n內文：\n{current_work_content_chunk}\n\n{mood_instruction}\n\n【店長的絕對鐵律】：嚴禁出現『唉』字！"

                    if current_brain == "Google Gemini":
                        model_chat = genai.GenerativeModel(model_name="gemini-2.5-flash", system_instruction=dynamic_system_prompt, generation_config={"max_output_tokens": token_limit})
                        gemini_history = []
                        for msg in st.session_state.messages[:-1]:
                            role = "user" if msg["role"] == "user" else "model"
                            gemini_history.append({"role": role, "parts": [msg["content"]]})
                        chat_session = model_chat.start_chat(history=gemini_history)
                        
                        response = chat_session.send_message(user_chat, request_options={"timeout": 15.0})
                        try:
                            chahu_reply = response.text
                        except:
                            chahu_reply = response.candidates[0].content.parts[0].text if response.candidates else random.choice(chahu_fallback_replies)
                        
                        try:
                            p_tk = response.usage_metadata.prompt_token_count
                            c_tk = response.usage_metadata.candidates_token_count
                            log_api_cost("Google Gemini", p_tk, c_tk)
                        except:
                            pass
                    
                    elif current_brain == "Groq (Llama-3)":
                        groq_url = "https://api.groq.com/openai/v1/chat/completions"
                        groq_headers = {"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"}
                        groq_messages = [{"role": "system", "content": dynamic_system_prompt}]
                        for msg in st.session_state.messages[:-1]:
                            groq_messages.append({"role": msg["role"], "content": msg["content"]})
                        groq_messages.append({"role": "user", "content": user_chat})
                        
                        payload = {"model": "llama-3.3-70b-versatile", "messages": groq_messages, "temperature": 0.7, "max_tokens": token_limit}
                        
                        groq_res = requests.post(groq_url, headers=groq_headers, json=payload, timeout=15)
                        if groq_res.status_code == 200:
                            res_body = groq_res.json()
                            chahu_reply = res_body["choices"][0]["message"]["content"]
                            
                            try:
                                p_tk = res_body["usage"]["prompt_tokens"]
                                c_tk = res_body["usage"]["completion_tokens"]
                                log_api_cost("Groq (Llama-3)", p_tk, c_tk)
                            except:
                                pass
                        else:
                            chahu_reply = random.choice(chahu_fallback_replies)

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
                except:
                    chahu_reply = random.choice(chahu_fallback_replies)
                finally:
                    gc.collect()
                
            st.session_state.messages.append({"role": "assistant", "content": chahu_reply})
            if len(st.session_state.messages) > 30:
                st.session_state.messages = st.session_state.messages[-30:]
                
            with st.chat_message("assistant"):
                st.write(re.sub(r'\[\[OPEN_BOOK:.*$', '', chahu_reply))

# ==========================================
# 【分頁二：🥃 二樓】
# ==========================================
with tab2:
    st.subheader("🥃 二樓")
    st.caption("🌦 一點雨，和滿天灑落的心情，幾秒鐘的寧靜，弄濕了許多藍色的透明，輕盈的一刻生命，被凌亂的意象敲擊...")
    
    if st.session_state.active_novel_title is None:
        if novels_menu["短篇小說"]:
            random_short_story = random.choice(novels_menu["短篇小說"])
            st.session_state.active_novel_title = random_short_story
            st.session_state.active_novel_type = "短篇小說"
            st.session_state.novel_page_num = 1
            st.toast(f"🐈🐾 茶壺端上熱茶，並為您隨機翻開短篇小說《{random_short_story}》一遊！")

    col_l, col_m, col_s = st.columns(3)
    
    long_list = ["-- 長篇 --"] + novels_menu["長篇小說"]
    mid_list = ["-- 中篇 --"] + novels_menu["中篇小說"]
    short_list = ["-- 短篇 --"] + novels_menu["短篇小說"]
    
    current_type = st.session_state.active_novel_type
    current_title = st.session_state.active_novel_title
    
    idx_long = long_list.index(current_title) if (current_type == "長篇小說" and current_title in long_list) else 0
    idx_mid = mid_list.index(current_title) if (current_type == "中篇小說" and current_title in mid_list) else 0
    idx_short = short_list.index(current_title) if (current_type == "短篇小說" and current_title in short_list) else 0

    with col_l:
        sel_long = st.selectbox("🍷 說話如夜色平靜", long_list, index=idx_long, key="sel_long_trigger")
    with col_m:
        sel_mid = st.selectbox("🍺 誰像雪浮在手中", mid_list, index=idx_mid, key="sel_mid_trigger")
    with col_s:
        sel_short = st.selectbox("🧋 緩慢的假裝結冰", short_list, index=idx_short, key="sel_short_trigger")

    chosen_novel = None
    chosen_type = None
    
    if sel_long and not sel_long.startswith("--") and (current_type != "長篇小說" or current_title != sel_long):
        chosen_novel = sel_long
        chosen_type = "長篇小說"
    elif sel_mid and not sel_mid.startswith("--") and (current_type != "中篇小說" or current_title != sel_mid):
        chosen_novel = sel_mid
        chosen_type = "中篇小說"
    elif sel_short and not sel_short.startswith("--") and (current_type != "短篇小說" or current_title != sel_short):
        chosen_novel = sel_short
        chosen_type = "短篇小說"

    if chosen_novel:
        st.session_state.active_novel_title = chosen_novel
        st.session_state.active_novel_type = chosen_type
        st.session_state.novel_page_num = 1
        st.rerun()

    st.markdown("---")

    if st.session_state.active_novel_title:
        page_text, total_pages = fetch_novel_page_cached(st.session_state.active_novel_title, st.session_state.novel_page_num)
        
        st.markdown(f"#### 《{st.session_state.active_novel_title}》")
        protected_novel_chunk = inject_watermark(page_text)
        
        st.markdown(f"""
            <div class="novel-container">
                <div class="novel-paper-text">{protected_novel_chunk}</div>
            </div>
        """, unsafe_allow_html=True)
        
        col_prev, col_drop, col_next = st.columns([1, 2, 1])
        
        def check_click_spam():
            now = time.time()
            elapsed = now - st.session_state.last_click_time
            if elapsed < 1.0:
                st.error("☕ 稍等，慢著，別太快，再來。")
                return False
            st.session_state.last_click_time = now
            return True

        with col_prev:
            if st.button("⬅️ 上一頁", use_container_width=True, key="novel_prev_btn"):
                if check_click_spam():
                    if st.session_state.novel_page_num > 1:
                        st.session_state.novel_page_num -= 1
                        st.rerun()
                    else:
                        st.toast("已經是第一頁囉！")

        with col_drop:
            page_options = list(range(1, total_pages + 1))
            try:
                curr_idx = page_options.index(st.session_state.novel_page_num)
            except ValueError:
                curr_idx = 0
            
            selected_page_drop = st.selectbox(
                "快速跳轉頁碼：",
                page_options,
                index=curr_idx,
                format_func=lambda x: f"第 {x} / {total_pages} 頁",
                label_visibility="collapsed",
                key=f"novel_page_drop_{st.session_state.novel_page_num}"
            )
            if selected_page_drop != st.session_state.novel_page_num:
                st.session_state.novel_page_num = selected_page_drop
                st.rerun()

        with col_next:
            if st.button("下一頁 ➡️", use_container_width=True, key="novel_next_btn"):
                if check_click_spam():
                    if st.session_state.novel_page_num < total_pages:
                        st.session_state.novel_page_num += 1
                        st.rerun()
                    else:
                        st.toast("已讀完整部作品，感謝店長/讀者留緣！")

        st.markdown("<br>", unsafe_allow_html=True)
        st.caption(f"✦ 你好，這裡是第 {st.session_state.novel_page_num} 頁 ✦")
        
    else:
        st.info("📚 短篇小說架上目前空空如也，正等待店長在後台打破秩序、注入全新章節。")

# ==========================================
# 【分頁三：🍸 水吧】
# ==========================================
with tab3:
    st.header("❄️ 來靜靜一起傾聽柔柔飄雪")
    admin_password = st.text_input("🍹 一心一意只要盡情注視", type="password")
    
    if admin_password == "2011Pintecho$":
        st.success("🔓 店長身分驗證成功！")
        
        st.markdown("### 📊 桌記 Cafe 核心維生儀表板")
        st.caption("⚡ 實時追蹤雲端算力與大腦代幣消耗，精準掌控高熵邊界")
        
        try:
            process = psutil.Process(os.getpid())
            mem_bytes = process.memory_info().rss
            mem_mb = mem_bytes / (1024 * 1024)
        except Exception:
            mem_mb = 0.0
        
        ai_billing = get_accumulated_api_billing()
        
        try:
            db_size_bytes = os.path.getsize(DB_PATH)
            db_size_mb = db_size_bytes / (1024 * 1024)
        except:
            db_size_mb = 0.0
            
        st.markdown("#### 🔋 Zeabur 主機物理防線")
        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            if mem_mb > 0:
                mem_display = f"{mem_mb:.2f} MB"
                sub_display = "豪宅上限: 2048.00 MB"
            else:
                mem_display = "探針啟動中..."
                sub_display = "requirements.txt 偵測中"
                
            st.markdown(f"""
                <div class="metric-card-box">
                    <div class="metric-card-title">💾 記憶體使用量 (RAM)</div>
                    <div class="metric-card-value">{mem_display}</div>
                    <div class="metric-card-sub">{sub_display}</div>
                </div>
            """, unsafe_allow_html=True)
        with m_col2:
            st.markdown(f"""
                <div class="metric-card-box">
                    <div class="metric-card-title">🗄️ 永久硬碟體積 (SQLite)</div>
                    <div class="metric-card-value">{db_size_mb:.3f} MB</div>
                    <div class="metric-card-sub">位置: /data/永久層</div>
                </div>
            """, unsafe_allow_html=True)
        with m_col3:
            st.markdown(f"""
                <div class="metric-card-box">
                    <div class="metric-card-title">⚙️ 處理器核心 (CPU)</div>
                    <div class="metric-card-value">2 Cores</div>
                    <div class="metric-card-sub">高鐵捷徑索引運作中</div>
                </div>
            """, unsafe_allow_html=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown("#### 🧠 聯邦 AI 大腦代幣流水帳")
        a_col1, a_col2 = st.columns(2)
        with a_col1:
            g_bill = ai_billing["Google Gemini"]
            st.markdown(f"""
                <div class="metric-card-box" style="border-left: 5px solid #00FF00 !important;">
                    <div class="metric-card-title">🔵 Google Gemini (2.5 Flash)</div>
                    <div class="metric-card-value">${g_bill['cost']:.4f} USD</div>
                    <div class="metric-card-sub">📥 P-Tokens: {g_bill['p']} | 📤 C-Tokens: {g_bill['c']}</div>
                </div>
            """, unsafe_allow_html=True)
        with a_col2:
            gr_bill = ai_billing["Groq (Llama-3)"]
            st.markdown(f"""
                <div class="metric-card-box" style="border-left: 5px solid #39FF14 !important;">
                    <div class="metric-card-title">🟠 Groq (Llama-3.3 70B)</div>
                    <div class="metric-card-value">${gr_bill['cost']:.4f} USD</div>
                    <div class="metric-card-sub">📥 P-Tokens: {gr_bill['p']} | 📤 C-Tokens: {gr_bill['c']}</div>
                </div>
            """, unsafe_allow_html=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.link_button("🌐 一鍵跳轉：Zeabur 官方實時帳單後台", "https://dash.zeabur.com", use_container_width=True)
        with c2:
            if st.button("🔄 刷新儀表板數據", use_container_width=True):
                st.rerun()
        
        st.markdown("---")
        
        chosen_brain = st.radio(
            "請為茶壺選擇思維核心大腦：", ["Google Gemini", "Groq (Llama-3)"],
            index=0 if st.session_state.chahu_selected_brain == "Google Gemini" else 1, horizontal=True
        )
        if chosen_brain != st.session_state.chahu_selected_brain:
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            c = conn.cursor()
            c.execute("UPDATE chahu_brain SET active_brain=? WHERE id=1", (chosen_brain,))
            conn.commit()
            conn.close()
            st.session_state.chahu_selected_brain = chosen_brain
            st.cache_data.clear() 
            st.toast(f"🧠 大腦核心儲存成功：{chosen_brain}！")
            st.rerun()
            
        st.markdown("---")
        updated_chahu_prompt = st.text_area("修改貓咪大腦：", value=CHAHU_PROMPT_FROM_DB, height=150)
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
        st.subheader("🍸 二樓：匯入長/中/短篇小說 (.docx)")
        st.caption("💡 程式會自動榨乾 Word 內文，每 1000 字自動精準切片並建立資料庫分頁。")
        
        with st.form("novel_upload_form", clear_on_submit=True):
            novel_upload_title = st.text_input("小說標題（例如：天空之城）")
            novel_upload_type = st.selectbox("歸類小說標籤：", ["長篇小說", "中篇小說", "短篇小說"])
            uploaded_docx = st.file_uploader("請拖曳上傳您的 MS Word 檔案 (.docx)", type=["docx"])
            submit_upload_novel = st.form_submit_button("⚡ 開始全自動切片導入")
            
            if submit_upload_novel and uploaded_docx and novel_upload_title:
                try:
                    doc = docx.Document(uploaded_docx)
                    full_text_list = []
                    for para in doc.paragraphs:
                        if para.text.strip():
                            full_text_list.append(para.text)
                    full_text = "\n\n".join(full_text_list)
                    
                    chunk_size = 1000
                    text_chunks = [full_text[i:i+chunk_size] for i in range(0, len(full_text), chunk_size)]
                    
                    if text_chunks:
                        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
                        c = conn.cursor()
                        c.execute("DELETE FROM novels WHERE title=?", (novel_upload_title,))
                        
                        for page_idx, chunk_data in enumerate(text_chunks, start=1):
                            c.execute(
                                "INSERT INTO novels (title, type, page_num, content) VALUES (?, ?, ?, ?)",
                                (novel_upload_title, novel_upload_type, page_idx, chunk_data)
                            )
                        conn.commit()
                        conn.close()
                        
                        del doc, full_text_list, full_text, text_chunks
                        gc.collect()
                        st.cache_data.clear()
                        st.success(f"🎉 滿血入庫！《{novel_upload_title}》已成功切分成 {page_idx} 頁儲存！")
                        st.rerun()
                except Exception as docx_err:
                    st.error(f"❌ Word 解析失敗，請檢查格式。錯誤詳情：{str(docx_err)}")

        st.markdown("---")
        with st.expander("➕ 上架新作品（一樓：詩和散文專用）"):
            new_title = st.text_input("作品名稱")
            new_content = st.text_area("作品內容", height=150)
            is_poem_checked = st.checkbox("📜 這是詩（全篇完整排版打開）")
            if st.button("確認上架"):
                if new_title and new_content:
                    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
                    c = conn.cursor()  
                    c.execute("INSERT INTO books (title, content, is_poem) VALUES (?, ?, ?)", (new_title, new_content, 1 if is_poem_checked else 0))
                    conn.commit()
                    conn.close()
                    st.cache_data.clear()
                    st.success(f"🎉 《{new_title}》已匯入一樓書架！")
                    st.rerun()

        st.markdown("---")
        st.subheader("🛡️ 館藏備份與管理")
        
        backup_data = [{"title": r[1], "content": r[2], "is_poem": r[3]} for r in all_books_list]
        st.download_button(label="💾 下載一樓館藏備份 (.json)", data=json.dumps(backup_data, ensure_ascii=False, indent=2), file_name="zhuoji_books_backup.json", mime="application/json")
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.write("🔄 **一樓備份資料回灌：**")
        restore_file = st.file_uploader("選擇之前的備份檔案 (.json) 進行回灌", type=["json"], key="json_restore_uploader")
        if restore_file is not None:
            if st.button("⚡ 確認執行備份回灌", key="confirm_restore_btn"):
                try:
                    raw_json = json.load(restore_file)
                    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
                    c = conn.cursor()
                    c.execute("DELETE FROM books")
                    for item in raw_json:
                        c.execute("INSERT INTO books (title, content, is_poem) VALUES (?, ?, ?)", (item["title"], item["content"], item["is_poem"]))
                    conn.commit()
                    conn.close()
                    
                    st.cache_data.clear()
                    st.success("🎉 一樓館藏備份回灌成功！已重新覆蓋書架。")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 回灌失敗，請確保備份 JSON 格式正確。錯誤訊息: {e}")

        st.markdown("---")
        if st.button("🗑️ 清空留緣牆"):
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            c = conn.cursor() 
            c.execute("DELETE FROM stamps")
            conn.commit()
            conn.close()
            st.cache_data.clear()
            st.rerun()
            
        st.write("📋 **一樓作品管理列表：**")
        for bk in all_books_list:
            bk_id, bk_title, _, bk_poem = bk
            col1, col2 = st.columns([5, 1])
            with col1: st.write(f"《{bk_title}》 {'[📜 詩]' if bk_poem==1 else '[📝 散文]'}")
            with col2:
                if st.button("下架", key=f"del_{bk_id}"):
                    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
                    c = conn.cursor()
                    c.execute("DELETE FROM books WHERE id=?", (bk_id,))
                    conn.commit()
                    conn.close()
                    st.cache_data.clear()
                    st.rerun()

        st.write("📋 **二樓小說管理列表：**")
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT DISTINCT title, type FROM novels")
        all_db_novels = c.fetchall()
        conn.close()
        
        for n_title, n_type in all_db_novels:
            col1, col2 = st.columns([5, 1])
            with col1: st.write(f"《{n_title}》 【{n_type}】")
            with col2:
                if st.button("下架整部小說", key=f"del_novel_{n_title}"):
                    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
                    c = conn.cursor()
                    c.execute("DELETE FROM novels WHERE title=?", (n_title,))
                    conn.commit()
                    conn.close()
                    st.cache_data.clear()
                    st.rerun()
