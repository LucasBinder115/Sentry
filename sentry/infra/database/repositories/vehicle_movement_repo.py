# sentry/infra/database/repositories/vehicle_movement_repo.py

import sqlite3
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from contextlib import contextmanager
from pathlib import Path

from sentry.core.entities.access_log import AccessLog

# Configuração de logging
logger = logging.getLogger(__name__)

# Exceções personalizadas para este módulo
class VehicleAccessError(Exception):
    """Exceção base para erros de acesso de veículos."""
    pass

class AccessLogNotFoundError(VehicleAccessError):
    """Exceção para quando um log de acesso não é encontrado."""
    pass


class DatabaseError(VehicleAccessError):
    """Exceção para erros de banco de dados."""
    pass


class AccessLogRepositoryError(VehicleAccessError):
    """Exceção base para erros do repositório de logs de acesso."""
    pass


class VehicleMovementRepository:
    """
    Repositório para gerenciar os logs de acesso (movimentação de veículos).
    
    Implementa operações robustas para registro e consulta de movimentações
    de veículos com tratamento completo de erros e otimizações.
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
            DatabaseError: Se não for possível conectar ao banco
        """
        conn = None
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Configurações de performance
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute("PRAGMA cache_size = -64000")
            
            yield conn
        except sqlite3.Error as e:
            logger.error("Erro de conexão com o banco de dados: %s", e)
            raise DatabaseError(f"Não foi possível conectar ao banco de dados: {str(e)}") from e
        finally:
            if conn:
                conn.close()
    
    def _create_tables(self):
        """Cria as tabelas necessárias se não existirem."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabela principal de logs de acesso
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
                    access_type TEXT NOT NULL DEFAULT 'entry',  -- 'entry' ou 'exit'
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
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    -- Índices e constraints
                    CONSTRAINT chk_access_type CHECK (access_type IN ('entry', 'exit'))
                )
            """)

            # Migrações suaves: garantir colunas obrigatórias em bancos antigos
            try:
                cursor.execute("PRAGMA table_info(access_logs)")
                existing_columns = {row[1] for row in cursor.fetchall()}

                if 'access_type' not in existing_columns:
                    logger.warning("Coluna ausente: access_logs.access_type → adicionando...")
                    cursor.execute("ALTER TABLE access_logs ADD COLUMN access_type TEXT NOT NULL DEFAULT 'entry'")

                if 'updated_at' not in existing_columns:
                    logger.warning("Coluna ausente: access_logs.updated_at → adicionando...")
                    cursor.execute("ALTER TABLE access_logs ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

            except sqlite3.Error as e:
                logger.error("Erro ao aplicar migrações de access_logs: %s", e)
            
            # Tabela para eventos de segurança relacionados
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS security_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    access_log_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL DEFAULT 'medium',
                    description TEXT NOT NULL,
                    resolved BOOLEAN DEFAULT FALSE,
                    resolved_by TEXT,
                    resolved_at TIMESTAMP,
                    resolution_notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    -- Chaves estrangeiras
                    CONSTRAINT fk_access_log FOREIGN KEY (access_log_id) REFERENCES access_logs(id) ON DELETE CASCADE
                )
            """)
            
            # Tabela para estatísticas de movimentação
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS movement_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    vehicle_plate TEXT NOT NULL,
                    entry_count INTEGER DEFAULT 0,
                    exit_count INTEGER DEFAULT 0,
                    total_movements INTEGER DEFAULT 0,
                    first_movement TIMESTAMP,
                    last_movement TIMESTAMP,
                    -- Metadados
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    -- Constraints
                    UNIQUE(date, vehicle_plate)
                )
            """)
            
            # Índices para melhor performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_access_logs_plate ON access_logs(vehicle_plate)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_access_logs_timestamp ON access_logs(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_access_logs_access_type ON access_logs(access_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_access_logs_carrier ON access_logs(carrier_cnpj)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_access_logs_alert ON access_logs(security_alert)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_security_events_log ON security_events(access_log_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_security_events_type ON security_events(event_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_movement_stats_date ON movement_stats(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_movement_stats_plate ON movement_stats(vehicle_plate)")
            
            conn.commit()
            logger.info("Tabelas de movimentação de veículos verificadas/criadas com sucesso")
    
    def _row_to_entity(self, row: sqlite3.Row) -> AccessLog:
        """
        Converte uma linha do banco para entidade AccessLog.
        
        Args:
            row: Linha do banco de dados
            
        Returns:
            Instância de AccessLog
        """
        # Campos básicos
        log_data = {
            'id': row['id'],
            'vehicle_plate': row['vehicle_plate'],
            'timestamp': row['timestamp']
        }
        
        # Campos opcionais
        optional_fields = [
            'vehicle_type', 'vehicle_model', 'vehicle_color',
            'driver_name', 'driver_document', 'carrier_name',
            'carrier_cnpj', 'access_type', 'gate_number',
            'lane_number', 'camera_id', 'security_alert',
            'alert_reason', 'manual_review_required', 'reviewed_by',
            'reviewed_at', 'review_notes', 'created_at', 'updated_at'
        ]
        
        for field in optional_fields:
            if row[field] is not None:
                log_data[field] = row[field]
        
        return AccessLog(**log_data)
    
    def save(self, log: AccessLog) -> AccessLog:
        """
        Salva um novo log de acesso.
        
        Args:
            log: Instância de AccessLog a ser salva
            
        Returns:
            AccessLog salvo com ID atualizado
            
        Raises:
            DatabaseError: Em caso de erro de banco
        """
        logger.info("Salvando log de acesso para veículo: %s", log.vehicle_plate)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT INTO access_logs (
                        vehicle_plate, timestamp, vehicle_type, vehicle_model, vehicle_color,
                        driver_name, driver_document, carrier_name, carrier_cnpj,
                        access_type, gate_number, lane_number, camera_id,
                        security_alert, alert_reason, manual_review_required
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    log.vehicle_plate,
                    log.timestamp,
                    getattr(log, 'vehicle_type', None),
                    getattr(log, 'vehicle_model', None),
                    getattr(log, 'vehicle_color', None),
                    getattr(log, 'driver_name', None),
                    getattr(log, 'driver_document', None),
                    getattr(log, 'carrier_name', None),
                    getattr(log, 'carrier_cnpj', None),
                    getattr(log, 'access_type', 'entry'),
                    getattr(log, 'gate_number', None),
                    getattr(log, 'lane_number', None),
                    getattr(log, 'camera_id', None),
                    getattr(log, 'security_alert', False),
                    getattr(log, 'alert_reason', None),
                    getattr(log, 'manual_review_required', False)
                ))
                
                conn.commit()
                log.id = cursor.lastrowid
                
                # Atualiza estatísticas de movimentação
                self._update_movement_stats(conn, log)
                
                logger.info(
                    "Log de acesso salvo com sucesso: %s (ID: %s, Tipo: %s)",
                    log.vehicle_plate, log.id, getattr(log, 'access_type', 'entry')
                )
                
                return log
                
            except sqlite3.Error as e:
                logger.error("Erro ao salvar log de acesso: %s", e)
                raise DatabaseError(f"Erro ao salvar log de acesso: {str(e)}") from e
    
    def _update_movement_stats(self, conn: sqlite3.Connection, log: AccessLog):
        """
        Atualiza as estatísticas de movimentação para o veículo.
        
        Args:
            conn: Conexão com o banco
            log: Log de acesso recém-salvo
        """
        try:
            cursor = conn.cursor()
            date_str = log.timestamp.date().isoformat()
            access_type = getattr(log, 'access_type', 'entry')
            
            cursor.execute("""
                INSERT INTO movement_stats (
                    date, vehicle_plate, entry_count, exit_count, total_movements,
                    first_movement, last_movement
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(date, vehicle_plate) DO UPDATE SET
                    entry_count = entry_count + CASE WHEN excluded.entry_count > 0 THEN 1 ELSE 0 END,
                    exit_count = exit_count + CASE WHEN excluded.exit_count > 0 THEN 1 ELSE 0 END,
                    total_movements = total_movements + 1,
                    first_movement = CASE 
                        WHEN movement_stats.first_movement IS NULL OR excluded.first_movement < movement_stats.first_movement 
                        THEN excluded.first_movement 
                        ELSE movement_stats.first_movement 
                    END,
                    last_movement = CASE 
                        WHEN movement_stats.last_movement IS NULL OR excluded.last_movement > movement_stats.last_movement 
                        THEN excluded.last_movement 
                        ELSE movement_stats.last_movement 
                    END,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                date_str,
                log.vehicle_plate,
                1 if access_type == 'entry' else 0,
                1 if access_type == 'exit' else 0,
                1,
                log.timestamp,
                log.timestamp
            ))
        except sqlite3.Error as e:
            logger.warning("Erro ao atualizar estatísticas de movimentação: %s", e)
    
    def find_by_id(self, log_id: int) -> Optional[AccessLog]:
        """
        Busca log de acesso por ID.
        
        Args:
            log_id: ID do log de acesso
            
        Returns:
            Instância de AccessLog se encontrado, None caso contrário
        """
        logger.debug("Buscando log de acesso por ID: %s", log_id)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("SELECT * FROM access_logs WHERE id = ?", (log_id,))
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_entity(row)
                return None
                    
            except sqlite3.Error as e:
                logger.error("Erro ao buscar log de acesso por ID %s: %s", log_id, e)
                raise DatabaseError(f"Erro ao buscar log de acesso: {str(e)}") from e
    
    def find_by_vehicle_plate(self, vehicle_plate: str, limit: int = 100) -> List[AccessLog]:
        """
        Busca logs de acesso por placa do veículo.
        
        Args:
            vehicle_plate: Placa do veículo
            limit: Número máximo de registros
            
        Returns:
            Lista de logs de acesso do veículo
        """
        logger.debug("Buscando logs de acesso por placa: %s", vehicle_plate)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    SELECT * FROM access_logs 
                    WHERE vehicle_plate = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (vehicle_plate, limit))
                
                rows = cursor.fetchall()
                logs = [self._row_to_entity(row) for row in rows]
                
                logger.debug("Encontrados %d logs para a placa %s", len(logs), vehicle_plate)
                return logs
                    
            except sqlite3.Error as e:
                logger.error("Erro ao buscar logs por placa %s: %s", vehicle_plate, e)
                raise DatabaseError(f"Erro ao buscar logs de acesso: {str(e)}") from e
    
    def find_all_recent(self, limit: int = 50) -> List[AccessLog]:
        """
        Busca os logs de acesso mais recentes.
        
        Args:
            limit: Número máximo de registros
            
        Returns:
            Lista dos logs de acesso mais recentes
        """
        logger.debug("Buscando %d logs de acesso mais recentes", limit)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    SELECT * FROM access_logs 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (limit,))
                
                rows = cursor.fetchall()
                logs = [self._row_to_entity(row) for row in rows]
                
                logger.debug("Encontrados %d logs recentes", len(logs))
                return logs
                    
            except sqlite3.Error as e:
                logger.error("Erro ao buscar logs recentes: %s", e)
                raise DatabaseError(f"Erro ao buscar logs de acesso: {str(e)}") from e
    
    def find_by_date_range(self, start_date: datetime, end_date: datetime) -> List[AccessLog]:
        """
        Busca logs de acesso por intervalo de datas.
        
        Args:
            start_date: Data de início
            end_date: Data de fim
            
        Returns:
            Lista de logs no intervalo especificado
        """
        logger.debug("Buscando logs de %s a %s", start_date, end_date)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    SELECT * FROM access_logs 
                    WHERE timestamp BETWEEN ? AND ? 
                    ORDER BY timestamp DESC
                """, (start_date, end_date))
                
                rows = cursor.fetchall()
                logs = [self._row_to_entity(row) for row in rows]
                
                logger.debug("Encontrados %d logs no intervalo", len(logs))
                return logs
                    
            except sqlite3.Error as e:
                logger.error("Erro ao buscar logs por intervalo: %s", e)
                raise DatabaseError(f"Erro ao buscar logs de acesso: {str(e)}") from e
    
    def find_with_alerts(self, limit: int = 100) -> List[AccessLog]:
        """
        Busca logs de acesso com alertas de segurança.
        
        Args:
            limit: Número máximo de registros
            
        Returns:
            Lista de logs com alertas
        """
        logger.debug("Buscando logs com alertas de segurança")
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    SELECT * FROM access_logs 
                    WHERE security_alert = TRUE 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (limit,))
                
                rows = cursor.fetchall()
                logs = [self._row_to_entity(row) for row in rows]
                
                logger.debug("Encontrados %d logs com alertas", len(logs))
                return logs
                    
            except sqlite3.Error as e:
                logger.error("Erro ao buscar logs com alertas: %s", e)
                raise DatabaseError(f"Erro ao buscar logs de acesso: {str(e)}") from e
    
    def get_movement_stats(self, vehicle_plate: str, days: int = 30) -> Dict[str, Any]:
        """
        Retorna estatísticas de movimentação de um veículo.
        
        Args:
            vehicle_plate: Placa do veículo
            days: Número de dias para análise
            
        Returns:
            Dicionário com estatísticas
        """
        start_date = datetime.now() - timedelta(days=days)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # Estatísticas gerais
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_movements,
                        COUNT(CASE WHEN access_type = 'entry' THEN 1 END) as entries,
                        COUNT(CASE WHEN access_type = 'exit' THEN 1 END) as exits,
                        MIN(timestamp) as first_movement,
                        MAX(timestamp) as last_movement,
                        COUNT(CASE WHEN security_alert = TRUE THEN 1 END) as alerts_count
                    FROM access_logs 
                    WHERE vehicle_plate = ? AND timestamp >= ?
                """, (vehicle_plate, start_date))
                
                stats_row = cursor.fetchone()
                
                # Movimentações por dia
                cursor.execute("""
                    SELECT 
                        DATE(timestamp) as movement_date,
                        COUNT(*) as daily_movements,
                        COUNT(CASE WHEN access_type = 'entry' THEN 1 END) as daily_entries,
                        COUNT(CASE WHEN access_type = 'exit' THEN 1 END) as daily_exits
                    FROM access_logs 
                    WHERE vehicle_plate = ? AND timestamp >= ?
                    GROUP BY DATE(timestamp)
                    ORDER BY movement_date DESC
                    LIMIT 30
                """, (vehicle_plate, start_date))
                
                daily_stats = cursor.fetchall()
                
                return {
                    'vehicle_plate': vehicle_plate,
                    'period_days': days,
                    'total_movements': stats_row['total_movements'],
                    'entries': stats_row['entries'],
                    'exits': stats_row['exits'],
                    'first_movement': stats_row['first_movement'],
                    'last_movement': stats_row['last_movement'],
                    'alerts_count': stats_row['alerts_count'],
                    'daily_breakdown': [
                        {
                            'date': row['movement_date'],
                            'total': row['daily_movements'],
                            'entries': row['daily_entries'],
                            'exits': row['daily_exits']
                        } for row in daily_stats
                    ]
                }
                    
            except sqlite3.Error as e:
                logger.error("Erro ao obter estatísticas para %s: %s", vehicle_plate, e)
                raise DatabaseError(f"Erro ao obter estatísticas: {str(e)}") from e
    
    def get_daily_summary(self, date: datetime) -> Dict[str, Any]:
        """
        Retorna resumo das movimentações de um dia específico.
        
        Args:
            date: Data para o resumo
            
        Returns:
            Dicionário com resumo do dia
        """
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_movements,
                        COUNT(CASE WHEN access_type = 'entry' THEN 1 END) as total_entries,
                        COUNT(CASE WHEN access_type = 'exit' THEN 1 END) as total_exits,
                        COUNT(DISTINCT vehicle_plate) as unique_vehicles,
                        COUNT(CASE WHEN security_alert = TRUE THEN 1 END) as total_alerts,
                        MIN(timestamp) as first_movement,
                        MAX(timestamp) as last_movement
                    FROM access_logs 
                    WHERE timestamp BETWEEN ? AND ?
                """, (start_of_day, end_of_day))
                
                summary = cursor.fetchone()
                
                # Veículos mais ativos
                cursor.execute("""
                    SELECT vehicle_plate, COUNT(*) as movement_count
                    FROM access_logs 
                    WHERE timestamp BETWEEN ? AND ?
                    GROUP BY vehicle_plate
                    ORDER BY movement_count DESC
                    LIMIT 10
                """, (start_of_day, end_of_day))
                
                top_vehicles = cursor.fetchall()
                
                return {
                    'date': date.date().isoformat(),
                    'total_movements': summary['total_movements'],
                    'total_entries': summary['total_entries'],
                    'total_exits': summary['total_exits'],
                    'unique_vehicles': summary['unique_vehicles'],
                    'total_alerts': summary['total_alerts'],
                    'first_movement': summary['first_movement'],
                    'last_movement': summary['last_movement'],
                    'top_vehicles': [
                        {
                            'vehicle_plate': row['vehicle_plate'],
                            'movement_count': row['movement_count']
                        } for row in top_vehicles
                    ]
                }
                    
            except sqlite3.Error as e:
                logger.error("Erro ao obter resumo do dia %s: %s", date, e)
                raise DatabaseError(f"Erro ao obter resumo: {str(e)}") from e


# Exemplo de uso
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    try:
        repo = VehicleMovementRepository()
        
        # Teste de criação de log
        log = AccessLog(
            vehicle_plate="ABC1D23",
            timestamp=datetime.now(),
            access_type="entry",
            vehicle_type="caminhao",
            driver_name="João Silva",
            carrier_name="Transportadora Teste LTDA"
        )
        
        saved_log = repo.save(log)
        print(f"Log de acesso salvo: {saved_log.vehicle_plate} (ID: {saved_log.id})")
        
        # Teste de busca de logs recentes
        recent_logs = repo.find_all_recent(limit=5)
        print(f"Encontrados {len(recent_logs)} logs recentes")
        
        # Estatísticas
        stats = repo.get_movement_stats("ABC1D23", days=7)
        print(f"Estatísticas: {stats}")
        
    except Exception as e:
        print(f"Erro: {e}")