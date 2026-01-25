import yfinance as yf
import json
import os
import resend
from datetime import datetime
import pytz

# 1. 获取数据
# CL=F 是原油期货 (Crude Oil), GC=F 是黄金期货 (Gold)
def get_prices():
    tickers = {"Crude Oil": "CL=F", "Gold": "GC=F"}
    data = {}
    
    for name, symbol in tickers.items():
        try:
            ticker = yf.Ticker(symbol)
            # 获取当天的最新数据
            todays_data = ticker.history(period="1d")
            if not todays_data.empty:
                #以此取收盘价为例，保留2位小数
                price = round(todays_data['Close'].iloc[0], 2)
                data[name] = price
            else:
                data[name] = "N/A"
        except Exception as e:
            print(f"Error fetching {name}: {e}")
            data[name] = "Error"
    
    return data

# 2. 更新 JSON 数据 (保留最近30条)
def update_json(new_data):
    filename = 'data.json'
    tz = pytz.timezone('Asia/Shanghai')
    current_time = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
    
    record = {
        "date": current_time,
        "prices": new_data
    }
    
    # 读取旧数据
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            try:
                history = json.load(f)
            except json.JSONDecodeError:
                history = []
    else:
        history = []
    
    # 追加新记录
    history.insert(0, record) # 把最新的插到最前面
    
    # 截取最近30条
    history = history[:30]
    
    # 写入文件
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=4, ensure_ascii=False)
        
    return record, history

# 3. 发送邮件 (Resend)
def send_email(record):
    # 从环境变量读取 API KEY 和 接收邮箱
    api_key = os.environ.get("RESEND_API_KEY")
    to_email = os.environ.get("RECEIVER_EMAIL")
    
    if not api_key or not to_email:
        print("Error: Missing RESEND_API_KEY or RECEIVER_EMAIL.")
        return

    resend.api_key = api_key
    
    prices_str = "\n".join([f"{k}: ${v}" for k, v in record['prices'].items()])
    
    params = {
        "from": "Daily Report <onboarding@resend.dev>", 
        "to": [to_email], 
        "subject": f"今日大宗商品报价 - {record['date']}",
        "html": f"""
        <div style="font-family: sans-serif; line-height: 1.6; color: #333;">
        <p style="font-size: 16px;"><b>Hello,Jian!</b></p>
        <p style="font-size: 16px;">以下是今日获取的最新数值：</p>
        <ul>
            {''.join([f'<li><strong>{k}</strong>: ${v}</li>' for k, v in record['prices'].items()])}
        </ul>
        <hr>
        <p style="font-size: 12px; color: #888;">Data updated at {record['date']} (Beijing Time)</p>
        </div>
        """
    }
    
    try:
        email = resend.Emails.send(params)
        print("Email sent successfully:", email)
    except Exception as e:
        print("Error sending email:", e)

if __name__ == "__main__":
    print("Starting job...")
    prices = get_prices()
    print(f"Fetched prices: {prices}")
    
    if prices:
        current_record, _ = update_json(prices)
        send_email(current_record)
        print("Job finished.")
    else:
        print("Failed to fetch prices.")
