import google.generativeai as genai
import logging
from dotenv import load_dotenv
import os

# Setup logging for the web app to capture errors and info
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)

# Load environment variables from .env file
try:
    load_dotenv()
    logging.info("Loaded environment variables from .env file.")
except Exception as e:
    logging.error(f"Error loading .env file: {e}")

# Configure the Google Generative AI API
try:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logging.error("GOOGLE_API_KEY not found in environment variables.")
    else:
        genai.configure(api_key=api_key)
        logging.info("Google Generative AI API configured.")
except Exception as e:
    logging.error(f"Error configuring Google Generative AI API: {e}")

def ask_gemini(user_msg: str) -> str:
    try:
        model = genai.GenerativeModel("gemini-2.5-pro")
        response = model.generate_content(user_msg)
        logging.info(f"Gemini response: {response.text.strip()}")
        return response.text.strip()
    except Exception as e:
        logging.error(f"Error in get_gemini_response(): {e}")
        return "Sorry, I couldn't process that."
