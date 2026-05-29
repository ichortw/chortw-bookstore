# 1. 使用官方 Python 輕量環境
FROM python:3.9-slim

# 2. 設定工作目錄
WORKDIR /app

# 3. 先複製依賴文件，並直接在此處安裝所有套件（包含 python-docx）
COPY requirements.txt ./

# 優化點：將升級 pip 與安裝套件合併，並確保 python-docx 被包含在 requirements.txt 中
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 4. 複製專案內的所有其他程式碼到 /app
COPY . .

# 5. 暴露 Zeabur 通訊埠
EXPOSE 8080

# 6. 啟動指令（加上 --server.enableCORS=false 與 --server.enableXsrfProtection=false，避免網頁 WebSocket 斷線）
CMD ["streamlit", "run", "app.py", \
     "--server.port=8080", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--server.enableCORS=false", \
     "--server.enableXsrfProtection=false"]
