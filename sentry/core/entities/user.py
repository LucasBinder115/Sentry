# sentry/core/entities/user.py

from datetime import datetime
from enum import Enum
import hashlib

class UserRole(Enum):
    """Enum para definir os papéis (níveis de acesso) do usuário."""
    ADMIN = "admin"               # Acesso total ao sistema
    MANAGER = "manager"           # Gerencia operações, usuários e relatórios
    OPERATOR = "operator"         # Operador do portão, registra acessos
    VIEWER = "viewer"             # Acesso somente leitura a dashboards e relatórios

class UserStatus(Enum):
    """Enum para definir o status da conta do usuário."""
    ACTIVE = "Ativa"
    INACTIVE = "Inativa"
    SUSPENDED = "Suspensa"
    PENDING_ACTIVATION = "Pendente de Ativação"

class User:
    """
    Entidade que representa um usuário do sistema de forma robusta.
    Contém dados de autenticação, perfil, permissões e auditoria.
    """
    def __init__(
        self,
        username: str,
        email: str,
        password_hash: str,
        role: UserRole = UserRole.VIEWER,
        status: UserStatus = UserStatus.PENDING_ACTIVATION,
        id: int = None,
        full_name: str = None,
        phone: str = None,
        department: str = None,
        created_at: datetime = None,
        updated_at: datetime = None,
        last_login_at: datetime = None,
        failed_login_attempts: int = 0,
        is_locked: bool = False,
        lock_until: datetime = None,
        details: dict = None
    ):
        self.id = id
        self.username = username.lower() # Usuário sempre em minúsculo para evitar duplicatas
        self.email = email.lower()       # Email sempre em minúsculo
        self.password_hash = password_hash
        self.role = role
        self.status = status
        
        # Dados do Perfil
        self.full_name = full_name
        self.phone = phone
        self.department = department
        
        # Controle de Tempo e Auditoria
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.last_login_at = last_login_at
        
        # Segurança
        self.failed_login_attempts = failed_login_attempts
        self.is_locked = is_locked
        self.lock_until = lock_until
        
        # Campo flexível para detalhes extras
        self.details = details or {}

    def __repr__(self):
        return (f"<User (id={self.id}, username='{self.username}', "
                f"role='{self.role.value}', status='{self.status.value}')>")

    # --- Métodos de Serialização ---

    def to_dict(self, include_sensitive_data: bool = False) -> dict:
        """
        Converte o objeto User para um dicionário.
        A opção include_sensitive_data controla a exposição de dados sensíveis.
        """
        data = {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role.value,
            "status": self.status.value,
            "full_name": self.full_name,
            "phone": self.phone,
            "department": self.department,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "is_locked": self.is_locked,
            "details": self.details
        }
        if include_sensitive_data:
            data["failed_login_attempts"] = self.failed_login_attempts
            data["lock_until"] = self.lock_until.isoformat() if self.lock_until else None
        
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """Cria uma instância de User a partir de um dicionário."""
        role = UserRole(data.get("role")) if data.get("role") else UserRole.VIEWER
        status = UserStatus(data.get("status")) if data.get("status") else UserStatus.PENDING_ACTIVATION
        
        created_at = datetime.fromisoformat(data.get("created_at")) if data.get("created_at") else datetime.now()
        updated_at = datetime.fromisoformat(data.get("updated_at")) if data.get("updated_at") else datetime.now()
        last_login_at = datetime.fromisoformat(data.get("last_login_at")) if data.get("last_login_at") else None
        lock_until = datetime.fromisoformat(data.get("lock_until")) if data.get("lock_until") else None

        return cls(
            id=data.get("id"),
            username=data.get("username"),
            email=data.get("email"),
            password_hash=data.get("password_hash"),
            role=role,
            status=status,
            full_name=data.get("full_name"),
            phone=data.get("phone"),
            department=data.get("department"),
            created_at=created_at,
            updated_at=updated_at,
            last_login_at=last_login_at,
            failed_login_attempts=data.get("failed_login_attempts", 0),
            is_locked=data.get("is_locked", False),
            lock_until=lock_until,
            details=data.get("details", {})
        )

    # --- Métodos de Lógica de Negócio e Segurança ---

    @staticmethod
    def hash_password(password: str) -> str:
        """Gera um hash seguro para a senha usando SHA-256."""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    def verify_password(self, password: str) -> bool:
        """Verifica se a senha fornecida corresponde ao hash armazenado."""
        return self.password_hash == self.hash_password(password)

    def is_account_locked(self) -> bool:
        """Verifica se a conta está bloqueada no momento."""
        if self.is_locked and self.lock_until:
            return datetime.now() < self.lock_until
        return self.is_locked

    def record_failed_login(self):
        """Registra uma tentativa de login falha e bloqueia a conta se necessário."""
        self.failed_login_attempts += 1
        self.updated_at = datetime.now()
        
        # Bloqueia a conta após 5 tentativas falhas por 30 minutos
        if self.failed_login_attempts >= 5:
            self.is_locked = True
            from datetime import timedelta
            self.lock_until = datetime.now() + timedelta(minutes=30)

    def reset_failed_logins(self):
        """Reseta o contador de tentativas falhas após um login bem-sucedido."""
        self.failed_login_attempts = 0
        self.is_locked = False
        self.lock_until = None
        self.last_login_at = datetime.now()
        self.updated_at = datetime.now()

    def activate(self):
        """Ativa a conta do usuário."""
        if self.status == UserStatus.PENDING_ACTIVATION:
            self.status = UserStatus.ACTIVE
            self.updated_at = datetime.now()
        else:
            raise ValueError(f"Não é possível ativar um usuário com status '{self.status.value}'.")

    def deactivate(self):
        """Desativa a conta do usuário."""
        if self.status != UserStatus.INACTIVE:
            self.status = UserStatus.INACTIVE
            self.updated_at = datetime.now()

    # --- Métodos de Verificação de Permissão (RBAC - Role-Based Access Control) ---

    def can(self, action: str) -> bool:
        """
        Verifica se o usuário tem permissão para realizar uma ação.
        Este é um exemplo simples de um sistema de controle de acesso baseado em papéis.
        """
        permissions = {
            UserRole.ADMIN: ["create", "read", "update", "delete", "manage_users", "view_reports"],
            UserRole.MANAGER: ["create", "read", "update", "view_reports"],
            UserRole.OPERATOR: ["create", "read"], # Ex: registrar veículo, registrar acesso
            UserRole.VIEWER: ["read"]
        }
        return action in permissions.get(self.role, [])

    def is_admin(self) -> bool:
        """Verifica se o usuário é um administrador."""
        return self.role == UserRole.ADMIN

    def is_manager_or_admin(self) -> bool:
        """Verifica se o usuário é gerente ou administrador."""
        return self.role in [UserRole.MANAGER, UserRole.ADMIN]