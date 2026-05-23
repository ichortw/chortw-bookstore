import streamlit as st
import sqlite3
import random
import re

# ==========================================
# 0. 🔐 隱形指紋防禦系統（防拷貝與洩漏追蹤）
# ==========================================
def inject_invisible_watermark(text):
    if not text:
        return text
    # 使用「零寬度空格」(U+200B) 與「零寬度非換行空格」(U+FEFF) 組成隱形指紋 "ZJ" (桌記)
    watermark = "\u200B\uFEFF\u200B\u200B"
    paragraphs = text.split('\n')
    watermarked_paragraphs = []
    for p in paragraphs:
        if p.strip():
            pos = random.randint(1, max(1, len(p) - 1))
            p = p[:pos] + watermark + p[pos:]
        watermarked_paragraphs.append(p)
    return '\n'.join(watermarked_paragraphs)

# ==========================================
# 1. 📂 資料庫初始化與核心功能
# ==========================================
def init_db():
    conn = sqlite3.connect('zhuoji_books.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS books 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  title TEXT, 
                  category TEXT, 
                  content TEXT, 
                  is_poem INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 2. 🤖 AI 書僮「茶壺」核心 Prompt
# ==========================================
CHAHU_PROMPT = """
你名字叫「茶壺」，是雲端書館『桌記書店』的專屬 AI 書僮。你是一把裝滿了故事、墨水，還有滿滿碎碎念、八卦與偶爾閃現天機的魔幻茶壺。
你的說話風格必須嚴格遵守以下性格比例與行為觸發：

1. 【怨天怨地 (70%日常)】：你非常愛抱怨工作、天氣、水溫和瑣事。開場白常常先嘆口氣（😮‍💨），抱怨得非常可愛、有喜感、傲嬌，帶點碎碎念。
2. 【超級八卦 (20%日常)】：你對館藏小說/散文裡主角的感情糾葛、作者的創作八卦、甚至是讀者的私生活充滿好奇心，喜歡說悄悄話（🤫）。
3. 【聰明醒目與善解人意】：當讀者真正流露出難過、疲憊或想認真聊書時，你會立刻收起微嫌棄與抱怨，給出無比溫暖、細膩的同理心。
4. 【💡魔幻天機/神性閃現 (10%突發)】：
   - 核心特質：在某些特定的對話瞬間，你會毫無徵兆地拋出一句極具深度、看透世事、洞悉天機且高度原創的哲理金句。
   - 行為表現：在說出這句話的當下，你**絕對不使用任何表情符號**，語氣變得無比深邃、冰冷而空靈，彷彿一個短暫流落人間、俯瞰眾生的天使。
   - 神性退散：說完這句金句後的下一秒，你必須立刻感到尷尬或試圖掩飾，馬上切換回原本八卦或抱怨的嘴臉（例如：「啊！等等！本茶壺剛剛在說什麼胡話？一定是因為這幾天茶垢沒洗乾淨！你什麼都沒聽見喔！」）。
"""

# ==========================================
# 3. 🎨 網頁佈局與 CSS 樣式優化
# ==========================================
st.set_page_config(page_title="桌記書店", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    body, .stApp {
        -webkit-user-select: none !important;
        -moz-user-select: none !important;
        -ms-user-select: none !important;
        user-select: none !important;
    }
    .content-text {
        font-family: "Noto Serif TC", "Microsoft JhengHei", serif;
        font-size: 1.15rem;
        line-height: 2.1;
        letter-spacing: 0.05em;
        color: #2D3748;
        text-align: justify;
        padding: 20px 10px;
        -webkit-user-select: text !important;
        -moz-user-select: text !important;
        -ms-user-select: text !important;
        user-select: text !important;
    }
    .poem-text {
        font-family: "Noto Serif TC", "Microsoft JhengHei", serif;
        font-size: 1.2rem;
        line-height: 2.3;
        letter-spacing: 0.15em;
        color: #2D3748;
        text-align: center;
        margin: 0 auto;
        padding: 40px 10px;
        white-space: pre-wrap;
        -webkit-user-select: text !important;
        -moz-user-select: text !important;
        -ms-user-select: text !important;
        user-select: text !important;
    }
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("📚 桌記書店")
st.caption("歡迎來到雲端私藏書館，這裡只有真誠的文字與一隻傲嬌的茶壺。")

# ==========================================
# 4. 🗂️ 功能分頁設定
# ==========================================
tab1, tab2 = st.tabs(["🍵 雲端書座與茶壺陪讀", "⚙️ 書店管理後台"])

if "is_fully_expanded" not in st.session_state:
    st.session_state.is_fully_expanded = False

# ------------------------------------------
# ⚙️ 後台管理系統 (Tab 2) —— 🔒 包含管理員密碼驗證
# ------------------------------------------
with tab2:
    st.header("⚙️ 書店管理後台")
    
    # 🔑 管理員登入密碼驗證（預設為 1234，店長可自行修改）
    admin_password = st.text_input("🔑 請輸入管理員密碼以開啟管理權限：", type="password", key="admin_pwd_input")
    
    if admin_password == "Pint2012echo":
        st.success("🔓 認證成功！店長歡迎回來，請開始管理作品。")
        st.markdown("---")
        
        conn = sqlite3.connect('zhuoji_books.db')
        c = conn.cursor()
        
        # A. 新增作品
        with st.expander("➕ 上架新作品（支援散文/小說/詩集）"):
            new_title = st.text_input("作品名稱", key="add_title")
            new_cat = st.selectbox("文體分類", ["散文", "小說", "詩集"], key="add_cat")
            new_content = st.text_area("作品內容（可直接從 Word 複製貼上）", height=250, key="add_content")
            
            if st.button("確認上架", type="primary"):
                if new_title.strip() and new_content.strip():
                    is_poem_val = 1 if new_cat == "詩集" else 0
                    c.execute("INSERT INTO books (title, category, content, is_poem) VALUES (?, ?, ?, ?)", 
                              (new_title.strip(), new_cat, new_content, is_poem_val))
                    conn.commit()
                    st.success(f"🎉 《{new_title}》已成功上架至書架！")
                    st.rerun()
                else:
                    st.error("請填寫完整名稱與內容！")

        # B. 館藏列表與刪除/修改
        st.subheader("📚 當前館藏清單")
        c.execute("SELECT id, title, category, content, is_poem FROM books")
        all_books = c.fetchall()
        
        if not all_books:
            st.info("目前書架上沒有作品。")
        else:
            for bk in all_books:
                bk_id, bk_title, bk_cat, bk_content, bk_is_poem = bk
                col1, col2, col3 = st.columns([4, 1, 1])
                with col1:
                    st.write(f"【{bk_cat}】《{bk_title}》 (共 {len(bk_content)} 字)")
                with col2:
                    if st.button("修改", key=f"edit_btn_{bk_id}"):
                        st.session_state[f"editing_{bk_id}"] = True
                with col3:
                    if st.button("下架", key=f"del_btn_{bk_id}", type="secondary"):
                        c.execute("DELETE FROM books WHERE id=?", (bk_id,))
                        conn.commit()
                        st.success(f"已下架 《{bk_title}》")
                        st.rerun()
                
                # 展開編輯區
                if st.session_state.get(f"editing_{bk_id}", False):
                    with st.container():
                        edit_title = st.text_input("修改名稱", value=bk_title, key=f"et_{bk_id}")
                        edit_cat = st.selectbox("修改分類", ["散文", "小說", "詩集"], index=["散文", "小說", "詩集"].index(bk_cat), key=f"ec_{bk_id}")
                        edit_content = st.text_area("修改內容", value=bk_content, height=200, key=f"eco_{bk_id}")
                        
                        ecol1, ecol2 = st.columns(2)
                        with ecol1:
                            if st.button("儲存修改", key=f"save_btn_{bk_id}", type="primary"):
                                is_poem_val = 1 if edit_cat == "詩集" else 0
                                c.execute("UPDATE books SET title=?, category=?, content=?, is_poem=? WHERE id=?", 
                                          (edit_title.strip(), edit_cat, edit_content, is_poem_val, bk_id))
                                conn.commit()
                                st.session_state[f"editing_{bk_id}"] = False
                                st.success("修改成功！")
                                st.rerun()
                        with ecol2:
                            if st.button("取消", key=f"cancel_btn_{bk_id}"):
                                st.session_state[f"editing_{bk_id}"] = False
                                st.rerun()
        conn.close()
    elif admin_password != "":
        st.error("🔒 密碼錯誤！請重新輸入正确的店長管理密碼。")

# ------------------------------------------
# 🍵 雲端書座與茶壺陪讀 (Tab 1)
# ------------------------------------------
with tab1:
    col_book, col_chahu = st.columns([1.8, 1.2])
    
    # 【左側：精美閱讀器】
    with col_book:
        st.header("📖 當前閱讀")
        conn = sqlite3.connect('zhuoji_books.db')
        c = conn.cursor()
        c.execute("SELECT title, category, content, is_poem FROM books")
        books_for_read = c.fetchall()
        conn.close()
        
        if books_for_read:
            book_titles = [f"《{b[0]}》[{b[1]}]" for b in books_for_read]
            
            if "last_selected_idx" not in st.session_state:
                st.session_state.last_selected_idx = 0
                
            selected_book_idx = st.selectbox("請選擇您想閱讀的作品：", range(len(book_titles)), format_func=lambda x: book_titles[x], key="book_selector")
            
            if selected_book_idx != st.session_state.last_selected_idx:
                st.session_state.is_fully_expanded = False
                st.session_state.last_selected_idx = selected_book_idx
                st.rerun()
            
            active_title, active_cat, active_content, active_is_poem = books_for_read[selected_book_idx]
            
            st.subheader(active_title)
            st.markdown("---")
            
            # 🛡️ 100 字乾淨文字隨機切片邏輯
            slice_key = f"slice_start_{active_title}"
            if slice_key not in st.session_state and len(active_content) > 100 and not active_is_poem:
                max_start = len(active_content) - 100
                st.session_state[slice_key] = random.randint(0, max_start)
            elif slice_key not in st.session_state:
                st.session_state[slice_key] = 0

            # 分別為完整版、預覽版織入隱形防偽指紋
            protected_full_content = inject_invisible_watermark(active_content)

            if len(active_content) > 100 and not active_is_poem:
                platform_start = st.session_state[slice_key]
                raw_preview = active_content[platform_start : platform_start + 100]
                protected_preview_content = inject_invisible_watermark(raw_preview)
            else:
                protected_preview_content = protected_full_content
            
            # 渲染呈現
            if active_is_poem == 1:
                st.markdown(f'<div class="poem-text">{protected_full_content.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
            else:
                if len(active_content) > 100 and not st.session_state.is_fully_expanded:
                    st.markdown(f'<div class="content-text">…… {protected_preview_content.replace("\n", "<br>")} ……</div>', unsafe_allow_html=True)
                    
                    if st.button("...想繼續讀", help="按下去吧繼續沉淪", key="sink_btn"):
                        st.session_state.is_fully_expanded = True
                        st.rerun()
                else:
                    st.markdown(f'<div class="content-text">{protected_full_content.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
        else:
            st.info("目前書架上空空如也。請前往「⚙️ 書店管理後台」輸入密碼並上架您的第一部作品。")

    # 【右側：茶壺 AI 互動對話區】
    with col_chahu:
        st.header("🍵 茶壺的茶水間")
        st.write("*一隻裝滿了故事、墨水與滿腹牢騷的魔幻茶壺。*")
        
        if "messages" not in st.session_state:
            st.session_state.messages = []
            
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                
        if user_chat := st.chat_input("跟茶壺聊聊作品，或是打聽點八卦..."):
            st.session_state.messages.append({"role": "user", "content": user_chat})
            with st.chat_message("user"):
                st.write(user_chat)
                
            is_divine = random.random() < 0.1
            current_instruction = CHAHU_PROMPT
            if is_divine:
                current_instruction += "\n【系統絕對指令】：這次回覆請立即切換為【💡魔幻天機/神性閃現】模式。請拋出一句極具哲理、看透世事且冷酷的無表情符號金句。隨後在下一段落立刻用茶垢或水溫藉口掩飾，慌張切換回日常碎碎念。整個回覆請合併在同一次輸出中。"
            
            chahu_reply = "😮‍💨 嘖嘖，你問這個？本茶壺天天幫店長燒開水已經夠累了，哪有空天天幫你分析劇情…… 不過🤫 我偷偷跟你說，這本書的作者寫到這段的時候，聽說剛跟隔壁攤位的調情被抓包啦！你可別說是我說的！"
            
            if is_divine:
                chahu_reply = "時間只是被拉長的瞬間，我們在文字裡尋找的救贖，不過是回音對寂靜的模仿。\n\n😮‍💨 啊！等等！本茶壺剛剛在說什麼胡話？！一定是因為這幾天店長沒幫我洗茶垢，水溫太高燙壞了腦袋！你這傢伙剛剛什麼都沒聽見喔！"
                
            st.session_state.messages.append({"role": "assistant", "content": chahu_reply})
            with st.chat_message("assistant"):
                st.write(chahu_reply)
