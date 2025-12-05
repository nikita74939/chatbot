from fastapi import FastAPI
from pydantic import BaseModel
from agent.router import ChatRouter

app = FastAPI()

# Inisiasi Router (pastikan path benar)
router = ChatRouter(
    df_path="dataset/data.csv",
    model_path="mining_simulation_rf.pkl"
)

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    result = router.handle_message(req.message)
    return result

@app.get("/")
def root():
    return {"message": "Mining Value Chatbox API is running"}
