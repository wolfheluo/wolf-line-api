# LINE Bot 相關導入
from flask import Flask, request, abort, current_app, render_template, jsonify, url_for, session, redirect
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient,
    MessagingApi,
    Configuration,
    ReplyMessageRequest,
    TextMessage,
    ImageMessage,
    FlexMessage,
    FlexContainer,
    TemplateMessage,
    ButtonsTemplate,
    MessageAction,
    URIAction
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)
import json
import os
from datetime import datetime, timedelta
import uuid
import secrets
from werkzeug.utils import secure_filename
from flask import g

app = Flask(__name__)

# 設定應用程式的 URL 前綴以支援反向代理
app.config['APPLICATION_ROOT'] = '/line-api-wolf'

# 設定 session 密鑰
app.secret_key = secrets.token_hex(16)  # 產生隨機密鑰

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

# 設定上傳檔案
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# 建立必要的資料夾
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('data', exist_ok=True)

# 資料檔案路徑
USERS_FILE = 'data/users.json'


# LINE Bot 相關設定
LINE_BOT_CHANNEL_ACCESS_TOKEN = 'X4TI6QwES7PlfHMN3bs/30IsmgCHqJKeKW0H/f6DpUpaFJT4sUTHuP8CEin05JSUEL2cXoRM8JvQMWDMCpwTdj8bRfvvz5KqxnxedgyqDDTqykPP7ogfepRfnliJqAC8PSkAFvJ+fZKAh95smeutpwdB04t89/1O/w1cDnyilFU='
LINE_BOT_CHANNEL_SECRET = '76f0b084ecea9625a5daab658da0391a'


# 初始化 LINE Bot API
configuration = Configuration(access_token=LINE_BOT_CHANNEL_ACCESS_TOKEN)
api_client = ApiClient(configuration)
line_bot_api = MessagingApi(api_client)
handler = WebhookHandler(LINE_BOT_CHANNEL_SECRET)


# 用戶資料處理函數
def load_users():
    """載入用戶資料"""
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        current_app.logger.error(f"載入用戶資料時發生錯誤: {str(e)}")
        return {}

def save_users(users_data):
    """儲存用戶資料"""
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        current_app.logger.error(f"儲存用戶資料時發生錯誤: {str(e)}")
        return False



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
                    current_app.logger.warning(f"無法獲取用戶 {user_id} 的個人資料: {str(e)}")
                    display_name = "未知用戶"
            
            users_data[user_id] = {
                'user_id': user_id,
                'display_name': display_name,
                'first_message_time': datetime.now().isoformat(),
                'last_message_time': datetime.now().isoformat(),
                'message_count': 1,
                'blocked': False
            }
            current_app.logger.info(f"新用戶記錄: {display_name} (ID: {user_id})")
        else:
            # 更新現有用戶的最後訊息時間和訊息計數
            users_data[user_id]['last_message_time'] = datetime.now().isoformat()
            users_data[user_id]['message_count'] += 1
            
        save_users(users_data)
        return True
        
    except Exception as e:
        current_app.logger.error(f"記錄用戶資訊時發生錯誤: {str(e)}")
        return False







# LINE Bot Webhook 路由
@app.route('/line-webhook', methods=['POST'])
def line_webhook():
    """LINE Bot Webhook 端點"""
    # 獲取 X-Line-Signature header value
    signature = request.headers.get('X-Line-Signature')
    
    if not signature:
        current_app.logger.error("Missing X-Line-Signature header")
        abort(400)
    
    # 獲取請求 body 作為文字
    body = request.get_data(as_text=True)
    current_app.logger.info("LINE Webhook request body: " + body)
    
    # 處理 webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        current_app.logger.error("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)
    
    return 'OK'


# LINE Bot 訊息事件處理器
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    """處理文字訊息"""
    global unauthorized_options
    try:
        # 獲取用戶 ID 和訊息
        user_id = event.source.user_id
        user_message = event.message.text.strip()
        
        current_app.logger.info(f"收到 LINE 訊息: {user_message} (用戶ID: {user_id})")
    
        
        # 記錄用戶資訊
        record_user(user_id)

        # 回覆訊息
        reply_token = event.reply_token


        reply_message = TextMessage(text=f"你說的是: {user_message}")
        
        # 對於非關鍵字回覆的情況
        line_bot_api.reply_message(ReplyMessageRequest(reply_token=reply_token, messages=[reply_message]))
        


    except Exception as e:
        current_app.logger.error(f"處理 LINE 訊息時發生錯誤: {str(e)}")





if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5050)