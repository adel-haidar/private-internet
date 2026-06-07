import psycopg2
from personal_intelligence.config import get_settings


def _connect():
    s = get_settings()
    return psycopg2.connect(
        host=s.db_host, dbname=s.db_name, user=s.db_user, password=s.db_password
    )
