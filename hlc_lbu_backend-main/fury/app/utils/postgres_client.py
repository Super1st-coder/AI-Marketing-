"""PostgreSQL client wrapper"""
from typing import Optional
from uuid import UUID, uuid5, NAMESPACE_DNS
import psycopg
from langchain_postgres import PostgresChatMessageHistory, PGEngine
from core.config import settings
from core.exceptions import FuryException
from core.logging import get_logger

logger = get_logger(__name__)


class PostgresClientWrapper:
    """Wrapper for PostgreSQL operations"""
    
    def __init__(self, connection_string: Optional[str] = None):
        self.connection_string = connection_string or settings.POSTGRES_CONNECTION_STRING
        self._engine = None
        self._connection = None
    
    def _get_connection_string_for_psycopg(self) -> str:
        """Convert SQLAlchemy connection string to psycopg format"""
        if self.connection_string.startswith("postgresql+psycopg://"):
            return self.connection_string.replace("postgresql+psycopg://", "postgresql://", 1)
        return self.connection_string
    
    def _get_connection(self) -> psycopg.Connection:
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
    
    def _get_engine(self) -> PGEngine:
        """Get or create PGEngine instance"""
        if self._engine is None:
            self._engine = PGEngine.from_connection_string(url=self.connection_string)
        return self._engine
    
    @staticmethod
    def _normalize_session_id(session_id: str) -> str:
        """
        Ensure the session id is a UUID.
        LangChain's Postgres history enforces UUID-formatted session ids.
        """
        if not session_id:
            generated = uuid5(NAMESPACE_DNS, "default-session")
            logger.warning("Empty session id received. Generated deterministic fallback UUID.")
            return str(generated)
        
        try:
            return str(UUID(session_id))
        except (ValueError, AttributeError, TypeError):
            generated = uuid5(NAMESPACE_DNS, session_id)
            logger.info(
                "Session id '%s' is not a valid UUID. Using deterministic UUID '%s' instead.",
                session_id,
                generated,
            )
            return str(generated)
    
    def get_chat_memory(self, session_id: str) -> PostgresChatMessageHistory:
        """Get chat memory for session"""
        normalized_session_id = self._normalize_session_id(session_id)
        try:
            sync_connection = self._get_connection()
            # Ensure tables exist (idempotent operation)
            PostgresChatMessageHistory.create_tables(sync_connection, "langchain")
            
            memory = PostgresChatMessageHistory(
                "langchain",
                normalized_session_id,
                sync_connection=sync_connection
            )
            logger.info(f"Created chat memory for session: {normalized_session_id}")
            return memory
        except Exception as e:
            logger.error(f"Failed to create chat memory: {str(e)}")
            raise FuryException(
                message="Failed to create chat memory",
                details={"error": str(e), "session_id": normalized_session_id}
            )
    
    def clear_chat_memory(self, session_id: str) -> None:
        """Clear chat memory for session"""
        try:
            memory = self.get_chat_memory(session_id)
            memory.clear()
            logger.info(f"Cleared chat memory for session: {memory.session_id}")
        except Exception as e:
            logger.error(f"Failed to clear chat memory: {str(e)}")
            raise FuryException(
                message="Failed to clear chat memory",
                details={"error": str(e), "session_id": session_id}
            )

