# agent/router.py (kode lengkap dan diperbaiki)
import pandas as pd
from sqlalchemy import create_engine, text
from agent.llm import ask_gemini
from model.calculator import MiningValueCalculator
from model.rules import apply_general_rules
import datetime
import json
import pickle
import os
import uuid

class ChatRouter:
    def __init__(self, df_path, model_paths):
        # Jika df_path='dummy', skip DB load untuk test
        if df_path == 'dummy':
            self.conn = None
            self.mining_calculator = MiningValueCalculator(df_path=None, model_path=None)
            self.shipping_model = None
            return
        
        # Setup DB dengan SQLAlchemy
        from config import DB_CONFIG
        db_uri = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
        self.engine = create_engine(db_uri)
        
        # Load data mining_clean2 dari DB
        if df_path is None:
            query = "SELECT * FROM mining_clean2;"
            mining_df = pd.read_sql_query(query, self.engine)
        else:
            mining_df = pd.read_csv(df_path)
        
        # Setup model paths
        if model_paths is None:
            self.model_paths = None
            self.mining_calculator = MiningValueCalculator(df=mining_df, model_path=None)
            self.shipping_model = None
        else:
            self.model_paths = model_paths
            # Load mining model
            mining_model_path = self.model_paths.get('mining')
            self.mining_calculator = MiningValueCalculator(df=mining_df, model_path=mining_model_path)
            
            # Load shipping model
            shipping_model_path = self.model_paths.get('shipping')
            if shipping_model_path and os.path.exists(shipping_model_path):
                try:
                    with open(shipping_model_path, 'rb') as f:
                        self.shipping_model = pickle.load(f)
                except Exception as e:
                    print(f"Warning: Shipping model gagal load ({str(e)}). Menggunakan rule-based.")
                    self.shipping_model = None
            else:
                self.shipping_model = None
        
        # Hitung delay_hours untuk shipping jika ada data
        if 'arrival_estimate' in mining_df.columns and 'departure_date' in mining_df.columns:
            mining_df["delay_hours"] = (
                (pd.to_datetime(mining_df["arrival_estimate"]) - pd.to_datetime(mining_df["departure_date"]))
                .dt.total_seconds() / 3600
            ).clip(lower=0).fillna(0)
        
        self.shipping_features = [
            "distance", "cargo_volume_ton", "capacity_ton", "rainfall_mm", 
            "wind_speed_kmh", "wave_height_m", "temperature_c", "humidity_percent"
        ]
    
    
    def is_simulation_request(self, message: str) -> bool:
        keywords = ["simulasi", "prediksi", "produksi", "minggu", "target", "kapasitas", "delay"]
        return any(k in message.lower() for k in keywords)
    
    def is_weather_related(self, message: str) -> bool:
        weather_keywords = ["hujan", "cuaca", "rain", "weather", "besok", "hari ini"]
        return any(k in message.lower() for k in message.lower())
    
    def is_production_target_related(self, message: str) -> bool:
        target_keywords = ["target", "ton", "produksi", "hasil", "output"]
        return any(k in message.lower() for k in target_keywords)
    
    def is_capacity_related(self, message: str) -> bool:
        capacity_keywords = ["kapasitas", "unit", "mesin", "alat"]
        return any(k in message.lower() for k in capacity_keywords)
    
    def is_efficiency_related(self, message: str) -> bool:
        efficiency_keywords = ["efisiensi", "persentase", "rate", "tingkat"]
        return any(k in message.lower() for k in efficiency_keywords)
    
    def is_weekly_prediction_related(self, message: str) -> bool:
        weekly_keywords = ["minggu", "weekly", "minggu depan", "prediksi minggu"]
        return any(k in message.lower() for k in weekly_keywords)
    
    def is_shipping_related(self, message: str) -> bool:
        shipping_keywords = ["kapal", "vessel", "shipping", "delay", "arrival", "departure"]
        return any(k in message.lower() for k in shipping_keywords)
    
    def parse_simulation_input(self, message: str):
        import re
        ton_match = re.findall(r"\d+", message)
        target_ton = float(ton_match[0]) if ton_match else 10000.0
        date_match = re.findall(r"\d{4}-\d{2}-\d{2}", message)
        week_start = datetime.datetime.strptime(date_match[0], "%Y-%m-%d") if date_match else datetime.datetime.today()
        return target_ton, week_start
    
    def format_simulation_for_llm(self, sim_result: dict, user_msg: str, sim_type: str) -> str:
        input_feat = sim_result.get("input_features", {})
        predictions = sim_result.get("predictions", {})
        
        if sim_type == "shipping":
            predicted_value = sim_result.get("predicted_delay_hours", "N/A")
            data_prompt = f"HASIL PREDIKSI SHIPPING: Prediksi Delay Hours: {predicted_value} jam. INPUT: {json.dumps(input_feat, indent=2, default=str)}"
        else:
            target_ton = input_feat.get('target_ton', 'N/A')
            predicted_production = predictions.get('predicted_production', 'N/A')
            data_prompt = f"HASIL PREDIKSI MINING: Target Produksi: {target_ton} ton, Produksi Diprediksi: {predicted_production} ton. INPUT: {json.dumps(input_feat, indent=2, default=str)}"
        
        intro_prompt = f"Anda adalah asisten ahli. Pertanyaan: '{user_msg}'"
        task_prompt = "Jelaskan hasil dengan bahasa natural, fokus pada yang ditanyakan."
        return intro_prompt + data_prompt + task_prompt
    
    def get_user_info(self, user_id):
        # Cast user_id ke UUID jika perlu, atau asumsikan input sudah UUID string
        query = text("SELECT user_id, username FROM users WHERE user_id = :user_id;")
        with self.engine.connect() as conn:
            result = conn.execute(query, {"user_id": user_id}).fetchone()
        return dict(result._mapping) if result else None
    
    def get_recent_chat_history(self, user_id, hours=24):
        since_time = datetime.datetime.now() - datetime.timedelta(hours=hours)
        query = text("""
        SELECT message, answer, created_at 
        FROM chat_history 
        WHERE user_id = :user_id AND created_at >= :since_time 
        ORDER BY created_at DESC;
        """)
        with self.engine.connect() as conn:
            results = conn.execute(query, {"user_id": user_id, "since_time": since_time}).fetchall()
        return [dict(row._mapping) for row in results] if results else None

    
    def save_chat_history(self, user_id, message, answer, chat_id=None):
        if chat_id is None:
            chat_id = str(uuid.uuid4())
        query = text("""
        INSERT INTO chat_history (user_id, message, answer, chat_id) 
        VALUES (:user_id, :message, :answer, :chat_id);
        """)
        with self.engine.connect() as conn:
            conn.execute(query, {"user_id": user_id, "message": message, "answer": answer, "chat_id": chat_id})
            conn.commit()
    
    def predict_shipping_delay(self, input_data: dict) -> dict:
        if self.shipping_model is None:
            return {"predicted_delay_hours": 0.0, "input_features": input_data}
        X_input = pd.DataFrame([input_data])[self.shipping_features].fillna(pd.Series(input_data).median())
        prediction = float(self.shipping_model.predict(X_input)[0])
        return {"predicted_delay_hours": prediction, "input_features": input_data}
    
    def handle_message(self, user_msg: str, user_id: str):
        user_info = self.get_user_info(user_id)
        if not user_info:
            return {"type": "error", "answer": "User tidak ditemukan."}
        
        recent_chats = self.get_recent_chat_history(user_id)
        greeting = f"Hai {user_info['username']}! " if not recent_chats else ""
        
        if self.is_simulation_request(user_msg):
            try:
                if self.is_shipping_related(user_msg):
                    target_ton, week_start = self.parse_simulation_input(user_msg)
                    input_data = {
                        "distance": 100.0,
                        "cargo_volume_ton": target_ton,
                        "capacity_ton": 5000.0,
                        "rainfall_mm": 0.0,
                        "wind_speed_kmh": 10.0,
                        "wave_height_m": 1.0,
                        "temperature_c": 25.0,
                        "humidity_percent": 60.0
                    }
                    sim = self.predict_shipping_delay(input_data)
                    sim_type = "shipping"
                else:
                    target_ton, week_start = self.parse_simulation_input(user_msg)
                    sim = self.mining_calculator.calculate_optimal_value(target_ton=target_ton, week_start=week_start)
                    sim_type = "mining"
                
                llm_prompt = self.format_simulation_for_llm(sim, user_msg, sim_type)
                natural_answer = ask_gemini(llm_prompt)
                self.save_chat_history(user_id, user_msg, natural_answer)
                return {
                    "type": "simulation",
                    "result": sim,
                    "answer": greeting + natural_answer
                }
            
            except Exception as e:
                error_msg = f"Error simulasi: {str(e)}"
                self.save_chat_history(user_id, user_msg, error_msg)
                return {"type": "error", "answer": greeting + error_msg}
        
        else:
            if recent_chats:
                history_context = "\n".join([f"User: {c['message']}\nBot: {c['answer']}" for c in recent_chats])
                full_prompt = f"Konteks: {history_context}\nPertanyaan: {user_msg}"
                answer = ask_gemini(full_prompt)
            else:
                answer = ask_gemini(user_msg)
            self.save_chat_history(user_id, user_msg, answer)
            return {"type": "llm", "answer": greeting + answer}
    
    def close_connection(self):
        if hasattr(self, 'engine') and self.engine:
            self.engine.dispose()
