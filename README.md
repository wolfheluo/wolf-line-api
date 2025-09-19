# LINE Bot API Wolf

一個基於 Flask 的 LINE Bot 應用程式，提供訊息回覆和用戶管理功能。

## 功能特色

- 📱 LINE Bot 訊息接收和回覆
- 👥 用戶資料記錄和管理
- 🔒 環境變數管理（保護敏感資訊）
- 📝 完整的日誌記錄系統
- ⚡ 錯誤處理和異常管理

## 安裝與設定

### 1. 安裝依賴套件

```bash
pip install -r requirements.txt
```

### 2. 環境變數設定

複製 `.env.example` 為 `.env` 並填入您的 LINE Bot 資訊：

```env
# LINE Bot 設定
LINE_BOT_CHANNEL_ACCESS_TOKEN=您的Channel_Access_Token
LINE_BOT_CHANNEL_SECRET=您的Channel_Secret

# Flask 設定
FLASK_ENV=development
FLASK_DEBUG=True
FLASK_HOST=0.0.0.0
FLASK_PORT=5050
```

### 3. 執行應用程式

```bash
python app.py
```

## 專案結構

```
line-api-wolf/
├── app.py              # 主要應用程式檔案
├── requirements.txt    # Python 依賴套件
├── .env               # 環境變數設定檔
├── .gitignore         # Git 忽略檔案設定
├── data/              # 用戶資料儲存目錄
├── static/uploads/    # 檔案上傳目錄
└── README.md          # 專案說明文件
```

## 主要優化項目

### ✅ 已完成的優化

1. **安全性提升**
   - 移除硬編碼的敏感資訊
   - 使用環境變數管理 LINE Bot Token 和 Secret
   - 添加 .gitignore 保護敏感檔案

2. **配置管理改善**
   - 建立 Config 類別統一管理所有設定
   - 支援從環境變數讀取配置

3. **錯誤處理強化**
   - 完整的異常處理機制
   - 詳細的日誌記錄系統
   - 錯誤訊息本地化

4. **程式碼結構優化**
   - 移除未使用的導入模組
   - 修復變數引用錯誤
   - 改善代碼可讀性

## LINE Bot Webhook 設定

1. 在 LINE Developers Console 中設定 Webhook URL：
   ```
   https://您的域名/line-webhook
   ```

2. 確保伺服器可以接收 HTTPS 請求

## 日誌檔案

應用程式會自動創建 `app.log` 檔案記錄運行日誌，包含：
- 用戶訊息記錄
- 錯誤和異常資訊
- 系統運行狀態

## 注意事項

- 請勿將 `.env` 檔案提交到版本控制系統
- 定期檢查日誌檔案以監控應用程式運行狀態
- 建議在生產環境中關閉 DEBUG 模式

## 貢獻

歡迎提交 Issue 和 Pull Request 來改善這個專案！