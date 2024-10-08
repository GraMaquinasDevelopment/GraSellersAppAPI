from datetime import datetime, timedelta, timezone
import jwt
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from DAO.AuthenticateDAO import AuthenticateDAO
import os

from DAO.UserDAO import UserDAO

router = APIRouter()
authenticate_dao = AuthenticateDAO()

# Obtém a SECRET_KEY da variável de ambiente
SECRET_KEY = "1e255487c1c756ce12133c0762a16fe5779ca1d313470369436f32c2190f56d08eeb0aced2217aeba658a246ac773d01392478e341e56ee1c68a343270d38dfd"
#os.getenv("SECRET_KEY")

# Verifica se a SECRET_KEY está definida
if SECRET_KEY is None:
    raise ValueError("A variável de ambiente SECRET_KEY não está definida.")


def generate_jwt_token(id: int, email: str, document: str, passwordVersion: str) -> str:
    # Define os dados do payload do token JWT
    current_time = datetime.now(timezone.utc)
    payload = {
        "id": id,
        "email": email,
        "document": document,
        "passwordVersion": passwordVersion
        #"exp": current_time + timedelta(seconds=3600)
    }

    # Gera o token JWT assinado com a chave secreta
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/user/authenticate")
async def authenticate_user(email: str = Header(...), password: str = Header(...)):
    # Verifique se as credenciais foram fornecidas no cabeçalho
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email e senha são necessários")

    # Instanciando UserDAO
    user_dao = UserDAO()

    # Verifique se o usuário existe no banco de dados
    user_data = user_dao.data_to_generate_token(email, password)

    if user_data:
        # Se o usuário existe, gere um token JWT
        id = user_data["id"]
        document = user_data["document"]
        email = user_data["email"]
        passwordVersion = user_data["passwordVersion"]

        token = generate_jwt_token(id, email, document, passwordVersion)

        return {"token": token, "secret_key": SECRET_KEY}
    else:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")