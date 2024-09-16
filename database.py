# database.py
import mysql.connector

def connect_to_database():
    # Credenciais do banco de dados (substitua com suas próprias credenciais)
    db_host = "localhost"#192.168.0.100"
    db_port = 3306
    db_user = "root"
    db_password = "root"
    #cli801"
    db_database = "grasellers"

    # Estabelecer a conexão com o banco de dados
    db_connection = mysql.connector.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_password,
        database=db_database
    )

    # Verificar se a conexão foi estabelecida corretamente
    if db_connection.is_connected():
        print("Conexão bem-sucedida ao banco de dados.")
    else:
        print("Falha ao conectar ao banco de dados.")
    return db_connection