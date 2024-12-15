import requests
import csv
from datetime import datetime, timedelta
import time
import os
import json

# CoinGecko API-Endpunkt
BASE_URL_TEMPLATE = "https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart/range"

# Liste der Kryptowährungen mit ihren Symbolen und Listungsdaten
cryptocurrencies = [
    {"coin_id": "pyth-network", "symbol": "PYTH", "date": "2024-02-02 14:20"},
    {"coin_id": "jupiter", "symbol": "JUP", "date": "2024-01-31 17:40"},
    {"coin_id": "altlayer", "symbol": "ALT", "date": "2024-01-25 12:10"},
    {"coin_id": "bitcoin", "symbol": "BTC", "date": "2013-04-28 00:00"},
    {"coin_id": "ethereum", "symbol": "ETH", "date": "2015-08-07 00:00"},
    {"coin_id": "binancecoin", "symbol": "BNB", "date": "2017-07-25 00:00"},
]

# Ordner zum Speichern der CSV-Dateien
output_directory = os.path.expanduser("~/Desktop/csv_files")
os.makedirs(output_directory, exist_ok=True)

# Fortschrittsdatei
progress_file = os.path.join(output_directory, "progress.json")

# Funktion zum Abrufen historischer Daten
def fetch_historical_data(coin_id, start_timestamp, end_timestamp):
    url = BASE_URL_TEMPLATE.format(coin_id=coin_id)
    params = {
        "vs_currency": "usd",
        "from": start_timestamp,
        "to": end_timestamp,
    }
    while True:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:  # Rate-Limit überschritten
            print(f"Rate-Limit erreicht bei {coin_id}. Warte 60 Sekunden...")
            time.sleep(60)
        else:
            print(f"Fehler bei {coin_id}: {response.status_code}, {response.text}")
            print("Warte 60 Sekunden nach Fehler...")
            time.sleep(60)
            return None

# Fortschritt speichern
def save_progress(coin_index, current_date):
    with open(progress_file, "w") as f:
        json.dump({"coin_index": coin_index, "current_date": current_date.strftime("%Y-%m-%d")}, f)
    print(f"Fortschritt gespeichert: Coin {coin_index}, Datum {current_date}")

# Fortschritt laden
def load_progress():
    if os.path.isfile(progress_file):
        with open(progress_file, "r") as f:
            return json.load(f)
    return {"coin_index": 0, "current_date": None}

# Daten für jede Kryptowährung abrufen und speichern
progress = load_progress()
start_coin_index = progress["coin_index"]
start_date_str = progress["current_date"]

for coin_index in range(start_coin_index, len(cryptocurrencies)):
    crypto = cryptocurrencies[coin_index]
    coin_id = crypto["coin_id"]
    symbol = crypto["symbol"]
    start_date = datetime.strptime(crypto["date"], "%Y-%m-%d %H:%M")

    # Falls ein Fortschritt für die aktuelle Coin existiert
    if start_date_str and coin_index == start_coin_index:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")

    end_date = start_date + timedelta(days=365)  # Bis zu einem Jahr nach dem Listungsdatum

    # CSV-Datei für diese Kryptowährung erstellen
    output_file = os.path.join(output_directory, f"{symbol}.csv")
    with open(output_file, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Date", "Open", "High", "Low", "Close"])  # Header

        current_date = start_date

        while current_date <= end_date:
            # Start- und Endzeitpunkt für die Abfrage berechnen (30 Tage pro Anfrage)
            start_timestamp = int(current_date.timestamp())
            next_date = current_date + timedelta(days=30)
            end_timestamp = int(next_date.timestamp()) if next_date <= end_date else int(end_date.timestamp())

            # Abrufen der historischen Daten
            data = fetch_historical_data(coin_id, start_timestamp, end_timestamp)

            if data:
                prices = data.get("prices", [])
                if prices:
                    # Verarbeite die täglichen Preise
                    daily_prices = {}
                    for timestamp, price in prices:
                        day = datetime.utcfromtimestamp(timestamp / 1000).date()
                        if day not in daily_prices:
                            daily_prices[day] = []
                        daily_prices[day].append(price)

                    for day, day_prices in daily_prices.items():
                        open_price = day_prices[0]
                        close_price = day_prices[-1]
                        high_price = max(day_prices)
                        low_price = min(day_prices)
                        writer.writerow([day, open_price, high_price, low_price, close_price])
                        print(f"Daten für {symbol} am {day} gespeichert.")
            else:
                print(f"Keine Daten für {symbol} im Zeitraum {current_date} bis {next_date} verfügbar.")

            # Zum nächsten Zeitraum
            current_date = next_date

            # Pause zwischen großen Abfragen
            time.sleep(1)

        print(f"CSV-Datei für {symbol} gespeichert: {output_file}")

    print("Warte 60 Sekunden vor der nächsten Kryptowährung...")
    time.sleep(60)

print("\nAlle Daten wurden erfolgreich abgerufen und gespeichert.")
