import yfinance as yf
import json
import os
import resend
from datetime import datetime
import pytz

# 1. 获取数据
# CL=F 是原油期货 (Crude Oil), GC=F 是黄金期货 (Gold)
def get_prices():
    tickers = {"Crude Oil": "CL=F", "Gold": "GC=F", "Copper": "HG=F"}
    data = {}
    
    for name, symbol in tickers.items():
        try:
            ticker = yf.Ticker(symbol)
            # 获取最近3天的数据
            hist = ticker.history(period="3d")
            if not hist.empty:
                # 取最后一行（最近的一个交易日）
                price = round(hist['Close'].iloc[-1], 2)
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
    api_key = os.environ.get("RESEND_API_KEY")
    to_email = os.environ.get("RECEIVER_EMAIL")
    from_email = os.environ.get("SENDER_EMAIL")
    from_addr = f"Market Report <{from_email}>"
    
    if not api_key or not to_email:
        print("Error: Missing API keys.")
        return

    resend.api_key = api_key
    
    # 动态生成列表 HTML
    items_html = ""
    for k, v in record['prices'].items():
        items_html += f"""
        <div style="margin-bottom: 10px; padding: 10px; border-left: 4px solid #3b82f6; background: #f9fafb;">
            <span style="font-weight: bold; color: #1f2937;">{k}:</span> 
            <span style="font-size: 18px; color: #059669; margin-left: 10px;">${v}</span>
        </div>
        """

    html_content = f"""
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 500px; margin: auto; border: 1px solid #eee; padding: 20px; border-radius: 10px;">
        <h2 style="color: #111827; border-bottom: 2px solid #f3f4f6; padding-bottom: 10px;">📊 Market Flash</h2>
        <p style="font-size: 14px; color: #6b7280;">Data updated at {record['date']}</p>
        
        <div style="margin-top: 20px;">
            {items_html}
        </div>

        <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="font-size: 12px; color: #9ca3af; text-align: center;">
            Data sourced from yfinance · Reports sent automatically
        </p>
    </div>
    """
    
    params = {
        "from": from_addr,
        "to": [to_email],
        "subject": f"📈 Quotation Update - {record['date'].split(' ')[0]}",
        "html": html_content
    }
    
    try:
        resend.Emails.send(params)
        print("Email sent successfully!")
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
