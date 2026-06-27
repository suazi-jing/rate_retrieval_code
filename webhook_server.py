import json
import requests
import threading
import time
import re
from flask import Flask, request, jsonify

app = Flask(__name__)

DIFY_API_URL = "http://192.168.3.39:5001/v1/chat-messages"
DIFY_API_KEY = "Bearer app-j9MOL8dHjpiWWXejgnOPtp3M"
WASENDER_API_KEY = "7e0546998cd0e9ee198ba4a62f971c750fdff79de5ba946b2f8835e4c71905ec"

processed_message_ids = set()
conversation_ids = {}

WAIT_FIRST = 5
WAIT_SUBSEQUENT = 2
msg_buffers = {}
timers = {}
has_processed = set()
lock = threading.Lock()

# ---------- 改进的关键词检测，避免误判 ----------
def should_send_wait(text):
    """
    判断是否为卡类相关查询，仅当消息中包含卡类关键词且同时存在金额/数字/币种/询问语句时才返回 True。
    避免纯陈述句、闲聊触发。
    """
    text_lower = text.lower()
    # 1. 必须包含一个卡类关键词（精确单词边界，防止 "card" 匹配 "cards"）
    card_keywords = [
        'steam card', 'apple card', '香草卡', '礼品卡',
        'gift card', 'card',
    ]
    has_card = False
    for kw in card_keywords:
        if kw in text_lower:
            has_card = True
            break
    # 2. 或者包含明确的查询意图词
    query_keywords = ['how much', 'balance', 'value', 'rate', '汇率', '查询', '面值']
    has_query = any(kw in text_lower for kw in query_keywords)
    # 3. 包含数字或币种符号
    has_number = bool(re.search(r'\d+', text))
    has_currency = any(symbol in text_lower for symbol in ['€', '$', '£', '¥']) or \
                   any(currency in text_lower.split() for currency in ['eur', 'usd', 'gbp', 'chf', 'jpy', 'cny', 'cad', 'aud'])

    # 触发规则：必须有卡类词+（数字或币种或查询意图）或 查询意图+数字/币种
    if has_card and (has_number or has_currency or has_query):
        return True
    if has_query and (has_number or has_currency or has_card):
        return True
    # 纯数字+币种且无卡类词，可能为闲聊提及金额，不触发（例如"20€" 无上下文不算查询）
    return False

def send_wait_message(target_id):
    """发送 wait 消息到指定目标（个人或群组）"""
    time.sleep(2)
    try:
        session = requests.Session()
        session.trust_env = False
        session.post(
            "https://www.wasenderapi.com/api/send-message",
            headers={
                "Authorization": f"Bearer {WASENDER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={"to": target_id, "text": "wait"},
            timeout=3,
            proxies={"http": None, "https": None}
        )
    except Exception as e:
        print(f"发送 wait 消息失败: {e}")

def process_buffered_message(target_id, context):
    """定时器回调：合并缓冲，异步触发 Dify，重置轮次标记"""
    with lock:
        messages = msg_buffers.pop(target_id, [])
        timers.pop(target_id, None)
        has_processed.discard(target_id)
    if not messages:
        return

    combined_msg = " ".join(messages)
    print(f"合并消息触发 Dify: target_id={target_id}, msg={combined_msg}")

    try:
        session = requests.Session()
        session.trust_env = False
        session.post(
            DIFY_API_URL,
            headers={
                "Authorization": DIFY_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "inputs": {
                    "target_id": target_id,
                    "query": combined_msg,
                    "context": json.dumps(context)
                },
                "query": combined_msg,
                "response_mode": "blocking",
                "user": target_id,
                "conversation_id": conversation_ids.get(target_id, "")
            },
            timeout=1,
            proxies={"http": None, "https": None}
        )
    except:
        pass

@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.json
    event = payload.get('event')
    print(f"收到事件: {event}")

    if event not in ['messages.upsert', 'messages-group.received']:
        return jsonify({"status": "ignored"})

    data = payload.get('data', {})
    msg_obj = data.get('messages', data)
    key = msg_obj.get('key', {})
    msg = msg_obj.get('message', {})
    message_id = key.get('id')

    if message_id:
        if message_id in processed_message_ids:
            print(f"消息 {message_id} 已处理，跳过")
            return jsonify({"status": "duplicate"})
        processed_message_ids.add(message_id)
        if len(processed_message_ids) > 10000:
            processed_message_ids.clear()

    user_msg = msg.get('conversation') or msg.get('extendedTextMessage', {}).get('text', '')
    from_me = key.get('fromMe', False)
    if from_me or not user_msg:
        return jsonify({"status": "ignored"})

    remote_jid = key.get('remoteJid', '')
    
    if '@g.us' in remote_jid:
        target_id = remote_jid
        context = {"type": "group", "group_id": remote_jid}
    else:
        sender_full = (
            key.get('senderPn') or
            key.get('participantPn') or
            key.get('participant') or
            remote_jid
        )
        if not sender_full or '@g.us' in sender_full:
            return jsonify({"status": "ignored"})
        phone = sender_full.split('@')[0]
        target_id = phone
        context = {"type": "personal", "user_phone": phone}

    # ---- 发送 wait 条件判断：首次消息且内容为卡类查询 ----
    if target_id not in has_processed and should_send_wait(user_msg):
        send_wait_message(target_id)

    with lock:
        if target_id in timers and timers[target_id].is_alive():
            timers[target_id].cancel()

        if target_id not in msg_buffers:
            msg_buffers[target_id] = []
        msg_buffers[target_id].append(user_msg)

        wait = WAIT_FIRST if target_id not in has_processed else WAIT_SUBSEQUENT
        if target_id not in has_processed:
            has_processed.add(target_id)

        timer = threading.Timer(wait, process_buffered_message, args=(target_id, context))
        timer.daemon = True
        timer.start()
        timers[target_id] = timer

    print(f"缓冲消息: target_id={target_id}, 缓冲数={len(msg_buffers[target_id])}, 等待={wait}s")
    return jsonify({"status": "ok"})

@app.route('/memory-callback', methods=['POST'])
def memory_callback():
    data = request.json
    target_id = data.get('target_id')
    new_conv_id = data.get('conversation_id')
    if not target_id or not new_conv_id:
        return jsonify({"status": "error", "msg": "缺少参数"})

    with lock:
        conversation_ids[target_id] = new_conv_id
    print(f"更新 conversation_id: {target_id} -> {new_conv_id}")
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000)
