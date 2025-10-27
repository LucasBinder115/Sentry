# sentry/ui/presenters/auth_presenter.py

import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from sentry.auth.credentials import verify_credentials, hash_password
from sentry.auth.session import SessionManager
from sentry.infra.database.repositories import UserRepository
from sentry.core.entities.user import User
from sentry.core.use_cases.auth import (
    UserNotFoundError,
    InvalidCredentialsError,
    # The following may be defined elsewhere; define locally if missing
)

# Configuração de logging
logger = logging.getLogger(__name__)


class AuthStatus(Enum):
    """Status possíveis da autenticação."""
    SUCCESS = "success"
    INVALID_CREDENTIALS = "invalid_credentials"
    ACCOUNT_LOCKED = "account_locked"
    USER_NOT_FOUND = "user_not_found"
    SYSTEM_ERROR = "system_error"
    PASSWORD_EXPIRED = "password_expired"


@dataclass
class AuthResult:
    """Resultado estruturado da autenticação."""
    status: AuthStatus
    user: Optional[User] = None
    session_token: Optional[str] = None
    message: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class LoginRequest:
    """Dados da requisição de login."""
    username: str
    password: str
    remember_me: bool = False
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


@dataclass  
class LoginResponse:
    """Resposta do processo de login."""
    success: bool
    message: str
    user_data: Optional[Dict[str, Any]] = None
    session_data: Optional[Dict[str, Any]] = None
    redirect_to: Optional[str] = None
    requires_password_change: bool = False


class AuthPresenter:
    """
    Presenter para autenticação de usuários.
    
    Responsável por:
    - Orquestrar o fluxo de autenticação
    - Gerenciar sessões de usuário
    - Fornecer dados formatados para a UI
    - Tratar erros e exceções
    """
    
    def __init__(self, view=None):
        self.view = view
        self.repo = UserRepository()
        self.session_manager = SessionManager()
        self.max_login_attempts = 5
        self.lockout_duration = timedelta(minutes=30)
        
        logger.info("AuthPresenter inicializado")
    
    def login(self, login_request: LoginRequest) -> LoginResponse:
        """
        Executa o processo completo de login.
        
        Args:
            login_request: Dados da requisição de login
            
        Returns:
            LoginResponse: Resposta formatada para a UI
        """
        logger.info(f"Tentativa de login para usuário: {login_request.username}")
        
        try:
            # Validação básica
            if not self._validate_login_input(login_request):
                return LoginResponse(
                    success=False,
                    message="Usuário e senha são obrigatórios"
                )
            
            # Busca usuário
            user = self.repo.find_by_username(login_request.username)
            if not user:
                self._handle_failed_login_attempt(login_request.username, login_request.ip_address)
                return LoginResponse(
                    success=False,
                    message="Usuário ou senha inválidos"
                )
            
            # Verifica se a conta está bloqueada
            if self._is_account_locked(user):
                return LoginResponse(
                    success=False,
                    message="Conta temporariamente bloqueada. Tente novamente mais tarde."
                )
            
            # Verifica se precisa trocar senha
            if self._requires_password_change(user):
                return LoginResponse(
                    success=False,
                    message="É necessário alterar sua senha",
                    requires_password_change=True
                )
            
            # Verifica credenciais
            auth_result = self._authenticate_user(user, login_request)
            
            if auth_result.status == AuthStatus.SUCCESS:
                return self._handle_successful_login(auth_result, login_request)
            else:
                return self._handle_failed_login(auth_result, login_request)
                
        except AuthenticationError as e:
            logger.error(f"Erro de autenticação: {e}")
            return LoginResponse(
                success=False,
                message="Erro no sistema de autenticação"
            )
        except Exception as e:
            logger.error(f"Erro inesperado no login: {e}")
            return LoginResponse(
                success=False,
                message="Erro interno do sistema"
            )
    
    def logout(self, session_token: str) -> bool:
        """
        Executa logout do usuário.
        
        Args:
            session_token: Token da sessão
            
        Returns:
            True se logout bem-sucedido
        """
        try:
            success = self.session_manager.invalidate_session(session_token)
            if success:
                logger.info("Logout realizado com sucesso")
                if self.view:
                    self.view.on_logout_success()
            else:
                logger.warning("Token de sessão inválido durante logout")
                
            return success
            
        except Exception as e:
            logger.error(f"Erro durante logout: {e}")
            return False
    
    def validate_session(self, session_token: str) -> Tuple[bool, Optional[User]]:
        """
        Valida se uma sessão é válida.
        
        Args:
            session_token: Token da sessão
            
        Returns:
            Tuple (é_válida, usuário)
        """
        try:
            session_data = self.session_manager.validate_session(session_token)
            if not session_data:
                return False, None
            
            user_id = session_data.get('user_id')
            if not user_id:
                return False, None
            
            user = self.repo.find_by_id(user_id)
            return user is not None, user
            
        except Exception as e:
            logger.error(f"Erro na validação da sessão: {e}")
            return False, None
    
    def change_password(
        self, 
        session_token: str, 
        current_password: str, 
        new_password: str
    ) -> LoginResponse:
        """
        Altera a senha do usuário.
        
        Args:
            session_token: Token da sessão
            current_password: Senha atual
            new_password: Nova senha
            
        Returns:
            LoginResponse: Resposta da operação
        """
        try:
            # Valida sessão
            is_valid, user = self.validate_session(session_token)
            if not is_valid or not user:
                return LoginResponse(
                    success=False,
                    message="Sessão inválida ou expirada"
                )
            
            # Verifica senha atual
            if not verify_credentials(user, current_password):
                return LoginResponse(
                    success=False, 
                    message="Senha atual incorreta"
                )
            
            # Valida nova senha
            if not self._validate_password_strength(new_password):
                return LoginResponse(
                    success=False,
                    message="A nova senha não atende aos requisitos de segurança"
                )
            
            # Atualiza senha
            new_password_hash = hash_password(new_password)
            user.password_hash = new_password_hash
            user.must_change_password = False
            user.updated_at = datetime.now()
            
            updated_user = self.repo.update(user)
            
            if updated_user:
                logger.info(f"Senha alterada com sucesso para usuário: {user.username}")
                return LoginResponse(
                    success=True,
                    message="Senha alterada com sucesso"
                )
            else:
                return LoginResponse(
                    success=False,
                    message="Erro ao atualizar senha"
                )
                
        except Exception as e:
            logger.error(f"Erro ao alterar senha: {e}")
            return LoginResponse(
                success=False,
                message="Erro interno ao alterar senha"
            )
    
    def get_user_permissions(self, session_token: str) -> Dict[str, bool]:
        """
        Obtém permissões do usuário logado.
        
        Args:
            session_token: Token da sessão
            
        Returns:
            Dict com permissões
        """
        try:
            is_valid, user = self.validate_session(session_token)
            if not is_valid or not user:
                return {}
            
            return self._map_user_permissions(user)
            
        except Exception as e:
            logger.error(f"Erro ao obter permissões: {e}")
            return {}
    
    def reset_password_request(self, username: str, email: str) -> LoginResponse:
        """
        Solicita redefinição de senha.
        
        Args:
            username: Nome de usuário
            email: Email do usuário
            
        Returns:
            LoginResponse: Resposta da operação
        """
        try:
            user = self.repo.find_by_username(username)
            if not user or user.email != email:
                # Por segurança, não revelamos se o usuário existe
                return LoginResponse(
                    success=True,
                    message="Se o usuário existir, um email de redefinição será enviado"
                )
            
            # Aqui implementaria a lógica de envio de email
            # token = self._generate_password_reset_token(user)
            # self._send_password_reset_email(user, token)
            
            logger.info(f"Solicitação de redefinição de senha para: {username}")
            
            return LoginResponse(
                success=True,
                message="Instruções para redefinição de senha foram enviadas para seu email"
            )
            
        except Exception as e:
            logger.error(f"Erro na solicitação de redefinição de senha: {e}")
            return LoginResponse(
                success=False,
                message="Erro ao processar solicitação de redefinição de senha"
            )
    
    def _authenticate_user(self, user: User, login_request: LoginRequest) -> AuthResult:
        """
        Autentica o usuário com as credenciais fornecidas.
        
        Args:
            user: Usuário a ser autenticado
            login_request: Dados do login
            
        Returns:
            AuthResult: Resultado da autenticação
        """
        try:
            if verify_credentials(user, login_request.password):
                # Login bem-sucedido - reseta tentativas falhas
                self._reset_failed_attempts(user)
                
                # Cria sessão
                session_token = self.session_manager.create_session(
                    user_id=user.id,
                    user_data=self._prepare_session_data(user),
                    remember_me=login_request.remember_me
                )
                
                # Registra login bem-sucedido
                self.repo.record_login_attempt(
                    user_id=user.id,
                    success=True,
                    ip_address=login_request.ip_address,
                    user_agent=login_request.user_agent
                )
                
                return AuthResult(
                    status=AuthStatus.SUCCESS,
                    user=user,
                    session_token=session_token,
                    message="Login realizado com sucesso"
                )
            else:
                # Login falhou - incrementa tentativas
                self._handle_failed_login_attempt(user.username, login_request.ip_address)
                self._increment_failed_attempts(user)
                
                # Registra tentativa falha
                self.repo.record_login_attempt(
                    user_id=user.id,
                    success=False,
                    ip_address=login_request.ip_address,
                    user_agent=login_request.user_agent,
                    failure_reason="Senha incorreta"
                )
                
                return AuthResult(
                    status=AuthStatus.INVALID_CREDENTIALS,
                    message="Usuário ou senha inválidos"
                )
                
        except Exception as e:
            logger.error(f"Erro na autenticação do usuário {user.username}: {e}")
            return AuthResult(
                status=AuthStatus.SYSTEM_ERROR,
                message="Erro interno na autenticação"
            )
    
    def _handle_successful_login(self, auth_result: AuthResult, login_request: LoginRequest) -> LoginResponse:
        """
        Processa login bem-sucedido.
        
        Args:
            auth_result: Resultado da autenticação
            login_request: Dados do login
            
        Returns:
            LoginResponse: Resposta formatada
        """
        user = auth_result.user
        
        # Prepara dados do usuário para a UI
        user_data = {
            'id': user.id,
            'username': user.username,
            'name': user.name,
            'email': user.email,
            'role': user.role,
            'permissions': self._map_user_permissions(user)
        }
        
        # Prepara dados da sessão
        session_data = {
            'token': auth_result.session_token,
            'expires_at': self.session_manager.get_session_expiry(auth_result.session_token),
            'remember_me': login_request.remember_me
        }
        
        # Determina redirecionamento baseado no role
        redirect_to = self._get_redirect_path(user.role)
        
        # Notifica view se disponível
        if self.view:
            self.view.on_login_success(user_data, session_data)
        
        logger.info(f"Login bem-sucedido: {user.username} (Role: {user.role})")
        
        return LoginResponse(
            success=True,
            message=auth_result.message,
            user_data=user_data,
            session_data=session_data,
            redirect_to=redirect_to
        )
    
    def _handle_failed_login(self, auth_result: AuthResult, login_request: LoginRequest) -> LoginResponse:
        """
        Processa login falho.
        
        Args:
            auth_result: Resultado da autenticação
            login_request: Dados do login
            
        Returns:
            LoginResponse: Resposta formatada
        """
        message = auth_result.message
        
        # Notifica view se disponível
        if self.view:
            self.view.on_login_failure(message)
        
        logger.warning(f"Login falhou: {login_request.username} - {message}")
        
        return LoginResponse(
            success=False,
            message=message
        )
    
    def _validate_login_input(self, login_request: LoginRequest) -> bool:
        """Valida dados de entrada do login."""
        return (
            login_request.username and 
            login_request.username.strip() and 
            login_request.password and 
            login_request.password.strip()
        )
    
    def _validate_password_strength(self, password: str) -> bool:
        """Valida força da senha."""
        if len(password) < 8:
            return False
        
        # Verifica complexidade (pelo menos uma letra maiúscula, uma minúscula e um número)
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        
        return has_upper and has_lower and has_digit
    
    def _is_account_locked(self, user: User) -> bool:
        """Verifica se a conta está bloqueada."""
        if getattr(user, 'lock_until', None) and user.lock_until > datetime.now():
            return True
        
        if getattr(user, 'failed_login_attempts', 0) >= self.max_login_attempts:
            return True
        
        return False
    
    def _requires_password_change(self, user: User) -> bool:
        """Verifica se o usuário precisa trocar a senha."""
        return getattr(user, 'must_change_password', False)
    
    def _increment_failed_attempts(self, user: User):
        """Incrementa contador de tentativas falhas."""
        try:
            current_attempts = getattr(user, 'failed_login_attempts', 0) + 1
            user.failed_login_attempts = current_attempts
            
            # Bloqueia conta se exceder limite
            if current_attempts >= self.max_login_attempts:
                user.lock_until = datetime.now() + self.lockout_duration
                logger.warning(f"Conta bloqueada: {user.username}")
            
            self.repo.update(user)
            
        except Exception as e:
            logger.error(f"Erro ao incrementar tentativas falhas: {e}")
    
    def _reset_failed_attempts(self, user: User):
        """Reseta contador de tentativas falhas."""
        try:
            user.failed_login_attempts = 0
            user.lock_until = None
            user.last_login = datetime.now()
            
            self.repo.update(user)
            
        except Exception as e:
            logger.error(f"Erro ao resetar tentativas falhas: {e}")
    
    def _handle_failed_login_attempt(self, username: str, ip_address: Optional[str]):
        """Registra tentativa falha de login."""
        # Esta é uma versão simplificada - em produção, registraríamos
        # em um sistema de auditoria mais robusto
        logger.warning(f"Tentativa de login falha - Usuário: {username}, IP: {ip_address}")
    
    def _prepare_session_data(self, user: User) -> Dict[str, Any]:
        """Prepara dados para a sessão."""
        return {
            'user_id': user.id,
            'username': user.username,
            'role': user.role,
            'name': user.name,
            'permissions': self._map_user_permissions(user),
            'login_time': datetime.now().isoformat()
        }
    
    def _map_user_permissions(self, user: User) -> Dict[str, bool]:
        """Mapeia permissões baseado no role do usuário."""
        base_permissions = {
            'view_dashboard': True,
            'view_reports': True,
        }
        
        role_permissions = {
            'operator': {
                'register_vehicles': True,
                'view_camera_feeds': True,
            },
            'supervisor': {
                'register_vehicles': True,
                'view_camera_feeds': True,
                'manage_users': True,
                'generate_reports': True,
            },
            'admin': {
                'register_vehicles': True,
                'view_camera_feeds': True,
                'manage_users': True,
                'generate_reports': True,
                'system_config': True,
                'audit_logs': True,
            }
        }
        
        permissions = base_permissions.copy()
        permissions.update(role_permissions.get(user.role, {}))
        
        return permissions
    
    def _get_redirect_path(self, role: str) -> str:
        """Determina para onde redirecionar após login."""
        redirect_paths = {
            'operator': '/dashboard',
            'supervisor': '/reports',
            'admin': '/admin'
        }
        return redirect_paths.get(role, '/dashboard')
    
    def cleanup(self):
        """Libera recursos."""
        try:
            if hasattr(self.repo, 'close'):
                self.repo.close()
            logger.info("AuthPresenter - recursos liberados")
        except Exception as e:
            logger.error(f"Erro no cleanup do AuthPresenter: {e}")
    
    def __del__(self):
        """Destrutor - garante que os recursos sejam liberados."""
        self.cleanup()


# Interface para a View
class AuthViewInterface:
    """Interface que a View deve implementar."""
    
    def on_login_success(self, user_data: Dict[str, Any], session_data: Dict[str, Any]):
        """Chamado quando login é bem-sucedido."""
        pass
    
    def on_login_failure(self, error_message: str):
        """Chamado quando login falha."""
        pass
    
    def on_logout_success(self):
        """Chamado quando logout é bem-sucedido."""
        pass


# Exemplo de uso
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # View de exemplo para demonstração
    class ExampleAuthView(AuthViewInterface):
        def on_login_success(self, user_data, session_data):
            print(f"✅ Login bem-sucedido: {user_data['username']}")
            print(f"📊 Permissões: {user_data['permissions']}")
        
        def on_login_failure(self, error_message):
            print(f"❌ Login falhou: {error_message}")
        
        def on_logout_success(self):
            print("✅ Logout realizado com sucesso")
    
    # Teste do presenter
    try:
        view = ExampleAuthView()
        presenter = AuthPresenter(view=view)
        
        # Simula login
        login_request = LoginRequest(
            username="admin",
            password="admin123",
            remember_me=True,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0..."
        )
        
        response = presenter.login(login_request)
        print(f"Resposta do login: {response.success} - {response.message}")
        
        # Cleanup
        presenter.cleanup()
        
    except Exception as e:
        print(f"❌ Erro no exemplo: {e}")