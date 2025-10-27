# LOGISICA/sentry/database/repositories/user_repo.py

import sqlite3
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from contextlib import contextmanager
from pathlib import Path

from sentry.core.entities.user import User  # Assumindo que existe uma entidade User
from sentry.core.use_cases.auth import (  # Assumindo casos de uso relacionados
    UserNotFoundError,
    InvalidCredentialsError,
)

# Configuração de logging
logger = logging.getLogger(__name__)


class DatabaseConnectionError(Exception):
    """Exceção para erros de conexão com o banco de dados."""
    pass


class UserRepositoryError(Exception):
    """Exceção base para erros do repositório de usuários."""
    pass


class UserNotFoundError(UserRepositoryError):
    """Exceção quando usuário não é encontrado."""
    pass


class DuplicateUserError(UserRepositoryError):
    """Exceção quando usuário já existe."""
    pass


class UserRepository:
    """
    Repositório para operações de banco de dados com usuários.
    
    Implementa padrão Repository para abstrair o acesso a dados
    e fornecer operações robustas com tratamento de erros.
    """
    
    def __init__(self, db_path: str = "data/database/sentry.db"):
        self.db_path = db_path
        self._ensure_database_dir()
        self._create_tables()
    
    def _ensure_database_dir(self):
        """Garante que o diretório do banco de dados existe."""
        db_path = Path(self.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug("Diretório do banco de dados verificado: %s", db_path.parent)
    
    @contextmanager
    def _get_connection(self):
        """
        Context manager para gerenciar conexões com o banco.
        
        Yields:
            sqlite3.Connection: Conexão com o banco de dados
            
        Raises:
            DatabaseConnectionError: Se não for possível conectar ao banco
        """
        conn = None
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,  # Timeout de 30 segundos
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            conn.row_factory = sqlite3.Row  # Para acessar colunas por nome
            conn.execute("PRAGMA foreign_keys = ON")  # Ativa chaves estrangeiras
            
            # Configurações adicionais para melhor performance
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute("PRAGMA cache_size = -64000")  # 64MB cache
            
            yield conn
        except sqlite3.Error as e:
            logger.error("Erro de conexão com o banco de dados: %s", e)
            raise DatabaseConnectionError(f"Não foi possível conectar ao banco de dados: {str(e)}") from e
        finally:
            if conn:
                conn.close()
    
    def _create_tables(self):
        """Cria as tabelas necessárias se não existirem."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabela principal de usuários
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    cpf TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    -- Informações de autenticação
                    password_hash TEXT,
                    salt TEXT,
                    -- Informações de contato
                    phone TEXT,
                    -- Endereço
                    street TEXT,
                    number TEXT,
                    complement TEXT,
                    neighborhood TEXT,
                    city TEXT,
                    state TEXT,
                    zip_code TEXT,
                    -- Metadados
                    status TEXT DEFAULT 'active',
                    last_login TIMESTAMP,
                    failed_login_attempts INTEGER DEFAULT 0,
                    lock_until TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    -- Índices e constraints
                    CONSTRAINT chk_email CHECK (email LIKE '%_@_%.%'),
                    CONSTRAINT chk_role CHECK (role IN ('admin', 'manager', 'user', 'operator')),
                    CONSTRAINT chk_status CHECK (status IN ('active', 'inactive', 'locked', 'suspended'))
                )
            """)
            
            # Tabela para histórico de login
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_login_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    login_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip_address TEXT,
                    user_agent TEXT,
                    success BOOLEAN NOT NULL,
                    failure_reason TEXT,
                    -- Chaves estrangeiras
                    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Tabela para tokens de redefinição de senha
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    used BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    -- Chaves estrangeiras
                    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Índices para melhor performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_cpf ON users(cpf)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_login_history_user ON user_login_history(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_login_history_timestamp ON user_login_history(login_timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_reset_tokens_token ON password_reset_tokens(token)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_reset_tokens_user ON password_reset_tokens(user_id)")
            
            conn.commit()
            logger.info("Tabelas de usuários verificadas/criadas com sucesso")
    
    def _row_to_entity(self, row: sqlite3.Row) -> User:
        """
        Converte uma linha do banco para entidade User.
        
        Args:
            row: Linha do banco de dados
            
        Returns:
            Instância de User
        """
        # Campos básicos
        user_data = {
            'id': row['id'],
            'email': row['email'],
            'cpf': row['cpf'],
            'name': row['name'],
            'role': row['role']
        }
        
        # Campos opcionais
        optional_fields = [
            'phone', 'street', 'number', 'complement', 'neighborhood',
            'city', 'state', 'zip_code', 'status', 'last_login',
            'failed_login_attempts', 'lock_until', 'created_at', 'updated_at'
        ]
        
        for field in optional_fields:
            if row[field] is not None:
                user_data[field] = row[field]
        
        # Endereço (se disponível)
        address_fields = ['street', 'number', 'complement', 'neighborhood', 'city', 'state', 'zip_code']
        address_data = {}
        
        for field in address_fields:
            if row[field] is not None:
                address_data[field] = row[field]
        
        if address_data:
            user_data['address'] = address_data
        
        return User(**user_data)
    
    def find_by_email_and_cpf(self, email: str, cpf: str) -> Optional[User]:
        """
        Busca usuário por email e CPF.
        
        Args:
            email: Email do usuário
            cpf: CPF do usuário
            
        Returns:
            Instância de User se encontrado, None caso contrário
            
        Raises:
            DatabaseConnectionError: Em caso de erro de conexão
        """
        logger.debug("Buscando usuário por email: %s e CPF: %s", email, cpf)
        
        if not email or not cpf:
            logger.warning("Email ou CPF vazios na busca de usuário")
            return None
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    SELECT * FROM users 
                    WHERE email = ? AND cpf = ? AND status = 'active'
                """, (email.strip().lower(), cpf.strip()))
                
                row = cursor.fetchone()
                
                if row:
                    user = self._row_to_entity(row)
                    logger.debug("Usuário encontrado: %s (ID: %s)", user.email, user.id)
                    return user
                else:
                    logger.debug("Nenhum usuário encontrado com email %s e CPF %s", email, cpf)
                    return None
                    
            except sqlite3.Error as e:
                logger.error("Erro ao buscar usuário por email %s e CPF %s: %s", email, cpf, e)
                raise DatabaseConnectionError(f"Erro ao buscar usuário: {str(e)}") from e
    
    def find_by_email(self, email: str) -> Optional[User]:
        """
        Busca usuário apenas por email.
        
        Args:
            email: Email do usuário
            
        Returns:
            Instância de User se encontrado, None caso contrário
        """
        logger.debug("Buscando usuário por email: %s", email)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_entity(row)
                return None
                    
            except sqlite3.Error as e:
                logger.error("Erro ao buscar usuário por email %s: %s", email, e)
                raise DatabaseConnectionError(f"Erro ao buscar usuário: {str(e)}") from e
    
    def find_by_cpf(self, cpf: str) -> Optional[User]:
        """
        Busca usuário apenas por CPF.
        
        Args:
            cpf: CPF do usuário
            
        Returns:
            Instância de User se encontrado, None caso contrário
        """
        logger.debug("Buscando usuário por CPF: %s", cpf)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("SELECT * FROM users WHERE cpf = ?", (cpf.strip(),))
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_entity(row)
                return None
                    
            except sqlite3.Error as e:
                logger.error("Erro ao buscar usuário por CPF %s: %s", cpf, e)
                raise DatabaseConnectionError(f"Erro ao buscar usuário: {str(e)}") from e
    
    def find_by_id(self, user_id: int) -> Optional[User]:
        """
        Busca usuário por ID.
        
        Args:
            user_id: ID do usuário
            
        Returns:
            Instância de User se encontrado, None caso contrário
        """
        logger.debug("Buscando usuário por ID: %s", user_id)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_entity(row)
                return None
                    
            except sqlite3.Error as e:
                logger.error("Erro ao buscar usuário por ID %s: %s", user_id, e)
                raise DatabaseConnectionError(f"Erro ao buscar usuário: {str(e)}") from e
    
    def save(self, user: User) -> User:
        """
        Salva um usuário no banco de dados.
        
        Args:
            user: Instância de User a ser salva
            
        Returns:
            User salvo com ID atualizado
            
        Raises:
            DuplicateUserError: Se já existir usuário com mesmo email ou CPF
            DatabaseConnectionError: Em caso de erro de conexão
        """
        logger.info("Salvando usuário: %s (Email: %s)", user.name, user.email)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                address = getattr(user, 'address', {})
                
                cursor.execute("""
                    INSERT INTO users (
                        email, cpf, name, role, phone,
                        street, number, complement, neighborhood, city, state, zip_code,
                        status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user.email.strip().lower(),
                    user.cpf.strip(),
                    user.name.strip(),
                    getattr(user, 'role', 'user'),
                    getattr(user, 'phone', None),
                    address.get('street'),
                    address.get('number'),
                    address.get('complement'),
                    address.get('neighborhood'),
                    address.get('city'),
                    address.get('state'),
                    address.get('zip_code'),
                    getattr(user, 'status', 'active')
                ))
                
                conn.commit()
                user.id = cursor.lastrowid
                
                logger.info(
                    "Usuário salvo com sucesso: %s (ID: %s)",
                    user.name, user.id
                )
                
                return user
                
            except sqlite3.IntegrityError as e:
                if "UNIQUE constraint failed: users.email" in str(e):
                    raise DuplicateUserError(f"Já existe um usuário com o email: {user.email}")
                elif "UNIQUE constraint failed: users.cpf" in str(e):
                    raise DuplicateUserError(f"Já existe um usuário com o CPF: {user.cpf}")
                else:
                    logger.error("Erro de integridade ao salvar usuário: %s", e)
                    raise DatabaseConnectionError(f"Erro de integridade no banco de dados: {str(e)}") from e
            
            except sqlite3.Error as e:
                logger.error("Erro ao salvar usuário: %s", e)
                raise DatabaseConnectionError(f"Erro ao salvar usuário: {str(e)}") from e
    
    def update(self, user: User) -> User:
        """
        Atualiza um usuário existente.
        
        Args:
            user: Instância de User com dados atualizados
            
        Returns:
            User atualizado
            
        Raises:
            UserNotFoundError: Se o usuário não for encontrado
            DatabaseConnectionError: Em caso de erro de conexão
        """
        logger.info("Atualizando usuário ID: %s", user.id)
        
        if not user.id:
            raise UserNotFoundError("Usuário não possui ID para atualização")
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                address = getattr(user, 'address', {})
                
                cursor.execute("""
                    UPDATE users SET
                        email = ?, cpf = ?, name = ?, role = ?, phone = ?,
                        street = ?, number = ?, complement = ?, neighborhood = ?, city = ?, state = ?, zip_code = ?,
                        status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    user.email.strip().lower(),
                    user.cpf.strip(),
                    user.name.strip(),
                    getattr(user, 'role', 'user'),
                    getattr(user, 'phone', None),
                    address.get('street'),
                    address.get('number'),
                    address.get('complement'),
                    address.get('neighborhood'),
                    address.get('city'),
                    address.get('state'),
                    address.get('zip_code'),
                    getattr(user, 'status', 'active'),
                    user.id
                ))
                
                if cursor.rowcount == 0:
                    raise UserNotFoundError(f"Usuário com ID {user.id} não encontrado")
                
                conn.commit()
                logger.info("Usuário atualizado com sucesso: ID %s", user.id)
                
                return user
                
            except sqlite3.IntegrityError as e:
                if "UNIQUE constraint failed: users.email" in str(e):
                    raise DuplicateUserError(f"Já existe outro usuário com o email: {user.email}")
                elif "UNIQUE constraint failed: users.cpf" in str(e):
                    raise DuplicateUserError(f"Já existe outro usuário com o CPF: {user.cpf}")
                else:
                    logger.error("Erro de integridade ao atualizar usuário: %s", e)
                    raise DatabaseConnectionError(f"Erro de integridade no banco de dados: {str(e)}") from e
            
            except sqlite3.Error as e:
                logger.error("Erro ao atualizar usuário ID %s: %s", user.id, e)
                raise DatabaseConnectionError(f"Erro ao atualizar usuário: {str(e)}") from e
    
    def record_login_attempt(self, user_id: int, success: bool, 
                           ip_address: Optional[str] = None, 
                           user_agent: Optional[str] = None,
                           failure_reason: Optional[str] = None):
        """
        Registra uma tentativa de login no histórico.
        
        Args:
            user_id: ID do usuário
            success: Se o login foi bem-sucedido
            ip_address: Endereço IP do cliente
            user_agent: User Agent do cliente
            failure_reason: Motivo da falha (se houver)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT INTO user_login_history (
                        user_id, ip_address, user_agent, success, failure_reason
                    ) VALUES (?, ?, ?, ?, ?)
                """, (user_id, ip_address, user_agent, success, failure_reason))
                
                # Atualiza contador de tentativas falhas e último login
                if success:
                    cursor.execute("""
                        UPDATE users 
                        SET last_login = CURRENT_TIMESTAMP, failed_login_attempts = 0, lock_until = NULL
                        WHERE id = ?
                    """, (user_id,))
                else:
                    cursor.execute("""
                        UPDATE users 
                        SET failed_login_attempts = failed_login_attempts + 1
                        WHERE id = ?
                    """, (user_id,))
                
                conn.commit()
                logger.debug("Tentativa de login registrada para usuário ID: %s", user_id)
                
            except sqlite3.Error as e:
                logger.error("Erro ao registrar tentativa de login: %s", e)
                # Não levanta exceção para não afetar o fluxo principal
    
    def get_login_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retorna o histórico de login de um usuário.
        
        Args:
            user_id: ID do usuário
            limit: Número máximo de registros
            
        Returns:
            Lista de registros de login
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    SELECT * FROM user_login_history 
                    WHERE user_id = ? 
                    ORDER BY login_timestamp DESC 
                    LIMIT ?
                """, (user_id, limit))
                
                rows = cursor.fetchall()
                history = []
                
                for row in rows:
                    history.append({
                        'id': row['id'],
                        'user_id': row['user_id'],
                        'login_timestamp': row['login_timestamp'],
                        'ip_address': row['ip_address'],
                        'user_agent': row['user_agent'],
                        'success': bool(row['success']),
                        'failure_reason': row['failure_reason']
                    })
                
                return history
                    
            except sqlite3.Error as e:
                logger.error("Erro ao buscar histórico de login: %s", e)
                raise DatabaseConnectionError(f"Erro ao buscar histórico: {str(e)}") from e


# Exemplo de uso
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    try:
        repo = UserRepository()
        
        # Teste de busca
        user = repo.find_by_email_and_cpf("admin@logisica.com", "12345678901")
        if user:
            print(f"Usuário encontrado: {user.name} ({user.role})")
        else:
            print("Usuário não encontrado")
        
    except Exception as e:
        print(f"Erro: {e}")