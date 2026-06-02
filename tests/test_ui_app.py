from securebox.ui.app import SecureBoxAppState


def test_app_state_initializes_local_database(tmp_path) -> None:
    db_path = tmp_path / "securebox.sqlite3"

    state = SecureBoxAppState.create(db_path)

    assert state.db_path == db_path
    assert state.auth_service.is_initialized() is False

