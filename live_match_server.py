from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from prompt_builder import (
    build_master_prompt,
    build_translation_prompt,
    build_stats_card_prompt
)
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
CORS(app)

DEEPSEEK_API_KEY = "sk-0af591eff7be4addacbf7e29297c5d4e"
API_FOOTBALL_KEY = "090f30ede667fc392255ad703176cb79"
fixture_id = 1218540


latest_stats = None
latest_events = None

# ========== دوال مساعدة ==========

def truncate_text(text, max_words=300):
    words = text.split()
    return ' '.join(words[:max_words]) + '...' if len(words) > max_words else text

def get_match_data(fixture_id):
    headers = {"x-apisports-key": API_FOOTBALL_KEY}
    stats_url = f"https://v3.football.api-sports.io/fixtures/statistics?fixture={fixture_id}"
    events_url = f"https://v3.football.api-sports.io/fixtures/events?fixture={fixture_id}"
    stats_res = requests.get(stats_url, headers=headers)
    events_res = requests.get(events_url, headers=headers)
    if stats_res.status_code != 200 or events_res.status_code != 200:
        return None, None
    return stats_res.json()['response'], events_res.json()['response']



def get_quarter_and_word_count(minute):
    if 1 <= minute <= 11:
        return 270
    elif 12 <= minute <= 22:
        return 135
    elif 23 <= minute <= 33:
        return 67
    elif 34 <= minute <= 45:
        return 67
    elif 46 <= minute <= 56:
        return 270
    elif 57 <= minute <= 67:
        return 135
    elif 68 <= minute <= 78:
        return 67
    elif 79 <= minute <= 90:
        return 67
    return 0

def generate_deepseek_prompt(mode, **kwargs):
    stats = kwargs.get("stats")
    events = kwargs.get("events")

    if mode == "translation":
        return build_translation_prompt(stats, events, kwargs["minute"], kwargs["start_second"], kwargs["end_second"], kwargs["word_count"])
    elif mode == "card":
        return build_stats_card_prompt(stats, events, kwargs["minute"] - 5, kwargs["minute"])
    elif mode == "chat":
        return build_master_prompt(stats, events, kwargs["question"])
    else:
        return "❌ الوضع غير معروف."

def call_deepseek(prompt):
    headers_ds = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "أنت مساعد تحليلي ذكي. لا تقدم رأيًا، فقط اعرض ما يُطلب بدقة."},
            {"role": "user", "content": prompt}
        ]
    }
    try:
        res = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers_ds, json=payload)
        return res.json()['choices'][0]['message']['content'] if res.status_code == 200 else "⚠ فشل في التوليد"
    except Exception as e:
        print(f"DeepSeek Error: {e}")
        return "⚠ خطأ تقني."

# ========== /live-summary ==========

@app.route("/live-summary", methods=["GET"])
def live_summary():
    try:
        elapsed = int(request.args.get("elapsed", 0))
        if elapsed < 1 or elapsed > 90:
            return jsonify({"error": "❌ وقت غير صالح"}), 400

        global latest_stats, latest_events
        if not latest_stats or not latest_events:
            latest_stats, latest_events = get_match_data(fixture_id)

        summaries = []
        for minute in range(1, elapsed + 1):
            word_count = get_quarter_and_word_count(minute)
            for segment in range(3):
                prompt = generate_deepseek_prompt(
                    "translation",
                    minute=minute,
                    start_second=segment * 20,
                    end_second=(segment + 1) * 20,
                    word_count=word_count,
                    stats=latest_stats,
                    events=latest_events
                )
                analysis = call_deepseek(prompt)
                summaries.append({
                    "minute": minute,
                    "range": f"{minute}:{segment*20:02d} - {minute}:{(segment+1)*20:02d}",
                    "text": analysis
                })

        stats_card = None
        if True: 
            prompt = generate_deepseek_prompt("card", minute=elapsed, stats=latest_stats, events=latest_events)
            stats_text = call_deepseek(prompt)
            stats_card = {
                "minute": elapsed,
                "text": stats_text
            }
             # ✅ تحقق قبل الإرسال
        print("🧪 الوقت الحالي:", elapsed)
        print("📊 محتوى البطاقة التحليلية:")
        print(stats_card)

        return jsonify({
            "summary": summaries,
            "stats_card": stats_card
        })


    except Exception as e:
        return jsonify({"error": f"⚠ حصل خطأ أثناء التوليد: {str(e)}"})

# ========== /ask ==========

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    question = data.get("question")

    global latest_stats, latest_events
    if not latest_stats or not latest_events:
        latest_stats, latest_events = get_match_data(fixture_id)

    if not latest_stats and not latest_events:
        return jsonify({"reply": "🚀 المباراة بدأت مؤخرًا، وراح توصلك البيانات والتحليل أول ما تبدأ الأحداث أو تتوفر الإحصائيات!"})

    prompt = generate_deepseek_prompt("chat", stats=latest_stats, events=latest_events, question=question)
    reply = call_deepseek(prompt)
    return jsonify({"reply": truncate_text(reply)})

# ========== جدولة تحديث البيانات ==========

scheduler = BackgroundScheduler()
scheduler.add_job(func=lambda: get_match_data(fixture_id), trigger="interval", seconds=60)
scheduler.start()

# ========== تشغيل السيرفر ==========

if __name__ == '__main__':
    app.run(debug=True, port=5000)