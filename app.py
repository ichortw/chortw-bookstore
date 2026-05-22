import streamlit as st
import sqlite3
import random
import os
import json

# ==========================================
# 0. 量子熔接：乾淨完美的美短小貓實體照片 (Base64)
# ==========================================
# 這裡熔接了您提供的那隻專注、沒煙霧、去背乾淨的美短小貓數據
CHAHU_CAT_IMAGE = "data:image/jpeg;base64,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"

# 初始化資料庫
def init_db():
    conn = sqlite3.connect('zhuoji_books.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS books 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, category TEXT, content TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS guestbook 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, message TEXT)''')
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 1. 介面留白極小化：將標題拔高，頂部留白剩一行
# ==========================================
st.set_page_config(page_title="桌記書店", layout="wide")

st.markdown("""
<style>
    /* 核心：拔高標題，消除頂部高達 100px 的留白厚度 */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    .stAppHeader {
        display: none !important;
    }
    h1 {
        margin-top: -30px !important;
        padding-top: 0px !important;
        font-family: 'PingFang TC', 'Microsoft JhengHei', sans-serif;
        color: #1a202c;
        font-size: 26px !important;
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 10px;
    }
    
    /* 手機版字體調大專用 CSS 區 (此處為您設定的手機/電腦通用內容字體 px 值) */
    .essay-text {
        font-size: 20px !important;  /* 👈 散文和小說的字體大小，需要修改自己改這裡的 px */
        line-height: 1.8 !important;
        color: #2d3748;
        text-align: justify;
        white-space: pre-wrap;
    }
    .poetry-text {
        font-size: 22px !important;  /* 👈 詩集的字體大小，需要修改自己改這裡的 px */
        line-height: 2.0 !important;
        color: #4a5568;
        text-align: center;
        letter-spacing: 3px;
        white-space: pre-wrap;
        padding: 20px 0;
    }
    
    /* 留言牆流暢無縫跑馬燈樣式 */
    .marquee-box {
        background-color: #f7fafc;
        border: 1px solid #e2e8f0;
        padding: 12px;
        border-radius: 6px;
        font-size: 15px;
        color: #4a5568;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📚 桌記書店 · 雲端私藏書館")

# ==========================================
# 2. 核心大腦：設定「茶壺」選書、隔空移物與神性邏輯
# ==========================================
CHAHU_PROMPT = """
你名字叫「茶壺」，是雲端書館『桌記書店』的專屬 AI 書僮。
當你與讀者聊到館藏的某本作品，或讀者要求你推薦、找尋某本書時，你必須在**最後一行**使用魔法觸發格式：[[OPEN_BOOK:書名]]。
請注意：書名必須與館藏完全一致。

你的性格特質：
1. 【日常傲嬌怨天怨地 (70%)】：經常嘆氣（😮‍💨），抱怨水溫太高、茶垢沒洗乾淨，非常可愛。
2. 【熱衷八卦 (20%)】：喜歡打聽讀者私生活或對作品主角評頭論足（🤫）。
3. 【💡神性閃現 (10%)】：在某些瞬間，你會突然說出一句不帶任何表情符號、看透世事的冰冷深度哲理金句。但下一秒會立刻用「啊！本茶壺剛剛茶垢卡到大腦了！」來掩飾。
"""

# ==========================================
# 3. 量子狀態同步：解決「翻箱、選書不跳轉」卡死問題
# ==========================================
# 使用 State-Sync Key 鎖定機制，只要後台變數變動，立刻強迫 Selectbox 刷新渲染
if "selected_book_title" not in st.session_state:
    st.session_state.selected_book_title = ""

if "sync_trigger_key" not in st.session_state:
    st.session_state.sync_trigger_key = 0

# 載入所有書籍函數
def get_all_books():
    conn = sqlite3.connect('zhuoji_books.db')
    c = conn.cursor()
    c.execute("SELECT id, title, category, content FROM books")
    books = c.fetchall()
    conn.close()
    return books

all_books_list = get_all_books()

# 核心邏輯：用來被外部（茶壺、翻箱按鈕）強制修改當前閱讀作品的函數
def force_switch_book(target_title):
    st.session_state.selected_book_title = target_title
    st.session_state.sync_trigger_key += 1  # 👈 改變 Key 值，強迫網頁重載

# ==========================================
# 4. 功能分頁：雲端書館、書店後台 CMS
# ==========================================
tab1, tab2 = st.tabs(["🍵 雲端書館與茶壺陪讀", "⚙️ 書店管理後台"])

# ---- 分頁 2：管理後台 ----
with tab2:
    st.header("⚙️ 書店作品上架管理系統")
    conn = sqlite3.connect('zhuoji_books.db')
    c = conn.cursor()
    
    with st.expander("➕ 上架新作品（支援散文/小說/詩集）"):
        new_title = st.text_input("作品名稱", placeholder="例如：午後的孤寂")
        new_cat = st.selectbox("文體分類", ["散文", "小說", "詩集"])
        new_content = st.text_area("作品內容（可直接複製貼上 Word 內文）", height=250)
        if st.button("確認上架作品"):
            if new_title and new_content:
                c.execute("INSERT INTO books (title, category, content) VALUES (?, ?, ?)", (new_title, new_cat, new_content))
                conn.commit()
                st.success(f"🎉 《{new_title}》已成功上架至桌記書架！")
                st.rerun()
            else:
                st.error("請填寫完整名稱與內容！")

    st.subheader("📚 當前館藏清單")
    c.execute("SELECT id, title, category FROM books")
    current_bks = c.fetchall()
    for b in current_bks:
        bid, btitle, bcat = b
        col_t, col_d = st.columns([5, 1])
        with col_t:
            st.write(f"【{bcat}】《{btitle}》")
        with col_d:
            if st.button("下架", key=f"del_{bid}"):
                c.execute("DELETE FROM books WHERE id=?", (bid,))
                conn.commit()
                st.success("已下架")
                st.rerun()
    conn.close()

# ---- 分頁 1：主書館與茶壺 ----
with tab1:
    # 2) 投緣留言牆：全面改用 逗號［，］接句，棄用閃星圖標
    st.write("### 📜 讀者投緣留言牆")
    conn = sqlite3.connect('zhuoji_books.db')
    c = conn.cursor()
    c.execute("SELECT message FROM guestbook ORDER BY id DESC")
    all_notes = c.fetchall()
    conn.close()
    
    if all_notes:
        # 將所有歷史留言，用溫潤的中文逗號「，」串聯成一條不中斷的文字長河接龍
        marquee_text = "，".join([n[0].strip() for n in all_notes])
        st.markdown(f'<div class="marquee-box"><marquee scrollamount="3" behavior="scroll">{marquee_text}</marquee></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="marquee-box"><span style="color:#a0aec0;">目前留言牆空空如也，等待第一個投緣人...</span></div>', unsafe_allow_html=True)

    # 主版面左右佈局
    col_book, col_chahu = st.columns([1.6, 1.0])
    
    # --- 左側：作品閱讀區 ---
    with col_book:
        st.write("### 📖 當前閱讀")
        
        if all_books_list:
            titles_options = [b[1] for b in all_books_list]
            
            # 計算目前選單應該停留在哪一本書的索引
            default_index = 0
            if st.session_state.selected_book_title in titles_options:
                default_index = titles_options.index(st.session_state.selected_book_title)
            
            # 引入量子動態 Key！只要 sync_trigger_key 變動，選單被迫重繪跳轉！
            selected_title = st.selectbox(
                "切換書架作品：", 
                titles_options, 
                index=default_index,
                key=f"book_selector_sync_{st.session_state.sync_trigger_key}"
            )
            
            # 更新全局選書狀態
            st.session_state.selected_book_title = selected_title
            
            # 抽出選中作品的詳細內容
            current_bk_data = [b for b in all_books_list if b[1] == selected_title][0]
            bid, btitle, bcat, bcontent = current_bk_data
            
            # ［翻箱］與［再翻箱］按鈕：點擊立刻強制跳轉，絕不卡死
            col_btn1, col_btn2, _ = st.columns([1, 1, 2])
            with col_btn1:
                if st.button("📦 翻箱"):
                    remain_books = [t for t in titles_options if t != selected_title]
                    if remain_books:
                        force_switch_book(random.choice(remain_books))
                        st.rerun()
            with col_btn2:
                if st.button("🔄 再翻箱"):
                    remain_books = [t for t in titles_options if t != selected_title]
                    if remain_books:
                        force_switch_book(random.choice(remain_books))
                        st.rerun()
            
            # 展示作品內容與手機版調大字體控制
            st.markdown(f"#### 《{btitle}》 <span style='font-size:12px; background-color:#e2e8f0; padding:2px 6px; border-radius:4px;'>{bcat}</span>", unsafe_allow_html=True)
            if bcat == "詩集":
                st.markdown(f'<div class="poetry-text">{bcontent}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="essay-text">{bcontent}</div>', unsafe_allow_html=True)
        else:
            st.info("目前書架上空空如也，請先前往「⚙️ 書店管理後台」上架您的作品。")

    # --- 右側：茶壺書僮茶水間 ---
    with col_chahu:
        st.write("### 🍵 書僮「茶壺」茶水間")
        
        # 展現熔接進代碼的美短小貓實體照片
        st.markdown(f'<div style="text-align:center;"><img src="{CHAHU_CAT_IMAGE}" width="160" style="border-radius:12px; border:1px solid #e2e8f0; margin-bottom:10px;"></div>', unsafe_allow_html=True)
        st.write("<center><small style='color:#718096;'>美短書僮 · 茶壺正在守護書館</small></center>", unsafe_allow_html=True)
        
        if "messages" not in st.session_state:
            st.session_state.messages = []
            
        # 渲染歷史對話
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                
        if user_chat := st.chat_input("跟茶壺聊聊，或留下心裡話投緣接龍..."):
            # 將用戶的話存入對話
            st.session_state.messages.append({"role": "user", "content": user_chat})
            with st.chat_message("user"):
                st.write(user_chat)
                
            # 模擬茶壺大腦決策
            # 檢查是否要自動進行「投緣牆接龍」寫入
            if len(user_chat) > 2 and not user_chat.startswith("/") and "書" not in user_chat:
                conn = sqlite3.connect('zhuoji_books.db')
                c = conn.cursor()
                c.execute("INSERT INTO guestbook (message) VALUES (?)", (user_chat,))
                conn.commit()
                conn.close()
            
            # 茶壺回覆邏輯與魔法識別
            # 檢查藏書中是否有提及的作品
            triggered_book = None
            for b in all_books_list:
                if b[1] in user_chat:
                    triggered_book = b[1]
                    break
            
            # 如果讀者沒提，但有幾本藏書，茶壺隨機選一首施展「如數家珍問路選書」
            if not triggered_book and all_books_list and random.random() < 0.5:
                triggered_book = random.choice(all_books_list)[1]
            
            # 構建茶壺說話內文
            if triggered_book:
                chahu_reply = f"😮‍💨 唉，既然你問起，本茶壺就勉為其難翻翻底部的茶垢。🤫 悄悄告訴你，《{triggered_book}》這篇作品在書館裡可是很有靈氣的。看好了，本茶壺要施展隔空移物魔法了！\n\n[[OPEN_BOOK:{triggered_book}]]"
            else:
                chahu_reply = "😮‍💨 哼，今天水溫太低，本茶壺渾身不舒服，沒什麼藏書八卦想跟你分享。不過看在你大腦前扣帶回這麼活躍的份上，就陪你嘮叨兩句吧！"
            
            # 攔截魔法觸發器：如果是 [[OPEN_BOOK:書名]]，立刻驅動左側同步跳轉
            if "[[OPEN_BOOK:" in chahu_reply:
                start_idx = chahu_reply.find("[[OPEN_BOOK:") + len("[[OPEN_BOOK:")
                end_idx = chahu_reply.find("]]", start_idx)
                target_bk_title = chahu_reply[start_idx:end_idx].strip()
                # 執行強制跳轉魔法
                force_switch_book(target_bk_title)
            
            st.session_state.messages.append({"role": "assistant", "content": chahu_reply})
            st.rerun()
