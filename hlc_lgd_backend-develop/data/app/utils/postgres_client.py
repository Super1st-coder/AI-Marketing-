"""PostgreSQL client wrapper"""
from typing import Optional
import psycopg
from core.config import settings
from core.exceptions import FuryException
from core.logging import get_logger

logger = get_logger(__name__)


class PostgresClientWrapper:
    """Wrapper for PostgreSQL operations"""
    
    def __init__(self, connection_string: Optional[str] = None):
        self.connection_string = connection_string or settings.POSTGRES_CONNECTION_STRING
        self._connection = None
    
    def _get_connection_string_for_psycopg(self) -> str:
        """Convert SQLAlchemy connection string to psycopg format"""
        if self.connection_string.startswith("postgresql+psycopg://"):
            return self.connection_string.replace("postgresql+psycopg://", "postgresql://", 1)
        return self.connection_string
    
    def get_connection(self) -> psycopg.Connection:
        """Get or create psycopg connection"""
        if self._connection is None:
            psycopg_conn_string = self._get_connection_string_for_psycopg()
            self._connection = psycopg.connect(psycopg_conn_string)
        else:
            try:
                with self._connection.cursor() as cur:
                    cur.execute("SELECT 1")
            except (psycopg.OperationalError, psycopg.InterfaceError):
                psycopg_conn_string = self._get_connection_string_for_psycopg()
                self._connection = psycopg.connect(psycopg_conn_string)
        return self._connection
