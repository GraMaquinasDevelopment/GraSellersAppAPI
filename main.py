# main.py
import uvicorn
from fastapi import FastAPI
from uvicorn import run
from Controller.controller_user_authenticate import router as controller_router
<<<<<<< HEAD
from companyEquipmentsExcelFile import process_excel_data
=======
>>>>>>> 6c9e17d11e6ac87cbe04ed80aac2ae4ff5f09c5f
from routes import router as dados_router

app = FastAPI()

# Adicione o roteador do controlador de autenticação de usuário ao aplicativo
app.include_router(controller_router)
app.include_router(dados_router)

<<<<<<< HEAD
process_excel_data()
=======
@app.get("/")
async def root():
    return {"message": "Hello World Teste Eback"}

if __name__ == "__main__":
    run(app, host="127.0.0.1", port=8001)
>>>>>>> 6c9e17d11e6ac87cbe04ed80aac2ae4ff5f09c5f
