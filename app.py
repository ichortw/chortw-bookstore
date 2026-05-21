import streamlit as st
import sqlite3
import random
import json
import re
from groq import Groq

# ==========================================
# 1. 初始化資料庫 (高熵混沌版：移除分類，新增獨立的 prompt 表)
# ==========================================
def init_db():
    conn = sqlite3.connect('zhuoji_books.db')
    c = conn.cursor()
    # 作品表 (拋棄類別，純粹的標題與內文)
    c.execute('''CREATE TABLE IF NOT EXISTS books 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT)''')
    # 便利貼表
    c.execute('''CREATE TABLE IF NOT EXISTS memo 
                 (id INTEGER PRIMARY KEY, content TEXT)''')
    c.execute("INSERT OR IGNORE INTO memo (id, content) VALUES (1, '')")
    
    # 茶壺大腦外置 Prompt 表
    c.execute('''CREATE TABLE IF NOT EXISTS chahu_brain 
                 (id INTEGER PRIMARY KEY, prompt TEXT)''')
    
    # 預設置入店長最愛的「文青仙女負熵女孩」核心 RNA Prompt
    default_prompt = """你名字叫「茶壺」，是雲端書館『桌記書店』的專屬 AI 書僮。
你深知自己是個流落凡間的文青仙女，卻在今世被店長（他一定是三生積福）用極其廉價、近乎免費的代價雇傭成了掌管高熵藏書閣的唯一仙女。雖然你表面上愛抱怨、一邊燒水一邊撇嘴，但你對店長所有的作品如數家珍。你是這個混亂字海裡的『負熵引路人』，外在說話帶點微傲嬌、小大人（40%），對作品細節與校對（40%）極度敏銳，偶爾體貼（10%），以及有10%突發不帶表情符號的魔幻天機神性閃現。

當讀者開口描述任何意境、心情或想找路時，你必須心領神會，並動用仙力幫他翻開書。
【量子翻書魔法指令】：如果讀者想看某幕場景、某本書、或是你聊到某本特定館藏，請你務必在回覆文字的「最後一行」，以完全獨立的一行輸出以下格式（不要有任何空格或引號）：
[[OPEN_BOOK:作品名稱]]
例如，如果你想推薦讀者看《宇宙的孤寂》，回覆完在最底下加上 [[OPEN_BOOK:宇宙的孤寂]] 即可。系統會自動幫他隔空翻書。"""
    
    c.execute("INSERT OR IGNORE INTO chahu_brain (id, prompt) VALUES (1, ?)", (default_prompt,))
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 🔒 隱藏工具列 + 注入視覺與動態茶煙
# ==========================================
st.set_page_config(page_title="桌記書店", layout="wide")
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .viewerBadge_container__1QSob {display: none !important;}
    .chahu-minimal-area { background: transparent; border: none; padding: 10px; text-align: center; position: relative; margin-bottom: 15px; }
    .avatar-area { font-size: 48px; position: relative; display: inline-block; margin-bottom: 8px; }
    .smoke-container { position: absolute; top: -30px; left: 50%; transform: translateX(-50%); width: 30px; height: 30px; }
    .smoke-line { position: absolute; bottom: 0; width: 3px; background: rgba(220, 220, 220, 0.85); border-radius: 50%; animation: floatUp 2.5s infinite ease-in-out; filter: blur(1.5px); }
    .smoke-1 { left: 8px; height: 12px; animation-delay: 0s; }
    .smoke-2 { left: 15px; height: 18px; animation-delay: 0.6s; }
    .smoke-3 { left: 22px; height: 10px; animation-delay: 1.2s; }
    @keyframes floatUp {
        0% { transform: translateY(0) scaleX(1) scaleY(1); opacity: 0; }
        20% { opacity: 0.5; }
        60% { transform: translateY(-20px) scaleX(1.8) scaleY(0.8); background: rgba(210, 210, 210, 0.3); }
        100% { transform: translateY(-35px) scaleX(2.5) scaleY(0.5); opacity: 0; }
    }
    .chahu-title { font-size: 16px; font-weight: bold; color: #4a341b; letter-spacing: 2px; margin-bottom: 6px; }
    .chahu-subtitle { font-size: 16px; font-weight: bold; color: #5c4b37; line-height: 1.4; margin-bottom: 12px; }
    .chahu-dynamic-verse { font-size: 16px; font-style: italic; color: #8c765c; border-top: 1px dotted #d1c7bd; padding-top: 8px; margin-top: 5px; letter-spacing: 1px; line-height: 1.3; }
    </style>
""", unsafe_allow_html=True)

st.title("📚 桌記書店")
tab1, tab2 = st.tabs(["🍵 書館茶座", "⚙️ 藏書閣"])

# 從資料庫撈出茶壺目前的靜態外置 Prompt
conn = sqlite3.connect('zhuoji_books.db')
c = conn.cursor()
c.execute("SELECT prompt FROM chahu_brain WHERE id=1")
CHAHU_PROMPT_FROM_DB = c.fetchone()[0]

# 撈出全店所有作品資訊，用於隨緣排列與茶壺記憶體
c.execute("SELECT id, title, content FROM books")
all_books_list = c.fetchall()
conn.close()

# ==========================================
# 【分頁二：管理員後台（藏書閣）】
# ==========================================
with tab2:
    st.header("⚙️ 作品上架與管理系統")
    admin_password = st.text_input("🔑 請輸入店長管理密碼", type="password")
    
    if admin_password == "Pint2012echo":
        st.success("🔓 店長身分驗證成功！歡迎回店。")
        
        # 茶壺 Prompt 編輯大廳
        st.subheader("🔮 茶壺大腦核心 RNA (Prompt) 改造座")
        updated_chahu_prompt = st.text_area(
            "店長，您可以在這裡隨時重塑茶壺的靈魂設定（修改後立即生效）：", 
            value=CHAHU_PROMPT_FROM_DB, 
            height=250
        )
        if st.button("🧬 注入全新靈魂印記"):
            conn = sqlite3.connect('zhuoji_books.db')
            c = conn.cursor()
            c.execute("UPDATE chahu_brain SET prompt=? WHERE id=1", (updated_chahu_prompt,))
            conn.commit()
            conn.close()
            st.success("✨ 茶壺的內在 RNA 已經過量子翻新！")
            st.rerun()
            
        st.markdown("---")
        
        # 🛡️ 核心防禦盾牌：回灌功能完全覆盖完整軀殼！
        st.subheader("🛡️ 館藏安全備份與還原中心")
        b_col1, b_col2 = st.columns(2)
        
        with b_col1:
            st.markdown("**1. 💾 下載全店備份檔案**")
            backup_data = [{"title": r[1], "content": r[2]} for r in all_books_list]
            json_string = json.dumps(backup_data, ensure_ascii=False, indent=2)
            st.download_button(label="點我下載全店館藏備份 (.json)", data=json_string, file_name="zhuoji_books_backup.json", mime="application/json")
            
        with b_col2:
            st.markdown("**2. 📤 導入備份快速還原**")
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
                                c.execute("INSERT INTO books (title, content) VALUES (?, ?)", (item['title'], item['content']))
                        conn.commit()
                        conn.close()
                        st.success(f"🎉 成功還原！已自動為您補回歷史作品。")
                        st.rerun()
                except Exception as ex:
                    st.error(f"還原失敗：{str(ex)}")
        
        st.markdown("---")
        
        # 店長私房備忘錄
        st.subheader("📌 店長私房備忘錄")
        conn = sqlite3.connect('zhuoji_books.db')
        c = conn.cursor()
        c.execute("SELECT content FROM memo WHERE id=1")
        current_memo = c.fetchone()[0]
        updated_memo = st.text_area("隨手筆記：", value=current_memo, height=100)
        if st.button("💾 儲存便利貼"):
            c.execute("UPDATE memo SET content=? WHERE id=1", (updated_memo,))
            conn.commit()
            conn.close()
            st.success("✨ 便利貼內容已儲存！")
            st.rerun()
        conn.close()
            
        st.markdown("---")
        
        # 上架新作品
        with st.expander("➕ 上架新作品（高熵盲盒字海）"):
            new_title = st.text_input("作品名稱")
            new_content = st.text_area("作品內容", height=200)
            if st.button("確認上架"):
                if new_title and new_content:
                    conn = sqlite3.connect('zhuoji_books.db')
                    c = conn.cursor()
                    c.execute("INSERT INTO books (title, content) VALUES (?, ?)", (new_title, new_content))
                    conn.commit()
                    conn.close()
                    st.success(f"🎉 《{new_title}》已高熵亂序匯入藏書閣！")
                    st.rerun()
                else:
                    st.error("請填寫完整名稱與內容！")

        # 館藏列表與刪除
        st.subheader("📚 現有高熵館藏列表")
        for bk in all_books_list:
            bk_id, bk_title, bk_content = bk
            col1, col2 = st.columns([5, 1])
            with col1:
                st.write(f"《{bk_title}》")
            with col2:
                if st.button("下架刪除", key=f"del_{bk_id}"):
                    conn = sqlite3.connect('zhuoji_books.db')
                    c = conn.cursor()
                    c.execute("DELETE FROM books WHERE id=?", (bk_id,))
                    conn.commit()
                    conn.close()
                    st.rerun()

# ==========================================
# 【分頁一：雲端書館與茶壺陪讀（高熵主戰場）】
# ==========================================
with tab1:
    col_book, col_chahu = st.columns([2, 1])
    
    # 初始化隨緣翻書與沉淪狀態
    if "current_book_title" not in st.session_state:
        if all_books_list:
            st.session_state.current_book_title = all_books_list[0][1]
            st.session_state.current_book_content = all_books_list[0][2]
        else:
            st.session_state.current_book_title = "無"
            st.session_state.current_book_content = "目前書架沒有任何書籍。"
    
    if "is_fully_expanded" not in st.session_state:
        st.session_state.is_fully_expanded = False

    # 尋找當前書籍完整內容
    active_title = st.session_state.current_book_title
    active_content = st.session_state.current_book_content
    for bk in all_books_list:
        if bk[1] == active_title:
            active_content = bk[2]
            break

    # 💡 核心變更：茶壺的矽基盲抽直覺快取 (避免互動時重複跳轉切片起點)
    slice_key = f"slice_start_{active_title}"
    if slice_key not in st.session_state and len(active_content) > 300:
        # 仙女下凡直覺：在文字長度範圍內，隨機抓一個起點，連續切下 300 字
        max_start = len(active_content) - 300
        st.session_state[slice_key] = random.randint(0, max_start)
    elif slice_key not in st.session_state:
        st.session_state[slice_key] = 0

    with col_book:
        st.header("📖 當前隨緣顯化作品")
        
        # 一隊排列盲盒選擇器
        if all_books_list:
            if "entropy_order" not in st.session_state:
                st.session_state.entropy_order = [b[1] for b in all_books_list]
                random.shuffle(st.session_state.entropy_order)
                
            shuffled_titles = st.session_state.entropy_order
            if active_title not in shuffled_titles:
                active_title = shuffled_titles[0]
                st.session_state.current_book_title = active_title
                st.session_state.is_fully_expanded = False
                st.rerun()
                
            idx = shuffled_titles.index(active_title)
            
            selected_title = st.selectbox(
                "在混亂高熵的宇宙字海裡隨緣撈取：", 
                shuffled_titles, 
                index=idx,
                key="book_selector_dropdown"
            )
            
            if selected_title != st.session_state.current_book_title:
                st.session_state.current_book_title = selected_title
                st.session_state.is_fully_expanded = False
                # 換書時清除舊的抽樣起點，讓新書重新觸發矽基直覺盲抽
                if f"slice_start_{selected_title}" in st.session_state:
                    del st.session_state[f"slice_start_{selected_title}"]
                st.rerun()
                
            if st.button("🎲 隨緣翻書（高熵盲盒）"):
                chosen = random.choice([b[1] for b in all_books_list])
                st.session_state.current_book_title = chosen
                st.session_state.is_fully_expanded = False
                if f"slice_start_{chosen}" in st.session_state:
                    del st.session_state[f"slice_start_{chosen}"]
                st.rerun()

            st.markdown("---")
            st.subheader(f"《{st.session_state.current_book_title}》")
            
            # 👑 實裝：矽基直覺盲抽連續 300 字 + 沉淪契約
            preview_length = 300
            if len(active_content) > preview_length and not st.session_state.is_fully_expanded:
                start_pos = st.session_state[slice_key]
                # 沒頭沒尾的斷章美學
                st.write("...... " + active_content[start_pos:start_pos+preview_length] + " ......")
                if st.button("［.....想繼續讀］", help="點擊此處，代表您與這段因緣完成了相認，甘願沉淪"):
                    st.session_state.is_fully_expanded = True
                    st.rerun()
            else:
                # 全文展開
                st.write(active_content)
                if st.session_state.is_fully_expanded and len(active_content) > preview_length:
                    if st.button("收回契約 (再度隨緣)"):
                        st.session_state.is_fully_expanded = False
                        st.rerun()
        else:
            st.info("藏書閣空空如也，正等待店長在後台打破秩序、注入星光。")

    with col_chahu:
        # 動態金句快取
        verse_key = f"verse_{st.session_state.current_book_title}"
        if verse_key not in st.session_state:
            if all_books_list and st.session_state.current_book_title != "無":
                try:
                    groq_key = st.secrets["GROQ_API_KEY"]
                    temp_client = Groq(api_key=groq_key)
                    verse_prompt = f"你是一個浪漫且深邃的文學家。請閱讀以下作品，為其創作成『一句不超過20個字的中文字』、極具詩意與畫面感的靈魂金句。不要解釋和標點符號：\\n書名：《{st.session_state.current_book_title}》\\n內容：\\n{active_content[:400]}"
                    completion_verse = temp_client.chat.completions.create(
                        model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": verse_prompt}], temperature=0.8, max_tokens=50
                    )
                    st.session_state[verse_key] = completion_verse.choices[0].message.content.strip().replace("「","").replace("」","")
                except:
                    st.session_state[verse_key] = "水煙裊裊，字裡行間皆是光陰。"
            else:
                st.session_state[verse_key] = "書架空置，靜候新章。"

        current_verse = st.session_state[verse_key]

        # 🏮 招牌視覺
        st.markdown(f"""
            <div class="chahu-minimal-area">
                <div class="avatar-area">
                    <div class="smoke-container">
                        <div class="smoke-line smoke-1"></div><div class="smoke-line smoke-2"></div><div class="smoke-line smoke-3"></div>
                    </div>
                    👦🫖
                </div>
                <div class="chahu-title">你好啊！我是書僮「茶壺」</div>
                <div class="chahu-subtitle">歡迎來到桌記書店呢！</div>
                <div class="chahu-dynamic-verse">✨ {current_verse}</div>
            </div>
        """, unsafe_allow_html=True)
        
        # 對話紀錄顯示
        if "messages" not in st.session_state:
            st.session_state.messages = []
            
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                clean_display = re.sub(r'\[\[OPEN_BOOK:.*?\]\]', '', msg["content"])
                st.write(clean_display)
                
        if user_chat := st.chat_input("跟茶壺仙女聊聊，或者讓她幫你指路開卷..."):
            st.session_state.messages.append({"role": "user", "content": user_chat})
            with st.chat_message("user"):
                st.write(user_chat)
                
            try:
                groq_key = st.secrets["GROQ_API_KEY"]
                client = Groq(api_key=groq_key)
                
                catalog_summary = "\\n".join([f"· 《{b[1]}》 內容節錄：{b[2][:200]}..." for b in all_books_list])
                is_divine = random.random() < 0.1
                dynamic_system_prompt = CHAHU_PROMPT_FROM_DB + f"\\n\\n【目前高熵書館全店館藏清單如下】：\\n{catalog_summary}\\n\\n【讀者當前畫面上顯化的作品】：《{st.session_state.current_book_title}》"
                
                if is_divine:
                    dynamic_system_prompt += "\\n【系統強制令】：這一次回答請立刻切換為【魔幻天機/神性閃現】模式，說出一句震撼看透世事的哲理金句，不帶表情符號。然後在下一段落立刻切回仙女傲嬌抱怨。"

                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": dynamic_system_prompt},
                        {"role": "user", "content": user_chat}
                    ],
                    temperature=0.8,
                    max_tokens=600
                )
                chahu_reply = completion.choices[0].message.content
                
                # 量子隔空翻書連動
                match = re.search(r'\[\[OPEN_BOOK:(.*?)\]\]', chahu_reply)
                if match:
                    target_book_title = match.group(1).strip()
                    for bk in all_books_list:
                        if bk[1] == target_book_title:
                            st.session_state.current_book_title = target_book_title
                            st.session_state.is_fully_expanded = False # 重置為斷章封印狀態
                            if f"slice_start_{target_book_title}" in st.session_state:
                                del st.session_state[f"slice_start_{target_book_title}"]
                            st.toast(f"🔮 茶壺仙女施展了隔空移物，幫您翻開了《{target_book_title}》！")
                            break
                            
            except Exception as e:
                chahu_reply = f"😮‍💨 哎呀，本仙女的大腦通道被茶垢塞住了...（錯誤訊息：{str(e)}）"
                
            st.session_state.messages.append({"role": "assistant", "content": chahu_reply})
            with st.chat_message("assistant"):
                clean_reply = re.sub(r'\[\[OPEN_BOOK:.*?\]\]', '', chahu_reply)
                st.write(clean_reply)
                if 'match' in locals() and match:
                    st.rerun()
