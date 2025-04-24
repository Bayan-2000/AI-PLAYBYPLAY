# -*- coding: utf-8 -*-
import requests

# 🔐 حط مفتاحك من DeepSeek هنا
DEEPSEEK_KEY = "sk-0af591eff7be4addacbf7e29297c5d4e"

# 🔗 إعدادات الاتصال
url = "https://api.deepseek.com/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {DEEPSEEK_KEY}",
    "Content-Type": "application/json"
}

# 📩 الرسالة التجريبية
payload = {
    "model": "deepseek-chat",
    "messages": [
        {"role": "system", "content": "أنت مساعد ذكي."},
        {"role": "user", "content": "ما رأيك في مباراة كرة قدم تنتهي بالتعادل؟"}
    ]
}

# 🚀 إرسال الطلب
response = requests.post(url, headers=headers, json=payload)

# ✅ عرض الرد بدون مشاكل ترميز
try:
    result = response.json()['choices'][0]['message']['content']
    print("\nالرد من DeepSeek:\n")
    for line in result.splitlines():
        print(line.encode('utf-8').decode('utf-8'))
except Exception as e:
    print("حدث خطأ أثناء معالجة الرد:")
    print(e)
    print("\nنص الرد الكامل (خام):\n")
    print(response.text)

