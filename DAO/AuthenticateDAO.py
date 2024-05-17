from database import connect_to_database

class AuthenticateDAO:
    def __init__(self):
        self.db = connect_to_database()

    def user_exists(self, email, password):
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
        user = cursor.fetchone()
        cursor.close()
        return user is not None