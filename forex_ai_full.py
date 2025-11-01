# ================================================================
# 📈 Bot IA de signaux Forex avec envoi automatique sur Telegram
# ================================================================
# Ce bot :
#  - Récupère les données Forex via Alpha Vantage
#  - Analyse les actualités financières via NewsAPI
#  - Utilise une IA (Random Forest + NLP) pour décider Buy / Sell
#  - Envoie les signaux sur Telegram (avec TP et SL)
# ================================================================

import requests
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from transformers import pipeline
import time
from telegram import Bot

# ===================== CONFIGURATION =====================
ALPHA_VANTAGE_API_KEY = 'TON_ALPHA_VANTAGE_API_KEY'
NEWSAPI_KEY = 'TA_NEWSAPI_KEY'
TELEGRAM_BOT_TOKEN = 'TON_TELEGRAM_BOT_TOKEN'
TELEGRAM_CHAT_ID = 'TON_CHAT_ID'

PAIR = 'EURUSD'          # Paire analysée
INTERVAL = '60min'       # Intervalle des données
SLEEP_TIME = 3600        # Délai entre deux analyses (en secondes, ici 1h)

# ===================== CONFIGURATION TELEGRAM =====================
bot = Bot(token=TELEGRAM_BOT_TOKEN)

def envoyer_telegram(message):
    """Envoie un message sur Telegram"""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as e:
        print('Erreur Telegram:', e)

# ===================== RÉCUPÉRATION DES DONNÉES FOREX =====================
BASE_URL = 'https://www.alphavantage.co/query'

def get_forex_data(pair=PAIR, interval=INTERVAL):
    """Récupère les données Forex depuis Alpha Vantage"""
    url = f'{BASE_URL}?function=FX_INTRADAY&from_symbol={pair[:3]}&to_symbol={pair[3:]}&interval={interval}&apikey={ALPHA_VANTAGE_API_KEY}&outputsize=compact'
    r = requests.get(url)
    data = r.json()
    if 'Time Series FX (60min)' in data:
        df = pd.DataFrame.from_dict(data['Time Series FX (60min)'], orient='index')
        df = df.rename(columns=lambda x: x.strip()).astype(float)
        df = df.rename(columns={
            '1. open': 'open',
            '2. high': 'high',
            '3. low': 'low',
            '4. close': 'close'
        })
        return df
    else:
        print('Erreur de récupération Forex:', data)
        return pd.DataFrame()

# ===================== RÉCUPÉRATION DES NEWS =====================
def get_news(query=PAIR, page_size=10):
    """Récupère les actualités économiques récentes"""
    url = f'https://newsapi.org/v2/everything?q={query}&sortBy=publishedAt&pageSize={page_size}&apiKey={NEWSAPI_KEY}'
    r = requests.get(url)
    articles = r.json().get('articles', [])
    news_texts = [a['title'] + '. ' + (a['description'] or '') for a in articles]
    return news_texts

# ===================== ANALYSE NLP (SENTIMENT) =====================
analyseur_sentiment = pipeline('sentiment-analysis')

def sentiment_score(texts):
    """Analyse le sentiment global des actualités"""
    if not texts:
        return 0
    scores = []
    for t in texts:
        result = analyseur_sentiment(t)[0]
        score = result['score'] if result['label'] == 'POSITIVE' else -result['score']
        scores.append(score)
    moyenne = sum(scores) / len(scores)
    return moyenne

# ===================== IA MARCHÉ (RANDOM FOREST) =====================
def prepare_features(df):
    """Prépare les indicateurs techniques"""
    df['MA_5'] = df['close'].rolling(5).mean()
    df['MA_10'] = df['close'].rolling(10).mean()
    df['diff'] = df['MA_5'] - df['MA_10']
    df = df.dropna()
    X = df[['MA_5', 'MA_10', 'diff']].values
    y = np.where(df['diff'].shift(-1) > 0, 1, 0)
    return X, y

def train_market_model(df):
    """Entraîne un modèle de prédiction sur les prix"""
    X, y = prepare_features(df)
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)
    return model

# ===================== DÉCISION SIGNAL + TP/SL =====================
def generate_signal(model, df, sentiment):
    """Combine marché + sentiment pour générer un signal"""
    X, _ = prepare_features(df)
    last_feat = X[-1].reshape(1, -1)
    market_pred = model.predict(last_feat)[0]
    confiance = model.predict_proba(last_feat)[0][market_pred]

    # Fusion IA et sentiment
    score_final = (confiance + (0.5 + sentiment / 2)) / 2

    if score_final > 0.6:
        signal = 'BUY'
    elif score_final < 0.4:
        signal = 'SELL'
    else:
        signal = 'HOLD'

    last_price = df['close'].iloc[-1]

    if signal == "BUY":
        tp = last_price * 1.003  # +0.3%
        sl = last_price * 0.997  # -0.3%
    elif signal == "SELL":
        tp = last_price * 0.997
        sl = last_price * 1.003
    else:
        tp = sl = last_price

    return signal, score_final, last_price, tp, sl

# ===================== BOUCLE PRINCIPALE =====================
print('=== 🤖 Bot IA Forex démarré ===')

while True:
    try:
        df = get_forex_data(PAIR)
        if df.empty:
            time.sleep(60)
            continue

        news = get_news(PAIR)
        sentiment = sentiment_score(news)
        modele = train_market_model(df)

        signal, score, prix, tp, sl = generate_signal(modele, df, sentiment)

        message = (
            f"📈 **Signal Forex IA**\n"
            f"Paire : {PAIR}\n"
            f"Signal : {signal}\n"
            f"Prix actuel : {round(prix, 5)}\n"
            f"🎯 TP : {round(tp, 5)}\n"
            f"⛔ SL : {round(sl, 5)}\n"
            f"Score IA : {round(score, 2)}\n"
            f"Sentiment : {'Positif 🟢' if sentiment > 0 else 'Négatif 🔴'}\n"
        )

        print(message)
        envoyer_telegram(message)
        time.sleep(SLEEP_TIME)

    except Exception as e:
        print("Erreur :", e)
        time.sleep(60)


from transformers import pipeline

classifier = pipeline(
    "sentiment-analysis",
    model="distilbert-base-uncased-finetuned-sst-2-english",
    revision="714eb0f"
)

