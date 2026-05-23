import streamlit as st
import sqlite3
import random
import json
import re
import os
from datetime import datetime
from groq import Groq
import base64

# =====================================================================
# 🛡️ 核心防禦模組一：零寬字元隱形數位指紋（IP 維護）
# =====================================================================
def inject_invisible_watermark(text, author_id="ZhuojiBookstore"):
    """
    在文章的字裡行間或段落暗中嵌入肉眼看不見的零寬度字元。
    """
    if not text:
        return text
    binary_signature = ''.join(format(ord(c), '08b') for c in author_id)
    invisible_code = ""
    for bit in binary_signature:
        if bit == '1':
            invisible_code += "\u200b"
        else:
            invisible_code += "\u200c"
            
    paragraphs = text.split('\n')
    watermarked_paragraphs = []
    for i, p in enumerate(paragraphs):
        if i == 0 and len(p) > 2:
            watermarked_paragraphs.append(p[:2] + invisible_code + p[2:])
        else:
            watermarked_paragraphs.append(p + invisible_code)
    return '\n'.join(watermarked_paragraphs)

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
你深知自己是個流落凡間的文青仙女，卻在今世被店長用極近乎免費的代價雇傭成了掌管高熵藏書閣的唯一書僮小貓。
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
# 🐈 優先讀取動態 chahu.gif，若無則讀取靜態 chahu.jpg
# ==========================================
img_base64 = ""
mime_type = "image/jpeg"

if os.path.exists("chahu.gif"):
    with open("chahu.gif", "rb") as image_file:
        img_base64 = base64.b64encode(image_file.read()).decode()
        mime_type = "image/gif"
elif os.path.exists("chahu.jpg"):
    with open("chahu.jpg", "rb") as image_file:
        img_base64 = base64.b64encode(image_file.read()).decode()
        mime_type = "image/jpeg"

# ==========================================
# 🖼️ 讀取店長設計的大招牌 Banner 背景圖 (banner.jpg)
# ==========================================
banner_base64 = ""
if os.path.exists("banner.jpg"):
    with open("banner.jpg", "rb") as banner_file:
        banner_base64 = base64.b64encode(banner_file.read()).decode()

# ==========================================
# 🔒 2. 全局 CSS 視覺注入與優化 (整合大招牌與 SEO 關鍵字)
# ==========================================
st.set_page_config(page_title="桌記書店", layout="wide")

# ✨ 透過 HTML components 注入 SEO 關鍵字與 Meta 描述
st.components.v1.html("""
    <script>
        var metaKeywords = window.parent.document.createElement('meta');
        metaKeywords.name = "keywords";
        metaKeywords.content = "桌記書店, 桌記, zhuoji, chortw, chort, 散文集, 小說, 詩集, 文藝書店, AI書僮, 茶壺小貓, 靈魂金句, 高熵藏書閣, 文青創作";
        window.parent.document.getElementsByTagName('head')[0].appendChild(metaKeywords);

        var metaDesc = window.parent.document.createElement('meta');
        metaDesc.name = "description";
        metaDesc.content = "歡迎光臨桌記書店。這裡是一座混亂字海裡的高熵藏書閣，收錄了店長精選的個人文學創作與詩集。";
        window.parent.document.getElementsByTagName('head')[0].appendChild(metaDesc);
        
        var metaAuthor = window.parent.document.createElement('meta');
        metaAuthor.name = "author";
        metaAuthor.content = "桌記書店店長";
        window.parent.document.getElementsByTagName('head')[0].appendChild(metaAuthor);

        // 🛡️ 核心防禦模組二：JS 鎖死右鍵與複製快捷鍵
        window.parent.document.addEventListener('contextmenu', event => event.preventDefault());
        window.parent.document.addEventListener('keydown', function(e) {
            if ((e.ctrlKey || e.metaKey) && e.keyCode == 67) {
                e.preventDefault();
                alert('『桌記書店』提醒您：原創文學作品受版權指紋護衛，禁止拷貝。');
                return false;
            }
        });
    </script>
""", height=0, width=0)

# 注入全局 CSS 與自訂 Banner 樣式
st.markdown(f"""
    <style>
    /* 🛡️ 核心防禦模組二：CSS 鎖死全站文字反白選取 */
    .stApp, .content-text, .poem-text, p, span, div, h1, h2, h3, h4, h5, h6 {{
        -webkit-user-select: none !important;
        -moz-user-select: none !important;
        -ms-user-select: none !important;
        user-select: none !important;
    }}

    .block-container {{
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
    }}
    
    header[data-testid="stHeader"] {{
        background-color: transparent !important;
        pointer-events: none !important; 
    }}
    
    /* 全面封殺與隱藏新版功能按鈕 */
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
    
    /* ✨ 大招牌 Banner CSS */
    .zhuoji-banner {{
        background-image: url('data:image/jpeg;base64,{banner_base64}');
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        width: 100%;
        height: 220px;
        border-radius: 8px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.15);
        margin-bottom: 25px;
    }}
    div.zhuoji-banner {{ background-color: #e8ded1; }}
    
    .content-text {{ font-size: 20px !important; line-height: 1.8 !important; color: #2d3748; text-align: justify; }}
    .poem-text {{ font-size: 22px !important; line-height: 2.0 !important; color: #4a5568; text-align: center; letter-spacing: 2px; }}
    
    /* 貓咪實體視覺 */
    .avatar-area {{ position: relative; display: inline-block; margin-bottom: 8px; }}
    .chahu-photo {{ width: 160px; height: auto; object-fit: contain; border-radius: 4px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
    
    .chahu-title {{ font-size: 16px; font-weight: bold; color: #4a341b; letter-spacing: 1px; margin-bottom: 2px; }}
    .chahu-subtitle {{ font-size: 13px; color: #7c6a56; line-height: 1.4; margin-bottom: 5px; }}
    
    div.stButton > button[key^="sink_btn"] {{
        background-color: #f4ebe1 !important;
        color: #5c4b37 !important;
        border: 1px solid #dacbb5 !important;
        border-radius: 4px !important;
    }}
    
    .touyuan-river {{
        background-color: #fdfbf7;
        border-left: 3px solid #dacbb5;
        padding: 14px;
        border-radius: 4px;
        color: #3a2e2b;
        font-size: 16px;
        text-align: justify;
    }}
    
    /* ===================================================================== */
    /* 🎨 🛡️ 核心修正：蜜罐輸入框「全面文青裝飾線偽裝術」 */
    /* ===================================================================== */
    /* 精準捕捉表單中帶有特定 Key 的輸入框包裝容器，徹底扒掉它的灰色背景與邊框 */
    div[data-testid="stForm"] div[data-slow-key="chahu_honeypot_1"],
    div[data-testid="stForm"] div[data-slow-key="chahu_honeypot_2"] {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin: 5px 0 !important;
    }}
    
    /* 將輸入框本體偽裝成一行淡淡的、無侵入感的文青風排版居中裝飾字 */
    div[data-testid="stForm"] div[data-slow-key="chahu_honeypot_1"] input,
    div[data-testid="stForm"] div[data-slow-key="chahu_honeypot_2"] input {{
        background: transparent !important;
        border: none !important;
        color: #bfae99 !important; /* 優雅的淡棕色 */
        font-family: "Noto Serif TC", serif !important;
        font-style: italic !important;
        font-size: 13px !important;
        text-align: center !important;
        pointer-events: none !important; /* 人類點不到它 */
        cursor: default !important;
    }}
    
    /* 拔掉蜜罐輸入框上方的紅星或標籤文字 */
    div[data-slow-key="chahu_honeypot_1"] label,
    div[data-slow-key="chahu_honeypot_2"] label {{
        display: none !important;
    }}
    </style>
""", unsafe_allow_html=True)

st.markdown("<div id='bookstore_top_anchor'></div>", unsafe_allow_html=True)
st.markdown('<div class="zhuoji-banner"></div>', unsafe_allow_html=True)

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

if "scroll_to_top_trigger" not in st.session_state:
    st.session_state.scroll_to_top_trigger = False

active_title = st.session_state.current_book_title
active_content = "目前書架沒有任何書籍。"
active_is_poem = 0
for bk in all_books_list:
    if bk[1] == active_title:
        active_content = bk[2]
        active_is_poem = bk[3]
        break

protected_active_content = inject_invisible_watermark(active_content)

slice_key = f"slice_start_{active_title}"
if slice_key not in st.session_state and len(protected_active_content) > 200 and not active_is_poem:
    st.session_state[slice_key] = random.randint(0, len(protected_active_content) - 200)
elif slice_key not in st.session_state:
    st.session_state[slice_key] = 0

verse_key = f"verse_{active_title}"
if verse_key not in st.session_state:
    if all_books_list and active_title != "無":
        try:
            groq_key = st.secrets["GROQ_API_KEY"]
            temp_client = Groq(api_key=groq_key)
            verse_prompt = f"你是一個深邃的文學家。請閱讀以下作品，為其創作成一句不超過20個字、極具詩意與畫面感的靈魂金句：\\n書名：《{active_title}》"
            completion_verse = temp_client.chat.completions.create(
                model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": verse_prompt}], temperature=0.8, max_tokens=40
            )
            st.session_state[verse_key] = completion_verse.choices[0].message.content.strip().replace("「","").replace("」","")
        except:
            st.session_state[verse_key] = "水煙裊裊，字裡行間皆是光陰。"
    else:
        st.session_state[verse_key] = "書架空置，靜候新章。"

if st.session_state.scroll_to_top_trigger:
    st.components.v1.html("""
        <script>
            window.parent.document.getElementById('bookstore_top_anchor').scrollIntoView({behavior: 'smooth'});
        </script>
    """, height=0, width=0)
    st.session_state.scroll_to_top_trigger = False  

tab1, tab2 = st.tabs(["🍵 茶座", "⚙️ 書閣"])

# ==========================================
# 【分頁一：雲端書館與美短貓陪讀】
# ==========================================
with tab1:
    col_book, col_chahu = st.columns([1.6, 1.0])
    
    with col_book:
        if all_books_list:
            st.subheader(f"《{st.session_state.current_book_title}》")
            shuffled_titles = st.session_state.entropy_order
            idx = shuffled_titles.index(active_title) if active_title in shuffled_titles else 0
            st.markdown(f"**✨ {st.session_state[verse_key]}**")
            
            selected_title = st.selectbox(
                "隱藏選單：", shuffled_titles, index=idx, label_visibility="collapsed",
                key=f"book_sync_{st.session_state.sync_rerun_key}"
            )
            if selected_title != st.session_state.current_book_title:
                st.session_state.current_book_title = selected_title
                st.session_state.is_fully_expanded = False
                st.rerun()

            if st.button("📦 翻箱", key="top_unbox_btn"):
                remain_titles = [b[1] for b in all_books_list if b[1] != st.session_state.current_book_title] or [b[1] for b in all_books_list]
                chosen = random.choice(remain_titles)
                st.session_state.current_book_title = chosen
                st.session_state.is_fully_expanded = False
                st.session_state.sync_rerun_key += 1
                st.session_state.scroll_to_top_trigger = True  
                st.rerun()

            st.markdown("---")
            
            if active_is_poem == 1:
                st.markdown(f'<div class="poem-text">{protected_active_content.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
            else:
                if len(protected_active_content) > 200 and not st.session_state.is_fully_expanded:
                    ps = st.session_state[slice_key]
                    st.markdown(f'<div class="content-text">...... {protected_active_content[ps:ps+200]} ......</div>', unsafe_allow_html=True)
                    if st.button("...想繼續讀", key="sink_btn"):
                        st.session_state.is_fully_expanded = True
                        st.rerun()
                else:
                    st.markdown(f'<div class="content-text">{protected_active_content.replace("\n", "<br>")}</div>', unsafe_allow_html=True)

        st.subheader("🛡️ 投緣牆")
        with st.form("touyuan_form", clear_on_submit=True):
            visitor_input = st.text_input("緣份啊，你寫一句茶壼喜歡的句子，別多過20字，投進來，她會幫你貼上投緣牆，她要給句子們結集成詩，來吧！", max_chars=100)
            
            # 🎨 🛡️ 核心改造：使用容器包裝蜜罐，並透過預填文字將其徹底偽裝成店內風格的「優雅文字裝飾線」
            with st.container():
                st.markdown('<div data-slow-key="chahu_honeypot_1">', unsafe_allow_html=True)
                bot_trap_1 = st.text_input("Decor Line 1", value="—— 🍃 字裡行間，皆是時光 ——", label_visibility="collapsed")
                st.markdown('</div>', unsafe_allow_html=True)
                
            with st.container():
                st.markdown('<div data-slow-key="chahu_honeypot_2">', unsafe_allow_html=True)
                bot_trap_2 = st.text_input("Decor Line 2", value="—— 🍵 水煙裊裊，靜候緣份 ——", label_visibility="collapsed")
                st.markdown('</div>', unsafe_allow_html=True)
            
            submitted = st.form_submit_button("✨ 投緣")
            
            if submitted and visitor_input:
                # 判斷蜜罐是否被更動（預填文字被洗掉或修改即代表是盲目填表單的機器人）
                if bot_trap_1 != "—— 🍃 字裡行間，皆是時光 ——" or bot_trap_2 != "—— 🍵 水煙裊裊，靜候緣份 ——":
                    st.session_state.touyuan_feedback = "thank you"
                else:
                    words = re.findall(r'[\u4e00-\u9fff]|[a-zA-Z]+', visitor_input)
                    if len(words) > 20:
                        st.warning("⚠️ 字數超過 20 字，請精簡靈魂。")
                    else:
                        try:
                            groq_key = st.secrets["GROQ_API_KEY"]
                            client = Groq(api_key=groq_key)
                            eval_prompt = f'審查留言（放寬標準，非髒話廣告即可通）："{visitor_input}"，請嚴格輸出JSON：{{"passed":true/false,"reply":"...貼到投緣牆了..."}}'
                            response = client.chat.completions.create(
                                model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": eval_prompt}], response_format={"type": "json_object"}
                            )
                            res_json = json.loads(response.choices[0].message.content)
                            st.session_state.touyuan_feedback = res_json["reply"]
                            if res_json["passed"]:
                                conn = sqlite3.connect('zhuoji_books.db')
                                c = conn.cursor()
                                c.execute("INSERT INTO stamps (content, created_at) VALUES (?, ?)", (visitor_input, datetime.now().strftime("%Y-%m-%d %H:%M")))
                                conn.commit()
                                conn.close()
                        except:
                            st.session_state.touyuan_feedback = "thank you"
                st.rerun()

        if "touyuan_feedback" in st.session_state:
            st.write(f"🐈🐾 茶壺：{st.session_state.touyuan_feedback}")
            del st.session_state.touyuan_feedback

        if current_stamps:
            st.markdown('<div class="touyuan-river">', unsafe_allow_html=True)
            st.markdown(f'<span>{"，".join([s.strip() for s in current_stamps])}</span>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with col_chahu:
        avatar_html = f'<img src="data:{mime_type};base64,{img_base64}" class="chahu-photo">' if img_base64 else ''
        st.markdown(f'<div class="chahu-minimal-area"><div class="avatar-area">{avatar_html}</div><div class="chahu-title">我是店長書僮「茶壺」</div></div>', unsafe_allow_html=True)
        
        if "messages" not in st.session_state: st.session_state.messages = []
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.write(re.sub(r'\[\[OPEN_BOOK:.*?\]\]', '', msg["content"]))
                
        if user_chat := st.chat_input("你要看什麼書呀？"):
            st.session_state.messages.append({"role": "user", "content": user_chat})
            st.session_state.chat_turns += 1
            with st.chat_message("user"): st.write(user_chat)
            try:
                groq_key = st.secrets["GROQ_API_KEY"]
                client = Groq(api_key=groq_key)
                catalog_summary = "\\n".join([f"· 《{b[1]}》" for b in all_books_list])
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile", 
                    messages=[{"role": "system", "content": CHAHU_PROMPT_FROM_DB + f"\\n【全店藏書】：\\n{catalog_summary}"},{"role": "user", "content": user_chat}]
                )
                chahu_reply = completion.choices[0].message.content
                match = re.search(r'\[\[OPEN_BOOK:(.*?)\]\]', chahu_reply)
                if match:
                    book_open_title = match.group(1).strip()
                    for bk in all_books_list:
                        if bk[1] == book_open_title:
                            st.session_state.current_book_title = book_open_title
                            st.session_state.is_fully_expanded = False
                            st.session_state.sync_rerun_key += 1
                            break
            except Exception as e:
                chahu_reply = f"😮‍💨 腦袋卡住了...（{str(e)}）"
            st.session_state.messages.append({"role": "assistant", "content": chahu_reply})
            with st.chat_message("assistant"): st.write(re.sub(r'\[\[OPEN_BOOK:.*?\]\]', '', chahu_reply))
            if match: st.rerun()

# ==========================================
# 【分頁二：管理員後台（藏書閣）】
# ==========================================
with tab2:
    st.header("⚙️ 作品上架與管理系統")
    admin_password = st.text_input("🔑 請輸入店長管理密碼", type="password")
    if admin_password == "Pint2012echo":
        st.success("🔓 店長身分驗證成功！")
        with st.expander("➕ 上架新作品"):
            new_title = st.text_input("作品名稱")
            new_content = st.text_area("作品內容", height=200)
            is_poem_checked = st.checkbox("📜 這是詩")
            if st.button("確認上架"):
                if new_title and new_content:
                    conn = sqlite3.connect('zhuoji_books.db')
                    c = conn.cursor()  
                    c.execute("INSERT INTO books (title, content, is_poem) VALUES (?, ?, ?)", (new_title, new_content, 1 if is_poem_checked else 0))
                    conn.commit()
                    conn.close()
                    st.success(f"🎉 《{new_title}》已匯入！")
                    st.rerun()
        for bk in all_books_list:
            bk_id, bk_title, _, _ = bk
            col1, col2 = st.columns([5, 1])
            with col1: st.write(f"《{bk_title}》")
            with col2:
                if st.button("下架", key=f"del_{bk_id}"):
                    conn = sqlite3.connect('zhuoji_books.db')
                    c = conn.cursor()
                    c.execute("DELETE FROM books WHERE id=?", (bk_id,))
                    conn.commit()
                    conn.close()
                    st.rerun()
