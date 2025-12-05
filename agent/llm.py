from google import genai
client = genai.Client(api_key="AIzaSyA2VA3tVdKjx8y-eoOcfUyNEApHr2hwjeI")

def ask_gemini(user_msg: str) -> str:
    """
    Mengirim pertanyaan ke Gemini dan mengembalikan jawaban teks.
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=user_msg
        )
        return response.text

    except Exception as e:
        return f"Maaf, terjadi kesalahan saat memanggil Gemini: {e}"
