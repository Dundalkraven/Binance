import os
import requests
import csv
from time import sleep
from datetime import datetime, timedelta
from google.cloud import bigquery
from google.oauth2 import service_account
import time
# Coingecko API-Schlüssel (mit deinem API-Schlüssel)
COINGECKO_API_KEY = "binance_botCG-927dnHGw9PBDjjWHuCAbpt3Y"  # Dein Coingecko API-Key
API_URL = "https://api.coingecko.com/api/v3/coins/{coin_id}/history"
# BigQuery-Konfiguration
BQ_PROJECT_ID = "binance-bot-442813"
BQ_DATASET = "simple"
credentials = service_account.Credentials.from_service_account_file(
    "/Users/juljul/Desktop/binance-bot-442813-3b39bea3142a.json"
)
bq_client = bigquery.Client(credentials=credentials, project=BQ_PROJECT_ID)
# Lokaler Ordner
output_folder = "/Users/juljul/Desktop/simple"
os.makedirs(output_folder, exist_ok=True)
# Währungsliste für 15 Coins (Erweitert)
coins = [
    {"coin_id": "pyth-network", "symbol": "PYTH", "date": "2024-02-02 14:20"},
    {"coin_id": "jupiter", "symbol": "JUP", "date": "2024-01-31 17:40"},
    # Füge hier alle deine Coins hinzu
]
# Funktion zum Abrufen der täglichen Durchschnittswerte
def get_daily_average(coin_id, date):
    try:
        params = {"date": date.strftime("%d-%m-%Y"), "localization": "false"}
        # API-Key im Header hinzufügen
        headers = {
            'Authorization': f'Bearer {COINGECKO_API_KEY}'
        }
        # Anfrage an die API
        response = requests.get(API_URL.format(coin_id=coin_id), params=params, headers=headers)
        # Fehlerbehandlung und Protokollierung
        if response.status_code == 200:
            data = response.json()
            if "market_data" in data:
                return data["market_data"].get("current_price", {}).get("usd", None)
            else:
                print(f"Keine Marktdaten für {coin_id} am {date}: {data}")
        elif response.status_code == 429:  # API-Limit erreicht
            print("API-Limit erreicht. Warte 60 Sekunden...")
            sleep(60)
            return get_daily_average(coin_id, date)  # Wiederholen
        else:
            print(f"Fehler: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Fehler beim Abrufen von {date} für {coin_id}: {e}")
    return None
# Funktion zur Überwachung der API-Anfragen
def limit_api_requests(request_count, last_request_time):
    current_time = time.time()
    # Prüfen, ob 60 Sekunden seit der letzten Anfrage vergangen sind
    if current_time - last_request_time >= 60:
        request_count = 0  # Zähler zurücksetzen, wenn 60 Sekunden vergangen sind
        last_request_time = current_time  # Zeitstempel zurücksetzen
    if request_count >= 50:
        # Wenn 50 Abfragen gemacht wurden, 60 Sekunden warten
        print("API-Limit erreicht. Warte 60 Sekunden...")
        sleep(60)
        request_count = 0  # Zähler zurücksetzen, nachdem gewartet wurde
        last_request_time = time.time()  # Zeitstempel zurücksetzen
    return request_count + 1, last_request_time  # Zähler erhöhen und Zeit beibehalten
# Hauptverarbeitung
for coin in coins:
    coin_id = coin["coin_id"]
    symbol = coin["symbol"]
    start_date = datetime.strptime(coin["date"].split(" ")[0], "%Y-%m-%d")
    end_date = datetime(2024, 11, 29)  # Fester Endzeitpunkt
    # Tägliche Daten abrufen
    daily_data = []
    current_date = start_date
    request_count = 0
    last_request_time = time.time()  # Initialer Zeitstempel
    while current_date <= end_date:
        # Überprüfe das API-Limit und warte gegebenenfalls
        request_count, last_request_time = limit_api_requests(request_count, last_request_time)
        avg_price = get_daily_average(coin_id, current_date)
        if avg_price is not None:
            daily_data.append({"date": current_date.date(), "price": avg_price})
            print(f"{current_date.date()} - {avg_price} USD")  # Debug-Ausgabe
        else:
            print(f"{current_date.date()} - Keine Daten verfügbar.")
        current_date += timedelta(days=1)
    # Preisdifferenz berechnen
    if daily_data:
        first_price = daily_data[0]["price"]
        last_price = daily_data[-1]["price"]
        percent_change = ((last_price - first_price) / first_price) * 100
        # CSV-Datei speichern
        file_name = f"{symbol}-{percent_change:.2f}%.csv"
        file_path = os.path.join(output_folder, file_name)
        with open(file_path, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Date", "Currency", "Daily Average (USD)"])
            for row in daily_data:
                writer.writerow([row["date"], symbol, row["price"]])
        # Daten in BigQuery hochladen
        table_id = f"{BQ_PROJECT_ID}.{BQ_DATASET}.{symbol}"
        job_config = bigquery.LoadJobConfig(
            schema=[
                bigquery.SchemaField("Date", "DATE"),
                bigquery.SchemaField("Currency", "STRING"),
                bigquery.SchemaField("Daily_Average_USD", "FLOAT"),
            ],
            write_disposition="WRITE_TRUNCATE",  # Überschreibt bestehende Daten
            skip_leading_rows=1,  # Überspringt die Header-Zeile
            source_format=bigquery.SourceFormat.CSV,
        )
        with open(file_path, "rb") as source_file:
            job = bq_client.load_table_from_file(source_file, table_id, job_config=job_config)
        job.result()  # Warten auf den Abschluss des Uploads
        print(f"{symbol}: Daten gespeichert in {file_path} und in BigQuery hochgeladen.")