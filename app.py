# app.py (update untuk handle error model dengan lebih baik)
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agent.router import ChatRouter
import os

app = FastAPI(
    title="Mining Value Chain Chatbox API",
    description="API untuk chatbot simulasi mining dan shipping dengan integrasi PostgreSQL.",
    version="1.0.0"
)

# Konfigurasi default untuk ChatRouter
DEFAULT_DF_PATH = None  # Jika None, load dari DB PostgreSQL
DEFAULT_MODEL_PATHS = {
    'mining': os.path.join(os.getcwd(), 'models', 'mining_simulation_rf.pkl'),
    'shipping': os.path.join(os.getcwd(), 'models', 'shipping_simulation_rf.pkl')
}

# Inisiasi Router dengan parameter
router = None
try:
    router = ChatRouter(
        df_path=DEFAULT_DF_PATH,
        model_paths=DEFAULT_MODEL_PATHS
    )
except Exception as e:
    print(f"Warning: Model gagal load ({str(e)}). Menggunakan fallback rule-based saja. Retrain model jika perlu.")
    try:
        # Fallback tanpa model
        router = ChatRouter(
            df_path=DEFAULT_DF_PATH,
            model_paths=None  # Skip load model
        )
    except Exception as fallback_e:
        print(f"Error fallback: {str(fallback_e)}")
        # Jika masih gagal, inisiasi minimal tanpa DB dan model (untuk test)
        try:
            router = ChatRouter(
                df_path='dummy',  # Gunakan dummy untuk skip DB load
                model_paths=None
            )
        except Exception as minimal_e:
            raise RuntimeError(f"Gagal inisiasi ChatRouter sepenuhnya: {str(minimal_e)}. Cek kode dan dependencies.")

class ChatRequest(BaseModel):
    message: str
    user_id: str

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    if router is None:
        raise HTTPException(status_code=500, detail="ChatRouter belum diinisiasi.")
    
    try:
        result = router.handle_message(req.message, req.user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")

@app.get("/")
def root():
    return {"message": "Mining Value Chatbox API is running. Gunakan POST /chat untuk interaksi."}

@app.get("/health")
def health_check():
    if router is None:
        return {"status": "unhealthy", "error": "ChatRouter belum diinisiasi."}
    
    try:
        return {"status": "healthy", "message": "API running."}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.post("/simulate")
async def simulate_endpoint(req: ChatRequest):
    if router is None:
        raise HTTPException(status_code=500, detail="ChatRouter belum diinisiasi.")
    
    try:
        result = router.handle_message(req.message, req.user_id)
        if result.get("type") not in ["simulation", "error"]:
            raise HTTPException(status_code=400, detail="Pesan bukan simulasi.")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error simulation: {str(e)}")