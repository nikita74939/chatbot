import numpy as np
import pandas as pd
import joblib

class MiningValueCalculator:
    """
    Pipeline perhitungan Mining Value Optimizer.
    Membungkus seluruh fungsi dari notebook ke dalam satu modul Python.
    """

    def __init__(self, df_path=None, df_data=None, model_path="mining_simulation_rf.pkl"):
        """
        df_path   : path ke file CSV (opsional)
        df_data   : DataFrame sudah ter-load (opsional)
        model_path: path ke model RF
        """

        # Load dataframe
        if df_data is not None:
            self.df = df_data.copy()
        elif df_path is not None:
            self.df = pd.read_csv(df_path)
        else:
            raise ValueError("Harus menyediakan df_path atau df_data untuk MiningValueCalculator.")

        # Preprocess
        self._prepare_dataframe()

        # Load trained model
        self.model = joblib.load(model_path)

        # Fitur yang dipakai model
        self.features = [
            'shipments',
            'unique_vessels',
            'avg_WSI',
            'pct_extreme_weather',
            'avg_load_ratio',
            'avg_actual_speed',
            'avg_base_speed',
            'avg_duration',
            'avg_rainfall',
            'avg_wind',
            'avg_wave'
        ]

    # ------------------------------------------------------------------------
    # 🧠 PREPROCESS DATAFRAME
    # ------------------------------------------------------------------------
    def _prepare_dataframe(self):
        df = self.df

        df['departure_date'] = pd.to_datetime(df['departure_date'])
        df['week_start'] = df['departure_date'].dt.to_period('W').apply(lambda r: r.start_time)
        df['is_extreme'] = df['weather_status'].str.lower().eq('ekstrem')

        self.df = df

    # ------------------------------------------------------------------------
    # 🧠 FUNGSI PEMBUAT FITUR MINGGUAN
    # ------------------------------------------------------------------------
    def make_week_features(self, week_start):
        df_source = self.df
        ws = pd.to_datetime(week_start)

        # Ambil window 4 minggu sebelumnya
        past_window = df_source[
            (df_source['departure_date'] < ws) &
            (df_source['departure_date'] >= ws - pd.Timedelta(weeks=4))
        ]

        feats = {
            'shipments': past_window.shape[0],
            'unique_vessels': past_window['vessel_name'].nunique(),
            'avg_WSI': past_window['WSI'].mean() if len(past_window) > 0 else 0.0,
            'pct_extreme_weather': past_window['weather_status'].str.lower().eq('ekstrem').mean() if len(past_window) > 0 else 0.0,
            'avg_load_ratio': past_window['load_ratio'].mean() if len(past_window) > 0 else 0.0,
            'avg_actual_speed': past_window['actual_speed'].mean() if len(past_window) > 0 else 0.0,
            'avg_base_speed': past_window['base_speed'].mean() if len(past_window) > 0 else 0.0,
            'avg_duration': past_window['duration'].mean() if len(past_window) > 0 else 0.0,
            'avg_rainfall': past_window['rainfall_mm'].mean() if len(past_window) > 0 else 0.0,
            'avg_wind': past_window['wind_speed_kmh'].mean() if len(past_window) > 0 else 0.0,
            'avg_wave': past_window['wave_height_m'].mean() if len(past_window) > 0 else 0.0
        }

        # Normalize NaN
        for k, v in feats.items():
            if pd.isna(v):
                feats[k] = 0.0

        return feats

    # ------------------------------------------------------------------------
    # 🔥 PIPELINE UTAMA
    # ------------------------------------------------------------------------
    def calculate_optimal_value(self, target_ton, week_start):
        """
        Jalankan simulasi produksi mingguan.
        
        Input:
            target_ton  : target produksi (float)
            week_start  : tanggal mulai minggu (string / datetime)
        """

        feats = self.make_week_features(week_start)

        # Model inference
        X_input = np.array([feats[f] for f in self.features]).reshape(1, -1)
        predicted = float(self.model.predict(X_input)[0])

        # Hitung persentase pencapaian
        achievement_pct = predicted / (target_ton + 1e-9) * 100.0

        # RULE ENGINE
        recs = []

        if feats['pct_extreme_weather'] > 0.3:
            recs.append("Forecast: cuaca ekstrem cukup tinggi → mitigasi operasional diperlukan.")

        if feats['avg_load_ratio'] > 1.15:
            recs.append("Load ratio tinggi → risiko over-utilization armada.")

        if feats['avg_actual_speed'] < 0.7 * feats['avg_base_speed'] and feats['avg_base_speed'] > 0:
            recs.append("Kecepatan aktual jauh di bawah normal → cek rute/maintenance.")

        if achievement_pct < 85:
            recs.append(f"Prediksi pencapaian {achievement_pct:.1f}% → target berisiko tidak tercapai.")
        else:
            recs.append(f"Pencapaian diperkirakan {achievement_pct:.1f}% → target realistis.")

        # Return lengkap
        return {
            "predicted_production_ton": predicted,
            "achievement_percent": achievement_pct,
            "recommendations": recs,
            "input_features": feats
        }
