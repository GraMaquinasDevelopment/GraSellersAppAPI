# main.py
import uvicorn
from fastapi import FastAPI
from uvicorn import run
from Controller.controller_user_authenticate import router as controller_router
from companyEquipmentsExcelFile import process_excel_data
from routes import router as dados_router

app = FastAPI()

# Adicione o roteador do controlador de autenticação de usuário ao aplicativo
app.include_router(controller_router)
app.include_router(dados_router)

process_excel_data()