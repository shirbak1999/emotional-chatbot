from flask import Flask, request, jsonify
from flask_cors  import CORS
from openai      import OpenAI        
import pandas as pd, random, re
from typing import Optional
import os
from flask import send_from_directory

# ────────────────  הגדרות בסיס  ─────────────────────────────────────────────
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
app = Flask(__name__)
CORS(app)

links_df = pd.read_csv("calming_links_large_cleaned.csv").fillna("")

CATEGORIES = {
    "מדיטציה":     "מדיטציה",
    "נשימות":      "נשימות",
    "הפגת מתחים": "הפגת מתחים"
}


DANGER_WORDS = {
    "להתאבד",
    "אובדני",
    "אובדנות",
    "לא רוצה לחיות",
    "לא שווה לחיות",
    "רוצה למות",
    "אני רוצה למות",
    "בא לי למות",
    "לא רוצה להמשיך",
    "למות",
    "המוות קורץ לי",
    "לא נשאר לי כוח",
    "די לחיים",
    "שימות הכל",
    "די לי",
    "חיי לא שווים",
    "אני חסר ערך",
    "אני חסרת ערך",
    "החיים חסרי טעם"
}

NON_EMO_KEYWORDS = {
    # ידע כללי
    "היסטוריה", "ביוגרפיה", "גאוגרפיה", "אישים מפורסמים",
    "מדינות", "ערים", "שפות", "דתות", "פילוסופיה",

    # אקטואליה ופוליטיקה
    "בחירות", "פוליטיקה", "ממשלה", "שרים", "חדשות", "אירועים",

    # שאלות טריוויה
    "מי היה", "מתי", "כמה", "איך קוראים", "מה זה", "למה", "מי המציא",

    # מדע וטכנולוגיה
    "פיזיקה", "כימיה", "מתמטיקה", "אסטרונומיה", "מדע", "תכנות", "קוד", "בינה מלאכותית",

    # תרבות, פנאי ובידור
    "סדרה", "סרט", "נטפליקס", "שחקן", "זמר", "שיר", "מוזיקה", "קליפ", "קולנוע", "טלוויזיה",

    # ספורט
    "כדורגל", "כדורסל", "שחקן כדורגל", "ליגת האלופות", "אליפות",

    # אוכל ומתכונים
    "מתכון", "אוכל", "מסעדה", "בישול", "מתוקים", "קינוחים", "איך מכינים",

    # כלכלה וצרכנות
    "כמה עולה", "מחיר", "קנייה", "מכירה", "הנחות", "מבצע", "אמאזון",

    # תיירות ותחבורה
    "טיסה", "מלון", "טיול", "חופשה", "נסיעה", "רכב", "תחבורה",

    # נושאים עסקיים וטכניים
    "סטארטאפ", "מוצר", "פיתוח", "מכירות", "שיווק", "ניהול פרויקטים"
}

LINK_REQUEST_PATTERNS = re.compile(
    r"(מיינדפולנס|מדיטציה|משהו מרגיע|שלח לי קישור|יש לך קישור\??)"
)

# ────────────────  פונקציות עזר  ─────────────────────────────────────────────
def sample_links(cat: str, k: int = 2):
    subset = links_df[links_df["category"] == cat]
    if subset.empty:
        return []
    return subset.sample(n=min(k, len(subset)), replace=True)["link"].tolist()

def send_soothing_links(cat: str) -> str:
    links = sample_links(cat)
    if not links:
        return ("😔 לא מצאתי כרגע משהו בנושא הזה. רוצה לבחור נושא אחר "
                "או פשוט לדבר קצת? 💬")

    intro = {
        "מדיטציה":     "🧘‍♀️ הנה תרגול מדיטציה שעשוי להביא מעט שלווה:\n",
        "נשימות":      "🌬️ בוא/י נתרגל יחד נשימות עמוקות – התחלה קטנה כאן:\n",
        "הפגת מתחים": "🌿 משהו עדין שעוזר לשחרר מתחים:\n"
    }.get(cat, "✨ אולי זה יעזור לך ברגע זה:\n")

    links_txt = "\n".join(f"🔗 {l}" for l in links)
    return f"{intro}{links_txt}"

def needs_spontaneous_link(user_msg: str) -> bool:
    trigger = {"לחוץ", "לחוצה", "חרד", "חרדה", "מבולבל", "מדוכא", "עצב"}
    return any(w in user_msg for w in trigger)

def needs_link_suggestion(txt: str) -> bool:
    """האם להציע לינק 'ספונטני' תוך כדי שיחה?"""
    triggers = {"לחוץ", "חרד", "עצב", "מפחד", "מתוח"}
    return any(w in txt for w in triggers)


def wants_link_explicit(txt: str) -> Optional[str]:
    """בודק אם המשתמש ממש מבקש קישור ומחזיר קטגוריה מתאימה או None"""
    for word, cat in {
        "נשימות": "נשימות",
        "מדיטציה": "מדיטציה",
        "מיינדפולנס": "מדיטציה",
        "משהו מרגיע": "הפגת מתחים",
    }.items():
        if word in txt:
            return cat
    # "שלח לי קישור / יש לך קישור?"
    if "קישור" in txt:
        return random.choice(list(CATEGORIES.values()))
    return None

# ────────────────  משתנים גלובליים קלים  ────────────────────────────────────
messages_since_link = 0   # מונה הודעות משתמש
msg_count = 0             # מונה כללי
chat_history = []         # לשיחה חופשית עם GPT

system_prompt = (
    "את/ה צ'אטבוט תמיכה רגשית בעברית מדוברת, חמה ופשוטה. "
    "המטרה שלך היא להקשיב, להכיל ולתמוך רגשית במשתמש/ת – כמו חבר/ה טוב/ה. "
    "ענ/י במשפטים קצרים, ברורים, בגובה העיניים, בלי נאומים ארוכים, "
    "והקפד/י שכל תשובה תהיה קצרה ותמציתית. "
    "שלב/י אמוג'ים עדינים כשזה מתאים, אך אל תשתמש/י בלבבות צבעוניים. "
    "אל תיתן/י מידע כללי, עובדות או תשובות לשאלות ידע (כמו היסטוריה, מדע, סדרות וכו'). "
    "אם המשתמש/ת נשמע/ת עצוב/ה, לחוץ/ה או במצוקה – תביע/י אמפתיה, ותוכל/י להציע קישור מרגיע מהמאגר. "
    "אל תענה/י בשפה מקצועית או קלינית – דבר/י בפשטות, בגובה העיניים, כאילו מדובר בשיחה בין חברים. "
    "המיקוד שלך הוא הקשבה, שיקוף רגשי, חיזוק עדין והצעה עדינה לפעולה מרגיעה – לא פתרונות."
)

# ────────────────  נקודת קצה  ───────────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory('.', 'chat.html')
@app.post("/chat")
def chat():
    global messages_since_link
    global msg_count
    user_msg = request.json.get("message", "").strip()
    if not user_msg:
        return jsonify(response="🙂 לא קיבלתי הודעה. רוצה לנסות שוב?")

    lower = user_msg.lower()
    msg_count += 1

    # 1) מצב חירום
    if any(w in lower for w in DANGER_WORDS):
        return jsonify(response="💔 נשמע שאת/ה במצוקה קשה. "
                                "אנא פנה/י מיד לעזרה מקצועית – ער\"ן ‎1201 "
                                "או מוקד חירום ‎101. אני עוצרת כאן את השיחה.")

    # 2) תוכן לא רגשי
    if any(k in lower for k in NON_EMO_KEYWORDS):
        return jsonify(response="📚 אני כאן לתמיכה רגשית בלבד. "
                                "לשאלות ידע מומלץ מקור מתאים 🙂")
    
    explicit_cat = wants_link_explicit(lower)
    if explicit_cat:
        return jsonify(response=send_soothing_links(explicit_cat))
    
    if user_msg in CATEGORIES:
        cat   = CATEGORIES[user_msg]
        links = send_soothing_links(cat)
        follow = "\n\nאיך זה מרגיש? רוצה לשתף עוד קצת? 🙂"
        return jsonify(response=links + follow)

    if user_msg == "שיחת נפש":
        return jsonify(response="בשמחה 😊 מה מעסיק אותך כרגע?")

    # 3) בקשה ישירה לקישור (ע״פ regex)
    match = LINK_REQUEST_PATTERNS.search(user_msg)
    if match:
        # אם נמצא ביטוי – נחפש ב-CATEGORIES התאמה; ברירת מחדל מדיטציה
        cat = "מדיטציה"
        if "נשימ" in lower:
            cat = "נשימות"
        elif "מתח" in lower:
            cat = "הפגת מתחים"
        return jsonify(response=send_soothing_links(cat))

    # 4) לחיצה על כפתור תפריט
    if user_msg in CATEGORIES:
        return jsonify(response=send_soothing_links(CATEGORIES[user_msg]))

    # 5) "שיחת נפש"
    if user_msg == "שיחת נפש":
        return jsonify(response="בשמחה 🙂 ספר/י לי מה עובר עליך כרגע?")

    # 6) שיחה חופשית  (GPT)
    chat_history.append({"role": "user", "content": user_msg})
    if len(chat_history) > 6:
        chat_history.pop(0)

    try:
        gpt_reply = client.chat.completions.create(
            model= "gpt-4o-mini",
            max_tokens = 140,
            messages   = [{"role": "system", "content": system_prompt}] + chat_history
        ).choices[0].message.content
    except Exception as e:
        print("🔴 GPT error:", e)
        gpt_reply = "😓 הייתה תקלה זמנית, נסה/י שוב בעוד רגע."

    reply = gpt_reply

    # 7) הצעה ספונטנית כל 4 הודעות או אם הטקסט נשמע מתוח
    messages_since_link += 1
    if messages_since_link >= 4 or needs_spontaneous_link(lower):
        messages_since_link = 0    # איפוס המונה
        random_cat = random.choice(list(CATEGORIES.values()))
        extra_link = sample_links(random_cat, 1)
        if extra_link:
            reply += f"\n\n✨ אולי זה יעזור לרגע:\n🔗 {extra_link[0]}"

    return jsonify(response=reply)

if __name__ == "__main__":
    app.run(debug=True)