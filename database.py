<<<<<<< HEAD
import pymysql

def connect_to_database():
    db_host = "192.168.0.129"
    db_port = 3306
    db_user = "root"
    db_password = "GRA-@2025maquinas"
    db_database = "grasellers"

    db_connection = pymysql.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_password,
        database=db_database
    )

    if db_connection.open:
        print("Conexão bem-sucedida ao banco de dados.")
    else:
        print("Falha ao conectar ao banco de dados.")
    return db_connection
=======
import mysql.connector
from mysql.connector import Error

def connect_to_database():
    try:
        db_host = "192.168.0.100"
        db_port = 3306
        db_user = "root"
        db_password = "root"
        db_database = "grasellers"

        db_connection = mysql.connector.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database=db_database
        )

        if db_connection.is_connected():
            print("Conexão bem-sucedida ao banco de dados.")
            return db_connection
    except Error as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        return None
>>>>>>> 6c9e17d11e6ac87cbe04ed80aac2ae4ff5f09c5f
