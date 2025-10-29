"""Tests for authentication presenter."""

import unittest
from unittest.mock import Mock

from sentry.ui.presenters.auth_presenter import AuthPresenter

class TestAuthPresenter(unittest.TestCase):
    """Test authentication presenter functionality."""

    def setUp(self):
        """Set up test environment."""
        self.mock_view = Mock()
        self.presenter = AuthPresenter(self.mock_view)

    def test_login_success(self):
        """Test successful login."""
        result = self.presenter.login("admin", "admin")
        self.assertIsNotNone(result)
        self.assertEqual(result["username"], "admin")
        self.assertEqual(result["role"], "admin")

    def test_login_failure(self):
        """Test failed login."""
        result = self.presenter.login("wrong", "wrong")
        self.assertIsNone(result)

    def test_logout(self):
        """Test logout functionality."""
        result = self.presenter.logout()
        self.assertTrue(result)

if __name__ == '__main__':
    unittest.main()