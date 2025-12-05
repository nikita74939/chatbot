# rules.py

def apply_general_rules(features):
    """
    Rules tambahan yang bersifat knowledge-base.
    """

    recs = []

    if features['avg_wind'] > 45:
        recs.append("Kecepatan angin tinggi → potensi gangguan stabilitas kapal.")

    if features['avg_wave'] > 3:
        recs.append("Tinggi gelombang di atas 3 meter → aktivitas bongkar muat berisiko.")

    if features['avg_rainfall'] > 80:
        recs.append("Curah hujan sangat tinggi → potensi delay operasional.")

    if features['shipments'] < 3:
        recs.append("Jumlah shipment rendah → periksa distribusi dan jadwal kapal.")

    return recs
