# LOGISICA/sentry/infra/database/database.py

import sqlite3
import logging
import os
from pathlib import Path
from typing import Generator, Optional, Any
from contextlib import contextmanager
from datetime import datetime

# Configuração de logging
logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Exceção base para erros de banco de dados."""
    pass


class DatabaseInitializationError(DatabaseError):
    """Exceção para erros durante a inicialização do banco."""
    pass


class DatabaseConnectionError(DatabaseError):
    """Exceção para erros de conexão com o banco."""
    pass


# --- Configuração do Caminho do Banco de Dados ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent 
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_DIR = DATA_DIR / "database"
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATABASE_DIR / "sentry.db"
DB_BACKUP_DIR = DATABASE_DIR / "backups"
DB_BACKUP_DIR.mkdir(exist_ok=True)

# Constantes do sistema
ADMIN_ACCESS_LEVEL = 3
USER_ACCESS_LEVELS = {
    'operator': 1,
    'supervisor': 2, 
    'admin': 3
}

# Configurações do banco
DB_CONFIG = {
    'timeout': 30.0,
    'detect_types': sqlite3.PARSE_DECLTYPES,
    'check_same_thread': False
}


class DatabaseManager:
    """
    Gerenciador centralizado para operações de banco de dados.
    
    Fornece:
    - Conexões gerenciadas automaticamente
    - Inicialização do esquema
    - Backup e recuperação
    - Operações de manutenção
    """
    
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._ensure_database_dir()
    
    def _ensure_database_dir(self):
        """Garante que o diretório do banco de dados existe."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            logger.debug("Diretório do banco verificado: %s", self.db_path.parent)
        except Exception as e:
            raise DatabaseInitializationError(f"Erro ao criar diretório do banco: {e}")
    
    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Context manager para gerenciar conexões com o banco.
        
        Yields:
            sqlite3.Connection: Conexão configurada com o banco
            
        Raises:
            DatabaseConnectionError: Se não for possível conectar
        """
        conn = None
        try:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=DB_CONFIG['timeout'],
                detect_types=DB_CONFIG['detect_types'],
                check_same_thread=DB_CONFIG['check_same_thread']
            )
            
            # Configurações de performance e funcionalidade
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute("PRAGMA cache_size = -64000")  # 64MB cache
            conn.execute("PRAGMA busy_timeout = 5000")  # 5 segundos timeout
            conn.execute("PRAGMA optimize")  # Otimização automática
            
            conn.row_factory = sqlite3.Row
            
            logger.debug("Conexão com banco de dados estabelecida")
            yield conn
            
        except sqlite3.Error as e:
            logger.error("Erro de conexão com o banco: %s", e)
            raise DatabaseConnectionError(f"Falha na conexão com o banco: {str(e)}") from e
        finally:
            if conn:
                try:
                    conn.close()
                    logger.debug("Conexão com banco de dados fechada")
                except sqlite3.Error as e:
                    logger.warning("Erro ao fechar conexão: %s", e)
    
    def initialize_database(self, force_recreate: bool = False):
        """
        Inicializa o banco de dados com todas as tabelas necessárias.
        
        Args:
            force_recreate: Se True, recria todas as tabelas (PERDE DADOS!)
            
        Raises:
            DatabaseInitializationError: Em caso de erro na inicialização
        """
        logger.info("Inicializando banco de dados em: %s", self.db_path)
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if force_recreate:
                    logger.warning("Recriando todas as tabelas (dados serão perdidos!)")
                    self._drop_all_tables(cursor)
                
                # Criar todas as tabelas do sistema
                self._create_users_table(cursor)
                self._create_carriers_table(cursor)
                self._create_vehicles_table(cursor)
                self._create_merchandise_table(cursor)
                self._create_access_logs_table(cursor)
                self._create_audit_logs_table(cursor)
                self._create_system_config_table(cursor)
                
                # Criar índices para performance
                self._create_indexes(cursor)
                
                # Inserir dados iniciais
                self._insert_initial_data(cursor)
                
                conn.commit()
                logger.info("✅ Banco de dados inicializado com sucesso")
                
        except sqlite3.Error as e:
            logger.error("Erro na inicialização do banco: %s", e)
            raise DatabaseInitializationError(f"Falha na inicialização: {str(e)}") from e
    
    def _drop_all_tables(self, cursor: sqlite3.Cursor):
        """Remove todas as tabelas existentes (uso cuidadoso!)."""
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            for table in tables:
                if table != "sqlite_sequence":  # Não remove sequência de auto-increment
                    cursor.execute(f"DROP TABLE IF EXISTS {table}")
                    logger.debug("Tabela removida: %s", table)
                    
        except sqlite3.Error as e:
            logger.error("Erro ao remover tabelas: %s", e)
            raise
    
    def _create_users_table(self, cursor: sqlite3.Cursor):
        """Cria tabela de usuários."""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                cpf TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL DEFAULT 'operator',
                phone TEXT,
                -- Endereço
                street TEXT,
                number TEXT,
                complement TEXT,
                neighborhood TEXT,
                city TEXT,
                state TEXT,
                zip_code TEXT,
                -- Segurança
                failed_login_attempts INTEGER DEFAULT 0,
                lock_until TIMESTAMP,
                last_login TIMESTAMP,
                must_change_password BOOLEAN DEFAULT FALSE,
                -- Metadados
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                -- Constraints
                CONSTRAINT chk_role CHECK (role IN ('admin', 'supervisor', 'operator')),
                CONSTRAINT chk_status CHECK (status IN ('active', 'inactive', 'locked'))
            )
        """)
    
    def _create_carriers_table(self, cursor: sqlite3.Cursor):
        """Cria tabela de transportadoras."""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS carriers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                cnpj TEXT UNIQUE NOT NULL,
                responsible_name TEXT,
                contact_phone TEXT,
                email TEXT,
                -- Endereço
                street TEXT,
                number TEXT,
                complement TEXT,
                neighborhood TEXT,
                city TEXT,
                state TEXT,
                zip_code TEXT,
                -- Informações adicionais
                operating_regions TEXT,
                vehicle_types TEXT,
                capacity_kg REAL,
                insurance_value REAL,
                notes TEXT,
                -- Metadados
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                -- Constraints
                CONSTRAINT chk_status CHECK (status IN ('active', 'inactive', 'suspended'))
            )
        """)
    
    def _create_vehicles_table(self, cursor: sqlite3.Cursor):
        """Cria tabela de veículos."""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plate TEXT UNIQUE NOT NULL,
                model TEXT NOT NULL,
                color TEXT,
                carrier_cnpj TEXT,
                -- Informações adicionais
                type TEXT DEFAULT 'other',
                year INTEGER,
                chassis_number TEXT,
                fuel_type TEXT,
                capacity_kg REAL,
                capacity_m3 REAL,
                insurance_policy TEXT,
                insurance_expiry TIMESTAMP,
                -- Metadados de manutenção
                last_maintenance TIMESTAMP,
                next_maintenance TIMESTAMP,
                maintenance_notes TEXT,
                -- Metadados do sistema
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                registered_by TEXT,
                -- Constraints
                CONSTRAINT chk_year CHECK (year IS NULL OR year >= 1900),
                CONSTRAINT chk_status CHECK (status IN ('active', 'inactive', 'maintenance', 'suspended'))
            )
        """)
    
    def _create_merchandise_table(self, cursor: sqlite3.Cursor):
        """Cria tabela de mercadorias."""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS merchandise (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                weight REAL,
                volume REAL,
                vehicle_plate TEXT,
                notes TEXT,
                -- Informações adicionais
                category TEXT DEFAULT 'other',
                value REAL,
                insurance_required BOOLEAN DEFAULT FALSE,
                fragile BOOLEAN DEFAULT FALSE,
                hazardous BOOLEAN DEFAULT FALSE,
                special_handling TEXT,
                storage_temperature TEXT,
                -- Metadados
                status TEXT DEFAULT 'registered',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                registered_by TEXT,
                carrier_id INTEGER,
                -- Constraints
                CONSTRAINT chk_weight CHECK (weight IS NULL OR weight >= 0),
                CONSTRAINT chk_status CHECK (status IN ('registered', 'in_transit', 'delivered', 'cancelled')),
                CONSTRAINT fk_carrier FOREIGN KEY (carrier_id) REFERENCES carriers(id)
            )
        """)
    
    def _create_access_logs_table(self, cursor: sqlite3.Cursor):
        """Cria tabela de logs de acesso."""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS access_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_plate TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                -- Informações do veículo
                vehicle_type TEXT,
                vehicle_model TEXT,
                vehicle_color TEXT,
                -- Informações do motorista
                driver_name TEXT,
                driver_document TEXT,
                -- Informações da transportadora
                carrier_name TEXT,
                carrier_cnpj TEXT,
                -- Informações do acesso
                access_type TEXT NOT NULL DEFAULT 'entry',
                gate_number TEXT,
                lane_number TEXT,
                camera_id TEXT,
                -- Dados de segurança
                security_alert BOOLEAN DEFAULT FALSE,
                alert_reason TEXT,
                manual_review_required BOOLEAN DEFAULT FALSE,
                reviewed_by TEXT,
                reviewed_at TIMESTAMP,
                review_notes TEXT,
                -- Metadados
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                -- Constraints
                CONSTRAINT chk_access_type CHECK (access_type IN ('entry', 'exit'))
            )
        """)
    
    def _create_audit_logs_table(self, cursor: sqlite3.Cursor):
        """Cria tabela de logs de auditoria."""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id INTEGER,
                details TEXT,
                ip_address TEXT,
                user_agent TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                -- Constraints
                CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
    
    def _create_system_config_table(self, cursor: sqlite3.Cursor):
        """Cria tabela de configurações do sistema."""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_key TEXT UNIQUE NOT NULL,
                config_value TEXT NOT NULL,
                data_type TEXT DEFAULT 'string',
                description TEXT,
                is_encrypted BOOLEAN DEFAULT FALSE,
                updated_by INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    def _create_indexes(self, cursor: sqlite3.Cursor):
        """Cria índices para otimização de consultas."""
        indexes = [
            # Users
            "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS idx_users_cpf ON users(cpf)",
            "CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)",
            
            # Carriers
            "CREATE INDEX IF NOT EXISTS idx_carriers_cnpj ON carriers(cnpj)",
            "CREATE INDEX IF NOT EXISTS idx_carriers_status ON carriers(status)",
            
            # Vehicles
            "CREATE INDEX IF NOT EXISTS idx_vehicles_plate ON vehicles(plate)",
            "CREATE INDEX IF NOT EXISTS idx_vehicles_carrier ON vehicles(carrier_cnpj)",
            "CREATE INDEX IF NOT EXISTS idx_vehicles_status ON vehicles(status)",
            
            # Merchandise
            "CREATE INDEX IF NOT EXISTS idx_merchandise_vehicle ON merchandise(vehicle_plate)",
            "CREATE INDEX IF NOT EXISTS idx_merchandise_status ON merchandise(status)",
            "CREATE INDEX IF NOT EXISTS idx_merchandise_category ON merchandise(category)",
            
            # Access logs
            "CREATE INDEX IF NOT EXISTS idx_access_logs_plate ON access_logs(vehicle_plate)",
            "CREATE INDEX IF NOT EXISTS idx_access_logs_timestamp ON access_logs(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_access_logs_access_type ON access_logs(access_type)",
            
            # Audit logs
            "CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action)"
        ]
        
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
            except sqlite3.Error as e:
                logger.warning("Erro ao criar índice %s: %s", index_sql, e)
    
    def _insert_initial_data(self, cursor: sqlite3.Cursor):
        """Insere dados iniciais no sistema."""
        # Usuário administrador padrão
        cursor.execute("""
            INSERT OR IGNORE INTO users 
            (username, email, password_hash, name, cpf, role)
            VALUES 
            ('admin', 'admin@sentry.com', 'admin123', 'Administrador do Sistema', '00000000000', 'admin')
        """)
        
        # Configurações padrão do sistema
        default_configs = [
            ('system_name', 'Sentry Logística', 'string', 'Nome do sistema'),
            ('max_login_attempts', '5', 'integer', 'Máximo de tentativas de login'),
            ('session_timeout_minutes', '30', 'integer', 'Timeout de sessão em minutos'),
            ('backup_retention_days', '30', 'integer', 'Dias de retenção de backup'),
            ('security_alert_enabled', 'true', 'boolean', 'Alertas de segurança ativos')
        ]
        
        for config_key, config_value, data_type, description in default_configs:
            cursor.execute("""
                INSERT OR IGNORE INTO system_config 
                (config_key, config_value, data_type, description)
                VALUES (?, ?, ?, ?)
            """, (config_key, config_value, data_type, description))
    
    def backup_database(self, backup_name: Optional[str] = None) -> Path:
        """
        Cria um backup do banco de dados.
        
        Args:
            backup_name: Nome personalizado do backup (opcional)
            
        Returns:
            Path: Caminho do arquivo de backup criado
            
        Raises:
            DatabaseError: Em caso de erro no backup
        """
        if not backup_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"sentry_backup_{timestamp}.db"
        
        backup_path = DB_BACKUP_DIR / backup_name
        
        try:
            with self.get_connection() as conn:
                # Cria backup usando a funcionalidade de backup do SQLite
                with sqlite3.connect(str(backup_path)) as backup_conn:
                    conn.backup(backup_conn)
            
            logger.info("Backup criado com sucesso: %s", backup_path)
            return backup_path
            
        except sqlite3.Error as e:
            logger.error("Erro ao criar backup: %s", e)
            raise DatabaseError(f"Falha no backup: {str(e)}") from e
    
    def get_database_info(self) -> Dict[str, Any]:
        """
        Retorna informações sobre o banco de dados.
        
        Returns:
            Dicionário com informações do banco
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Informações básicas
            cursor.execute("SELECT COUNT(*) as table_count FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            db_size = cursor.fetchone()[0]
            
            # Contagem de registros por tabela
            tables = []
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            for row in cursor.fetchall():
                table_name = row[0]
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                record_count = cursor.fetchone()[0]
                tables.append({'name': table_name, 'records': record_count})
            
            return {
                'path': str(self.db_path),
                'size_bytes': db_size,
                'size_mb': round(db_size / (1024 * 1024), 2),
                'table_count': table_count,
                'tables': tables,
                'last_backup': self._get_last_backup_info()
            }
    
    def _get_last_backup_info(self) -> Optional[Dict[str, Any]]:
        """Retorna informações do último backup."""
        try:
            backups = list(DB_BACKUP_DIR.glob("sentry_backup_*.db"))
            if backups:
                latest_backup = max(backups, key=lambda p: p.stat().st_mtime)
                stat = latest_backup.stat()
                return {
                    'filename': latest_backup.name,
                    'size_mb': round(stat.st_size / (1024 * 1024), 2),
                    'created_at': datetime.fromtimestamp(stat.st_mtime)
                }
        except Exception as e:
            logger.warning("Erro ao obter info do backup: %s", e)
        
        return None
    
    def vacuum_database(self):
        """Executa operação VACUUM para otimizar o banco."""
        try:
            with self.get_connection() as conn:
                conn.execute("VACUUM")
            logger.info("Operação VACUUM executada com sucesso")
        except sqlite3.Error as e:
            logger.error("Erro ao executar VACUUM: %s", e)
            raise DatabaseError(f"Erro no VACUUM: {str(e)}") from e
    
    def execute_migration(self, migration_sql: str):
        """
        Executa uma migração SQL no banco.
        
        Args:
            migration_sql: SQL da migração
            
        Raises:
            DatabaseError: Em caso de erro na migração
        """
        try:
            with self.get_connection() as conn:
                conn.executescript(migration_sql)
                conn.commit()
            logger.info("Migração executada com sucesso")
        except sqlite3.Error as e:
            logger.error("Erro na migração: %s", e)
            raise DatabaseError(f"Erro na migração: {str(e)}") from e


# Instância global do gerenciador de banco
db_manager = DatabaseManager()


def init_database(force_recreate: bool = False):
    """
    Função de conveniência para inicializar o banco.
    
    Args:
        force_recreate: Se True, recria todas as tabelas
    """
    db_manager.initialize_database(force_recreate=force_recreate)


@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """
    Função de conveniência para obter conexão com o banco.
    
    Yields:
        sqlite3.Connection: Conexão com o banco
    """
    with db_manager.get_connection() as conn:
        yield conn


if __name__ == "__main__":
    # Configuração básica de logging para teste
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Inicializar banco
        init_database()
        
        # Mostrar informações
        info = db_manager.get_database_info()
        print("=== Informações do Banco de Dados ===")
        print(f"Localização: {info['path']}")
        print(f"Tamanho: {info['size_mb']} MB")
        print(f"Tabelas: {info['table_count']}")
        
        print("\n=== Tabelas e Registros ===")
        for table in info['tables']:
            print(f"  {table['name']}: {table['records']} registros")
        
        # Criar backup
        backup_path = db_manager.backup_database()
        print(f"\n✅ Backup criado: {backup_path.name}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")