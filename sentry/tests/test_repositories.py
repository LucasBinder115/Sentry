"""Unit tests for the SENTRY system."""

import unittest
from unittest.mock import Mock, patch
from datetime import datetime

from sentry.data.database import (
    VehicleRepository, 
    CarrierRepository,
    AccessLogRepository
)

class TestVehicleRepository(unittest.TestCase):
    """Test vehicle repository operations."""

    def setUp(self):
        """Setup test database."""
        self.repo = VehicleRepository()

    def test_create_vehicle(self):
        """Test creating a new vehicle."""
        data = self.repo.create_vehicle(
            plate="ABC1234",
            model="Test Model",
            color="Black"
        )
        self.assertIsNotNone(data)
        self.assertEqual(data['plate'], "ABC1234")

    def test_duplicate_plate(self):
        """Test handling duplicate plate numbers."""
        self.repo.create_vehicle("XYZ5678", "Test Model")
        with self.assertRaises(ValueError):
            self.repo.create_vehicle("XYZ5678", "Another Model")

class TestAccessLogs(unittest.TestCase):
    """Test access log operations."""

    def setUp(self):
        """Setup test database and repositories."""
        self.vehicle_repo = VehicleRepository()
        self.log_repo = AccessLogRepository()

    def test_log_access(self):
        """Test logging vehicle access."""
        # Create test vehicle
        vehicle = self.vehicle_repo.create_vehicle(
            plate="TEST123",
            model="Test Model"
        )

        # Log entry
        log = self.log_repo.log_access(
            vehicle_id=vehicle['id'],
            access_type="ENTRY"
        )

        self.assertIsNotNone(log)
        self.assertEqual(log['vehicle_id'], vehicle['id'])
        self.assertEqual(log['type'], "ENTRY")

class TestCarrierRepository(unittest.TestCase):
    """Test carrier repository operations."""

    def setUp(self):
        """Setup test database."""
        self.repo = CarrierRepository()

    def test_create_carrier(self):
        """Test creating a new carrier."""
        data = self.repo.create_carrier(
            name="Test Carrier",
            cnpj="12345678901234",
            contact_phone="123456789"
        )
        self.assertIsNotNone(data)
        self.assertEqual(data['name'], "Test Carrier")

    def test_invalid_cnpj(self):
        """Test handling invalid CNPJ."""
        with self.assertRaises(ValueError):
            self.repo.create_carrier(
                name="Test",
                cnpj="123"  # Invalid CNPJ
            )