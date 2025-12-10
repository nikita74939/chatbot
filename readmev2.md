# ✔ Chatbox Backend 

### 🟦 **POST /api/chat**

Backend Node.js harus:

1. menerima `{ user_id, message }`
2. call python:

   ```
   POST http://localhost:8000/chat
   body: { message }
   ```
3. python balikin `{ answer }`
4. Node.js simpan ke database:

   ```sql
   INSERT INTO chat_history (user_id, message, answer)
   ```
5. Node.js balikin:

   ```json
   { "status": "success", "answer": "..." }
   ```

---

### 🟪 **GET /api/chat?user_id=...**

Backend Node.js harus:

1. ambil data dari PostgreSQL
2. urutkan berdasarkan `created_at`
3. kirim list chat ke frontend

---

# 🧩 Tugas Frontend (Ringkasan)

### ✔ 1.1 Buat state untuk chat

* daftar chat (`chatList`)
* input yang diketikan user (`inputMessage`)
* user_id 

### ✔ 1.2 Fungsi untuk kirim chat (POST)

* ambil input user
* panggil POST ke `/api/chat`
* server balikin `answer`
* setelah itu FE harus **reload history**

### ✔ 1.3 Fungsi untuk load history (GET)

* GET ke endpoint
* update daftar chat di UI

### ✔ 1.4 Render chat ke UI

* render array chat:

  * message user
  * answer AI
  * waktu

### ✔ 1.5 Trigger pengiriman

* tombol kirim
* enter key (optional)

### ✔ 1.6 Loading indicator (opsional)

* tampilkan loading saat POST sedang dipanggil

---

# 🔄 Alur Lengkap Frontend

1. **Chatbox dibuka → loadHistory()**
2. User mengetik pesan → klik kirim
3. FE panggil:

   * `sendChat(message)`
   * lalu `loadHistory()`
4. UI menampilkan chat terbaru
5. Riwayat tersimpan di database
