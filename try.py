import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import pickle
import os

# Load data mining (ganti dengan data Anda)
df = pd.read_csv('Mining_Clean3.csv')  # Atau dari DB
features = ['distance', 'capacity_ton', 'rainfall_mm', 'wind_speed_kmh', 'wave_height_m', 'temperature_c', 'humidity_percent', 'wsi', 'load_ratio', 'base_speed', 'weather_factor', 'actual_speed', 'duration', 'is_extreme']
X = df[features]
y = df['cargo_volume_ton']  # Ganti target sesuai (misal predicted_production)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
model = RandomForestRegressor()
model.fit(X_train, y_train)

# Simpan model
os.makedirs('models', exist_ok=True)
with open('models/mining_simulation_rf.pkl', 'wb') as f:
    pickle.dump(model, f)

# Untuk shipping: Ganti y dengan delay_hours, features sesuai
# shipping_df["delay_hours"] = ... (sesuai kode Anda)
# X_ship = shipping_df[features]
# y_ship = shipping_df["delay_hours"]
# model_ship = RandomForestRegressor()
# model_ship.fit(X_ship, y_ship)
# with open('models/shipping_simulation_rf.pkl', 'wb') as f:
#     pickle.dump(model_ship, f)