# sentry/infra/database/repositories/vehicle_repo.py

import sqlite3
import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from contextlib import contextmanager
from pathlib import Path

from sentry.core.entities.vehicle import Vehicle
from sentry.core.use_cases.register_vehicle import (
    VehicleRegistrationError,
    DuplicatePlateError,
    CarrierNotFoundError
)

# Configuração de logging
logger = logging.getLogger(__name__)


class DatabaseError(VehicleRegistrationError):
    """Exceção para erros de banco de dados."""
    pass


class VehicleNotFoundError(VehicleRegistrationError):
    """Exceção quando veículo não é encontrado."""
    pass


class VehicleRepository:
    """
    Repositório para gerenciar operações de banco de dados relacionadas a Veículos.
    
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
            
            # Tabela principal de veículos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vehicles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plate TEXT UNIQUE NOT NULL,
                    model TEXT NOT NULL,
                    color TEXT,
                    carrier_cnpj TEXT,
                    -- Informações adicionais
                    type TEXT DEFAULT 'outro',
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
                    -- Índices e constraints
                    CONSTRAINT chk_year CHECK (year IS NULL OR year >= 1900),
                    CONSTRAINT chk_capacity_kg CHECK (capacity_kg IS NULL OR capacity_kg >= 0),
                    CONSTRAINT chk_capacity_m3 CHECK (capacity_m3 IS NULL OR capacity_m3 >= 0),
                    CONSTRAINT chk_status CHECK (status IN ('active', 'inactive', 'maintenance', 'suspended'))
                )
            """)
            
            # Tabela para histórico de manutenção
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vehicle_maintenance_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_id INTEGER NOT NULL,
                    maintenance_date TIMESTAMP NOT NULL,
                    maintenance_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    cost REAL,
                    service_provider TEXT,
                    odometer_reading INTEGER,
                    next_maintenance_date TIMESTAMP,
                    notes TEXT,
                    -- Metadados
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    -- Chaves estrangeiras
                    CONSTRAINT fk_vehicle FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE
                )
            """)
            
            # Tabela para histórico de seguros
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vehicle_insurance_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_id INTEGER NOT NULL,
                    policy_number TEXT NOT NULL,
                    insurance_company TEXT NOT NULL,
                    coverage_type TEXT NOT NULL,
                    premium_value REAL NOT NULL,
                    start_date TIMESTAMP NOT NULL,
                    end_date TIMESTAMP NOT NULL,
                    notes TEXT,
                    -- Metadados
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    -- Chaves estrangeiras
                    CONSTRAINT fk_vehicle FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE
                )
            """)
            
            # Índices para melhor performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vehicles_plate ON vehicles(plate)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vehicles_carrier ON vehicles(carrier_cnpj)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vehicles_status ON vehicles(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vehicles_type ON vehicles(type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vehicles_year ON vehicles(year)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_maintenance_vehicle ON vehicle_maintenance_history(vehicle_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_maintenance_date ON vehicle_maintenance_history(maintenance_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_insurance_vehicle ON vehicle_insurance_history(vehicle_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_insurance_dates ON vehicle_insurance_history(start_date, end_date)")
            
            conn.commit()
            logger.info("Tabelas de veículos verificadas/criadas com sucesso")
    
    def _row_to_entity(self, row: sqlite3.Row) -> Vehicle:
        """
        Converte uma linha do banco para entidade Vehicle.
        
        Args:
            row: Linha do banco de dados
            
        Returns:
            Instância de Vehicle
        """
        # Campos básicos
        vehicle_data = {
            'id': row['id'],
            'plate': row['plate'],
            'model': row['model']
        }
        
        # Campos opcionais básicos
        basic_optional_fields = ['color', 'carrier_cnpj', 'type', 'chassis_number', 
                               'fuel_type', 'insurance_policy', 'status']
        
        for field in basic_optional_fields:
            if row[field] is not None:
                vehicle_data[field] = row[field]
        
        # Campos numéricos
        numeric_fields = ['year', 'capacity_kg', 'capacity_m3']
        for field in numeric_fields:
            if row[field] is not None:
                if field in ['capacity_kg', 'capacity_m3']:
                    vehicle_data[field] = Decimal(str(row[field]))
                else:
                    vehicle_data[field] = row[field]
        
        # Campos de data
        date_fields = ['insurance_expiry', 'last_maintenance', 'next_maintenance', 
                      'created_at', 'updated_at']
        for field in date_fields:
            if row[field] is not None:
                vehicle_data[field] = row[field]
        
        # Campos adicionais
        additional_fields = ['maintenance_notes', 'registered_by']
        for field in additional_fields:
            if row[field] is not None:
                vehicle_data[field] = row[field]
        
        return Vehicle(**vehicle_data)
    
    def save(self, vehicle: Vehicle) -> Vehicle:
        """
        Salva um novo veículo no banco de dados.
        
        Args:
            vehicle: Instância de Vehicle a ser salva
            
        Returns:
            Vehicle salvo com ID atualizado
            
        Raises:
            DuplicatePlateError: Se já existir veículo com a mesma placa
            DatabaseError: Em caso de erro de banco
        """
        logger.info("Salvando veículo: %s (Placa: %s)", vehicle.model, vehicle.plate)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT INTO vehicles (
                        plate, model, color, carrier_cnpj, type, year, chassis_number,
                        fuel_type, capacity_kg, capacity_m3, insurance_policy, insurance_expiry,
                        last_maintenance, next_maintenance, maintenance_notes, status, registered_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    vehicle.plate,
                    vehicle.model,
                    getattr(vehicle, 'color', None),
                    getattr(vehicle, 'carrier_cnpj', None),
                    getattr(vehicle, 'type', 'outro'),
                    getattr(vehicle, 'year', None),
                    getattr(vehicle, 'chassis_number', None),
                    getattr(vehicle, 'fuel_type', None),
                    float(getattr(vehicle, 'capacity_kg', 0)) if getattr(vehicle, 'capacity_kg', None) else None,
                    float(getattr(vehicle, 'capacity_m3', 0)) if getattr(vehicle, 'capacity_m3', None) else None,
                    getattr(vehicle, 'insurance_policy', None),
                    getattr(vehicle, 'insurance_expiry', None),
                    getattr(vehicle, 'last_maintenance', None),
                    getattr(vehicle, 'next_maintenance', None),
                    getattr(vehicle, 'maintenance_notes', None),
                    getattr(vehicle, 'status', 'active'),
                    getattr(vehicle, 'registered_by', None)
                ))
                
                conn.commit()
                vehicle.id = cursor.lastrowid
                
                logger.info(
                    "Veículo salvo com sucesso: %s (ID: %s, Placa: %s)",
                    vehicle.model, vehicle.id, vehicle.plate
                )
                
                return vehicle
                
            except sqlite3.IntegrityError as e:
                if "UNIQUE constraint failed: vehicles.plate" in str(e):
                    raise DuplicatePlateError(f"Já existe um veículo com a placa: {vehicle.plate}")
                else:
                    logger.error("Erro de integridade ao salvar veículo: %s", e)
                    raise DatabaseError(f"Erro de integridade no banco de dados: {str(e)}") from e
            
            except sqlite3.Error as e:
                logger.error("Erro ao salvar veículo: %s", e)
                raise DatabaseError(f"Erro ao salvar veículo: {str(e)}") from e
    
    def find_by_plate(self, plate: str) -> Optional[Vehicle]:
        """
        Busca um veículo pela placa.
        
        Args:
            plate: Placa do veículo
            
        Returns:
            Instância de Vehicle se encontrado, None caso contrário
        """
        logger.debug("Buscando veículo por placa: %s", plate)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("SELECT * FROM vehicles WHERE plate = ?", (plate,))
                row = cursor.fetchone()
                
                if row:
                    vehicle = self._row_to_entity(row)
                    logger.debug("Veículo encontrado: %s (Placa: %s)", vehicle.model, vehicle.plate)
                    return vehicle
                else:
                    logger.debug("Nenhum veículo encontrado com a placa: %s", plate)
                    return None
                    
            except sqlite3.Error as e:
                logger.error("Erro ao buscar veículo por placa %s: %s", plate, e)
                raise DatabaseError(f"Erro ao buscar veículo: {str(e)}") from e
    
    def find_by_id(self, vehicle_id: int) -> Optional[Vehicle]:
        """
        Busca veículo por ID.
        
        Args:
            vehicle_id: ID do veículo
            
        Returns:
            Instância de Vehicle se encontrado, None caso contrário
        """
        logger.debug("Buscando veículo por ID: %s", vehicle_id)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("SELECT * FROM vehicles WHERE id = ?", (vehicle_id,))
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_entity(row)
                return None
                    
            except sqlite3.Error as e:
                logger.error("Erro ao buscar veículo por ID %s: %s", vehicle_id, e)
                raise DatabaseError(f"Erro ao buscar veículo: {str(e)}") from e
    
    def find_by_carrier(self, carrier_cnpj: str, active_only: bool = True) -> List[Vehicle]:
        """
        Busca veículos por CNPJ da transportadora.
        
        Args:
            carrier_cnpj: CNPJ da transportadora
            active_only: Se True, retorna apenas veículos ativos
            
        Returns:
            Lista de veículos da transportadora
        """
        logger.debug("Buscando veículos da transportadora: %s", carrier_cnpj)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                if active_only:
                    cursor.execute("""
                        SELECT * FROM vehicles 
                        WHERE carrier_cnpj = ? AND status = 'active'
                        ORDER BY model
                    """, (carrier_cnpj,))
                else:
                    cursor.execute("""
                        SELECT * FROM vehicles 
                        WHERE carrier_cnpj = ?
                        ORDER BY model
                    """, (carrier_cnpj,))
                
                rows = cursor.fetchall()
                vehicles = [self._row_to_entity(row) for row in rows]
                
                logger.debug("Encontrados %d veículos para a transportadora %s", len(vehicles), carrier_cnpj)
                return vehicles
                    
            except sqlite3.Error as e:
                logger.error("Erro ao buscar veículos da transportadora %s: %s", carrier_cnpj, e)
                raise DatabaseError(f"Erro ao buscar veículos: {str(e)}") from e
    
    def find_all(self, active_only: bool = True) -> List[Vehicle]:
        """
        Busca todos os veículos cadastrados.
        
        Args:
            active_only: Se True, retorna apenas veículos ativos
            
        Returns:
            Lista de todos os veículos
        """
        logger.debug("Buscando todos os veículos (active_only: %s)", active_only)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                if active_only:
                    cursor.execute("SELECT * FROM vehicles WHERE status = 'active' ORDER BY model")
                else:
                    cursor.execute("SELECT * FROM vehicles ORDER BY model")
                
                rows = cursor.fetchall()
                vehicles = [self._row_to_entity(row) for row in rows]
                
                logger.debug("Encontrados %d veículos", len(vehicles))
                return vehicles
                    
            except sqlite3.Error as e:
                logger.error("Erro ao buscar todos os veículos: %s", e)
                raise DatabaseError(f"Erro ao buscar veículos: {str(e)}") from e
    
    def update(self, vehicle: Vehicle) -> Vehicle:
        """
        Atualiza um veículo existente.
        
        Args:
            vehicle: Instância de Vehicle com dados atualizados
            
        Returns:
            Vehicle atualizado
            
        Raises:
            VehicleNotFoundError: Se o veículo não for encontrado
            DatabaseError: Em caso de erro de banco
        """
        logger.info("Atualizando veículo ID: %s", vehicle.id)
        
        if not vehicle.id:
            raise VehicleNotFoundError("Veículo não possui ID para atualização")
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    UPDATE vehicles SET
                        plate = ?, model = ?, color = ?, carrier_cnpj = ?, type = ?, year = ?, 
                        chassis_number = ?, fuel_type = ?, capacity_kg = ?, capacity_m3 = ?,
                        insurance_policy = ?, insurance_expiry = ?, last_maintenance = ?,
                        next_maintenance = ?, maintenance_notes = ?, status = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    vehicle.plate,
                    vehicle.model,
                    getattr(vehicle, 'color', None),
                    getattr(vehicle, 'carrier_cnpj', None),
                    getattr(vehicle, 'type', 'outro'),
                    getattr(vehicle, 'year', None),
                    getattr(vehicle, 'chassis_number', None),
                    getattr(vehicle, 'fuel_type', None),
                    float(getattr(vehicle, 'capacity_kg', 0)) if getattr(vehicle, 'capacity_kg', None) else None,
                    float(getattr(vehicle, 'capacity_m3', 0)) if getattr(vehicle, 'capacity_m3', None) else None,
                    getattr(vehicle, 'insurance_policy', None),
                    getattr(vehicle, 'insurance_expiry', None),
                    getattr(vehicle, 'last_maintenance', None),
                    getattr(vehicle, 'next_maintenance', None),
                    getattr(vehicle, 'maintenance_notes', None),
                    getattr(vehicle, 'status', 'active'),
                    vehicle.id
                ))
                
                if cursor.rowcount == 0:
                    raise VehicleNotFoundError(f"Veículo com ID {vehicle.id} não encontrado")
                
                conn.commit()
                logger.info("Veículo atualizado com sucesso: ID %s", vehicle.id)
                
                return vehicle
                
            except sqlite3.IntegrityError as e:
                if "UNIQUE constraint failed: vehicles.plate" in str(e):
                    raise DuplicatePlateError(f"Já existe outro veículo com a placa: {vehicle.plate}")
                else:
                    logger.error("Erro de integridade ao atualizar veículo: %s", e)
                    raise DatabaseError(f"Erro de integridade no banco de dados: {str(e)}") from e
            
            except sqlite3.Error as e:
                logger.error("Erro ao atualizar veículo ID %s: %s", vehicle.id, e)
                raise DatabaseError(f"Erro ao atualizar veículo: {str(e)}") from e
    
    def update_status(self, vehicle_id: int, new_status: str) -> bool:
        """
        Atualiza o status de um veículo.
        
        Args:
            vehicle_id: ID do veículo
            new_status: Novo status
            
        Returns:
            True se atualizado com sucesso
        """
        logger.info("Atualizando status do veículo ID %s para: %s", vehicle_id, new_status)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    UPDATE vehicles 
                    SET status = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                """, (new_status, vehicle_id))
                
                if cursor.rowcount == 0:
                    raise VehicleNotFoundError(f"Veículo com ID {vehicle_id} não encontrado")
                
                conn.commit()
                logger.info("Status do veículo ID %s atualizado para: %s", vehicle_id, new_status)
                return True
                
            except sqlite3.Error as e:
                logger.error("Erro ao atualizar status do veículo ID %s: %s", vehicle_id, e)
                raise DatabaseError(f"Erro ao atualizar status: {str(e)}") from e
    
    def search(self, query: str, vehicle_type: Optional[str] = None) -> List[Vehicle]:
        """
        Busca veículos por placa, modelo ou número do chassi.
        
        Args:
            query: Termo de busca
            vehicle_type: Filtro por tipo de veículo (opcional)
            
        Returns:
            Lista de veículos encontrados
        """
        logger.debug("Buscando veículos com query: '%s', tipo: %s", query, vehicle_type)
        
        search_term = f"%{query.strip()}%" if query else "%"
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                if vehicle_type:
                    cursor.execute("""
                        SELECT * FROM vehicles 
                        WHERE (plate LIKE ? OR model LIKE ? OR chassis_number LIKE ?) 
                        AND type = ? AND status = 'active'
                        ORDER BY model
                    """, (search_term, search_term, search_term, vehicle_type))
                else:
                    cursor.execute("""
                        SELECT * FROM vehicles 
                        WHERE (plate LIKE ? OR model LIKE ? OR chassis_number LIKE ?) 
                        AND status = 'active'
                        ORDER BY model
                    """, (search_term, search_term, search_term))
                
                rows = cursor.fetchall()
                vehicles = [self._row_to_entity(row) for row in rows]
                
                logger.debug("Encontrados %d veículos na busca", len(vehicles))
                return vehicles
                    
            except sqlite3.Error as e:
                logger.error("Erro ao buscar veículos: %s", e)
                raise DatabaseError(f"Erro na busca de veículos: {str(e)}") from e
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas dos veículos.
        
        Returns:
            Dicionário com estatísticas
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN status = 'active' THEN 1 END) as active,
                        COUNT(CASE WHEN status = 'inactive' THEN 1 END) as inactive,
                        COUNT(CASE WHEN status = 'maintenance' THEN 1 END) as maintenance,
                        COUNT(CASE WHEN status = 'suspended' THEN 1 END) as suspended,
                        COUNT(DISTINCT carrier_cnpj) as total_carriers,
                        AVG(capacity_kg) as avg_capacity_kg,
                        AVG(capacity_m3) as avg_capacity_m3,
                        MIN(created_at) as oldest,
                        MAX(created_at) as newest
                    FROM vehicles
                """)
                
                row = cursor.fetchone()
                
                # Contagem por tipo
                cursor.execute("""
                    SELECT type, COUNT(*) as count
                    FROM vehicles 
                    WHERE status = 'active'
                    GROUP BY type
                    ORDER BY count DESC
                """)
                
                type_counts = cursor.fetchall()
                
                return {
                    'total': row['total'],
                    'active': row['active'],
                    'inactive': row['inactive'],
                    'maintenance': row['maintenance'],
                    'suspended': row['suspended'],
                    'total_carriers': row['total_carriers'],
                    'avg_capacity_kg': row['avg_capacity_kg'],
                    'avg_capacity_m3': row['avg_capacity_m3'],
                    'oldest_registration': row['oldest'],
                    'newest_registration': row['newest'],
                    'type_breakdown': [
                        {'type': row['type'], 'count': row['count']}
                        for row in type_counts
                    ]
                }
                    
            except sqlite3.Error as e:
                logger.error("Erro ao obter estatísticas: %s", e)
                raise DatabaseError(f"Erro ao obter estatísticas: {str(e)}") from e


# Exemplo de uso
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    try:
        repo = VehicleRepository()
        
        # Teste de criação de veículo
        vehicle = Vehicle(
            plate="ABC1D23",
            model="Volvo FH 540",
            color="Azul",
            type="caminhao",
            year=2023,
            carrier_cnpj="12345678000195",
            chassis_number="9BR12345678901234",
            fuel_type="diesel",
            capacity_kg=Decimal('25000'),
            capacity_m3=Decimal('80')
        )
        
        saved_vehicle = repo.save(vehicle)
        print(f"Veículo salvo: {saved_vehicle.model} (ID: {saved_vehicle.id})")
        
        # Teste de busca
        found_vehicle = repo.find_by_plate("ABC1D23")
        if found_vehicle:
            print(f"Veículo encontrado: {found_vehicle.model}")
        
        # Estatísticas
        stats = repo.get_stats()
        print(f"Estatísticas: {stats}")
        
    except Exception as e:
        print(f"Erro: {e}")