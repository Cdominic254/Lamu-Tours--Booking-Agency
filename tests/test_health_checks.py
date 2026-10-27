from unittest.mock import patch

from sqlalchemy.exc import SQLAlchemyError

from app import app


def test_health_check_reports_process_is_running():
    response = app.test_client().get('/healthz')

    assert response.status_code == 200
    assert response.get_json() == {'status': 'ok'}


def test_readiness_check_reports_database_is_available():
    response = app.test_client().get('/readyz')

    assert response.status_code == 200
    assert response.get_json() == {'status': 'ready'}


def test_readiness_check_requires_database_connection():
    with patch('app.db.session.execute', side_effect=SQLAlchemyError('database unavailable')):
        response = app.test_client().get('/readyz')

    assert response.status_code == 503
    assert response.get_json() == {'status': 'unavailable'}
