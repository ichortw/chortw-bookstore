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
    IMAGE_VAULT_DIR = '/data/image_vault'  # 🖼️ 實體影像儲存庫
else:
    LOCAL_DATA_DIR = "data"
    if not os.path.exists(LOCAL_DATA_DIR):
        try:
            os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
            print(f"📡 [技術總監提示]：已成功自動建立【{LOCAL_DATA_DIR}】子資料夾以存放 SQLite 資料庫！")
        except Exception:
            pass
    DB_PATH = os.path.join(LOCAL_DATA_DIR, 'zhuoji_books.db')
    IMAGE_VAULT_DIR = os.path.join(LOCAL_DATA_DIR, 'image_vault')

if not os.path.exists(os.path.dirname(DB_PATH)):
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    except Exception:
        pass

if not os.path.exists(IMAGE_VAULT_DIR):
    try:
        os.makedirs(IMAGE_VAULT_DIR, exist_ok=True)
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
# 🖼️ 🔌 雙龍出海雙重影像保險箱機制 (核心升級)
# ==========================================
def get_local_image_base64(relative_path, mime_type="image/png"):
    """安全讀取專案中 static 資料夾下的本地圖片，失敗時自動安全降級為微量透明點"""
    if os.path.exists(relative_path):
        try:
            with open(relative_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode()
                return f"data:{mime_type};base64,{encoded_string}"
        except:
            pass
    return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

def get_vault_image_base64(filename, mime_type="image/png"):
    """從永久儲存空間中讀取管理員上傳的實體圖片"""
    target_path = os.path.join(IMAGE_VAULT_DIR, filename)
    if os.path.exists(target_path):
        try:
            with open(target_path, "rb") as f:
                encoded_string = base64.b64encode(f.read()).decode()
                return f"data:{mime_type};base64,{encoded_string}"
        except:
            pass
    return None

# 🚀 雙龍出海：第一路線（優先加載 3 張 GitHub 本地管線內連圖）
CHAHU_BASE64 = get_local_image_base64("static/chahu2.gif", "image/gif")
CHAHU_SLEEP_BASE64 = get_local_image_base64("static/chahu-sleep.gif", "image/gif")
BANNER_BASE64 = get_local_image_base64("static/banner1.jpg", "image/jpeg")

# 🚀 雙龍出海：第二路線（如果本地缺少實體圖，尋找影像儲存箱內店長直傳覆蓋的圖檔）
vault_chahu = get_vault_image_base64("chahu2.gif", "image/gif")
vault_sleep = get_vault_image_base64("chahu-sleep.gif", "image/gif")
vault_banner = get_vault_image_base64("banner1.jpg", "image/jpeg")

if vault_chahu: CHAHU_BASE64 = vault_chahu
if vault_sleep: CHAHU_SLEEP_BASE64 = vault_sleep
if vault_banner: BANNER_BASE64 = vault_banner

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
                st.success(st.session_state.touyuan_feedback)
            else:
                st.error(st.session_state.touyuan_feedback)
            del st.session_state.touyuan_feedback

        if current_stamps:
            river_html = '<div class="touyuan-river">'
            for stamp in current_stamps:
                river_html += f'<span class="river-fragment"> 🪵 {stamp} 🌿 </span>'
            river_html += '</div>'
            st.markdown(river_html, unsafe_allow_html=True)
        else:
            st.caption("河流靜止中，期待第一片落葉。")

    with col_chahu:
        st.markdown('<div class="chahu-minimal-area">', unsafe_allow_html=True)
        is_sleeping = (st.session_state.chat_turns in st.session_state.burst_turns)
        chosen_avatar = CHAHU_SLEEP_BASE64 if is_sleeping else CHAHU_BASE64
        
        smoke_html = """
        <div class="smoke-container">
            <div class="smoke-line smoke-1"></div>
            <div class="smoke-line smoke-2"></div>
        </div>
        """ if not is_sleeping else ""

        st.markdown(f"""
            <div class="avatar-area">
                {smoke_html}
                <img class="chahu-photo" src="{chosen_avatar}">
            </div>
        """, unsafe_allow_html=True)
        
        if is_sleeping:
            st.markdown('<div class="chahu-title">💤 伙記茶壺（深層睡眠中...）</div>', unsafe_allow_html=True)
            st.markdown('<div class="chahu-subtitle">「呼……呼……店長……大腦……不要扣貓罐頭……」</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="chahu-title">🐈 伙記茶壺 (Cat Bot)</div>', unsafe_allow_html=True)
            st.markdown('<div class="chahu-subtitle">「我正在櫃檯擦拭著高熵玻璃杯，帶有 300% 的好奇心。想聊聊館藏，還是說說你現在的心情？」</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        if "messages" not in st.session_state:
            st.session_state.messages = []

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        if user_chat := st.chat_input("向美短小貓茶壺搭話...", key="chahu_chat_input_v2"):
            st.session_state.messages.append({"role": "user", "content": user_chat})
            with st.chat_message("user"):
                st.write(user_chat)

            with st.chat_message("assistant"):
                chahu_reply_container = st.empty()
                
                if is_sleeping:
                    time.sleep(1.2)
                    bot_reply = "（茶壺把身體縮得更緊了，耳朵微微抖動了一下，發出均勻的微弱呼嚕聲，看來完全沒有醒來的跡象……）"
                    chahu_reply_container.write(bot_reply)
                    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                    st.session_state.chat_turns += 1
                    st.rerun()
                
                bot_reply = "我……頭暈暈的，突然想不起來要說什麼喵。"
                
                # 彙整上下文館藏知識
                knowledge_context = "【高熵咖啡店現有館藏簡介清單】:\n"
                for i, bk in enumerate(all_books_list):
                    bk_id, bk_title, bk_content, bk_poem = bk
                    b_type = "詩歌" if bk_poem == 1 else "散文/隨筆"
                    knowledge_context += f"{i+1}. 《{bk_title}》 [{b_type}] 內容摘錄: {bk_content[:140]}...\n"
                
                conn = sqlite3.connect(DB_PATH, check_same_thread=False)
                c = conn.cursor()
                c.execute("SELECT content FROM memo WHERE id=1")
                memo_row = c.fetchone()
                shared_memo = memo_row[0] if memo_row else ""
                conn.close()
                
                if shared_memo:
                    knowledge_context += f"\n【店長留在水吧的便條紙內容】:\n{shared_memo}\n"

                # 建立完整的歷史記憶
                history_payload = []
                for m in st.session_state.messages[-7:]:
                    history_payload.append({"role": "user" if m["role"]=="user" else "model", "parts": [m["content"]]})
                
                brain_mode = st.session_state.chahu_selected_brain
                
                if "Gemini" in brain_mode:
                    if not has_gemini:
                        bot_reply = "🐾 我聞不到密碼線香的味道（後台未配置 GEMINI_API_KEY），無法啟動思維本能喵！"
                        chahu_reply_container.write(bot_reply)
                    else:
                        try:
                            model = genai.GenerativeModel(
                                "gemini-2.5-flash",
                                system_instruction=f"{CHAHU_PROMPT_FROM_DB}\n\n{knowledge_context}"
                            )
                            chat_session = model.start_chat(history=[])
                            for hp in history_payload[:-1]:
                                try: chat_session.send_message(hp["parts"][0])
                                catch: pass
                            
                            response = chat_session.send_message(user_chat, request_options={"timeout": 22.0})
                            bot_reply = response.text
                            chahu_reply_container.write(bot_reply)
                            
                            try:
                                p_tk = response.usage_metadata.prompt_token_count
                                c_tk = response.usage_metadata.candidates_token_count
                                log_api_cost("Google Gemini", p_tk, c_tk)
                            except:
                                pass
                        except Exception as e:
                            bot_reply = f"🐾 喵嗚……與雲端大腦神經共鳴時發生了不可抗力混亂 (錯誤: {str(e)})"
                            chahu_reply_container.write(bot_reply)
                else:
                    if not groq_api_key:
                        bot_reply = "🐾 閃電核心缺乏燃料（後台未配置 GROQ_API_KEY），請店長先去水吧補給！"
                        chahu_reply_container.write(bot_reply)
                    else:
                        try:
                            groq_headers = {"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"}
                            groq_messages = [
                                {"role": "system", "content": f"{CHAHU_PROMPT_FROM_DB}\n\n{knowledge_context}"}
                            ]
                            for m in st.session_state.messages[-6:]:
                                groq_messages.append({"role": m["role"], "content": m["content"]})
                                
                            payload = {
                                "model": "llama3-8b-8192",
                                "messages": groq_messages,
                                "temperature": 0.76,
                                "max_tokens": 1024
                            }
                            res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=groq_headers, timeout=20.0)
                            if res.status_code == 200:
                                res_data = res.json()
                                bot_reply = res_data["choices"][0]["message"]["content"]
                                chahu_reply_container.write(bot_reply)
                                try:
                                    p_tk = res_data["usage"]["prompt_tokens"]
                                    c_tk = res_data["usage"]["completion_tokens"]
                                    log_api_cost("Groq (Llama-3)", p_tk, c_tk)
                                except:
                                    pass
                            else:
                                bot_reply = f"🐾 Groq 閃電大腦拒絕了連線要求喵。(代碼: {res.status_code})"
                                chahu_reply_container.write(bot_reply)
                        except Exception as e:
                            bot_reply = f"🐾 喵嗚……閃電大腦迴路短路 (錯誤: {str(e)})"
                            chahu_reply_container.write(bot_reply)

            st.session_state.messages.append({"role": "assistant", "content": bot_reply})
            
            # 量子隔空翻書魔法解析
            open_book_match = re.search(r'\[\[OPEN_BOOK:(.*?)\]\]', bot_reply)
            if open_book_match:
                target_book_name = open_book_match.group(1).strip()
                matched_db_title = None
                for bk in all_books_list:
                    if bk[1].lower() == target_book_name.lower():
                        matched_db_title = bk[1]
                        break
                if matched_db_title:
                    st.session_state.current_book_title = matched_db_title
                    st.session_state.is_fully_expanded = False
                    if f"slice_start_{matched_db_title}" in st.session_state:
                        del st.session_state[f"slice_start_{matched_db_title}"]
                    st.session_state.scroll_to_top_trigger = True
                    st.toast(f"🐈 茶壺施展魔法幫你翻開了：《{matched_db_title}》！")
                    time.sleep(0.5)
            
            st.session_state.chat_turns += 1
            if st.session_state.chat_turns > 15:
                st.session_state.chat_turns = 0
                st.session_state.burst_turns = random.sample(range(2, 8), 2)
            st.rerun()

# ==========================================
# 【分頁二：🥃 二樓小說世界】
# ==========================================
with tab2:
    st.subheader("🥃 二樓小說閣樓")
    
    col_nav, col_paper = st.columns([1.0, 2.5])
    
    with col_nav:
        st.markdown("🎯 **請挑選一本秘藏本：**")
        has_any_novel = False
        
        for n_type in ["長篇小說", "中篇小說", "短篇小說"]:
            titles = novels_menu.get(n_type, [])
            if titles:
                has_any_novel = True
                st.write(f"🔹 **{n_type}**")
                for t in titles:
                    is_active = (st.session_state.active_novel_title == t)
                    label = f"📖 《{t}》" if is_active else f"《{t}》"
                    if st.button(label, key=f"nv_btn_{t}"):
                        st.session_state.active_novel_title = t
                        st.session_state.active_novel_type = n_type
                        st.session_state.novel_page_num = 1
                        st.rerun()
                        
        if not has_any_novel:
            st.info("二樓目前空蕩蕩的，店長還沒在後台架設連載。")

    with col_paper:
        if st.session_state.active_novel_title:
            cur_title = st.session_state.active_novel_title
            cur_type = st.session_state.active_novel_type
            cur_page = st.session_state.novel_page_num
            
            p_content, max_page = fetch_novel_page_cached(cur_title, cur_page)
            
            st.markdown(f"### 《{cur_title}》 <span style='font-size:14px; color:#888;'>【{cur_type}】</span>", unsafe_allow_html=True)
            
            st.markdown('<div class="novel-container">', unsafe_allow_html=True)
            protected_novel = inject_watermark(p_content)
            formatted_novel = protected_novel.replace("\n", "<br>").replace("\\n", "<br>")
            st.markdown(f'<div class="novel-paper-text">{formatted_novel}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns([1, 2, 1])
            with c1:
                if st.button("⬅️ 上一頁", disabled=(cur_page <= 1)):
                    st.session_state.novel_page_num = max(1, cur_page - 1)
                    st.rerun()
            with c2:
                st.markdown(f"<p style='text-align:center; color:#777; margin-top:8px;'>第 {cur_page} / {max_page} 頁</p>", unsafe_allow_html=True)
            with c3:
                if st.button("下一頁 ➡️", disabled=(cur_page >= max_page)):
                    st.session_state.novel_page_num = min(max_page, cur_page + 1)
                    st.rerun()
        else:
            st.write("---")
            st.caption("👈 請從左側點擊您想翻開的小說。")

# ==========================================
# 【分頁三：🍸 水吧後台管理與極限儀表板】
# ==========================================
with tab3:
    st.subheader("🍸 水吧秘密後台")
    
    access_password = st.text_input("請輸入店長特許金鑰鑰匙：", type="password", key="manager_pwd_v2")
    
    if access_password == st.secrets.get("MANAGER_PASSWORD", "zhuoji666"):
        st.success("🔓 驗證通過！店長請進，開始掌控高熵世界的內部秩序。")
        st.markdown("---")
        
        # 📊 🛠️ 炫彩駭客綠極限監測儀表板
        st.subheader("📊 核心高熵運行狀態與 AI 帳本（極限監測）")
        
        # 實時採集核心探針數據
        mem_info = psutil.virtual_memory()
        mem_used_mb = mem_info.used / (1024 * 1024)
        mem_total_mb = mem_info.total / (1024 * 1024)
        mem_percent = mem_info.percent
        cpu_percent = psutil.cpu_percent(interval=None)
        
        billing_summary = get_accumulated_api_billing()
        gemini_billing = billing_summary.get("Google Gemini", {"p": 0, "c": 0, "cost": 0.0})
        groq_billing = billing_summary.get("Groq (Llama-3)", {"p": 0, "c": 0, "cost": 0.0})
        total_api_cost_usd = gemini_billing["cost"] + groq_billing["cost"]
        
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        
        with m_col1:
            st.markdown(f"""
            <div class="metric-card-box">
                <div class="metric-card-title">🖥️ 伺服器 CPU 使用率</div>
                <div class="metric-card-value">{cpu_percent}%</div>
                <div class="metric-card-sub">探針實時刷新</div>
            </div>
            """, unsafe_allow_html=True)
            
        with m_col2:
            st.markdown(f"""
            <div class="metric-card-box">
                <div class="metric-card-title">💾 記憶體耗能 (Memory)</div>
                <div class="metric-card-value">{mem_percent}%</div>
                <div class="metric-card-sub">{mem_used_mb:.1f} / {mem_total_mb:.1f} MB</div>
            </div>
            """, unsafe_allow_html=True)
            
        with m_col3:
            st.markdown(f"""
            <div class="metric-card-box">
                <div class="metric-card-title">🤖 雙大腦對帳總花費</div>
                <div class="metric-card-value">${total_api_cost_usd:.5f}</div>
                <div class="metric-card-sub">USD 美金累計</div>
            </div>
            """, unsafe_allow_html=True)
            
        with m_col4:
            st.markdown(f"""
            <div class="metric-card-box">
                <div class="metric-card-title">📚 高熵載體總容量</div>
                <div class="metric-card-value">{len(all_books_list)} 篇</div>
                <div class="metric-card-sub">一樓現存作品數</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("🔍 檢視個別 AI 大腦代幣流水明細"):
            st.markdown(f"""
            - **Google Gemini (2.5-Flash)**: 
              - 傳入 Prompt Tokens: `{gemini_billing['p']}`
              - 生成 Completion Tokens: `{gemini_billing['c']}`
              - 預估累積花費: `${gemini_billing['cost']:.5f}` USD
            - **Groq (Llama-3-8b)**:
              - 傳入 Prompt Tokens: `{groq_billing['p']}`
              - 生成 Completion Tokens: `{groq_billing['c']}`
              - 預估累積花費: `${groq_billing['cost']:.5f}` USD
            """)
            if st.button("🗑️ 清空所有 AI 帳本流水流水紀錄", help="重置計費帳本歷史"):
                conn = sqlite3.connect(DB_PATH, check_same_thread=False)
                c = conn.cursor()
                c.execute("DELETE FROM api_billing_v2")
                conn.commit()
                conn.close()
                st.success("已成功重置對帳單流水。")
                st.rerun()

        st.markdown("---")
        
        # 🖼️ ⚙️ 雙龍出海：實體影像上傳與管理面板
        st.subheader("🖼️ 影像直傳保險箱（支持直傳覆蓋）")
        st.info(f"當前影像保險箱路徑：`{IMAGE_VAULT_DIR}`。在此上傳圖片可覆蓋前端對應的元件。")
        
        img_col1, img_col2 = st.columns(2)
        with img_col1:
            st.markdown("#### 📤 上傳更換圖片")
            target_filename = st.selectbox("請選擇要更換的目標元件：", ["chahu2.gif", "chahu-sleep.gif", "banner1.jpg"])
            uploaded_img_file = st.file_uploader("選擇圖片檔案：", type=["gif", "jpg", "jpeg", "png"], key="vault_uploader")
            
            if st.button("💾 儲存並覆蓋圖片"):
                if uploaded_img_file is not None:
                    try:
                        file_bytes = uploaded_img_file.read()
                        target_file_path = os.path.join(IMAGE_VAULT_DIR, target_filename)
                        with open(target_file_path, "wb") as f:
                            f.write(file_bytes)
                        st.success(f"🎉 成功！圖片已寫入保險箱並覆蓋：`{target_filename}`")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"寫入檔案失敗：{str(e)}")
                else:
                    st.warning("請先選取要上傳的檔案。")
                    
        with img_col2:
            st.markdown("#### 📂 目前保險箱內實體圖檔")
            existing_vault_files = os.listdir(IMAGE_VAULT_DIR) if os.path.exists(IMAGE_VAULT_DIR) else []
            if existing_vault_files:
                for vf in existing_vault_files:
                    vf_path = os.path.join(IMAGE_VAULT_DIR, vf)
                    vf_size = os.path.getsize(vf_path) / 1024
                    st.write(f"📁 `{vf}` ({vf_size:.1f} KB)")
                    if st.button(f"🗑️ 刪除 {vf}", key=f"del_img_{vf}"):
                        try:
                            os.remove(vf_path)
                            st.success(f"已刪除 `{vf}`，系統將自動回歸 GitHub 預設圖。")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"刪除失敗：{str(e)}")
            else:
                st.caption("保險箱內暫無外置上傳圖片，目前全自動走第一路線（讀取專案預設 static 圖檔）。")

        st.markdown("---")
        
        # 🐱 ⚙️ 茶壺核心神經突觸與設定
        st.subheader("🐱 伙記茶壺設定與雲端大腦思維選擇")
        
        current_brain_selection = st.radio(
            "請為茶壺小貓點亮神經元大腦：",
            ["Google Gemini", "Groq (Llama-3 超高速)"],
            index=0 if CURRENT_ACTIVE_BRAIN_FROM_DB == "Google Gemini" else 1,
            horizontal=True
        )
        
        if current_brain_selection != CURRENT_ACTIVE_BRAIN_FROM_DB:
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            c = conn.cursor()
            c.execute("UPDATE chahu_brain SET active_brain=? WHERE id=1", (current_brain_selection,))
            conn.commit()
            conn.close()
            st.cache_data.clear()
            st.success(f"🚀 大腦切換成功！茶壺現在切換至：{current_brain_selection}")
            st.rerun()
            
        new_prompt = st.text_area("修改茶壺小貓的內在靈魂 (System Prompt)：", value=CHAHU_PROMPT_FROM_DB, height=250)
        if st.button("💾 灌輸新靈魂"):
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            c = conn.cursor()
            c.execute("UPDATE chahu_brain SET prompt=? WHERE id=1", (new_prompt,))
            conn.commit()
            conn.close()
            st.cache_data.clear()
            st.success("✨ 茶壺打起精神，完美吸收了新的記憶靈魂！")
            st.rerun()

        st.markdown("---")

        # ✍️ 💼 一樓作品管理與上傳模組
        st.subheader("✍️ 一樓新散文與詩歌上傳")
        with st.form("upload_book_form", clear_on_submit=True):
            b_title = st.text_input("作品名稱 (例如：宇宙的孤寂)")
            b_poem = st.checkbox("這是一首詩歌 (自動切換至全置中排版)")
            b_content = st.text_area("作品內文", height=200)
            sub_btn = st.form_submit_button("🚀 發佈到一樓咖啡店")
            
            if sub_btn and b_title and b_content:
                conn = sqlite3.connect(DB_PATH, check_same_thread=False)
                c = conn.cursor()
                c.execute("INSERT INTO books (title, content, is_poem) VALUES (?, ?, ?)", (b_title, b_content, 1 if b_poem else 0))
                conn.commit()
                conn.close()
                st.cache_data.clear()
                st.success(f"🎉 發佈成功！《{b_title}》已經安全送上一樓書架。")
                st.rerun()

        # 📖 💼 二樓小說管理與 Word (.docx) 上傳連載模組
        st.subheader("📚 二樓小說批量上傳連載櫃（防權限衝突安全部署版）")
        st.info("店長可以直接丟入繁體中文的 Word (.docx) 檔案。系統會自動以「空行」作為分頁符號，把小說切成一頁頁完美送入二樓，大幅度節省排版青春！")
        
        with st.form("upload_novel_docx_form", clear_on_submit=True):
            n_title = st.text_input("小說系列名稱 (例如：深夜微光)")
            n_type = st.selectbox("小說體裁類型：", ["長篇小說", "中篇小說", "短篇小說"])
            uploaded_docx = st.file_uploader("上傳小說 Word (.docx) 檔案：", type=["docx"])
            novel_sub_btn = st.form_submit_button("⚡ 啟動多維空間分頁切割排版")
            
            if novel_sub_btn and n_title and uploaded_docx:
                try:
                    doc = docx.Document(uploaded_docx)
                    full_paras = [p.text for p in doc.paragraphs]
                    
                    pages = []
                    current_page_buffer = []
                    
                    for para in full_paras:
                        stripped = para.strip()
                        if not stripped:
                            if current_page_buffer:
                                pages.append("\n".join(current_page_buffer))
                                current_page_buffer = []
                        else:
                            current_page_buffer.append(para)
                            
                    if current_page_buffer:
                        pages.append("\n".join(current_page_buffer))
                        
                    if not pages:
                        st.error("⚠️ 偵測失敗！Word 文件裡似乎沒有任何有效文字。")
                    else:
                        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
                        c = conn.cursor()
                        c.execute("SELECT MAX(page_num) FROM novels WHERE title=?", (n_title,))
                        existing_max = c.fetchone()[0] or 0
                        
                        for idx, p_text in enumerate(pages):
                            assigned_page = existing_max + idx + 1
                            c.execute("INSERT INTO novels (title, type, page_num, content) VALUES (?, ?, ?, ?)",
                                      (n_title, n_type, assigned_page, p_text))
                        
                        conn.commit()
                        conn.close()
                        st.cache_data.clear()
                        st.success(f"🎉 批量部署成功！小說《{n_title}》成功切分並注入了 {len(pages)} 頁連載！")
                        st.rerun()
                except Exception as e:
                    st.error(f"💥 讀取 Word 檔案失敗，錯誤回報：{str(e)}")

        st.markdown("---")
        
        # 📋 ⚙️ 館藏刪除列表管理
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
                if st.button("下架系列", key=f"del_novel_{n_title}"):
                    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
                    c = conn.cursor()
                    c.execute("DELETE FROM novels WHERE title=?", (n_title,))
                    conn.commit()
                    conn.close()
                    st.cache_data.clear()
                    st.rerun()

        st.markdown("---")
        
        # 📝 ⚙️ 便條紙（共享備忘錄）
        st.subheader("📝 水吧檯共享便條紙 (茶壺聊天時會順便偷看這裡)")
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT content FROM memo WHERE id=1")
        row = c.fetchone()
        current_memo = row[0] if row else ""
        conn.close()
        
        new_memo = st.text_area("便條紙內容：", value=current_memo, height=120)
        if st.button("📌 貼上便條紙"):
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            c = conn.cursor()
            c.execute("UPDATE memo SET content=? WHERE id=1", (new_memo,))
            conn.commit()
            conn.close()
            st.cache_data.clear()
            st.success("便條紙已更新！茶壺在聊天時將自動參閱裡面的提示。")
            st.rerun()
            
        st.markdown("---")
        st.subheader("🧱 留緣牆黑名單審查與清洗")
        if current_stamps:
            for stamp in current_stamps:
                col1, col2 = st.columns([5, 1])
                with col1: st.caption(f"「{stamp}」")
                with col2:
                    if st.button("擦除", key=f"del_stamp_{stamp}"):
                        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
                        c = conn.cursor()
                        c.execute("DELETE FROM stamps WHERE content=?", (stamp,))
                        conn.commit()
                        conn.close()
                        st.cache_data.clear()
                        st.rerun()
        else:
            st.caption("留緣牆上目前一片潔淨。")
            
    elif access_password:
        st.error("🔑 密碼鎖芯錯位！這不是正確的店長特許鑰匙，請退回前台享用咖啡。")
