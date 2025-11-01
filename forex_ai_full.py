import os
import requests
import time
import gc
from transformers import pipeline
import telegram

# === CONFIGURATION ===
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# === INITIALISATION ===
print("=== 🤖 Bot IA Forex (version légère) démarré ===")

# modèle ultra-léger de sentiment (10x plus petit que DistilBERT)
classifier = pipeline(
    "sentiment-analysis",
    model="sshleifer/tiny-distilbert-base-uncased-finetuned-sst-2-english"
)

bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

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
    """Analyse rapide du sentiment des dernières actualités"""
    url = f"https://newsapi.org/v2/everything?q={query}&apiKey={NEWSAPI_KEY}&language=en&pageSize=3"
    try:
        data = requests.get(url, timeout=10).json()
        texts = [article["title"] for article in data["articles"]]
        if not texts:
            return "NEUTRAL", 0.0
        results = [classifier(t)[0] for t in texts]
        pos = sum(1 for r in results if r["label"] == "POSITIVE")
        neg = sum(1 for r in results if r["label"] == "NEGATIVE")
        score = (pos - neg) / len(results)
        sentiment = "BUY" if score > 0 else "SELL" if score < 0 else "NEUTRAL"
        return sentiment, round(abs(score), 2)
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
    if price:
        send_signal(pair, sentiment, score, price)
    gc.collect()
    time.sleep(60 * 15)  # toutes les 15 minutes
