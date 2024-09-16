from database import connect_to_database
from BcryptHasher import BcryptHasher  # Ajuste o import conforme a estrutura do seu projeto


class UserDAO:
    def __init__(self):
        self.db = connect_to_database()

    def data_to_generate_token(self, email: str, password: str):
        cursor = self.db.cursor()

        # Primeiro, obter o hash da senha armazenada
        query_password = """
            SELECT password
            FROM users
            WHERE email = %s AND isActive = 1
        """
        cursor.execute(query_password, (email,))
        stored_hash = cursor.fetchone()

        if stored_hash:
            stored_hash = stored_hash[0]

            # Instanciar BcryptHasher
            hasher = BcryptHasher()

            # Verificar se a senha fornecida corresponde ao hash armazenado
            if not hasher.verify_password(password, stored_hash):
                cursor.close()
                return None

            # Se a senha estiver correta, buscar os dados do usuário
            query_user_data = """
                SELECT id, email, document, passwordVersion
                FROM users
                WHERE email = %s
            """
            cursor.execute(query_user_data, (email,))
            user_data = cursor.fetchone()
            cursor.close()

            # Se user_data não estiver vazio (ou seja, se a consulta retornou algum resultado)
            if user_data:
                # Retorna um dicionário com os dados
                return {
                    "id": user_data[0],
                    "email": user_data[1],
                    "document": user_data[2],
                    "passwordVersion": user_data[3]
                }
            else:
                return None
        else:
            cursor.close()
            return None