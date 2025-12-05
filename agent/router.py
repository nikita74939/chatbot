from agent.llm import ask_gemini
from model.calculator import MiningValueCalculator
from model.rules import apply_general_rules
import datetime
import json

class ChatRouter:

    def __init__(self, df_path, model_path):
        self.calculator = MiningValueCalculator(df_path=df_path, model_path=model_path)

    def is_simulation_request(self, message: str) -> bool:
        """
        Deteksi apakah user ingin menjalankan simulasi ML.
        Contoh trigger:
        - "simulasi"
        - "prediksi"
        - "minggu depan"
        - "target"
        """
        keywords = ["simulasi", "prediksi", "produksi", "minggu", "target", "kapasitas"]
        return any(k in message.lower() for k in keywords)

    def is_weather_related(self, message: str) -> bool:
        """
        Deteksi apakah pertanyaan berkaitan dengan cuaca (misalnya hujan).
        """
        weather_keywords = ["hujan", "cuaca", "rain", "weather", "besok", "hari ini"]
        return any(k in message.lower() for k in weather_keywords)

    def is_production_target_related(self, message: str) -> bool:
        """
        Deteksi apakah pertanyaan berkaitan dengan target produksi.
        """
        target_keywords = ["target", "ton", "produksi", "hasil", "output"]
        return any(k in message.lower() for k in target_keywords)

    def is_capacity_related(self, message: str) -> bool:
        """
        Deteksi apakah pertanyaan berkaitan dengan kapasitas unit.
        """
        capacity_keywords = ["kapasitas", "unit", "mesin", "alat"]
        return any(k in message.lower() for k in capacity_keywords)

    def is_efficiency_related(self, message: str) -> bool:
        """
        Deteksi apakah pertanyaan berkaitan dengan efisiensi.
        """
        efficiency_keywords = ["efisiensi", "persentase", "rate", "tingkat"]
        return any(k in message.lower() for k in efficiency_keywords)

    def is_weekly_prediction_related(self, message: str) -> bool:
        """
        Deteksi apakah pertanyaan berkaitan dengan prediksi mingguan.
        """
        weekly_keywords = ["minggu", "weekly", "minggu depan", "prediksi minggu"]
        return any(k in message.lower() for k in weekly_keywords)

    def parse_simulation_input(self, message: str):
        """
        Ekstraksi target ton dan week_start dari pertanyaan user.
        Format bebas, tapi minimal:
        - angka → target ton
        - tanggal → week_start
        """

        import re

        # Ambil angka → target ton
        ton_match = re.findall(r"\d+", message)
        target_ton = float(ton_match[0]) if ton_match else 10000.0

        # Cari tanggal (YYYY-MM-DD)
        date_match = re.findall(r"\d{4}-\d{2}-\d{2}", message)
        if date_match:
            week_start = datetime.datetime.strptime(date_match[0], "%Y-%m-%d")
        else:
            week_start = datetime.datetime.today()

        return target_ton, week_start

    def format_simulation_for_llm(self, sim_result: dict, user_msg: str) -> str:
        """
        Format hasil simulasi menjadi prompt untuk Gemini agar menghasilkan
        jawaban yang natural seperti manusia. Prompt dibuat lebih rinci dan bisa dipisah-pisah
        berdasarkan jenis pertanyaan (cuaca, target produksi, kapasitas, efisiensi, prediksi mingguan, dll.).
        """
        
        # Ambil data dengan safe get
        input_feat = sim_result.get("input_features", {})
        predictions = sim_result.get("predictions", {})
        recommendations = sim_result.get("recommendations", [])
        
        # Jika struktur berbeda, coba ambil dari key lain
        if not predictions and "prediction" in sim_result:
            predictions = sim_result["prediction"]
        
        # Ekstrak nilai-nilai dengan aman
        target_ton = input_feat.get('target_ton', 'N/A')
        week_start = input_feat.get('week_start', 'N/A')
        unit_capacity = input_feat.get('unit_capacity', 'N/A')
        num_units = input_feat.get('num_units', 'N/A')
        operating_hours = input_feat.get('operating_hours', 'N/A')
        efficiency = input_feat.get('efficiency', 'N/A')
        
        # Ambil prediksi
        if isinstance(predictions, dict):
            predicted_production = predictions.get('predicted_production', predictions.get('production', 'N/A'))
            success_rate = predictions.get('success_rate', predictions.get('rate', 'N/A'))
            status = predictions.get('status', 'N/A')
        else:
            predicted_production = predictions if predictions else 'N/A'
            success_rate = 'N/A'
            status = 'N/A'
        
        # Format rekomendasi
        rec_text = "\n".join(f"- {rec}" for rec in recommendations) if recommendations else "Tidak ada rekomendasi khusus"
        
        # Deteksi jenis pertanyaan untuk menyesuaikan prompt
        is_weather = self.is_weather_related(user_msg)
        is_target = self.is_production_target_related(user_msg)
        is_capacity = self.is_capacity_related(user_msg)
        is_efficiency = self.is_efficiency_related(user_msg)
        is_weekly = self.is_weekly_prediction_related(user_msg)
        
        # Bagian prompt dasar (bisa dipisah-pisah)
        intro_prompt = f"""
Anda adalah asisten ahli pertambangan yang ramah dan profesional. 
Berdasarkan pertanyaan user: "{user_msg}"
"""
        
        data_prompt = f"""
Berikut hasil analisis simulasi produksi:

INPUT PARAMETER:
- Target Produksi: {target_ton} ton
- Minggu Mulai: {week_start}
- Kapasitas Unit: {unit_capacity}
- Jumlah Unit: {num_units}
- Jam Operasi: {operating_hours} jam
- Efisiensi: {efficiency}%

HASIL PREDIKSI:
- Produksi yang Diprediksi: {predicted_production} ton
- Tingkat Keberhasilan: {success_rate}%
- Status: {status}

REKOMENDASI:
{rec_text}

DATA LENGKAP (untuk referensi):
{json.dumps(sim_result, indent=2, default=str)}
"""
        
        # Sesuaikan task_prompt berdasarkan jenis pertanyaan
        if is_weather:
            task_prompt = f"""
TUGAS ANDA:
Pertanyaan user berkaitan dengan cuaca (seperti hujan). Jawab hanya mengenai prediksi produksi besok yang berkaitan dengan hujan dan alasannya.
- Jelaskan apakah hujan akan menghambat produksi besok berdasarkan data simulasi.
- Berikan alasan konkret, seperti dampak pada efisiensi, jam operasi, atau rekomendasi terkait cuaca.
- Jangan jelaskan semua input parameter atau hasil simulasi secara keseluruhan; fokus hanya pada aspek cuaca dan produksi besok.
- Gunakan bahasa natural, mudah dipahami, dan profesional, seperti sedang berbicara langsung dengan user.
- Berikan insight yang berguna dan saran actionable terkait cuaca.
"""
        elif is_target:
            task_prompt = f"""
TUGAS ANDA:
Pertanyaan user berkaitan dengan target produksi. Jawab hanya mengenai pencapaian target produksi dan alasannya.
- Jelaskan apakah target produksi dapat dicapai berdasarkan prediksi, termasuk produksi yang diprediksi dan tingkat keberhasilan.
- Berikan alasan konkret, seperti kapasitas unit, jam operasi, atau rekomendasi terkait target.
- Jangan jelaskan semua input parameter atau hasil simulasi secara keseluruhan; fokus hanya pada aspek target produksi.
- Gunakan bahasa natural, mudah dipahami, dan profesional, seperti sedang berbicara langsung dengan user.
- Berikan insight yang berguna dan saran actionable terkait target produksi.
"""
        elif is_capacity:
            task_prompt = f"""
TUGAS ANDA:
Pertanyaan user berkaitan dengan kapasitas unit. Jawab hanya mengenai kapasitas unit dan dampaknya pada produksi.
- Jelaskan bagaimana kapasitas unit mempengaruhi produksi, termasuk jumlah unit dan jam operasi.
- Berikan alasan konkret berdasarkan data simulasi, seperti produksi yang diprediksi.
- Jangan jelaskan semua input parameter atau hasil simulasi secara keseluruhan; fokus hanya pada aspek kapasitas.
- Gunakan bahasa natural, mudah dipahami, dan profesional, seperti sedang berbicara langsung dengan user.
- Berikan insight yang berguna dan saran actionable terkait kapasitas unit.
"""
        elif is_efficiency:
            task_prompt = f"""
TUGAS ANDA:
Pertanyaan user berkaitan dengan efisiensi. Jawab hanya mengenai tingkat efisiensi dan dampaknya pada produksi.
- Jelaskan bagaimana efisiensi mempengaruhi produksi, termasuk persentase efisiensi dan tingkat keberhasilan.
- Berikan alasan konkret berdasarkan data simulasi, seperti rekomendasi terkait efisiensi.
- Jangan jelaskan semua input parameter atau hasil simulasi secara keseluruhan; fokus hanya pada aspek efisiensi.
- Gunakan bahasa natural, mudah dipahami, dan profesional, seperti sedang berbicara langsung dengan user.
- Berikan insight yang berguna dan saran actionable terkait efisiensi.
"""
        elif is_weekly:
            task_prompt = f"""
TUGAS ANDA:
Pertanyaan user berkaitan dengan prediksi mingguan. Jawab hanya mengenai prediksi produksi untuk minggu tersebut dan alasannya.
- Jelaskan produksi yang diprediksi untuk minggu mulai, termasuk status dan rekomendasi.
- Berikan alasan konkret, seperti target ton, kapasitas, atau jam operasi.
- Jangan jelaskan semua input parameter atau hasil simulasi secara keseluruhan; fokus hanya pada aspek prediksi mingguan.
- Gunakan bahasa natural, mudah dipahami, dan profesional, seperti sedang berbicara langsung dengan user.
- Berikan insight yang berguna dan saran actionable terkait prediksi mingguan.
"""
        else:
            # Prompt umum untuk simulasi lainnya
            task_prompt = f"""
TUGAS ANDA:
Jelaskan hasil simulasi ini dengan bahasa yang natural, mudah dipahami, dan profesional.
Berikan insight yang berguna dan saran yang actionable.
Jangan gunakan format bullet point atau terlalu formal.
Buatlah seperti Anda sedang berbicara langsung dengan user.
Gunakan angka-angka dari data di atas untuk memberikan penjelasan yang konkret.
Berikan penjelasan yang to the point mengenai apa yang ditanyakan oleh user, jangan terlalu banyak membahas diluar yang ditanyakan user.
"""
        
        # Gabungkan prompt (bisa dipisah-pisah jika diperlukan)
        full_prompt = intro_prompt + data_prompt + task_prompt
        
        return full_prompt

    def handle_message(self, user_msg: str):
        """
        Router utama untuk chatbox.
        """

        # 1. Cek apakah user minta simulasi
        if self.is_simulation_request(user_msg):
            try:
                target_ton, week_start = self.parse_simulation_input(user_msg)

                sim = self.calculator.calculate_optimal_value(
                    target_ton=target_ton,
                    week_start=week_start
                )

                # Tambahkan rules tambahan
                extra_rules = apply_general_rules(sim["input_features"])
                
                # Pastikan recommendations adalah list
                if "recommendations" not in sim:
                    sim["recommendations"] = []
                elif not isinstance(sim["recommendations"], list):
                    sim["recommendations"] = [sim["recommendations"]]
                    
                sim["recommendations"].extend(extra_rules)

                # PROSES HASIL SIMULASI DENGAN GEMINI
                llm_prompt = self.format_simulation_for_llm(sim, user_msg)
                natural_answer = ask_gemini(llm_prompt)

                return {
                    "type": "simulation",
                    "result": sim,  # Data mentah tetap disimpan
                    "answer": natural_answer  # Jawaban natural dari Gemini
                }
            
            except Exception as e:
                # Jika ada error, fallback ke LLM biasa
                error_msg = f"Maaf, terjadi error saat simulasi: {str(e)}. Silakan coba lagi atau tanyakan hal lain."
                return {
                    "type": "error",
                    "answer": error_msg,
                    "error_details": str(e)
                }

        # 2. Jika bukan simulasi → lempar ke Gemini
        else:
            answer = ask_gemini(user_msg)
            return {
                "type": "llm",
                "answer": answer
            }
