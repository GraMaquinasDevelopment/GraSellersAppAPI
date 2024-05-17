from database import connect_to_database

class UserDAO:
    def __init__(self):
        self.db = connect_to_database()

    def data_to_generate_token(self, email, password):
        cursor = self.db.cursor()
        query = """
            SELECT id, email, document 
            FROM users 
            WHERE email = %s AND password = %s
        """
        cursor.execute(query, (email, password))
        user_data = cursor.fetchone()
        cursor.close()

        # Se user_data não estiver vazio (ou seja, se a consulta retornou algum resultado)
        if user_data:
            # Retorna um dicionário com os dados
            return {"id": user_data[0], "email": user_data[1], "document": user_data[2]}
        else:
            return None