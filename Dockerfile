# 1. 使用官方 Python 環境
FROM python:3.9-slim

# 2. 設定工作目錄（後續的指令都會在此目錄下執行）
WORKDIR /app

# 3. 先複製依賴文件，並安裝套件（利用 Docker 快取機制，沒改套件時編譯極快）
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 4. 複製專案內的所有其他程式碼到 /app
COPY . .

# 5. 暴露 Zeabur 或 容器預設的通訊埠
EXPOSE 8080

# 6. 啟動指令（加入 headless 參數，確保 Streamlit 在伺服器環境下不會跳出瀏覽器請求而崩潰）
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0", "--server.headless=true"]
