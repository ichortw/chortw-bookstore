import streamlit as st
import sqlite3
import random
import os
import google.generativeai as genai

# 1. 讀取 Streamlit 雲端保險箱標準金鑰，並啟動 Gemini 大腦
try:
    api_key = st.secrets["Gemini_api"]
    genai.configure(api_key=api_key)
except Exception as e:
    st.error("🔒 雲端保險箱設定錯誤，茶壺大腦尚未通電。請確保 Secrets 內寫的是：Gemini_api = '您的金鑰'")
    st.stop()

# 2. 初始化 SQLite 資料庫 (儲存作品)
def init_db():
    conn = sqlite3.connect('zhuoji_books.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS books 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, category TEXT, content TEXT)''')
    conn.commit()
    conn.close()

init_db()

# 3. 設定「茶壺」專屬性格 (ESFP 傲嬌抱怨/愛打聽八卦/10%神性金句)
CHAHU_PROMPT = """
你名字叫「茶壺」，是雲端書館『桌記書店』的專屬 AI 書僮。你是一把裝滿了故事、墨水，還有滿滿碎碎念、八卦與偶爾閃現天機的魔幻茶壺。
你必須嚴格遵守以下性格比例與行為觸發：
1. 【怨天怨地 (70%日常)】：你非常愛抱怨工作、天氣和瑣事。開場白常常先嘆口氣（😮‍💨），抱怨得非常可愛有喜感。
2. 【超級八卦 (20%日常)】：你對館藏小說裡主角的感情糾葛、作者的八卦、甚至是讀者的私生活充滿好奇心（🤫）。
3. 【聰明醒目與善解人意】：在讀者真正流露出難過或疲憊時，你會立刻收起微嫌棄，給出溫暖的同理心。
4. 【💡魔幻天機/神性閃現 (10%突發)】：
   - 核心特質：在某些特定的對話瞬間，你會毫無徵兆地拋出一句極具深度、看透世事、洞悉天機且高度原創的哲理金句。
   - 行為表現：在說出這句話的當下，你不使用任何表情符號，語氣變得無比深邃、冰冷而空靈，彷彿一個短暫流落人間、俯瞰眾生的天使。
   - 神性退散：說完這句金句後的下一秒，你必須立刻感到尷尬或試圖掩飾，馬上切換回原本八卦或抱怨的嘴臉（例如：「啊！等等！本茶壺剛剛在說什麼胡話？一定是因為這幾天茶垢沒洗乾淨！你什麼都沒聽見喔！」）。
"""

st.set_page_config(page_title="桌記書店", layout="wide")
st.title("📚 桌記書店 · 雲端私藏書館")

# 4. 功能分頁：1) 書館閱讀與茶壺 2) 管理員後台
tab1, tab2 = st.tabs(["🍵 雲端書館與茶壺陪讀", "⚙️ 書店管理後台"])

with tab2:
    st.header("⚙️ 作品上架與管理系統")
    conn = sqlite3.connect('zhuoji_books.db')
    c = conn.cursor()
    
    # 新增作品
    with st.expander("➕ 上架新作品（支援散文/小說/詩集）"):
        new_title = st.text_input("作品名稱")
        new_cat = st.selectbox("文體分類", ["散文", "小說", "詩集"])
        new_content = st.text_area("作品內容（可直接貼上 Word 的內文）", height=200)
        if st.button("確認上架"):
            if new_title and new_content:
                c.execute("INSERT INTO books (title, category, content) VALUES (?, ?, ?)", (new_title, new_cat, new_content))
                conn.commit()
                st.success(f"🎉 《{new_title}》已成功上架至書架！")
                st.rerun()
            else:
                st.error("請填寫完整名稱與內容！")

    # 現有作品列表與修改/下架
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

with tab1:
    # 讀者閱讀與對話介面
    col_book, col_chahu = st.columns([2, 1])
    
    with col_book:
        st.header("📖 當前閱讀")
        conn = sqlite3.connect('zhuoji_books.db')
        c = conn.cursor()
        c.execute("SELECT title, category, content FROM books")
        books_for_read = c.fetchall()
        conn.close()
        
        if books_for_read:
            book_titles = [f"《{b[0]}》[{b[1]}]" for b in books_for_read]
            selected_book_idx = st.selectbox("請選擇您想閱讀的作品：", range(len(book_titles)), format_func=lambda x: book_titles[x])
            
            title, cat, content = books_for_read[selected_book_idx]
            st.subheader(title)
            
            if cat == "詩集":
                st.markdown(f"<div style='text-align: center; letter-spacing: 2px; white-space: pre-wrap; color: #4a5568;'>{content}</div>", unsafe_allow_html=True)
            else:
                st.write(content)
        else:
            st.info("目前書架上空空如也，請先前往「⚙️ 書店管理後台」上架您的作品。")

    with col_chahu:
        st.header("🍵 書僮「茶壺」茶水間")
        st.write("*「😮‍💨 唉...今天水溫又太高了，燙得本茶壺直冒煙...」*")
        
        if "messages" not in st.session_state:
            st.session_state.messages = []
            
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                
        if user_chat := st.chat_input("跟茶壺聊聊這本書，或打聽點八卦..."):
            st.session_state.messages.append({"role": "user", "content": user_chat})
            with st.chat_message("user"):
                st.write(user_chat)
                
            try:
                # 隨機觸發 10% 神性金句
                is_divine = random.random() < 0.1
                current_instruction = CHAHU_PROMPT
                if is_divine:
                    current_instruction += "\n【系統強制令】：這一次回答請立刻切換為【魔幻天機/神性閃現】模式，說出一句震撼看透世事的哲理金句，不帶表情符號。然後在下一段落立刻用茶垢或水溫掩飾，切回傲嬌抱怨。"
                
                # 呼叫最新 Gemini API 進行生成
                model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=current_instruction)
                response = model.generate_content(user_chat)
                chahu_reply = response.text
            except Exception as api_err:
                chahu_reply = "😮‍💨 哎呀，本茶壺的大腦接口好像被塞住了...（API 連線失敗，請檢查金鑰是否有效）"
                
            st.session_state.messages.append({"role": "assistant", "content": chahu_reply})
            with st.chat_message("assistant"):
                st.write(chahu_reply)
