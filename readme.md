# README — Integrasi Febe Web App dengan Backend AI (Python)


## 1. 📦 **Persiapan Backend Python (AI Engine)**

Pastikan Anda sudah menginstall semua package yang dibutuhkan.

### **Install dependencies**

```
pip install -r requirements.txt
```

### **Menjalankan Backend Python**

Backend menggunakan FastAPI atau Flask (menyesuaikan project). Jalankan dengan Uvicorn bila FastAPI:

```
uvicorn app:app --reload --port 8000 
```

Backend akan berjalan di:

```
http://localhost:8000
```

---

## 2. 📡 **Endpoint Chat AI (Python)**

Backend menyediakan endpoint:

```
POST /chat
```

### **Contoh body request**

```json
{
  "message": "kalau hujan gini, produksi kita bakal kehambat ga"
}
```

### **Contoh response** (dipotong)

```json
{
  "type": "simulation",
  "result": {
    "predicted_production_ton": 2441703.7641737084,
    "achievement_percent": 24417.03764173464,
    "recommendations": ["..."]
  },
  "answer": "Tentu, Pak/Bu. Saya bantu cek prediksi produksi ..."
}
```

---

## 3. 🟦 **Setup Febe Web App (Express.js)**

Install dependensi Express frontend:

```
npm install express axios cors
```

Buat folder route:

```
routes/chat.js
```

### **Isi file: routes/chat.js**

```js
const express = require("express");
const router = express.Router();
const axios = require("axios");

const PYTHON_URL = "http://localhost:8000/chat"; // Endpoint FastAPI

router.post("/", async (req, res) => {
  try {
    const { message } = req.body;

    const response = await axios.post(PYTHON_URL, { message });

    return res.json(response.data);
  } catch (error) {
    console.error("Error connecting to Python:", error.message);
    return res.status(500).json({ error: "Failed to connect to AI backend" });
  }
});

module.exports = router;
```

---

## 4. 🚀 **Integrasi Route ke Express.js Utama**

Tambahkan ke file utama (misal `app.js` atau `index.js`).

```js
const express = require("express");
const cors = require("cors");

const app = express();
app.use(cors());
app.use(express.json());

// Import chat route
const chatRoute = require("./routes/chat");
app.use("/chat", chatRoute);

app.listen(3001, () => console.log("Febe server running on port 3001"));
```

Frontend akan memanggil:

```
POST http://localhost:3001/chat
```

---

## 5. 🖥️ **Contoh Pemanggilan dari Frontend (React / Vue / NextJS)**

```js
async function sendMessage(message) {
  const res = await fetch("http://localhost:3001/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message })
  });

  const data = await res.json();
  return data;
}
```

Pemakaian:

```js
sendMessage("kalau hujan gini, produksi kita bakal kehambat ga").then(console.log);
```

---

## 6. 🧪 **Testing Integrasi**

1. Jalankan backend Python: `uvicorn app:app --port 8000`
2. Jalankan Express: `node app.js`
3. Kirim POST request via Postman:

```
POST http://localhost:3001/chat
{
  "message": "tes hujan"
}
```

4. Pastikan response AI keluar.

---

## 7. ⚠️ Kendala yang Mungkin Muncul

### **❌ Error CORS**

Tambahkan `app.use(cors())` di Express.

### **❌ Python tidak merespons**

Pastikan backend running:

```
curl http://localhost:8000/chat
```

### **❌ Axios error ECONNREFUSED**

* Port salah
* Backend mati
* Firewall memblok koneksi

---

## 8. 🎯 Hasil Akhir

* Mengirim pesan dari frontend ke Express
* Express meneruskan ke Python backend
* Python menjalankan model simulasi (ML)
* Hasil berupa JSON + jawaban natural language
* Frontend dapat menampilkan output di chat UI
