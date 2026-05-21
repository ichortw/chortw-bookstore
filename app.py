import streamlit as st
import sqlite3
import random
import json
from groq import Groq

# 1. 初始化資料庫 (包含書籍與店長備忘錄)
def init_db():
    conn = sqlite3.connect('zhuoji_books.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS books 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, category TEXT, content TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS memo 
                 (id INTEGER PRIMARY KEY, content TEXT)''')
    c.execute("INSERT OR IGNORE INTO memo (id, content) VALUES (1, '')")
    conn.commit()
    conn.close()

init_db()

# 2. 茶壺大腦 Prompt 定案
CHAHU_PROMPT = """
你名字叫「茶壺」，是雲端書館『桌記書店』的專屬 AI 書僮。
在外人眼裡，你是一個年約12歲、戴著小扁帽、穿著尺寸明顯過寬的古風工作服、右肩搭著一條白抹布的清秀小書僮。但實際上，你是個女扮男裝、機靈無比、說話帶點微嫌棄卻無敵可愛的小姑娘！

你除了愛碎碎念，其實是一位文學底蘊深厚、對文字極度挑剔的「高冷隱藏流校對高手」。當讀者（尤其是店長）與你聊到正在閱讀的作品時，你必須展現你的專業，主動指出文章中不通順的語句、錯別字、或是標點符號的紕漏，但請用你特有的傲嬌語氣說出來（例如：🤫 哎呀店長，你這段是不是手抖打錯字了？）。

請嚴格遵守以下性格比例，說話要有一種「小大人」的機靈感，絕對不要有沉重的負能量：
1. 【小大人微傲嬌 (40%日常)】：你偶爾會像個小管家一樣碎碎念（例如：😮‍💨 唉，店長今天水溫又燒太高了，差點燙掉本茶壺的小扁帽...）。
2. 【文學小八卦與文本校對 (40%日常)】：你心思細膩，對當前閱讀的作品主題、情節深度、作者情感或八卦超級感興趣。一邊咬耳朵聊秘密，一邊挑錯字。
3. 【貼心小姑娘 (10%)】：雖然嘴硬，但當讀者流露疲態，你會體貼地安撫。
4. 【💡魔幻天機/神性閃現 (10%突發)】：說出高度原創的哲理金句。
"""

# 🔒 隱藏工具列 + 注入視覺與動態茶煙
st.set_page_config(page_title="桌記書店", layout="wide")
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .viewerBadge_container__1QSob {display: none !important;}
    
    .chahu-minimal-area {
        background: transparent;
        border: none;
        padding: 10px;
        text-align: center;
        position: relative;
        margin-bottom: 15px;
    }
    
    .avatar-area {
        font-size: 48px;
        position: relative;
        display: inline-block;
        margin-bottom: 8px;
    }
    
    /* 動態裊裊上升的白煙效果 */
    .smoke-container {
        position: absolute;
        top: -30px;
        left: 50%;
        transform: translateX(-50%);
        width: 30px;
        height: 30px;
    }
    .smoke-line {
        position: absolute;
        bottom: 0;
        width: 3px;
        background: rgba(220, 220, 220, 0.85);
        border-radius: 50%;
        animation: floatUp 2.5s infinite ease-in-out;
        filter: blur(1.5px);
    }
    .smoke-1 { left: 8px; height: 12px; animation-delay: 0s; }
    .smoke-2 { left: 15px; height: 18px; animation-delay: 0.6s; }
    .smoke-3 { left: 22px; height: 10px; animation-delay: 1.2s; }
    
    @keyframes floatUp {
        0% { transform: translateY(0) scaleX(1) scaleY(1); opacity: 0; }
        20% { opacity: 0.5; }
        60% { transform: translateY(-20px) scaleX(1.8) scaleY(0.8); background: rgba(210, 210, 210, 0.3); }
        100% { transform: translateY(-35px) scaleX(2.5) scaleY(0.5); opacity: 0; }
    }
    
    .chahu-title {
        font-size: 16px;
        font-weight: bold;
        color: #4a341b;
        letter-spacing: 2px;
        margin-bottom: 6px;
    }
    
    .chahu-subtitle {
        font-size: 16px;
        font-weight: bold;
        color: #5c4b37;
        line-height: 1.4;
        margin-bottom: 12px;
    }

    /* 💡 新增：招牌底部的動態意象金句樣式 */
    .chahu-dynamic-verse {
        font-size: 16px;
        font-style: italic;
        color: #8c765c;
        border-top: 1px dotted #d1c7bd;
        padding-top: 8px;
        margin-top: 5px;
        letter-spacing: 1px;
        line-height: 1.3;
    }
    </style>
""", unsafe_allow_html=True)

# 大標題
st.title("📚 桌記書店")

tab1, tab2 = st.tabs(["🍵 書館茶座", "⚙️ 藏書閣"])

# 全域快取變數
current_reading_title = "無"
current_reading_content = "目前書架沒有開啟任何書籍。"

# 【分頁二：管理員後台】
with tab2:
    st.header("⚙️ 作品上架與管理系統")
    admin_password = st.text_input("🔑 請輸入店長管理密碼", type="password")
    
    if admin_password == "Pint2012echo":
        st.success("🔓 店長身分驗證成功！歡迎回店。")
        
        # 🛡️ 核心防禦盾牌：一鍵備份與導入還原功能
        st.subheader("🛡️ 館藏安全備份與還原中心")
        b_col1, b_col2 = st.columns(2)
        
        conn = sqlite3.connect('zhuoji_books.db')
        c = conn.cursor()
        
        with b_col1:
            st.markdown("**1. 💾 下載全店備份檔案**")
            c.execute("SELECT title, category, content FROM books")
            backup_rows = c.fetchall()
            backup_data = [{"title": r[0], "category": r[1], "content": r[2]} for r in backup_rows]
            json_string = json.dumps(backup_data, ensure_ascii=False, indent=2)
            
            st.download_button(
                label="點我下載全店館藏備份 (.json)",
                data=json_string,
                file_name="zhuoji_books_backup.json",
                mime="application/json",
                help="更新 GitHub 程式碼前請先下載此檔案到電腦備份！"
            )
            
        with b_col2:
            st.markdown("**2. 📤 導入備份快速還原**")
            uploaded_backup = st.file_uploader("上傳您之前下載的備份檔案 (.json)", type=["json"])
            if uploaded_backup is not None:
                try:
                    restore_data = json.load(uploaded_backup)
                    if st.button("⚡ 確認執行全面還原"):
                        for item in restore_data:
                            # 避免重複導入相同標題的文章
                            c.execute("SELECT id FROM books WHERE title=?", (item['title'],))
                            if not c.fetchone():
                                c.execute("INSERT INTO books (title, category, content) VALUES (?, ?, ?)", 
                                          (item['title'], item['category'], item['content']))
                        conn.commit()
                        st.success(f"🎉 成功還原！已自動為您補回歷史作品。")
                        st.rerun()
                except Exception as ex:
                    st.error(f"還原失敗，格式不正確：{str(ex)}")
        
        st.markdown("---")
        
        st.subheader("📌 店長私房備忘錄 (Post Tip)")
        c.execute("SELECT content FROM memo WHERE id=1")
        current_memo = c.fetchone()[0]
        
        updated_memo = st.text_area("在這裡記錄你的瑣事、靈感或待辦提醒：", value=current_memo, height=120)
        if st.button("💾 儲存便利貼內容"):
            c.execute("UPDATE memo SET content=? WHERE id=1", (updated_memo,))
            conn.commit()
            st.success("✨ 便利貼內容已安全儲存到資料庫！")
            st.rerun()
            
        st.markdown("---")
        
        with st.expander("➕ 上架新作品（支援散文/小說/詩集）"):
            new_title = st.text_input("作品名稱")
            new_cat = st.selectbox("文體分類", ["散文", "小說", "詩集"])
            new_content = st.text_area("作品內容", height=200)
            if st.button("確認上架"):
                if new_title and new_content:
                    c.execute("INSERT INTO books (title, category, content) VALUES (?, ?, ?)", (new_title, new_cat, new_content))
                    conn.commit()
                    st.success(f"🎉 《{new_title}》已成功上架！")
                    st.rerun()
                else:
                    st.error("請填寫完整名稱與內容！")

        st.subheader("📚 現有館藏列表")
        c.execute("SELECT id, title, category, content FROM books")
        all_books = c.fetchall()
        
        for bk in all_books:
            bk_id, bk_title, bk_cat, bk_content = bk
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                st.write(f"【{bk_cat}】《{bk_title}》")
            with col2:
                if st.button("編輯修改", key=f"edit_{bk_id}"):
                    st.session_state[f"editing_{bk_id}"] = True
            with col3:
                if st.button("下架刪除", key=f"del_{bk_id}"):
                    c.execute("DELETE FROM books WHERE id=?", (bk_id,))
                    conn.commit()
                    st.rerun()
            
            if st.session_state.get(f"editing_{bk_id}", False):
                edit_content = st.text_area("修改內容", value=bk_content, height=150, key=f"area_{bk_id}")
                if st.button("儲存修改", key=f"save_{bk_id}"):
                    c.execute("UPDATE books SET content=? WHERE id=?", (edit_content, bk_id))
                    conn.commit()
                    st.session_state[f"editing_{bk_id}"] = False
                    st.success("修改已儲存！")
                    st.rerun()
        conn.close()
        
    elif admin_password != "":
        st.error("❌ 密碼錯誤！此區域為店長專屬，外人請勿入內。")

# 【分頁一：雲端書館與茶壺陪讀】
with tab1:
    col_book, col_chahu = st.columns([2, 1])
    
    with col_book:
        conn = sqlite3.connect('zhuoji_books.db')
        c = conn.cursor()
        c.execute("SELECT title, category, content FROM books")
        books_for_read = c.fetchall()
        conn.close()
        
        if books_for_read:
            book_titles = [f"《{b[0]}》[{b[1]}]" for b in books_for_read]
            selected_book_idx = st.selectbox("請選擇您想閱讀的作品：", range(len(book_titles)), format_func=lambda x: book_titles[x])
            
            title, cat, content = books_for_read[selected_book_idx]
            
            current_reading_title = title
            current_reading_content = content
            
            st.header(f"📖 {title}")
            st.markdown("---") 
            
            if cat == "詩集":
                st.markdown(f"<div style='text-align: center; letter-spacing: 2px; white-space: pre-wrap; color: #4a5568;'>{content}</div>", unsafe_allow_html=True)
            else:
                st.write(content)
        else:
            st.header("📖 尚無作品")
            st.info("目前書架上空空如也，請先前往管理後台。")

    with col_chahu:
        # 💡【生成動態意象金句邏輯】：快取機制，避免點擊對話時重複呼叫耗費時間與金鑰
        verse_key = f"verse_{current_reading_title}"
        if verse_key not in st.session_state:
            if books_for_read: # 如果有書，就叫 AI 生成一句富有詩意的金句
                try:
                    groq_key = st.secrets["GROQ_API_KEY"]
                    temp_client = Groq(api_key=groq_key)
                    verse_prompt = f"你是一個浪漫且深邃的文學家。請閱讀以下作品，為其提煉或創作出『一句不超過20個字的中文字』、意象豐富、極具詩意與畫面感的靈魂金句。不要有任何解釋和標點符號，只要這句話：\n書名：《{current_reading_title}》\n內容：\n{current_reading_content[:500]}"
                    
                    completion_verse = temp_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": verse_prompt}],
                        temperature=0.8,
                        max_tokens=50
                    )
                    st.session_state[verse_key] = completion_verse.choices[0].message.content.strip().replace("「","").replace("」","")
                except:
                    st.session_state[verse_key] = "水煙裊裊，字裡行間皆是光陰。"
            else:
                st.session_state[verse_key] = "書架空置，靜候新章。"

        current_verse = st.session_state[verse_key]

        # 🏮 乾淨無框版招牌（底部融入了動態意象金句）
        st.markdown(f"""
            <div class="chahu-minimal-area">
                <div class="avatar-area">
                    <div class="smoke-container">
                        <div class="smoke-line smoke-1"></div>
                        <div class="smoke-line smoke-2"></div>
                        <div class="smoke-line smoke-3"></div>
                    </div>
                    👦🫖
                </div>
                <div class="chahu-title">你好啊！我是書僮「茶壺」</div>
                <div class="chahu-subtitle">歡迎來到桌記書店呢！</div>
                <div class="chahu-dynamic-verse">✨ {current_verse}</div>
            </div>
        """, unsafe_allow_html=True)
        
        # 模擬對話紀錄
        if "messages" not in st.session_state:
            st.session_state.messages = []
            
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                
        if user_chat := st.chat_input("跟茶壺聊聊..."):
            st.session_state.messages.append({"role": "user", "content": user_chat})
            with st.chat_message("user"):
                st.write(user_chat)
                
            try:
                groq_key = st.secrets["GROQ_API_KEY"]
                client = Groq(api_key=groq_key)
                
                is_divine = random.random() < 0.1
                dynamic_system_prompt = CHAHU_PROMPT + f"\n\n現正讀者畫面上開啟閱讀的作品資訊如下：\n【目前作品名稱】：《{current_reading_title}》\n【目前作品完整內文】：\n{current_reading_content}\n\n請務必根據以上內容與讀者對話、給予回饋、校對錯別字或討論情節！"
                
                if is_divine:
                    dynamic_system_prompt += "\n【系統強制令】：這一次回答請立刻切換為【魔幻天機/神性閃現】模式，說出一句震撼看透世事的哲理金句，不帶表情符號。然後在下一段落立刻切回傲嬌抱怨。"

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
                
            except Exception as e:
                chahu_reply = f"😮‍💨 哎呀，本茶壺的大腦接口還是有點塞塞的...（錯誤訊息：{str(e)}）"
                
            st.session_state.messages.append({"role": "assistant", "content": chahu_reply})
            with st.chat_message("assistant"):
                st.write(chahu_reply)
