"""Database connection and query execution layer with read-only access."""

import logging
import os
from contextlib import contextmanager
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool

load_dotenv()

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration from environment variables."""
    
    def __init__(self):
        self.host = os.getenv("DB_HOST", "localhost")
        self.port = int(os.getenv("DB_PORT", "5432"))
        self.database = os.getenv("DB_NAME", "smart_insights")
        self.user = os.getenv("DB_USER", "postgres")
        self.password = os.getenv("DB_PASSWORD", "postgres")
        self.pool_size = int(os.getenv("DB_POOL_SIZE", "5"))
        self.max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    
    @property
    def connection_url(self) -> str:
        """Build PostgreSQL connection URL."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class DatabaseManager:
    """
    Manages database connections with read-only access enforcement.
    
    Uses connection pooling for efficient resource management and
    enforces read-only transactions for security.
    """
    
    _instance: "DatabaseManager | None" = None
    _engine: Engine | None = None
    
    def __new__(cls) -> "DatabaseManager":
        """Singleton pattern to ensure single connection pool."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._engine is None:
            self._config = DatabaseConfig()
            self._initialize_engine()
    
    def _initialize_engine(self) -> None:
        """Initialize SQLAlchemy engine with connection pooling."""
        try:
            self._engine = create_engine(
                self._config.connection_url,
                poolclass=QueuePool,
                pool_size=self._config.pool_size,
                max_overflow=self._config.max_overflow,
                pool_pre_ping=True,  # Verify connections before use
                pool_recycle=3600,   # Recycle connections after 1 hour
                echo=False,          # Set to True for SQL debugging
            )
            logger.info("Database engine initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database engine: {e}")
            raise
    
    @contextmanager
    def get_readonly_connection(self):
        """
        Context manager for read-only database connections.
        
        Sets the transaction to read-only mode at the database level
        for an extra layer of security.
        """
        if self._engine is None:
            raise RuntimeError("Database engine not initialized")
        
        connection = self._engine.connect()
        try:
            # Set transaction to read-only mode
            connection.execute(text("SET TRANSACTION READ ONLY"))
            yield connection
            connection.commit()
        except SQLAlchemyError as e:
            connection.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            connection.close()
    
    def execute_query(
        self,
        query: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute a read-only SQL query and return results as list of dicts.
        
        Args:
            query: SQL query string (should use :param syntax for parameters)
            params: Dictionary of query parameters
        
        Returns:
            List of dictionaries representing rows
        
        Raises:
            ValueError: If query appears to contain write operations
            SQLAlchemyError: On database errors
        """
        # Basic validation to prevent write operations
        self._validate_readonly_query(query)
        
        params = params or {}
        
        logger.debug(f"Executing query: {query[:100]}...")
        
        with self.get_readonly_connection() as conn:
            result = conn.execute(text(query), params)
            
            # Convert to list of dicts
            columns = result.keys()
            rows = [dict(zip(columns, row)) for row in result.fetchall()]
            
            logger.info(f"Query returned {len(rows)} rows")
            return rows
    
    def _validate_readonly_query(self, query: str) -> None:
        """
        Validate that a query doesn't contain write operations.
        
        This is a defense-in-depth measure; the actual protection
        comes from the READ ONLY transaction mode.
        """
        forbidden_keywords = [
            "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER",
            "TRUNCATE", "GRANT", "REVOKE", "EXECUTE", "CALL"
        ]
        
        query_upper = query.upper()
        for keyword in forbidden_keywords:
            # Check for keyword as a whole word
            if f" {keyword} " in f" {query_upper} " or query_upper.startswith(f"{keyword} "):
                raise ValueError(f"Write operations are not allowed: {keyword}")
    
    def health_check(self) -> bool:
        """Check if database connection is healthy."""
        try:
            with self.get_readonly_connection() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def close(self) -> None:
        """Close the database engine and connection pool."""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            logger.info("Database engine closed")


# Global database manager instance
db_manager = DatabaseManager()


def get_db() -> DatabaseManager:
    """Get the database manager instance."""
    return db_manager
