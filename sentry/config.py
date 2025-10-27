# sentry/config.py
"""
Sistema de configuração centralizado para SENTRY.INC

Este módulo fornece uma configuração robusta e flexível para toda a aplicação,
incluindo suporte a variáveis de ambiente, validação de configurações e
diferentes ambientes (desenvolvimento, produção, teste).

Características:
- Configuração baseada em classes com herança
- Suporte a variáveis de ambiente via .env
- Validação automática de configurações
- Configurações específicas por ambiente
- Logging configurado
- Caminhos relativos ao projeto
- Configurações de banco de dados
- Configurações de segurança
- Configurações de UI/UX
"""

import os
import logging
import secrets
from pathlib import Path
from typing import Any, Dict, Optional, Union, List
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime, timedelta

# ============================================================================
# CONSTANTES E ENUMS
# ============================================================================

class Environment(Enum):
    """Ambientes disponíveis para a aplicação."""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"
    STAGING = "staging"

class LogLevel(Enum):
    """Níveis de log disponíveis."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

# ============================================================================
# EXCEÇÕES PERSONALIZADAS
# ============================================================================

class ConfigurationError(Exception):
    """Exceção base para erros de configuração."""
    pass

class EnvironmentVariableError(ConfigurationError):
    """Exceção para variáveis de ambiente inválidas."""
    pass

class ConfigurationValidationError(ConfigurationError):
    """Exceção para validação de configuração falhada."""
    pass

# ============================================================================
# CONFIGURAÇÃO BASE
# ============================================================================

@dataclass
class DatabaseConfig:
    """Configurações do banco de dados."""
    # Caminhos
    path: Path
    backup_dir: Path
    migrations_dir: Path
    
    # Configurações de conexão
    timeout: float = 30.0
    check_same_thread: bool = False
    detect_types: bool = True
    
    # Configurações de performance
    cache_size: int = -64000  # 64MB
    journal_mode: str = "WAL"
    synchronous: str = "NORMAL"
    busy_timeout: int = 5000  # 5 segundos
    
    # Configurações de backup
    backup_retention_days: int = 30
    auto_backup: bool = True
    backup_interval_hours: int = 24
    
    # Configurações de segurança
    enable_foreign_keys: bool = True
    enable_optimize: bool = True

@dataclass
class SecurityConfig:
    """Configurações de segurança."""
    # Autenticação
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 30
    session_timeout_minutes: int = 30
    password_min_length: int = 8
    require_password_change: bool = True
    
    # Criptografia
    secret_key: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    encryption_algorithm: str = "AES-256-GCM"
    
    # Logs de auditoria
    enable_audit_logs: bool = True
    audit_log_retention_days: int = 90
    
    # Alertas de segurança
    enable_security_alerts: bool = True
    alert_email: Optional[str] = None
    alert_phone: Optional[str] = None

@dataclass
class UIConfig:
    """Configurações da interface do usuário."""
    # Janela principal
    window_width: int = 1400
    window_height: int = 900
    window_min_width: int = 1000
    window_min_height: int = 700
    
    # Tema e aparência
    theme: str = "light"  # light, dark, auto
    font_family: str = "Segoe UI"
    font_size: int = 10
    primary_color: str = "#1a237e"
    secondary_color: str = "#f5f7fa"
    
    # Splash screen
    splash_duration_ms: int = 3000
    splash_show_version: bool = True
    
    # Configurações de notificação
    show_notifications: bool = True
    notification_duration_ms: int = 5000

@dataclass
class APIConfig:
    """Configurações de APIs externas."""
    # NHTSA API
    nhtsa_base_url: str = "https://vpic.nhtsa.dot.gov/api"
    nhtsa_timeout: int = 30
    nhtsa_retry_attempts: int = 3
    
    # DENATRAN API
    denatran_base_url: str = "https://www.denatran.gov.br"
    denatran_timeout: int = 30
    denatran_retry_attempts: int = 3
    
    # Configurações gerais
    request_timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0

@dataclass
class OCRConfig:
    """Configurações de OCR e reconhecimento."""
    # EasyOCR
    easyocr_languages: List[str] = field(default_factory=lambda: ["pt", "en"])
    easyocr_gpu: bool = False
    easyocr_confidence_threshold: float = 0.7
    
    # Tesseract
    tesseract_path: Optional[str] = None
    tesseract_config: str = "--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    
    # Processamento de imagem
    image_preprocessing: bool = True
    image_enhancement: bool = True
    resize_factor: float = 2.0

@dataclass
class LoggingConfig:
    """Configurações de logging."""
    level: LogLevel = LogLevel.INFO
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    
    # Arquivos de log
    log_dir: Path = field(default_factory=lambda: Path("logs"))
    log_file: str = "sentry.log"
    max_file_size_mb: int = 10
    backup_count: int = 5
    
    # Configurações específicas
    log_database_queries: bool = False
    log_api_requests: bool = True
    log_user_actions: bool = True

# ============================================================================
# CONFIGURAÇÃO PRINCIPAL
# ============================================================================

class Config:
    """
    Classe principal de configuração para SENTRY.INC.
    
    Esta classe centraliza todas as configurações da aplicação e fornece
    métodos para carregar, validar e acessar essas configurações.
    """
    
    # Caminho base do projeto
    BASE_DIR = Path(__file__).resolve().parent.parent
    
    def __init__(self, environment: Union[str, Environment] = Environment.DEVELOPMENT):
        """
        Inicializa a configuração.
        
        Args:
            environment: Ambiente da aplicação (development, production, testing, staging)
        """
        self.environment = Environment(environment) if isinstance(environment, str) else environment
        self._config_loaded = False
        
        # Inicializar configurações padrão
        self._init_default_configs()
        
        # Carregar configurações do ambiente
        self.load_environment_config()
        
        # Validar configurações
        self.validate_config()
        
        self._config_loaded = True
        
        # Configurar logging
        self._setup_logging()
    
    def _init_default_configs(self):
        """Inicializa as configurações padrão."""
        # Diretórios
        self.data_dir = self.BASE_DIR / "data"
        self.logs_dir = self.BASE_DIR / "logs"
        self.backups_dir = self.BASE_DIR / "backups"
        self.temp_dir = self.BASE_DIR / "temp"
        self.assets_dir = self.BASE_DIR / "sentry" / "assets"
        
        # Criar diretórios necessários
        for directory in [self.data_dir, self.logs_dir, self.backups_dir, self.temp_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Configurações específicas
        self.database = DatabaseConfig(
            path=self.data_dir / "sentry.db",
            backup_dir=self.backups_dir / "database",
            migrations_dir=self.BASE_DIR / "sentry" / "infra" / "database" / "migrations"
        )
        
        self.security = SecurityConfig()
        self.ui = UIConfig()
        self.api = APIConfig()
        self.ocr = OCRConfig()
        self.logging = LoggingConfig(log_dir=self.logs_dir)
        
        # Configurações específicas do ambiente
        self._apply_environment_config()
    
    def _apply_environment_config(self):
        """Aplica configurações específicas do ambiente."""
        if self.environment == Environment.DEVELOPMENT:
            self.logging.level = LogLevel.DEBUG
            self.database.auto_backup = False
            self.security.enable_audit_logs = True
            
        elif self.environment == Environment.PRODUCTION:
            self.logging.level = LogLevel.WARNING
            self.database.auto_backup = True
            self.security.enable_audit_logs = True
            self.ui.splash_duration_ms = 2000
            
        elif self.environment == Environment.TESTING:
            self.logging.level = LogLevel.ERROR
            self.database.path = self.data_dir / "sentry_test.db"
            self.database.auto_backup = False
            self.security.enable_audit_logs = False
    
    def load_environment_config(self):
        """Carrega configurações do arquivo .env e variáveis de ambiente."""
        env_path = self.BASE_DIR / ".env"
        
        # Carregar .env se existir
        if env_path.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_path)
            except ImportError:
                logging.warning("python-dotenv não instalado. Arquivo .env será ignorado.")
        
        # Carregar configurações do banco de dados
        self._load_database_config()
        
        # Carregar configurações de segurança
        self._load_security_config()
        
        # Carregar configurações de UI
        self._load_ui_config()
        
        # Carregar configurações de API
        self._load_api_config()
        
        # Carregar configurações de OCR
        self._load_ocr_config()
        
        # Carregar configurações de logging
        self._load_logging_config()
    
    def _load_database_config(self):
        """Carrega configurações do banco de dados."""
        if os.getenv("DB_PATH"):
            self.database.path = self.BASE_DIR / os.getenv("DB_PATH")
        
        if os.getenv("DB_BACKUP_DIR"):
            self.database.backup_dir = self.BASE_DIR / os.getenv("DB_BACKUP_DIR")
        
        if os.getenv("DB_TIMEOUT"):
            self.database.timeout = float(os.getenv("DB_TIMEOUT"))
        
        if os.getenv("DB_CACHE_SIZE"):
            self.database.cache_size = int(os.getenv("DB_CACHE_SIZE"))
    
    def _load_security_config(self):
        """Carrega configurações de segurança."""
        if os.getenv("SECRET_KEY"):
            self.security.secret_key = os.getenv("SECRET_KEY")
        
        if os.getenv("MAX_LOGIN_ATTEMPTS"):
            self.security.max_login_attempts = int(os.getenv("MAX_LOGIN_ATTEMPTS"))
        
        if os.getenv("SESSION_TIMEOUT_MINUTES"):
            self.security.session_timeout_minutes = int(os.getenv("SESSION_TIMEOUT_MINUTES"))
        
        if os.getenv("ALERT_EMAIL"):
            self.security.alert_email = os.getenv("ALERT_EMAIL")
    
    def _load_ui_config(self):
        """Carrega configurações da interface."""
        if os.getenv("UI_THEME"):
            self.ui.theme = os.getenv("UI_THEME")
        
        if os.getenv("UI_FONT_SIZE"):
            self.ui.font_size = int(os.getenv("UI_FONT_SIZE"))
        
        if os.getenv("UI_PRIMARY_COLOR"):
            self.ui.primary_color = os.getenv("UI_PRIMARY_COLOR")
    
    def _load_api_config(self):
        """Carrega configurações de APIs."""
        if os.getenv("NHTSA_BASE_URL"):
            self.api.nhtsa_base_url = os.getenv("NHTSA_BASE_URL")
        
        if os.getenv("API_TIMEOUT"):
            self.api.request_timeout = int(os.getenv("API_TIMEOUT"))
    
    def _load_ocr_config(self):
        """Carrega configurações de OCR."""
        if os.getenv("TESSERACT_PATH"):
            self.ocr.tesseract_path = os.getenv("TESSERACT_PATH")
        
        if os.getenv("OCR_CONFIDENCE_THRESHOLD"):
            self.ocr.easyocr_confidence_threshold = float(os.getenv("OCR_CONFIDENCE_THRESHOLD"))
    
    def _load_logging_config(self):
        """Carrega configurações de logging."""
        if os.getenv("LOG_LEVEL"):
            self.logging.level = LogLevel(os.getenv("LOG_LEVEL").upper())
        
        if os.getenv("LOG_FILE"):
            self.logging.log_file = os.getenv("LOG_FILE")
    
    def validate_config(self):
        """Valida todas as configurações."""
        errors = []
        
        # Validar diretórios
        if not self.data_dir.exists():
            errors.append(f"Diretório de dados não existe: {self.data_dir}")
        
        # Validar configurações do banco
        if self.database.timeout <= 0:
            errors.append("Timeout do banco deve ser positivo")
        
        if self.database.cache_size > 0:
            errors.append("Cache size deve ser negativo (em KB)")
        
        # Validar configurações de segurança
        if len(self.security.secret_key) < 32:
            errors.append("Chave secreta deve ter pelo menos 32 caracteres")
        
        if self.security.max_login_attempts <= 0:
            errors.append("Máximo de tentativas de login deve ser positivo")
        
        # Validar configurações de UI
        if self.ui.window_width < self.ui.window_min_width:
            errors.append("Largura da janela deve ser maior que a largura mínima")
        
        if self.ui.font_size < 8 or self.ui.font_size > 24:
            errors.append("Tamanho da fonte deve estar entre 8 e 24")
        
        # Validar configurações de API
        if self.api.request_timeout <= 0:
            errors.append("Timeout da API deve ser positivo")
        
        # Validar configurações de OCR
        if not 0 <= self.ocr.easyocr_confidence_threshold <= 1:
            errors.append("Threshold de confiança do OCR deve estar entre 0 e 1")
        
        if errors:
            raise ConfigurationValidationError(f"Erros de validação: {'; '.join(errors)}")
    
    def _setup_logging(self):
        """Configura o sistema de logging."""
        # Criar diretório de logs se não existir
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurar logging
        logging.basicConfig(
            level=getattr(logging, self.logging.level.value),
            format=self.logging.format,
            datefmt=self.logging.date_format,
            handlers=[
                logging.FileHandler(self.logs_dir / self.logging.log_file),
                logging.StreamHandler()
            ]
        )
        
        # Configurar loggers específicos
        logging.getLogger("sentry").setLevel(self.logging.level.value)
        logging.getLogger("sqlite3").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    def get_database_connection_params(self) -> Dict[str, Any]:
        """Retorna parâmetros para conexão com o banco de dados."""
        return {
            "database": str(self.database.path),
            "timeout": self.database.timeout,
            "check_same_thread": self.database.check_same_thread,
            "detect_types": self.database.detect_types
        }
    
    def get_database_pragmas(self) -> List[str]:
        """Retorna PRAGMAs para configuração do SQLite."""
        return [
            f"PRAGMA foreign_keys = {'ON' if self.database.enable_foreign_keys else 'OFF'}",
            f"PRAGMA journal_mode = {self.database.journal_mode}",
            f"PRAGMA synchronous = {self.database.synchronous}",
            f"PRAGMA cache_size = {self.database.cache_size}",
            f"PRAGMA busy_timeout = {self.database.busy_timeout}",
            "PRAGMA optimize" if self.database.enable_optimize else ""
        ]
    
    def save_config(self, file_path: Optional[Path] = None) -> Path:
        """
        Salva a configuração atual em um arquivo.
        
        Args:
            file_path: Caminho do arquivo (opcional)
            
        Returns:
            Path: Caminho do arquivo salvo
        """
        if file_path is None:
            file_path = self.data_dir / f"config_{self.environment.value}.json"
        
        config_dict = {
            "environment": self.environment.value,
            "database": {
                "path": str(self.database.path),
                "backup_dir": str(self.database.backup_dir),
                "timeout": self.database.timeout,
                "cache_size": self.database.cache_size,
                "auto_backup": self.database.auto_backup
            },
            "security": {
                "max_login_attempts": self.security.max_login_attempts,
                "session_timeout_minutes": self.security.session_timeout_minutes,
                "enable_audit_logs": self.security.enable_audit_logs
            },
            "ui": {
                "theme": self.ui.theme,
                "font_size": self.ui.font_size,
                "primary_color": self.ui.primary_color
            },
            "api": {
                "nhtsa_base_url": self.api.nhtsa_base_url,
                "request_timeout": self.api.request_timeout
            },
            "ocr": {
                "confidence_threshold": self.ocr.easyocr_confidence_threshold,
                "languages": self.ocr.easyocr_languages
            },
            "logging": {
                "level": self.logging.level.value,
                "log_file": self.logging.log_file
            }
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)
        
        return file_path
    
    def load_config(self, file_path: Path):
        """
        Carrega configuração de um arquivo.
        
        Args:
            file_path: Caminho do arquivo de configuração
        """
        if not file_path.exists():
            raise ConfigurationError(f"Arquivo de configuração não encontrado: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            config_dict = json.load(f)
        
        # Aplicar configurações carregadas
        if "environment" in config_dict:
            self.environment = Environment(config_dict["environment"])
        
        # Aplicar outras configurações...
        # (implementação detalhada seria muito longa aqui)
    
    def get_info(self) -> Dict[str, Any]:
        """Retorna informações sobre a configuração atual."""
        return {
            "environment": self.environment.value,
            "base_dir": str(self.BASE_DIR),
            "data_dir": str(self.data_dir),
            "database_path": str(self.database.path),
            "database_exists": self.database.path.exists(),
            "logs_dir": str(self.logs_dir),
            "config_loaded": self._config_loaded,
            "version": "2.0.0"
        }
    
    def __repr__(self) -> str:
        return f"Config(environment={self.environment.value}, loaded={self._config_loaded})"

# ============================================================================
# INSTÂNCIA GLOBAL E FUNÇÕES DE CONVENIÊNCIA
# ============================================================================

# Instância global da configuração
_config_instance: Optional[Config] = None

def get_config() -> Config:
    """
    Retorna a instância global da configuração.
    
    Returns:
        Config: Instância da configuração
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance

def init_config(environment: Union[str, Environment] = Environment.DEVELOPMENT) -> Config:
    """
    Inicializa a configuração global.
    
    Args:
        environment: Ambiente da aplicação
        
    Returns:
        Config: Instância da configuração
    """
    global _config_instance
    _config_instance = Config(environment)
    return _config_instance

def reload_config() -> Config:
    """
    Recarrega a configuração global.
    
    Returns:
        Config: Nova instância da configuração
    """
    global _config_instance
    _config_instance = None
    return get_config()

# ============================================================================
# INICIALIZAÇÃO AUTOMÁTICA
# ============================================================================

# Carregar configuração automaticamente quando o módulo é importado
if _config_instance is None:
    try:
        _config_instance = Config()
    except Exception as e:
        logging.error(f"Erro ao inicializar configuração: {e}")
        # Usar configuração mínima em caso de erro
        _config_instance = Config(Environment.DEVELOPMENT)

# ============================================================================
# COMPATIBILIDADE COM CÓDIGO EXISTENTE
# ============================================================================

# Manter compatibilidade com código existente
DB_PATH = get_config().database.path
BASE_DIR = get_config().BASE_DIR

# Função de conveniência para carregar .env (compatibilidade)
def load_env():
    """Carrega configurações do arquivo .env (compatibilidade)."""
    get_config().load_environment_config()

# ============================================================================
# TESTE E VALIDAÇÃO
# ============================================================================

if __name__ == "__main__":
    # Teste da configuração
    print("=== Teste da Configuração SENTRY.INC ===")
    
    try:
        config = get_config()
        print(f"✅ Configuração carregada: {config}")
        print(f"📁 Diretório base: {config.BASE_DIR}")
        print(f"🗄️  Banco de dados: {config.database.path}")
        print(f"📊 Ambiente: {config.environment.value}")
        print(f"🔒 Segurança: {config.security.max_login_attempts} tentativas máx")
        print(f"🎨 UI: {config.ui.theme} theme, fonte {config.ui.font_size}px")
        
        # Salvar configuração de exemplo
        config_file = config.save_config()
        print(f"💾 Configuração salva em: {config_file}")
        
    except Exception as e:
        print(f"❌ Erro na configuração: {e}")
        import traceback
        traceback.print_exc()