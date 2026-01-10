import pandas as pd
import numpy as np
import xgboost as xgb
import sys
import os
from datetime import timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from src.database.db_manager import DatabaseManager

class PricePredictor:
    def __init__(self):
        self.db = DatabaseManager()
        self.model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100, learning_rate=0.05, max_depth=4)
        self.forecast_days = 7

    def _process_prediction(self, df):
        if len(df) < 15: return None
        
        # Prepare data
        df = df.copy()
        df['day_of_year'] = df['scraped_at'].dt.dayofyear
        df['price_lag_1'] = df['price'].shift(1)
        df['price_lag_7'] = df['price'].shift(7)
        df['target_future_price'] = df['price'].shift(-self.forecast_days)
        
        train_df = df.dropna()
        if train_df.empty: return None

        # Train model
        features = ['day_of_year', 'price', 'price_lag_1', 'price_lag_7']
        X = train_df[features]
        y = train_df['target_future_price']
        self.model.fit(X, y)

        # Predict prices
        last_row = df.iloc[-1]
        price_last_week = df.iloc[-8]['price'] if len(df) >= 8 else last_row['price']
        
        current_features = pd.DataFrame([{
            'day_of_year': last_row['scraped_at'].dayofyear,
            'price': last_row['price'],
            'price_lag_1': df.iloc[-2]['price'],
            'price_lag_7': price_last_week
        }])
        
        predicted_price = self.model.predict(current_features)[0]
        current_price = float(last_row['price'])
        change_percent = ((predicted_price - current_price) / current_price) * 100
        
        return {
            "current_price": current_price,
            "predicted_price_7_days": round(predicted_price, 2),
            "percent_change": round(change_percent, 2),
            "recommendation": self._get_procurement_advice(change_percent)
        }

    def predict_single(self, product_id):
        conn = self.db.get_connection()
        try:
            query = "SELECT scraped_at, price FROM market_data WHERE product_id = %s ORDER BY scraped_at ASC"
            df = pd.read_sql(query, conn, params=(product_id,))
            df['scraped_at'] = pd.to_datetime(df['scraped_at'])
            return self._process_prediction(df)
        finally:
            conn.close()

    #predicts average price
    def predict_group(self, product_ids):
        if not product_ids: return None
        conn = self.db.get_connection()
        try:
            #Get average price of the GROUP per day
            format_strings = ','.join(['%s'] * len(product_ids))
            query = f"""
                SELECT DATE(scraped_at) as scraped_at, AVG(price) as price 
                FROM market_data 
                WHERE product_id IN ({format_strings}) 
                GROUP BY DATE(scraped_at) 
                ORDER BY scraped_at ASC
            """
            df = pd.read_sql(query, conn, params=tuple(product_ids))
            df['scraped_at'] = pd.to_datetime(df['scraped_at'])
            return self._process_prediction(df)
        finally:
            conn.close()

    def _get_procurement_advice(self, percent):
        if percent < -5.0: return "📉 WAIT (Significant Drop)"
        if percent < -1.0: return "↘️ CAUTION (Slight Downtrend)"
        if percent > 2.0:  return "📈 BUY NOW (Price Rising)"
        return "⚖️ SAFE (Stable Market)"