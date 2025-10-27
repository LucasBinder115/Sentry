# sentry/auth/credentials.py
"""
Sistema de Autenticação e Gerenciamento de Credenciais
Autor: SENTRY.INC
Versão: 2.0
"""

import hashlib
import secrets
import re
import datetime
from typing import Optional, Dict, Tuple
from sentry.infra.database.repositories import UserRepository

# ============================================================================
# CONSTANTES DE SEGURANÇA
# ============================================================================

# Requisitos de senha
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
REQUIRE_UPPERCASE = True
REQUIRE_LOWERCASE = True
REQUIRE_NUMBERS = True
REQUIRE_SPECIAL_CHARS = True

# Tentativas de login
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30

# Salt para hashing
SALT_LENGTH = 32

# Níveis de acesso
ACCESS_LEVELS = {
    'admin': 100,
    'supervisor': 50,
    'operador': 10,
    'visitante': 1
}


# ============================================================================
# CLASSE DE GERENCIAMENTO DE CREDENCIAIS
# ============================================================================

class CredentialsManager:
    """Gerenciador de credenciais e autenticação"""
    
    def __init__(self):
        self.repository = UserRepository()
        self.login_attempts = {}  # {username: {'count': int, 'last_attempt': datetime}}
    
    def __del__(self):
        """Fechar conexão ao destruir objeto"""
        if hasattr(self, 'repository'):
            self.repository.close()
    
    # ========================================================================
    # MÉTODOS DE AUTENTICAÇÃO
    # ========================================================================
    
    def verify_credentials(self, username: str, password: str) -> Tuple[bool, Optional[Dict], str]:
        """
        Verifica se as credenciais são válidas
        
        Args:
            username: Nome de usuário
            password: Senha em texto plano
        
        Returns:
            Tupla (sucesso, dados_usuario, mensagem)
        """
        try:
            # Validar entrada
            if not username or not password:
                return False, None, "Usuário e senha são obrigatórios"
            
            # Verificar se usuário está bloqueado
            if self.is_user_locked(username):
                remaining_time = self.get_lockout_remaining_time(username)
                return False, None, f"Conta bloqueada temporariamente. Tente novamente em {remaining_time} minutos"
            
            # Buscar usuário no banco
            user = self.repository.find_by_username(username)
            
            if not user:
                self.register_failed_attempt(username)
                return False, None, "Usuário ou senha inválidos"
            
            # Verificar se usuário está ativo
            if not user.get('ativo', True):
                return False, None, "Usuário desativado. Contate o administrador"
            
            # Verificar senha
            password_valid = self.verify_password(password, user['password_hash'], user.get('salt', ''))
            
            if not password_valid:
                self.register_failed_attempt(username)
                attempts_left = MAX_LOGIN_ATTEMPTS - self.get_login_attempts(username)
                return False, None, f"Usuário ou senha inválidos. Tentativas restantes: {attempts_left}"
            
            # Login bem-sucedido
            self.clear_login_attempts(username)
            self.update_last_login(username)
            
            # Remover informações sensíveis antes de retornar
            safe_user_data = self.get_safe_user_data(user)
            
            return True, safe_user_data, "Login realizado com sucesso"
            
        except Exception as e:
            print(f"❌ Erro ao verificar credenciais: {e}")
            import traceback
            traceback.print_exc()
            return False, None, f"Erro interno: {str(e)}"
    
    def verify_password(self, plain_password: str, hashed_password: str, salt: str = '') -> bool:
        """
        Verifica se a senha corresponde ao hash armazenado
        
        Args:
            plain_password: Senha em texto plano
            hashed_password: Hash armazenado no banco
            salt: Salt usado no hash (opcional para compatibilidade)
        
        Returns:
            True se a senha é válida
        """
        try:
            # Se há salt, usar PBKDF2
            if salt:
                computed_hash = self.hash_password_with_salt(plain_password, salt)
            else:
                # Compatibilidade com hashes SHA256 simples (não recomendado)
                computed_hash = hashlib.sha256(plain_password.encode()).hexdigest()
            
            return computed_hash == hashed_password
            
        except Exception as e:
            print(f"❌ Erro ao verificar senha: {e}")
            return False
    
    def hash_password(self, password: str) -> Tuple[str, str]:
        """
        Gera hash seguro da senha com salt
        
        Args:
            password: Senha em texto plano
        
        Returns:
            Tupla (hash, salt)
        """
        # Gerar salt aleatório
        salt = secrets.token_hex(SALT_LENGTH)
        
        # Gerar hash com salt
        password_hash = self.hash_password_with_salt(password, salt)
        
        return password_hash, salt
    
    def hash_password_with_salt(self, password: str, salt: str) -> str:
        """
        Gera hash da senha usando PBKDF2
        
        Args:
            password: Senha em texto plano
            salt: Salt para o hash
        
        Returns:
            Hash da senha
        """
        # Usar PBKDF2 com SHA256
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # 100,000 iterações
        )
        return password_hash.hex()
    
    # ========================================================================
    # CONTROLE DE TENTATIVAS DE LOGIN
    # ========================================================================
    
    def is_user_locked(self, username: str) -> bool:
        """Verifica se usuário está bloqueado por excesso de tentativas"""
        if username not in self.login_attempts:
            return False
        
        attempts_data = self.login_attempts[username]
        
        if attempts_data['count'] < MAX_LOGIN_ATTEMPTS:
            return False
        
        # Verificar se tempo de bloqueio expirou
        lockout_time = attempts_data['last_attempt']
        time_passed = datetime.datetime.now() - lockout_time
        
        if time_passed.total_seconds() / 60 >= LOCKOUT_DURATION_MINUTES:
            # Bloqueio expirou, limpar tentativas
            self.clear_login_attempts(username)
            return False
        
        return True
    
    def get_lockout_remaining_time(self, username: str) -> int:
        """Retorna tempo restante de bloqueio em minutos"""
        if username not in self.login_attempts:
            return 0
        
        lockout_time = self.login_attempts[username]['last_attempt']
        time_passed = datetime.datetime.now() - lockout_time
        remaining = LOCKOUT_DURATION_MINUTES - (time_passed.total_seconds() / 60)
        
        return max(0, int(remaining))
    
    def register_failed_attempt(self, username: str):
        """Registra tentativa de login falha"""
        if username not in self.login_attempts:
            self.login_attempts[username] = {'count': 0, 'last_attempt': datetime.datetime.now()}
        
        self.login_attempts[username]['count'] += 1
        self.login_attempts[username]['last_attempt'] = datetime.datetime.now()
        
        print(f"⚠️  Tentativa de login falha para '{username}': {self.login_attempts[username]['count']}/{MAX_LOGIN_ATTEMPTS}")
    
    def get_login_attempts(self, username: str) -> int:
        """Retorna número de tentativas de login"""
        return self.login_attempts.get(username, {}).get('count', 0)
    
    def clear_login_attempts(self, username: str):
        """Limpa tentativas de login"""
        if username in self.login_attempts:
            del self.login_attempts[username]
    
    # ========================================================================
    # VALIDAÇÃO DE SENHAS
    # ========================================================================
    
    def validate_password_strength(self, password: str) -> Tuple[bool, str]:
        """
        Valida força da senha
        
        Args:
            password: Senha a ser validada
        
        Returns:
            Tupla (válida, mensagem)
        """
        errors = []
        
        # Comprimento
        if len(password) < MIN_PASSWORD_LENGTH:
            errors.append(f"Senha deve ter no mínimo {MIN_PASSWORD_LENGTH} caracteres")
        
        if len(password) > MAX_PASSWORD_LENGTH:
            errors.append(f"Senha deve ter no máximo {MAX_PASSWORD_LENGTH} caracteres")
        
        # Letra maiúscula
        if REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            errors.append("Senha deve conter ao menos uma letra maiúscula")
        
        # Letra minúscula
        if REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            errors.append("Senha deve conter ao menos uma letra minúscula")
        
        # Números
        if REQUIRE_NUMBERS and not re.search(r'\d', password):
            errors.append("Senha deve conter ao menos um número")
        
        # Caracteres especiais
        if REQUIRE_SPECIAL_CHARS and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Senha deve conter ao menos um caractere especial (!@#$%^&*...)")
        
        # Senhas comuns
        common_passwords = ['123456', 'password', '12345678', 'qwerty', 'abc123', 
                          '111111', '123123', 'admin', 'letmein', 'welcome']
        if password.lower() in common_passwords:
            errors.append("Senha muito comum, escolha uma senha mais forte")
        
        if errors:
            return False, "\n".join(errors)
        
        return True, "Senha válida"
    
    def calculate_password_strength(self, password: str) -> Tuple[int, str]:
        """
        Calcula força da senha (0-100)
        
        Args:
            password: Senha a avaliar
        
        Returns:
            Tupla (pontuação, classificação)
        """
        score = 0
        
        # Comprimento
        if len(password) >= 8:
            score += 20
        if len(password) >= 12:
            score += 10
        if len(password) >= 16:
            score += 10
        
        # Variedade de caracteres
        if re.search(r'[a-z]', password):
            score += 10
        if re.search(r'[A-Z]', password):
            score += 10
        if re.search(r'\d', password):
            score += 10
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            score += 15
        
        # Padrões
        if not re.search(r'(.)\1{2,}', password):  # Sem repetições
            score += 10
        if not re.search(r'(012|123|234|345|456|567|678|789|890)', password):  # Sem sequências
            score += 5
        
        # Classificação
        if score >= 80:
            classification = "Muito Forte"
        elif score >= 60:
            classification = "Forte"
        elif score >= 40:
            classification = "Média"
        elif score >= 20:
            classification = "Fraca"
        else:
            classification = "Muito Fraca"
        
        return score, classification
    
    # ========================================================================
    # VALIDAÇÃO DE USUÁRIO
    # ========================================================================
    
    def validate_username(self, username: str) -> Tuple[bool, str]:
        """
        Valida nome de usuário
        
        Args:
            username: Nome de usuário
        
        Returns:
            Tupla (válido, mensagem)
        """
        # Comprimento
        if len(username) < 3:
            return False, "Usuário deve ter no mínimo 3 caracteres"
        
        if len(username) > 50:
            return False, "Usuário deve ter no máximo 50 caracteres"
        
        # Caracteres permitidos (alfanuméricos, underscore, hífen)
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            return False, "Usuário deve conter apenas letras, números, _ ou -"
        
        # Não pode começar com número
        if username[0].isdigit():
            return False, "Usuário não pode começar com número"
        
        return True, "Usuário válido"
    
    def username_exists(self, username: str) -> bool:
        """Verifica se usuário já existe"""
        try:
            user = self.repository.find_by_username(username)
            return user is not None
        except:
            return False
    
    # ========================================================================
    # GERENCIAMENTO DE USUÁRIOS
    # ========================================================================
    
    def create_user(self, username: str, password: str, nome_completo: str, 
                   email: str, nivel_acesso: str = 'operador') -> Tuple[bool, str]:
        """
        Cria novo usuário
        
        Args:
            username: Nome de usuário
            password: Senha
            nome_completo: Nome completo
            email: Email
            nivel_acesso: Nível de acesso
        
        Returns:
            Tupla (sucesso, mensagem)
        """
        try:
            # Validar username
            valid, message = self.validate_username(username)
            if not valid:
                return False, message
            
            # Verificar se usuário já existe
            if self.username_exists(username):
                return False, "Nome de usuário já existe"
            
            # Validar senha
            valid, message = self.validate_password_strength(password)
            if not valid:
                return False, message
            
            # Validar email
            if not self.validate_email(email):
                return False, "Email inválido"
            
            # Validar nível de acesso
            if nivel_acesso not in ACCESS_LEVELS:
                return False, f"Nível de acesso inválido. Opções: {', '.join(ACCESS_LEVELS.keys())}"
            
            # Gerar hash da senha
            password_hash, salt = self.hash_password(password)
            
            # Criar usuário no banco
            user_data = {
                'username': username,
                'password_hash': password_hash,
                'salt': salt,
                'nome_completo': nome_completo,
                'email': email,
                'nivel_acesso': nivel_acesso,
                'ativo': True,
                'created_at': datetime.datetime.now()
            }
            
            success = self.repository.create(user_data)
            
            if success:
                print(f"✅ Usuário '{username}' criado com sucesso")
                return True, "Usuário criado com sucesso"
            else:
                return False, "Erro ao criar usuário no banco de dados"
            
        except Exception as e:
            print(f"❌ Erro ao criar usuário: {e}")
            return False, f"Erro interno: {str(e)}"
    
    def change_password(self, username: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        """
        Altera senha do usuário
        
        Args:
            username: Nome de usuário
            old_password: Senha atual
            new_password: Nova senha
        
        Returns:
            Tupla (sucesso, mensagem)
        """
        try:
            # Verificar senha atual
            valid, user, message = self.verify_credentials(username, old_password)
            if not valid:
                return False, "Senha atual incorreta"
            
            # Validar nova senha
            valid, message = self.validate_password_strength(new_password)
            if not valid:
                return False, message
            
            # Verificar se nova senha é diferente da antiga
            if old_password == new_password:
                return False, "Nova senha deve ser diferente da senha atual"
            
            # Gerar novo hash
            password_hash, salt = self.hash_password(new_password)
            
            # Atualizar no banco
            success = self.repository.update_password(username, password_hash, salt)
            
            if success:
                print(f"✅ Senha alterada para usuário '{username}'")
                return True, "Senha alterada com sucesso"
            else:
                return False, "Erro ao atualizar senha no banco de dados"
            
        except Exception as e:
            print(f"❌ Erro ao alterar senha: {e}")
            return False, f"Erro interno: {str(e)}"
    
    def reset_password(self, username: str, new_password: str, admin_username: str) -> Tuple[bool, str]:
        """
        Reseta senha do usuário (apenas admin)
        
        Args:
            username: Usuário que terá senha resetada
            new_password: Nova senha
            admin_username: Usuário administrador executando a ação
        
        Returns:
            Tupla (sucesso, mensagem)
        """
        try:
            # Verificar se admin tem permissão
            admin_user = self.repository.find_by_username(admin_username)
            if not admin_user or admin_user.get('nivel_acesso') != 'admin':
                return False, "Apenas administradores podem resetar senhas"
            
            # Validar nova senha
            valid, message = self.validate_password_strength(new_password)
            if not valid:
                return False, message
            
            # Gerar novo hash
            password_hash, salt = self.hash_password(new_password)
            
            # Atualizar no banco
            success = self.repository.update_password(username, password_hash, salt)
            
            if success:
                print(f"✅ Senha resetada para usuário '{username}' por '{admin_username}'")
                return True, "Senha resetada com sucesso"
            else:
                return False, "Erro ao resetar senha no banco de dados"
            
        except Exception as e:
            print(f"❌ Erro ao resetar senha: {e}")
            return False, f"Erro interno: {str(e)}"
    
    # ========================================================================
    # MÉTODOS AUXILIARES
    # ========================================================================
    
    def validate_email(self, email: str) -> bool:
        """Valida formato de email"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def get_safe_user_data(self, user: Dict) -> Dict:
        """Remove informações sensíveis dos dados do usuário"""
        safe_data = user.copy()
        
        # Remover campos sensíveis
        safe_data.pop('password_hash', None)
        safe_data.pop('salt', None)
        
        return safe_data
    
    def update_last_login(self, username: str):
        """Atualiza timestamp do último login"""
        try:
            self.repository.update_last_login(username, datetime.datetime.now())
            print(f"📅 Último login atualizado para '{username}'")
        except Exception as e:
            print(f"⚠️  Erro ao atualizar último login: {e}")
    
    def deactivate_user(self, username: str, admin_username: str) -> Tuple[bool, str]:
        """
        Desativa usuário (apenas admin)
        
        Args:
            username: Usuário a ser desativado
            admin_username: Admin executando a ação
        
        Returns:
            Tupla (sucesso, mensagem)
        """
        try:
            # Verificar permissão de admin
            admin_user = self.repository.find_by_username(admin_username)
            if not admin_user or admin_user.get('nivel_acesso') != 'admin':
                return False, "Apenas administradores podem desativar usuários"
            
            # Não permitir desativar a si mesmo
            if username == admin_username:
                return False, "Você não pode desativar sua própria conta"
            
            # Desativar usuário
            success = self.repository.deactivate_user(username)
            
            if success:
                print(f"✅ Usuário '{username}' desativado por '{admin_username}'")
                return True, "Usuário desativado com sucesso"
            else:
                return False, "Erro ao desativar usuário"
            
        except Exception as e:
            print(f"❌ Erro ao desativar usuário: {e}")
            return False, f"Erro interno: {str(e)}"
    
    def activate_user(self, username: str, admin_username: str) -> Tuple[bool, str]:
        """Ativa usuário desativado"""
        try:
            # Verificar permissão
            admin_user = self.repository.find_by_username(admin_username)
            if not admin_user or admin_user.get('nivel_acesso') != 'admin':
                return False, "Apenas administradores podem ativar usuários"
            
            success = self.repository.activate_user(username)
            
            if success:
                print(f"✅ Usuário '{username}' ativado por '{admin_username}'")
                return True, "Usuário ativado com sucesso"
            else:
                return False, "Erro ao ativar usuário"
            
        except Exception as e:
            print(f"❌ Erro ao ativar usuário: {e}")
            return False, f"Erro interno: {str(e)}"
    
    def get_user_info(self, username: str) -> Optional[Dict]:
        """Retorna informações do usuário (sem dados sensíveis)"""
        try:
            user = self.repository.find_by_username(username)
            if user:
                return self.get_safe_user_data(user)
            return None
        except Exception as e:
            print(f"❌ Erro ao buscar usuário: {e}")
            return None
    
    def list_all_users(self, admin_username: str) -> Tuple[bool, list]:
        """Lista todos os usuários (apenas admin)"""
        try:
            # Verificar permissão
            admin_user = self.repository.find_by_username(admin_username)
            if not admin_user or admin_user.get('nivel_acesso') != 'admin':
                return False, []
            
            users = self.repository.find_all()
            safe_users = [self.get_safe_user_data(user) for user in users]
            
            return True, safe_users
            
        except Exception as e:
            print(f"❌ Erro ao listar usuários: {e}")
            return False, []


# ============================================================================
# FUNÇÕES DE CONVENIÊNCIA (COMPATIBILIDADE)
# ============================================================================

def verify_credentials(username: str, password: str) -> bool:
    """
    Função de conveniência para verificação de credenciais (compatibilidade)
    
    Args:
        username: Nome de usuário
        password: Senha
    
    Returns:
        True se credenciais válidas
    """
    """
    Compat wrapper that accepts either a username (str) or a user object/dict.

    If `username_or_user` is a str, it will call the manager to authenticate by
    username. If it's a dict or object with password_hash/salt, it will verify
    the plain password against the stored hash.
    """
    manager = CredentialsManager()
    # If a username string is provided, use manager.verify_credentials
    if isinstance(username, str):
        success, user, message = manager.verify_credentials(username, password)
        return success

    # Otherwise assume a user-like object/dict containing password_hash and optional salt
    try:
        if isinstance(username, dict):
            stored_hash = username.get('password_hash')
            salt = username.get('salt', '')
        else:
            # object with attributes
            stored_hash = getattr(username, 'password_hash', None)
            salt = getattr(username, 'salt', '')

        if not stored_hash:
            return False

        return manager.verify_password(password, stored_hash, salt)
    except Exception:
        return False


def hash_password(password: str) -> str:
    """Convenience wrapper that returns only the password hash (no salt).

    Many callers in the codebase expect a single hash string; internal
    CredentialsManager.hash_password returns (hash, salt). This function
    returns just the hash to preserve backward compatibility.
    """
    manager = CredentialsManager()
    password_hash, salt = manager.hash_password(password)
    return password_hash


# ============================================================================
# TESTES E EXEMPLOS
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🔐 SISTEMA DE AUTENTICAÇÃO - SENTRY.INC")
    print("=" * 70)
    
    manager = CredentialsManager()
    
    # Exemplo 1: Criar usuário
    print("\n📝 Teste 1: Criar novo usuário")
    success, message = manager.create_user(
        username="admin",
        password="Admin@123",
        nome_completo="Administrador do Sistema",
        email="admin@sentry.inc",
        nivel_acesso="admin"
    )
    print(f"   Resultado: {message}")
    
    # Exemplo 2: Verificar credenciais
    print("\n🔑 Teste 2: Verificar credenciais")
    success, user, message = manager.verify_credentials("admin", "Admin@123")
    print(f"   Sucesso: {success}")
    print(f"   Mensagem: {message}")
    if user:
        print(f"   Usuário: {user.get('nome_completo')}")
    
    # Exemplo 3: Força da senha
    print("\n💪 Teste 3: Calcular força da senha")
    score, classification = manager.calculate_password_strength("Admin@123")
    print(f"   Pontuação: {score}/100")
    print(f"   Classificação: {classification}")
    
    print("\n" + "=" * 70)