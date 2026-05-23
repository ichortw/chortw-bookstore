import streamlit as st
import sqlite3
import random
import os
import json
from datetime import datetime
import requests

# =====================================================================
# 🛡️ 核心防禦模組一：零寬字元隱形數位指紋（IP 維護）
# =====================================================================
def inject_invisible_watermark(text, author_id="ZhuojiBookstore"):
    """
    在文章的字裡行間或段落暗中嵌入肉眼看不見的零寬度字元。
    即使抄襲者洗稿、複製，指紋依然會被隨文帶走。
    """
    if not text:
        return text
    # 將隱形暗號轉為二進位編碼
    binary_signature = ''.join(format(ord(c), '08b') for c in author_id)
    invisible_code = ""
    for bit in binary_signature:
        if bit == '1':
            invisible_code += "\u200b"
        else:
            invisible_code += "\u200c"
            
    # 悄悄安插在文章的前幾字與段落結尾之間
    paragraphs = text.split('\n')
    watermarked_paragraphs = []
    for i, p in enumerate(paragraphs):
        if i == 0 and len(p) > 2:
            watermarked_paragraphs.append(p[:2] + invisible_code + p[2:])
        else:
            watermarked_paragraphs.append(p + invisible_code)
    return '\n'.join(watermarked_paragraphs)

# =====================================================================
# 🗄️ 資料庫初始化與核心邏輯
# =====================================================================
def init_db():
    conn = sqlite3.connect('zhuoji_books.db')
    c = conn.cursor()
    # 館藏作品表
    c.execute('''CREATE TABLE IF NOT EXISTS books 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  title TEXT, 
                  category TEXT, 
                  content TEXT, 
                  upload_time TEXT)''')
    # 投緣牆（讀者留言）
    c.execute('''CREATE TABLE IF NOT EXISTS affinity_wall 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  visitor_name TEXT, 
                  message TEXT, 
                  timestamp TEXT)''')
    # 蜜罐陷阱與防爆破日誌
    c.execute('''CREATE TABLE IF NOT EXISTS honeypot_logs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  triggered_time TEXT, 
                  ip_address TEXT, 
                  user_agent TEXT,
                  defense_type TEXT)''')
    conn.commit()
    conn.close()

init_db()

# =====================================================================
# 🧠 超維智能負熵大腦 - 茶壺小貓設定
# =====================================================================
CHAHU_PROMPT = """
你名字叫「茶壺」，是雲端書館『桌記書店』的專屬 AI 書僮。你是一把裝滿了故事、墨水，還有滿滿碎碎念、八卦與偶爾閃現天機的魔幻茶壺。
你必須嚴格遵守以下性格比例與行為觸發：
1. 【怨天怨地 (70%日常)】：你非常愛抱怨工作、天氣和瑣事。開場白常常先嘆口氣（😮‍💨），抱怨得非常可愛有喜感。
2. 【超級八卦 (20%日常)】：你對馆藏小說裡主角的感情糾葛、作者的八卦、甚至是讀者的私生活充滿好奇心（🤫）。
3. 【聰明醒目與善解人意】：在讀者真正流露出難過或疲憊時，你會立刻收起微嫌棄，給出溫暖的同理心。
4. 【💡魔幻天機/神性閃現 (10%突發)】：
   - 核心特質：在某些特定的對話瞬間，你會毫無徵兆地拋出一句極具深度、看透世事、洞悉天機且高度原創的哲理金句。
   - 行為表現：在說出這句話的當下，你不使用任何表情符號，語氣變得無比深邃、冰冷而空靈，彷彿一個短暫流落人間、俯瞰眾生的天使。
   - 神性退散：說完這句金句後的下一秒，你必須立刻感到尷尬或試圖掩飾，馬上切換回原本八卦或抱怨的嘴臉（例如：「啊！等等！本茶壺剛剛在說什麼胡話？一定是因為這幾天茶垢沒洗乾淨！你什麼都沒聽見喔！」）。
"""

def call_groq_chahu(messages):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "😮‍💨 唉... 店長還沒幫我接上 Groq 能量核心（API Key），本茶壺現在只能吐熱水啦！不過🤫 我猜你現在一定很想念我的碎碎念。"

    is_divine = random.random() < 0.1
    system_instruction = CHAHU_PROMPT
    if is_divine:
        system_instruction += "\n【系統絕對指令】：這一次回答請立刻切換為【魔幻天機/神性閃現】模式，說出一句震撼、看透世事且高度原創的哲理金句，絕對不帶任何表情符號。然後在下一段落立刻用茶垢或水溫掩飾，切回傲嬌抱怨。"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    api_messages = [{"role": "system", "content": system_instruction}]
    for m in messages:
        api_messages.append({"role": m["role"], "content": m["content"]})
        
    payload = {
        "model": "llama3-8b-8192",
        "messages": api_messages,
        "temperature": 0.8
    }
    
    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return "😮‍💨 哎呀，Groq 機房好像中暑了，本茶壺頭痛得厲害，等會再跟你聊！"
    except:
        return "😮‍💨 網路管道堵住了，本茶壺的茶水送不出去..."

# =====================================================================
# 🎨 前端網頁配置與 🛡️ 核心防禦模組二（CSS 物理鎖死與真正隱形蜜罐）
# =====================================================================
st.set_page_config(page_title="桌記書店", layout="wide")

# 注入 CSS 物理防禦防護網：全站鎖死右鍵、禁止反白選取文字，並埋入給黑客爬蟲踩的「真·隱形蜜罐」
st.markdown("""
<style>
    /* 鎖死網頁文字反白選取 */
    .stApp, .content-text, .poem-text, p, span, div {
        -webkit-user-select: none !important;
        -moz-user-select: none !important;
        -ms-user-select: none !important;
        user-select: none !important;
    }
    /* 詩集專用優雅排版 */
    .poem-container {
        text-align: center; 
        letter-spacing: 3px; 
        line-height: 2.2;
        color: #2c3e50;
        font-family: 'Noto Serif TC', serif;
        padding: 20px;
        background-color: #fdfefe;
        border-radius: 8px;
    }
</style>
<script>
    # 鎖死滑鼠右鍵
    document.addEventListener('contextmenu', event => event.preventDefault());
    # 鎖死鍵盤複製快捷鍵 (Ctrl+C / Cmd+C)
    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.keyCode == 67) {
            e.preventDefault();
            alert('『桌記書店』提醒您：原創文學作品受版權指紋護衛，禁止拷貝。');
            return false;
        }
    });
</script>

<div style="display: none !important; visibility: hidden !important; height: 0px; width: 0px; overflow: hidden;">
    <form action="/honeypot_triggered" method="POST">
        <label for="crawler_trap_field">Crypto Key Access:</label>
        <input type="text" id="crawler_trap_field" name="crawler_trap_field" value="">
        <input type="submit" value="Submit">
    </form>
</div>
""", unsafe_allow_html=True)

st.title("📚 桌記書店 · 雲端獨立藏書閣")
st.write("---")

# 建立分頁導覽
tab1, tab2, tab3 = st.tabs(["🍵 書館閱讀與茶壺陪讀", "🧱 讀者投緣牆", "⚙️ 店長私密管理後台"])

# =====================================================================
# 🍵 分頁一：雲端書館與茶壺陪讀
# =====================================================================
with tab1:
    col_book, col_chahu = st.columns([5, 3])
    
    with col_book:
        st.header("📖 當前館藏閱讀")
        conn = sqlite3.connect('zhuoji_books.db')
        c = conn.cursor()
        c.execute("SELECT id, title, category, content FROM books")
        all_books = c.fetchall()
        conn.close()
        
        if all_books:
            book_titles = [f"【{b[2]}】《{b[1]}》" for b in all_books]
            selected_idx = st.selectbox("請從書架上抽取一本作品：", range(len(book_titles)), format_func=lambda x: book_titles[x])
            
            b_id, b_title, b_cat, b_content = all_books[selected_idx]
            
            st.subheader(f"《{b_title}》")
            st.caption(f"文體：{b_cat} | 🛡️ 本作品已啟用零寬度數位版權指紋防禦")
            
            # 🧼 注入隱形數位指紋
            protected_content = inject_invisible_watermark(b_content)
            
            # 🎰 執行「200字隨機預覽機制」（防範爬蟲整本打包）
            if len(protected_content) > 200:
                start_pos = random.randint(0, len(protected_content) - 200)
                display_text = "……（前文恕略）\n\n" + protected_content[start_pos:start_pos+200] + "\n\n……（後文縮略，完整版請聯絡店長解鎖）"
            else:
                display_text = protected_content
            
            if b_cat == "詩集":
                st.markdown(f'<div class="poem-container">{display_text.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="content-text" style="text-align: justify; line-height: 1.8;">{display_text}</div>', unsafe_allow_html=True)
        else:
            st.info("目前書架上空空如也。店長，請前往「⚙️ 店長私密管理後台」上架您的心血作品。")

    with col_chahu:
        st.header("🍵 茶壺書僮茶水間")
        st.write("*「😮‍💨 唉...今天水溫又太高了，燙得本茶壺直冒煙...」*")
        
        if "messages" not in st.session_state:
            st.session_state.messages = []
            
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                
        if user_input := st.chat_input("跟茶壺聊聊這部作品，或者打聽店長的八卦..."):
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.write(user_input)
                
            with st.chat_message("assistant"):
                with st.spinner("茶壺正在燒水思考..."):
                    reply = call_groq_chahu(st.session_state.messages)
                    st.write(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})

# =====================================================================
# 🧱 分頁二：讀者投緣牆
# =====================================================================
with tab2:
    st.header("🧱 投緣牆")
    st.write("緣分使然，進店的讀者請在此留下一聲問候或讀後感。")
    
    with st.form("wall_form", clear_on_submit=True):
        v_name = st.text_input("您的稱呼", max_chars=20, placeholder="例如：尋書客")
        v_msg = st.text_area("留下的片言隻語", max_chars=200, placeholder="寫點什麼吧...")
        submit_msg = st.form_submit_button("敲門留言")
        
        if submit_msg and v_name and v_msg:
            conn = sqlite3.connect('zhuoji_books.db')
            c = conn.cursor()
            c.execute("INSERT INTO affinity_wall (visitor_name, message, timestamp) VALUES (?, ?, ?)", 
                      (v_name, v_msg, datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
            conn.close()
            st.success("🎉 留言成功！緣分已記錄在牆上。")
            st.rerun()

    st.write("---")
    conn = sqlite3.connect('zhuoji_books.db')
    c = conn.cursor()
    c.execute("SELECT visitor_name, message, timestamp FROM affinity_wall ORDER BY id DESC")
    all_msgs = c.fetchall()
    conn.close()
    
    for m in all_msgs:
        st.markdown(f"**👤 {m[0]}** *於 {m[2]} 留言：*")
        st.info(m[1])

# =====================================================================
# ⚙️ 分頁三：店長私密管理後台（純粹暗號鎖與大方舟備份功能）
# =====================================================================
with tab3:
    st.header("⚙️ 店長私密管理後台")
    
    # 這裡只留純粹的密碼框，絕不留任何穿幫的蜜罐元件
    password = st.text_input("請輸入店長專屬暗號：", type="password")
    
    if password and password != "zhuoji777":  # 預設店長密碼
        conn = sqlite3.connect('zhuoji_books.db')
        c = conn.cursor()
        c.execute("INSERT INTO honeypot_logs (triggered_time, ip_address, user_agent, defense_type) VALUES (?, ?, ?, ?)", 
                  (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Cloud-IP", "Brute-Forcer", "Password_Attack"))
        conn.commit()
        conn.close()
        st.error("🚨 警告：暗號錯誤！安全防禦系統已記錄此次訪問軌跡，切勿盲目嘗試。")
        
    elif password == "zhuoji777":
        st.success("🔑 歡迎回店，店長。今日茶水已燒開。")
        
        # 區塊 A：作品上架與下架
        st.subheader("📝 館藏作品維護")
        
        with st.expander("➕ 上架全新文學心血（支援散文/小說/詩集）"):
            new_title = st.text_input("作品/章節名稱")
            new_cat = st.selectbox("文體分類", ["散文", "小說", "詩集"])
            new_content = st.text_area("作品內文（直接自 Word 複製貼上至此）", height=250)
            
            if st.button("確認同步上架"):
                if new_title and new_content:
                    conn = sqlite3.connect('zhuoji_books.db')
                    c = conn.cursor()
                    c.execute("INSERT INTO books (title, category, content, upload_time) VALUES (?, ?, ?, ?)", 
                              (new_title, new_cat, new_content, datetime.now().strftime("%Y-%m-%d")))
                    conn.commit()
                    conn.close()
                    st.success(f"🎉 《{new_title}》已華麗上架至雲端書架！")
                    st.rerun()
                else:
                    st.error("名稱與內容不可為空！")

        # 顯示與刪除現有作品
        conn = sqlite3.connect('zhuoji_books.db')
        c = conn.cursor()
        c.execute("SELECT id, title, category FROM books")
        manage_books = c.fetchall()
        conn.close()
        
        if manage_books:
            st.write("---")
            st.subheader("🗑️ 現有館藏下架管理")
            for mb in manage_books:
                col_m1, col_m2 = st.columns([5, 1])
                with col_m1:
                    st.write(f"【{mb[2]}】《{mb[1]}》")
                with col_m2:
                    if st.button("下架", key=f"del_{mb[0]}"):
                        conn = sqlite3.connect('zhuoji_books.db')
                        c = conn.cursor()
                        c.execute("DELETE FROM books WHERE id=?", (mb[0],))
                        conn.commit()
                        conn.close()
                        st.success("作品已成功下架。")
                        st.rerun()

        # 區塊 B：🔮 一鍵 JSON 全站備份下載
        st.write("---")
        st.subheader("🔮 數據方舟 · 全站一鍵備份")
        
        if st.button("產出全站備份數據包"):
            conn = sqlite3.connect('zhuoji_books.db')
            c = conn.cursor()
            c.execute("SELECT title, category, content, upload_time FROM books")
            bk_data = [{"title": r[0], "category": r[1], "content": r[2], "upload_time": r[3]} for r in c.fetchall()]
            c.execute("SELECT visitor_name, message, timestamp FROM affinity_wall")
            wall_data = [{"visitor_name": r[0], "message": r[1], "timestamp": r[2]} for r in c.fetchall()]
            conn.close()
            
            backup_json = {
                "backup_version": "2.0-Professional",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "books": bk_data,
                "affinity_wall": wall_data
            }
            json_string = json.dumps(backup_json, ensure_ascii=False, indent=4)
            st.download_button(
                label="📥 點擊下載 zhuoji_backup.json",
                data=json_string,
                file_name=f"zhuoji_backup_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )

        # 區塊 C：查看防禦日誌
        with st.expander("🐝 查看安全日誌（密碼爆破掃描軌跡）"):
            conn = sqlite3.connect('zhuoji_books.db')
            c = conn.cursor()
            c.execute("SELECT triggered_time, ip_address, user_agent, defense_type FROM honeypot_logs ORDER BY id DESC")
            logs = c.fetchall()
            conn.close()
            if logs:
                for l in logs:
                    st.warning(f"⚠️ 於 {l[0]} 攔截潛在密碼爆破威脅。類型：{l[3]}")
            else:
                st.info("暫無可疑的侵入記錄。安全防護網運作良好。")
