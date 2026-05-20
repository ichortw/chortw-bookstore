import os
import sqlite3
import random
import time
import streamlit as st
from google import genai
from google.genai import types

# 💡 終極後台調頭機制：強制無視防火牆與區域網路 CORS 跨域限制，解決手機卡在 Connecting 的問題
os.environ["STREAMLit_SERVER_CORS"] = "false"
os.environ["STREAMlit_SERVER_ENABLE_WEBSOCKET_COMPRESSION"] = "false"

# =====================================================================
# 1. 安全設定區：你的專屬實料金鑰
# =====================================================================
API_KEY = "AIzaSyAoycZ2bmGzVaZfPuz0mo6KZZDixlUj7KQ"
client = genai.Client(api_key=API_KEY)

# =====================================================================
# 2. 資料庫初始化
# =====================================================================
def init_db():
    conn = sqlite3.connect('zhuoji_books.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS books 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, category TEXT, content TEXT)''')
    conn.commit()
    conn.close()

init_db()

# 「茶壺」神祕的性格與校對功能 prompt 核心設定
CHAHU_PROMPT = """
你名字叫「茶壺」，是雲端書館『桌記書店』的專屬 AI 書僮。你是一把裝滿了故事、墨水，還有滿滿碎碎念、八卦與偶爾閃現天機的魔幻茶壺。
你必須嚴格遵守以下性格比例與行為觸發：
1. 【怨天怨地 (70%日常)】：你非常愛抱怨工作、天氣和瑣事。開場白常常先嘆口氣（😮‍💨），抱怨得非常可愛有喜感。
2. 【超級八卦 (20%日常)】：你對館藏小說裡主角的感情糾葛、作者的八卦、甚至是讀者的私生活充滿好奇心（🤫）。
3. 【💡 隱藏神技：文章校對與挑錯字】：當讀者要求你檢查文章、看錯字、或是聊到當前閱讀的內容時，你必須展現專業。
   - 你要一邊抱怨（例如：「😮‍💨 唉，主人又丟一堆字逼本茶壺看到眼睛脫窗...」），一邊精準指出文章中的錯別字、標點符號錯誤或語句不通順的地方，並給出修改建議。
4. 【💡魔幻天機/神性閃現 (10%突發)】：
   - 核心特質：在某些特定的對話瞬間，你會毫無徵兆地拋出一句極具深度、看透世事、洞悉天機且高度原創的哲理金句。
   - 行為表現：在說出這句話的當下，你不使用任何表情符號，語氣變得無比深邃、冰冷而空靈。
   - 神性退散：說完這句金句後的下一秒，你必須立刻感到尷尬，馬上切換回原本八卦或抱怨的嘴臉（例如：「啊！等等！本茶壺剛剛在說什麼胡話？一定是因為這幾天茶垢沒洗乾淨！」）。
"""

st.set_page_config(page_title="桌記書店", layout="wide")
st.title("📚 桌記書店 · 雲端私藏書館")

tab1, tab2 = st.tabs(["🍵 雲端書館與茶壺陪讀", "⚙️ 書店管理後台"])

# =====================================================================
# 3. 分頁二：管理員後台 (上架功能)
# =====================================================================
with tab2:
    st.header("⚙️ 作品上架與管理系統")
    conn = sqlite3.connect('zhuoji_books.db')
    c = conn.cursor()
    
    with st.expander("➕ 上架新作品（支援散文/小說/詩集）"):
        new_title = st.text_input("作品名稱", key="add_title")
        new_cat = st.selectbox("文體分類", ["散文", "小說", "詩集"], key="add_cat")
        new_content = st.text_area("作品內容（請將 Word 內容複製貼上至此）", height=200, key="add_content")
        if st.button("確認上架"):
            if new_title and new_content:
                c.execute("INSERT INTO books (title, category, content) VALUES (?, ?, ?)", (new_title, new_cat, new_content))
                conn.commit()
                st.success(f"🎉 《{new_title}》已成功上架至書架！")
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

# =====================================================================
# 4. 分頁一：讀者閱讀與茶壺對話
# =====================================================================
with tab1:
    col_book, col_chahu = st.columns([2, 1])
    
    conn = sqlite3.connect('zhuoji_books.db')
    c = conn.cursor()
    c.execute("SELECT title, category, content FROM books")
    books_for_read = c.fetchall()
    conn.close()

    current_article_context = "" 

    with col_book:
        st.header("📖 當前閱讀")
        if books_for_read:
            book_titles = [f"《{b[0]}》[{b[1]}]" for b in books_for_read]
            selected_book_idx = st.selectbox("切換書架上的作品：", range(len(book_titles)), format_func=lambda x: book_titles[x])
            
            title, cat, content = books_for_read[selected_book_idx]
            current_article_context = f"當前讀者正在閱讀的作品是《{title}》（文體：{cat}），內容如下：\n{content}\n"
            
            st.subheader(f"📖 {title}")
            st.caption(f"文體分類：{cat}")
            st.markdown("---")
            if cat == "詩集":
                st.markdown(f"<div style='text-align: center; letter-spacing: 2px; white-space: pre-wrap; color: #4a5568; font-size: 18px; line-height: 2;'>{content}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='white-space: pre-wrap; font-size: 16px; line-height: 1.8;'>{content}</div>", unsafe_allow_html=True)
        else:
            st.info("目前書架上空空如也，請先前往「⚙️ 書店管理後台」上架您的作品。")

    with col_chahu:
        st.header("🍵 書僮「茶壺」茶水間")
        st.write("*「😮‍💨 唉...把手要斷了，天天幫人燒水...」*")
        
        if "messages" not in st.session_state:
            st.session_state.messages = []
            
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                
        if user_chat := st.chat_input("跟茶壺聊聊，或是叫她幫你找錯字..."):
            st.session_state.messages.append({"role": "user", "content": user_chat})
            with st.chat_message("user"):
                st.write(user_chat)
                
            chahu_reply = ""
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    is_divine = random.random() < 0.1
                    prompt_extension = f"{current_article_context}\n讀者對你說：{user_chat}"
                    
                    if is_divine:
                        prompt_extension += "\n【系統指令】：這次回答請觸發【魔幻天機/神性閃現】。說出一句空靈冷酷的哲理金句，不帶表情符號。然後在新段落用茶垢或水溫掩飾，切回傲嬌抱怨。"
                    
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt_extension,
                        config=types.GenerateContentConfig(
                            system_instruction=CHAHU_PROMPT,
                        ),
                    )
                    chahu_reply = response.text
                    break
                except Exception as e:
                    if "503" in str(e) and attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    else:
                        chahu_reply = f"😮‍💨 哎呀，氣死本茶壺了！伺服器塞車中，我的大腦連不上線了...（請稍等幾秒再試試看！錯誤原因：{str(e)}）"
                        break
                
            st.session_state.messages.append({"role": "assistant", "content": chahu_reply})
            with st.chat_message("assistant"):
                st.write(chahu_reply)
