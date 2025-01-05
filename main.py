
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
from flask import Flask, render_template_string

# Flask app setup
app = Flask(__name__)

class TokenAnalyzer:
    def __init__(self, token_address: str, timeframe: str = '1h'):
        self.token_address = token_address
        self.timeframe = timeframe
        self.api_url = f"https://api.dexscreener.com/latest/dex/search/?q={self.token_address}"

    def fetch_data(self) -> Optional[List[Dict]]:
        try:
            print(f"\nRécupération des données pour {self.token_address}...")
            response = requests.get(self.api_url, timeout=10)
            data = response.json()

            if not data.get('pairs'):
                print("⚠️ Aucune paire trouvée pour l'adresse du token.")
                return None

            # Extraire la première paire
            pair = data['pairs'][0]
            current_time = datetime.now()

            # Créer un point de données
            data_point = {
                'timestamp': int(current_time.timestamp()),
                'price': float(pair.get('priceUsd', 0)),
                'volume': float(pair.get('volume24h', 0)),
                'liquidity': float(pair.get('liquidity', {}).get('usd', 0))
            }

            print(f"✅ Données récupérées : {data_point}")
            return [data_point]

        except requests.exceptions.RequestException as e:
            print(f"❌ Erreur de connexion à l'API : {str(e)}")
            return None
        except Exception as e:
            print(f"❌ Erreur inattendue : {str(e)}")
            return None

    def analyze_data(self, data: List[Dict]) -> pd.DataFrame:
        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')

        # Si seulement un point de données est disponible, générer un signal simple
        if len(df) == 1:
            df['signal'] = np.where(df['price'] < 0.05, 'ACHAT', 'VENTE')
        else:
            # Calculer des signaux basés sur le prix instantané
            df['signal'] = np.where(
                df['price'] < df['price'].shift(1), 'ACHAT',
                np.where(df['price'] > df['price'].shift(1), 'VENTE', 'ATTENTE')
            )

        return df

    def run_analysis(self) -> Optional[pd.DataFrame]:
        print("\nDémarrage de l'analyse...")
        data = self.fetch_data()

        if not data:
            print("⚠️ Aucune donnée valide trouvée. Analyse impossible.")
            return None

        df = self.analyze_data(data)

        if df.empty:
            print("⚠️ Erreur lors de l'analyse des données.")
            return None

        # Filtrer uniquement les signaux d'achat et de vente
        signals = df[df['signal'].isin(['ACHAT', 'VENTE'])].copy()

        if not signals.empty:
            print("\n✅ Signaux trouvés :")
            print(signals[['timestamp', 'price', 'signal']])
            return signals
        else:
            print("⚠️ Aucun signal détecté.")
            return None

# Route Flask pour afficher le graphique et les signaux
@app.route("/<token_address>")
def display_chart(token_address):
    analyzer = TokenAnalyzer(token_address)
    results = analyzer.run_analysis()

    if results is not None:
        signals_html = results[['timestamp', 'price', 'signal']].to_html(index=False)
    else:
        signals_html = "<p>⚠️ Aucun signal de trading détecté.</p>"

    chart_iframe = f'''
    <iframe src="https://dexscreener.com/solana/{token_address}" width="100%" height="600" frameborder="0"></iframe>
    '''

    html_content = f'''
    <html>
        <head>
            <title>Analyse du Token {token_address}</title>
        </head>
        <body>
            <h1>Analyse du Token : {token_address}</h1>
            {chart_iframe}
            <h2>Signaux de Trading :</h2>
            {signals_html}
        </body>
    </html>
    '''
    return html_content

# Lancement de l'application Flask
if __name__ == "__main__":
    app.run(debug=True)
