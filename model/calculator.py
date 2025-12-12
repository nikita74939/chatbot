import pandas as pd
import numpy as np
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

class MiningValueCalculator:
    def __init__(self, df_path: str = None, df: pd.DataFrame = None, model_path: str = None):
        """
        Inisialisasi kalkulator dengan data mining dan model RF.
        - df_path: Path ke CSV data mining.
        - df: DataFrame langsung (prioritas jika diberikan).
        - model_path: Path ke model RF (misalnya, 'mining_simulation_rf.pkl').
        """
        if df is not None:
            self.df = df
        elif df_path:
            self.df = pd.read_csv(df_path)
        else:
            raise ValueError("Harus berikan df_path atau df.")
        
        # Load model RF untuk mining
        if model_path:
            with open(model_path, 'rb') as f:
                self.model = pickle.load(f)
        else:
            self.model = None  # Jika tidak ada model, gunakan rule-based saja
        
        # Fitur untuk mining (sesuaikan berdasarkan data Anda)
        self.features = [
            'distance', 'capacity_ton', 'rainfall_mm', 'wind_speed_kmh', 
            'wave_height_m', 'temperature_c', 'humidity_percent', 'wsi', 
            'load_ratio', 'base_speed', 'weather_factor', 'actual_speed', 
            'duration', 'is_extreme'
        ]
    
    # HELPER FUNCTIONS
    # ==========================
    def calculate_risk_level(self, wave_height_m: float, wind_speed_kmh: float) -> str:
        """Menghitung risk level berdasarkan cuaca."""
        if wave_height_m > 2 or wind_speed_kmh > 30:
            return "High"
        elif wave_height_m > 1 or wind_speed_kmh > 20:
            return "Medium"
        else:
            return "Low"
    
    def get_speed_status(self, actual_speed: float, base_speed: float) -> str:
        """Menentukan status kecepatan kapal."""
        if base_speed == 0:
            return "Normal"
        ratio = actual_speed / base_speed
        if ratio < 0.8:
            return "Slow"
        elif ratio > 1.2:
            return "Fast"
        else:
            return "Normal"
    
    def calculate_delay_hours(self, arrival_estimate: Optional[datetime], arrival_estimate_new: Optional[datetime]) -> float:
        """Menghitung delay dalam jam."""
        if arrival_estimate is None or arrival_estimate_new is None:
            return 0.0
        delay = (arrival_estimate_new - arrival_estimate).total_seconds() / 3600
        return max(0.0, delay)
    
    # SIMULASI SHIPPING
    # ==========================
    def run_shipping_simulation(self, row: pd.Series) -> Dict[str, Any]:
        """
        Jalankan simulasi shipping berdasarkan satu row data.
        Mengembalikan dict dengan bagian_1 (data), bagian_2 (status & rekomendasi).
        """
        recs, justifications = [], []
        
        risk = self.calculate_risk_level(row["wave_height_m"], row["wind_speed_kmh"])
        speed_status = self.get_speed_status(row["actual_speed"], row["base_speed"])
        delay_hours = self.calculate_delay_hours(
            row.get("arrival_estimate"), 
            row.get("arrival_estimate_new")
        )
        
        # Rekomendasi risk
        if risk == "High":
            recs.append("Cuaca berat → gelombang & angin tinggi, jadwal kapal berpotensi terganggu.")
            justifications.append("Risk level High (gelombang >2 m, angin >30 km/h).")
        elif risk == "Medium":
            recs.append("Cuaca cukup berpengaruh → pertimbangkan buffer waktu keberangkatan.")
            justifications.append("Risk level Medium (gelombang >1 m).")
        else:
            recs.append("Cuaca aman → operasional normal.")
            justifications.append("Risk level Low (gelombang & angin normal).")
        
        # Rekomendasi speed
        if speed_status == "Slow":
            recs.append("Kecepatan kapal rendah → evaluasi rute/maintenance.")
            justifications.append("Aktual speed < 80% baseline.")
        elif speed_status == "Fast":
            recs.append("Kecepatan kapal tinggi → percepatan jadwal kedatangan.")
            justifications.append("Aktual speed > 120% baseline.")
        else:
            recs.append("Kecepatan kapal normal → estimasi kedatangan sesuai standar.")
            justifications.append("Aktual speed dalam kisaran normal (80–120%).")
        
        # Rekomendasi delay
        if delay_hours > 2:
            recs.append(f"Perkiraan delay {delay_hours:.1f} jam → siapkan notifikasi pelabuhan.")
            justifications.append("Selisih signifikan antara estimated arrival awal dan baru.")
        elif delay_hours > 0:
            recs.append(f"Perkiraan delay ringan {delay_hours:.1f} jam → tetap dipantau.")
            justifications.append("Delay minor terdeteksi.")
        else:
            recs.append("Tidak ada delay → jadwal tetap on time.")
            justifications.append("Arrival estimate tidak berubah.")
        
        status_operasional = "Delay" if delay_hours > 0 else "On track"
        
        return {
            "bagian_1": {
                "wave_height_m": row["wave_height_m"],
                "wind_speed_kmh": row["wind_speed_kmh"],
                "load_ratio": row["load_ratio"],
                "actual_speed": row["actual_speed"],
                "duration": row["duration"],
                "load_status": row.get("load_status", "Normal"),
                "risk_level": risk,
                "est_delay": delay_hours,
                "speed_status": speed_status
            },
            "bagian_2": {
                "status_operasional": status_operasional,
                "est_delay": delay_hours,
                "rekomendasi": recs,
                "justifikasi": " ".join(justifications)
            }
        }
    
    def run_all_shipping_simulations(self, shipping_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Jalankan simulasi shipping untuk semua row di shipping_df.
        Mengembalikan list hasil simulasi.
        """
        return [self.run_shipping_simulation(row) for idx, row in shipping_df.iterrows()]
    
    # SIMULASI MINING
    # ==========================
    def make_week_features(self, week_start: datetime, df_source: pd.DataFrame = None) -> Dict[str, float]:
        """
        Buat fitur mingguan berdasarkan data historis 4 minggu sebelum week_start.
        """
        if df_source is None:
            df_source = self.df
        
        ws = pd.to_datetime(week_start)
        past_window = df_source[
            (df_source['departure_date'] < ws) &
            (df_source['departure_date'] >= ws - pd.Timedelta(weeks=4))
        ]
        
        feats = {
            'distance': past_window['distance'].mean() if len(past_window) > 0 else 0.0,
            'capacity_ton': past_window['capacity_ton'].mean() if len(past_window) > 0 else 0.0,
            'rainfall_mm': past_window['rainfall_mm'].mean() if len(past_window) > 0 else 0.0,
            'wind_speed_kmh': past_window['wind_speed_kmh'].mean() if len(past_window) > 0 else 0.0,
            'wave_height_m': past_window['wave_height_m'].mean() if len(past_window) > 0 else 0.0,
            'temperature_c': past_window['temperature_c'].mean() if len(past_window) > 0 else 0.0,
            'humidity_percent': past_window['humidity_percent'].mean() if len(past_window) > 0 else 0.0,
            'wsi': past_window['wsi'].mean() if len(past_window) > 0 else 0.0,
            'load_ratio': past_window['load_ratio'].mean() if len(past_window) > 0 else 0.0,
            'base_speed': past_window['base_speed'].mean() if len(past_window) > 0 else 0.0,
            'weather_factor': (
                (past_window['rainfall_mm'].mean() if len(past_window) > 0 else 0.0) * 0.2 +
                (past_window['wind_speed_kmh'].mean() if len(past_window) > 0 else 0.0) * 0.4 +
                (past_window['wave_height_m'].mean() if len(past_window) > 0 else 0.0) * 0.4
            ),
            'actual_speed': past_window['actual_speed'].mean() if len(past_window) > 0 else 0.0,
            'duration': past_window['duration'].mean() if len(past_window) > 0 else 0.0,
            'is_extreme': past_window['is_extreme'].mean() if len(past_window) > 0 else 0.0
        }
        
        # Pastikan semua NaN jadi 0
        for k, v in feats.items():
            if pd.isna(v):
                feats[k] = 0.0
        
        return feats
    
    def run_mining_simulation(self, target_ton: float, week_start: datetime) -> Dict[str, Any]:
        """
        Jalankan simulasi mining dengan RF model + rules.
        Mengembalikan dict dengan prediksi, rekomendasi, dll.
        """
        feats = self.make_week_features(week_start)
        
        # Prediksi menggunakan RF model jika ada
        if self.model:
            X_input = np.array([feats[f] for f in self.features]).reshape(1, -1)
            predicted = float(self.model.predict(X_input)[0])
        else:
            # Fallback: estimasi sederhana berdasarkan kapasitas
            predicted = feats['capacity_ton'] * 0.8  # Placeholder
        
        achievement_pct = predicted / (target_ton + 1e-9) * 100.0
        
        recs = []
        justifications = []
        
        # RULE CUACA (weather_factor)
        if feats['weather_factor'] > 70:
            recs.append("Cuaca sangat berat (angin/gelombang/hujan tinggi) → risiko operasional meningkat, siapkan mitigasi.")
            justifications.append("Weather factor tinggi sehingga berpotensi menghambat operasi.")
        elif feats['weather_factor'] > 40:
            recs.append("Cuaca cukup berpengaruh minggu ini → potensi keterlambatan 5–10%.")
            justifications.append("Kondisi cuaca cukup menekan performa logistik.")
        else:
            recs.append("Kondisi cuaca relatif aman untuk operasi minggu ini.")
            justifications.append("Cuaca mendukung sehingga operasi dapat berjalan optimal.")
        
        # RULE KELAIKAN ARMADA (fleet_health_index)
        if feats['base_speed'] > 0:
            fleet_health_index = feats['actual_speed'] / feats['base_speed']
        else:
            fleet_health_index = 1.0
        
        if fleet_health_index < 0.6:
            recs.append("Kesehatan armada rendah → kecepatan kapal rata-rata drop signifikan, perlu maintenance.")
            justifications.append("Fleet health rendah yang dapat menurunkan kecepatan kapal.")
        elif fleet_health_index < 0.8:
            recs.append("Performa armada menurun → cek jadwal maintenance dan kapasitas kapal.")
            justifications.append("Fleet health menurun sehingga efisiensi kapal berkurang.")
        else:
            recs.append("Status armada sehat → performa mendukung target minggu ini.")
            justifications.append("Armada dalam kondisi optimal untuk produksi.")
        
        # RULE EXTREME WEATHER
        if feats['is_extreme'] > 0.3:
            recs.append("Cuaca ekstrem sering terjadi → evaluasi jadwal kapal dan slot bongkar.")
            justifications.append("Frekuensi cuaca ekstrem cukup tinggi.")
        
        # RULE LOAD RATIO
        if feats['load_ratio'] > 1.15:
            recs.append("Load ratio tinggi → risiko over-utilization armada.")
            justifications.append("Load ratio di atas normal sehingga risiko overload meningkat.")
        
        # TARGET ACHIEVEMENT
        if achievement_pct < 85:
            recs.append(f"Pencapaian diperkirakan {achievement_pct:.1f}% → target berisiko tidak tercapai.")
            justifications.append("Prediksi produksi di bawah 85% dari target.")
        else:
            recs.append(f"Pencapaian diperkirakan {achievement_pct:.1f}% → target realistis.")
            justifications.append("Prediksi produksi memenuhi atau melampaui target minggu ini.")
        
        full_justification = " ".join(justifications)
        
        simulation_context = {
            "features": feats,
            "predicted_weekly_production": predicted,
            "achievement_pct": achievement_pct,
            "justification": full_justification
        }
        
        return {
            "predicted_production_ton": predicted,
            "achievement_percent": achievement_pct,
            "recommendations": recs,
            "justification": full_justification,
            "simulation_context": simulation_context
        }
    
    # METHOD UTAMA UNTUK KOMPATIBILITAS DENGAN CHATROUTER
    def calculate_optimal_value(self, target_ton: float, week_start: datetime) -> Dict[str, Any]:
        """
        Method utama untuk kalkulasi mining (dipanggil dari ChatRouter).
        """
        return self.run_mining_simulation(target_ton, week_start)
    
    # TAMBAHAN: METHOD UNTUK SHIPPING (JIKA DIPERLUKAN OLEH CHATROUTER)
    def calculate_shipping_delay(self, input_features: Dict[str, float]) -> Dict[str, Any]:
        """
        Prediksi delay untuk shipping berdasarkan input features.
        Menggunakan rule-based (bisa dikembangkan dengan model RF jika ada).
        """
        # Placeholder: gunakan run_shipping_simulation dengan row dummy
        row = pd.Series(input_features)
        return self.run_shipping_simulation(row)