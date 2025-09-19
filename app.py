# LINE Bot 相關導入
from flask import Flask, request, abort, current_app, url_for, g
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient,
    MessagingApi,
    Configuration,
    ReplyMessageRequest,
    TextMessage,
    MessagingApiBlob
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    ImageMessageContent
)
import json
import os
import logging
from datetime import datetime
import secrets
from dotenv import load_dotenv
import requests
import uuid

# 載入環境變數
load_dotenv()

app = Flask(__name__)

# 配置類別
class Config:
    # 基本設定
    APPLICATION_ROOT = '/line-api-wolf'
    SECRET_KEY = secrets.token_hex(16)
    
    # LINE Bot 設定 - 從環境變數讀取
    LINE_BOT_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_BOT_CHANNEL_ACCESS_TOKEN')
    LINE_BOT_CHANNEL_SECRET = os.getenv('LINE_BOT_CHANNEL_SECRET')
    
    
    # Flask 伺服器設定
    FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5050))
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    # 資料檔案路徑
    USERS_FILE = 'data/users.json'

# 套用配置
app.config.from_object(Config)

# 檢查必要的環境變數
if not Config.LINE_BOT_CHANNEL_ACCESS_TOKEN or not Config.LINE_BOT_CHANNEL_SECRET:
    raise ValueError("請在 .env 檔案中設定 LINE_BOT_CHANNEL_ACCESS_TOKEN 和 LINE_BOT_CHANNEL_SECRET")

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.FileHandler('app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@app.before_request
def before_request():
    g.script_root = '/line-api-wolf'

@app.context_processor
def override_url_for():
    return dict(url_for=dated_url_for)

def dated_url_for(endpoint, **values):
    if endpoint == 'static':
        filename = values.get('filename', None)
        if filename:
            return f'/line-api-wolf/static/{filename}'
    return url_for(endpoint, **values)


# 初始化 LINE Bot API
try:
    configuration = Configuration(access_token=Config.LINE_BOT_CHANNEL_ACCESS_TOKEN)
    api_client = ApiClient(configuration)
    line_bot_api = MessagingApi(api_client)
    line_bot_blob_api = MessagingApiBlob(api_client)
    handler = WebhookHandler(Config.LINE_BOT_CHANNEL_SECRET)
    logger.info("LINE Bot API 初始化成功")
except Exception as e:
    logger.error(f"LINE Bot API 初始化失敗: {str(e)}")
    raise


def load_users():
    """載入用戶資料"""
    try:
        if os.path.exists(Config.USERS_FILE):
            with open(Config.USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"載入用戶資料時發生錯誤: {str(e)}")
        return {}

def save_users(users_data):
    """儲存用戶資料"""
    try:
        with open(Config.USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"儲存用戶資料時發生錯誤: {str(e)}")
        return False

def save_message_to_file(user_id, user_name, message, message_type="text"):
    """儲存訊息到檔案"""
    try:
        message_file = os.path.join('static', 'message.txt')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 確保目錄存在
        os.makedirs('static', exist_ok=True)
        
        # 格式化訊息內容
        if message_type == "text":
            log_entry = f"[{timestamp}] [{user_name}] 文字訊息: {message}\n"
        else:
            log_entry = f"[{timestamp}] [{user_name}] {message_type}訊息: {message}\n"

        # 追加寫入檔案
        with open(message_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
            
        logger.info(f"成功儲存訊息到 {message_file}")
        return True
        
    except Exception as e:
        logger.error(f"儲存訊息到檔案時發生錯誤: {str(e)}")
        return False

def download_and_save_image(message_id, user_id, user_name):
    """下載並儲存圖片"""
    try:
        # 確保 static/IMG 目錄存在
        os.makedirs('static/IMG', exist_ok=True)
        
        # 獲取圖片內容 - 使用 MessagingApiBlob
        message_content = line_bot_blob_api.get_message_content(message_id)
        
        # 生成唯一的檔案名稱
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{uuid.uuid4().hex[:8]}.jpg"
        file_path = os.path.join('static', 'IMG', filename)
        
        # 儲存圖片
        with open(file_path, 'wb') as f:
            f.write(message_content)
                
        logger.info(f"成功儲存圖片到 {file_path}")
        
        # 同時記錄到訊息檔案
        save_message_to_file(user_id, user_name, f"圖片已儲存為 static/IMG/{filename}", "image")
        
        return filename
        
    except Exception as e:
        logger.error(f"下載並儲存圖片時發生錯誤: {str(e)}")
        return None



def record_user(user_id, display_name=None):
    """記錄用戶資訊"""
    try:
        users_data = load_users()
        
        # 如果用戶不存在，則新增
        if user_id not in users_data:
            # 如果沒有提供名字，嘗試從 LINE API 獲取
            if not display_name:
                try:
                    profile = line_bot_api.get_profile(user_id)
                    display_name = profile.display_name
                except Exception as e:
                    logger.warning(f"無法獲取用戶 {user_id} 的個人資料: {str(e)}")
                    display_name = "未知用戶"
            
            users_data[user_id] = {
                'user_id': user_id,
                'display_name': display_name,
                'first_message_time': datetime.now().isoformat(),
                'last_message_time': datetime.now().isoformat(),
                'message_count': 1,
                'blocked': False
            }
            logger.info(f"新用戶記錄: {display_name} (ID: {user_id})")
        else:
            # 更新現有用戶的最後訊息時間和訊息計數
            users_data[user_id]['last_message_time'] = datetime.now().isoformat()
            users_data[user_id]['message_count'] += 1
            
        return save_users(users_data)
        
    except Exception as e:
        logger.error(f"記錄用戶資訊時發生錯誤: {str(e)}")
        return False


# LINE Bot Webhook 路由
@app.route('/line-webhook', methods=['POST'])
def line_webhook():
    """LINE Bot Webhook 端點"""
    try:
        # 獲取 X-Line-Signature header value
        signature = request.headers.get('X-Line-Signature')
        
        if not signature:
            logger.error("Missing X-Line-Signature header")
            abort(400)
        
        # 獲取請求 body 作為文字
        body = request.get_data(as_text=True)
        logger.info("收到 LINE Webhook 請求")
        
        # 處理 webhook body
        handler.handle(body, signature)
        return 'OK'
        
    except InvalidSignatureError:
        logger.error("Invalid signature. 請檢查您的 channel access token/channel secret.")
        abort(400)
    except Exception as e:
        logger.error(f"處理 Webhook 時發生錯誤: {str(e)}")
        abort(500)


# LINE Bot 訊息事件處理器
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    """處理文字訊息"""
    try:
        # 獲取用戶 ID 和訊息
        user_id = event.source.user_id
        user_message = event.message.text.strip()
        
        logger.info(f"收到 LINE 訊息: {user_message} (用戶ID: {user_id})")
        
        # 獲取用戶名稱
        display_name = "未知用戶"
        try:
            profile = line_bot_api.get_profile(user_id)
            display_name = profile.display_name
        except Exception as e:
            logger.warning(f"無法獲取用戶 {user_id} 的個人資料: {str(e)}")
        
        # 記錄用戶資訊
        if not record_user(user_id, display_name):
            logger.warning(f"記錄用戶 {user_id} 資訊失敗")

        # 儲存訊息到檔案
        save_message_to_file(user_id, display_name, user_message, "text")

        # 回覆訊息
        reply_token = event.reply_token
        reply_message = TextMessage(text=f"你說的是: {user_message}")
        
        # 發送回覆
        line_bot_api.reply_message(
            ReplyMessageRequest(reply_token=reply_token, messages=[reply_message])
        )
        logger.info(f"成功回覆用戶 {user_id} 的訊息")
        
    except Exception as e:
        logger.error(f"處理 LINE 訊息時發生錯誤: {str(e)}", exc_info=True)

@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image(event):
    """處理圖片訊息"""
    try:
        # 獲取用戶 ID 和訊息 ID
        user_id = event.source.user_id
        message_id = event.message.id
        
        logger.info(f"收到 LINE 圖片訊息 (用戶ID: {user_id}, 訊息ID: {message_id})")
        
        # 獲取用戶名稱
        display_name = "未知用戶"
        try:
            profile = line_bot_api.get_profile(user_id)
            display_name = profile.display_name
        except Exception as e:
            logger.warning(f"無法獲取用戶 {user_id} 的個人資料: {str(e)}")
        
        # 記錄用戶資訊
        if not record_user(user_id, display_name):
            logger.warning(f"記錄用戶 {user_id} 資訊失敗")

        # 下載並儲存圖片
        saved_filename = download_and_save_image(message_id, user_id, display_name)
        
        # 回覆訊息
        reply_token = event.reply_token
        if saved_filename:
            reply_message = TextMessage(text=f"收到你的圖片！已儲存為: {saved_filename}")
        else:
            reply_message = TextMessage(text="收到你的圖片，但儲存時發生錯誤。")
        
        # 發送回覆
        line_bot_api.reply_message(
            ReplyMessageRequest(reply_token=reply_token, messages=[reply_message])
        )
        logger.info(f"成功回覆用戶 {user_id} 的圖片訊息")
        
    except Exception as e:
        logger.error(f"處理 LINE 圖片訊息時發生錯誤: {str(e)}", exc_info=True)





if __name__ == '__main__':
    try:
        logger.info(f"啟動 LINE Bot 伺服器於 {Config.FLASK_HOST}:{Config.FLASK_PORT}")
        app.run(
            host=Config.FLASK_HOST, 
            debug=Config.FLASK_DEBUG, 
            port=Config.FLASK_PORT
        )
    except Exception as e:
        logger.error(f"啟動伺服器時發生錯誤: {str(e)}")
        raise