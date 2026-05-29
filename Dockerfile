# 使用官方標準版 Python 環境（內建編譯工具，安裝套件不卡關）
FROM python:3.9

# 設定工作目錄
WORKDIR /app

# 把 GitHub 倉庫裡的所有程式碼複製到 /app 內
COPY . /app

# 執行安裝
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 暴露通訊埠
EXPOSE 8080

# 啟動指令
CMD ["streamlit", "run", "app.py", "--server.port", "8080", "--server.address", "0.0.0.0"]
