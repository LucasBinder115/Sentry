# teste_imports.py (criar temporariamente)
try:
    from sentry.main import main
    from sentry.ui.presenters.auth_presenter import AuthPresenter
    from sentry.core.use_cases.auth import LoginUseCase
    from sentry.infra.database.database import Database
    print("✅ Todos os imports básicos funcionando!")
except ImportError as e:
    print(f"❌ Erro de import: {e}")