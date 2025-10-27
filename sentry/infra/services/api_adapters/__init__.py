# sentry/infra/services/api_adapters/__init__.py

from .denatran import DenatranAPIAdapter # <--- Esta linha agora deve funcionar

class ApiAdapters:
    @staticmethod
    def get_safety_adapter():
        return DenatranAPIAdapter()