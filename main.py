# main.py
from fastapi import FastAPI
from uvicorn import run
from Controller.controller_user_authenticate import router as controller_router
from routes import router as dados_router

app = FastAPI()

# Adicione o roteador do controlador de autenticação de usuário ao aplicativo
app.include_router(controller_router)
app.include_router(dados_router)

@app.get("/")
async def root():
    return {"message": "Hello World Teste Eback"}

if __name__ == "__main__":
    run(app, host="127.0.0.1", port=8000)
