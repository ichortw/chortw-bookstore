# 使用官方輕量級 Python 環境
FROM python:3.9-slim

# 設定貨櫃內的工作目錄
WORKDIR /app

# 複製當前目錄內的所有檔案到貨櫃中
COPY . /app

# 升級 pip 並強制安裝 requirements.txt 裡的所有套件
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 暴露 Streamlit 預設通訊埠（Zeabur 會自動對接）
EXPOSE 8080

# 強制使用 Streamlit 啟動專案
CMD ["streamlit", "run", "app.py", "--server.port", "8080", "--server.address", "0.0.0.0"]
