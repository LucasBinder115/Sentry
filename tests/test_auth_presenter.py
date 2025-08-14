# tests/test_auth_presenter.py
def test_login_success():
    view = MockView()
    presenter = AuthPresenter(view)
    assert presenter.login("admin", "admin123") is True