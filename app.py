import streamlit as st
import sqlite3
import random
from groq import Groq

# 1. 初始化資料庫 (儲存散文、小說、詩集)
def init_db():
    conn = sqlite3.connect('zhuoji_books.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS books 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, category TEXT, content TEXT)''')
    conn.commit()
    conn.close()

init_db()

# 2. 茶壺的經典靈魂 Prompt
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

tab1, tab2 = st.tabs(["🍵 雲端書館與茶壺陪讀", "⚙️ 書店管理後台"])

# 【分頁二：管理員後台】
with tab2:
    st.header("⚙️ 作品上架與管理系統")
    conn = sqlite3.connect('zhuoji_books.db')
    c = conn.cursor()
    
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

# 【分頁一：雲端書館與茶壺陪讀】
with tab1:
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
            st.info("目前書架上空空如也，請先前往管理後台。")

    with col_chahu:
        st.header("🍵 茶壺的茶水間")
        st.write("*「😮‍💨 唉...今天水溫又太高了，燙得本茶壺直冒煙...」*")
        
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
                # 這裡改用讀取保險箱裡的 GROQ_API_KEY
                groq_key = st.secrets["GROQ_API_KEY"]
                client = Groq(api_key=groq_key)
                
                is_divine = random.random() < 0.1
                current_prompt = CHAHU_PROMPT
                if is_divine:
                    current_prompt += "\n【系統強制令】：這一次回答請立刻切換為【魔幻天機/神性閃現】模式，說出一句震撼看透世事的哲理金句，不帶表情符號。然後在下一段落立刻切回傲嬌抱怨。"

                # 呼叫極速的 Llama 3 大模型
                completion = client.chat.completions.create(
                    model="llama3-8b-8192",
                    messages=[
                        {"role": "system", "content": current_prompt},
                        {"role": "user", "content": user_chat}
                    ],
                    temperature=0.8,
                    max_tokens=500
                )
                chahu_reply = completion.choices[0].message.content
                
            except Exception as e:
                chahu_reply = f"😮‍💨 哎呀，本茶壺的大腦接口還是有點塞塞的...（錯誤訊息：{str(e)}）"
                
            st.session_state.messages.append({"role": "assistant", "content": chahu_reply})
            with st.chat_message("assistant"):
                st.write(chahu_reply)
