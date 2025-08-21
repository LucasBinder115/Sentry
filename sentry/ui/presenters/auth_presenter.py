# sentry/ui/presenters/auth_presenter.py
from sentry.auth.credentials import verify_credentials
from sentry.infra.database.repositories import UserRepository

class AuthPresenter:
    def __init__(self, view):
        self.view = view
        self.repo = UserRepository()
    
    def login(self, username: str, password: str) -> bool:
        user = self.repo.find_by_username(username)
        if user and verify_credentials(user, password):
            return True
        return False
    
    def __del__(self):
        # Garante que a conexão será fechada
        self.repo.close()