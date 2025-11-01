import os
import requests
import time
import gc
import telegram

# === CONFIGURATION ===
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")  # utilisé pour récupérer les titres d'actualité
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

print("=== 🤖 Bot IA Forex (version légère) démarré ===")

# === INITIALISATION DU BOT TELEGRAM ===
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# === ANALYSE LEXICALE SIMPLE ===
def analyse_sentiment(text):
    pos = ["good", "growth", "strong", "profit", "rise"]
    neg = ["bad", "loss", "fall", "weak", "crash"]
    score = sum(1 for w in pos if w in text.lower()) - sum(1 for w in neg if w in text.lower())
    if score > 0:
        return "BUY", min(score / 5, 1.0)
    elif score < 0:
        return "SELL", min(abs(score / 5), 1.0)
    else:
        return "NEUTRAL", 0.0

# === FONCTIONS ===
def get_forex_price(pair="EURUSD"):
    """Récupère le dernier prix Forex depuis Alpha Vantage"""
    url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={pair[:3]}&to_currency={pair[3:]}&apikey={ALPHA_VANTAGE_API_KEY}"
    try:
        data = requests.get(url, timeout=10).json()
        return float(data["Realtime Currency Exchange Rate"]["5. Exchange Rate"])
    except Exception as e:
        print(f"Erreur récupération prix : {e}")
        return None

def get_news_sentiment(query="forex"):
    """Récupère les titres de news et calcule le sentiment via analyse lexicale"""
    url = f"https://newsapi.org/v2/everything?q={query}&apiKey={NEWSAPI_KEY}&language=en&pageSize=3"
    try:
        data = requests.get(url, timeout=10).json()
        texts = [article["title"] for article in data["articles"]]
        if not texts:
            return "NEUTRAL", 0.0
        results = [analyse_sentiment(t) for t in texts]
        # moyenne des scores
        total_score = sum(r[1] if r[0]=="BUY" else -r[1] if r[0]=="SELL" else 0 for r in results) / len(results)
        sentiment = "BUY" if total_score > 0 else "SELL" if total_score < 0 else "NEUTRAL"
        return sentiment, round(abs(total_score), 2)
    except Exception as e:
        print(f"Erreur analyse news : {e}")
        return "NEUTRAL", 0.0

def send_signal(pair, sentiment, score, price):
    """Envoie un signal sur Telegram"""
    message = f"💹 *Signal Forex IA*\nPaire : {pair}\nSignal : {sentiment}\nScore : {score}\nPrix : {price}"
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode="Markdown")
        print(f"Signal envoyé : {sentiment} ({score})")
    except Exception as e:
        print(f"Erreur envoi Telegram : {e}")

# === BOUCLE PRINCIPALE ===
while True:
    pair = "EURUSD"
    price = get_forex_price(pair)
    sentiment, score = get_news_sentiment(pair)
    if price is not None:
        send_signal(pair, sentiment, score, price)
    # libération mémoire
    gc.collect()
    # pause 15 minutes
    time.sleep(60 * 15)
