# sentry/auth/credentials.py
from sentry.infra.database.repositories import UserRepository

def verify_credentials(username, password):
    """Verifica se as credenciais são válidas"""
    try:
        repo = UserRepository()
        user = repo.find_by_username(username)
        repo.close()
        
        if user and user['password_hash'] == password:
            return True
        return False
    except Exception as e:
        print(f"Erro ao verificar credenciais: {e}")
        return False