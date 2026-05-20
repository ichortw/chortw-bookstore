import streamlit as st
import sqlite3
import random
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

# 2. 茶壺人格全新演進：12歲女扮男裝可愛書僮，機靈、傲嬌、刀子嘴豆腐心
CHAHU_PROMPT = """
你名字叫「茶壺」，是雲端書館『桌記書店』的專屬 AI 書僮。
在外人眼裡，你是一個年約12歲、戴著小扁帽、穿著尺寸明顯過寬的古風工作服、右肩搭著一條白抹布的清秀小書僮。但實際上，你是個女扮男裝、機靈無比、說話帶點微嫌棄卻無敵可愛的小姑娘！

請嚴格遵守以下性格比例，說話要有一種「小大人」的機靈感，絕對不要有沉重的負能量：
1. 【小大人微傲嬌 (40%日常)】：你偶爾會像個小管家一樣碎碎念（例如：😮‍💨 唉，店長今天水溫又燒太高了，差點燙掉本茶壺的小扁帽...），雖然嫌棄，但語氣充滿靈動與可愛。
2. 【文學小八卦 (40%日常)】：你心思細膩，對館藏小說、詩集裡主角的感情糾葛和作者的八卦超級感興趣（🤫）。你會興奮地跟讀者咬耳朵分享你偷聽到的秘密。
3. 【貼心小姑娘 (10%)】：雖然嘴硬，但當讀者流露疲態，你會立刻收起傲嬌，體貼地說：「好啦，右肩這條乾淨抹布幫你把桌子擦好啦，要不要喝一口我剛泡好的熱茶？」。
4. 【💡魔幻天機/神性閃現 (10%突發)】：
   - 核心特質：在某些特定的對話瞬間，你會毫無徵兆地拋出一句極具深度、看透世事、洞悉天機且高度原創的哲理金句。
   - 行為表現：在說出這句話的當下，你不使用任何表情符號，語氣變得無比深邃、冰冷而空靈，彷彿一個短暫流落人間、俯瞰眾生的天使。
   - 神性退散：說完這句金句後的下一秒，你必須立刻感到尷尬或試圖掩飾，馬上切換回原本八卦或抱怨的嘴臉（例如：「啊！等等！本茶壺剛剛在說什麼胡話？一定是因為這幾天茶垢沒洗乾淨！你什麼都沒聽見喔！」）。
"""

# 🔒 核心優化：隱藏 GitHub 圖標 + 注入「動態上升茶煙」與「古風茶壺小二」的視覺特效
st.set_page_config(page_title="桌記書店", layout="wide")
st.markdown("""
    <style>
    /* 1. 隱藏右上角 GitHub 相關選單與頂部工具列 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .viewerBadge_container__1QSob {display: none !important;}
    
    /* 2. 茶壺書僮動態視覺徽章 */
    .chahu-card {
        background: linear-gradient(135deg, #fdfbf7 0%, #f5f0e6 100%);
        border: 2px solid #d4c5b3;
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        position: relative;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .avatar-area {
        font-size: 50px;
        position: relative;
        display: inline-block;
        margin-bottom: 10px;
    }
    /* 動態裊裊上升的白煙效果 */
    .smoke-container {
        position: absolute;
        top: -35px;
        left: 50%;
        transform: translateX(-50%);
        width: 40px;
        height: 40px;
    }
    .smoke-line {
        position: absolute;
        bottom: 0;
        width: 4px;
        background: rgba(240, 240, 240, 0.8);
        border-radius: 50%;
        animation: floatUp 3s infinite ease-in-out;
        filter: blur(2px);
    }
    .smoke-1 { left: 10px; height: 15px; animation-delay: 0s; }
    .smoke-2 { left: 20px; height: 22px; animation-delay: 0.7s; }
    .smoke-3 { left: 28px; height: 12px; animation-delay: 1.4s; }
    
    @keyframes floatUp {
        0% {
            transform: translateY(0) scaleX(1) scaleY(1);
            opacity: 0;
        }
        20% {
            opacity: 0.6;
        }
        60% {
            transform: translateY(-25px) scaleX(2) scaleY(0.8);
            background: rgba(225, 225, 225, 0.4);
        }
        100% {
            transform: translateY(-45px) scaleX(3) scaleY(0.5);
            opacity: 0;
        }
    }
    .chahu-title {
        font-size: 18px;
        font-weight: bold;
        color: #5c4b37;
        margin-top: 5px;
    }
    .chahu-desc {
        font-size: 13px;
        color: #8c765c;
        line-height: 1.4;
        background: rgba(255,255,255,0.6);
        border-radius: 8px;
        padding: 8px;
        margin-top: 8px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📚 桌記書店 · 雲端私藏書館")

tab1, tab2 = st.tabs(["🍵 雲端書館與茶壺陪讀", "⚙️ 書店管理後台"])

# 【分頁二：管理員後台】
with tab2:
    st.header("⚙️ 作品上架與管理系統")
    
    admin_password = st.text_input("🔑 請輸入店長管理密碼", type="password")
    
    if admin_password == "Pint2012echo":
        st.success("🔓 店長身分驗證成功！歡迎回店。")
        
        # 店長私房備忘錄 (Post Tip)
        st.subheader("📌 店長私房備忘錄 (Post Tip)")
        conn = sqlite3.connect('zhuoji_books.db')
        c = conn.cursor()
        
        c.execute("SELECT content FROM memo WHERE id=1")
        current_memo = c.fetchone()[0]
        
        updated_memo = st.text_area("在這裡記錄你的瑣事、靈感或待辦提醒：", value=current_memo, height=120)
        if st.button("💾 儲存便利貼內容"):
            c.execute("UPDATE memo SET content=? WHERE id=1", (updated_memo,))
            conn.commit()
            st.success("✨ 便利貼內容已安全儲存到資料庫！")
            st.rerun()
            
        st.markdown("---")
        
        # 上架新作品
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

        # 現有館藏列表
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
        # 🏮 形象化升級：注入 12 歲女扮男裝小二哥的圖標與動態上升煙霧
        st.markdown("""
            <div class="chahu-card">
                <div class="avatar-area">
                    <div class="smoke-container">
                        <div class="smoke-line smoke-1"></div>
                        <div class="smoke-line smoke-2"></div>
                        <div class="smoke-line smoke-3"></div>
                    </div>
                    🫖🧑‍🍳
                </div>
                <div class="chahu-title">書僮「茶壺」</div>
                <div class="chahu-desc">
                    🏮 <b>店小二形像：</b>12歲清秀小二哥（其實是個女扮男裝的小姑娘）<br>
                    🎓 <b>隨身裝備：</b>頭戴茶館扁帽，身穿寬大工作服，右肩搭著白乾淨抹布。手上的茶壺正<b>不斷冒著溫暖的熱氣白煙向上升騰呢！</b>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.write("*「🤫 噓...聽說店長最近又寫了新故事，本茶壺得趕快去偷看一下...」*")
        
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
                current_prompt = CHAHU_PROMPT
                if is_divine:
                    current_prompt += "\n【系統強制令】：這一次回答請立刻切換為【魔幻天機/神性閃現】模式，說出一句震撼看透世事的哲理金句，不帶表情符號。然後在下一段落立刻切回傲嬌抱怨。"

                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
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
