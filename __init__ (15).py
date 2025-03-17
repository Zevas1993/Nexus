"""
Database package for Nexus AI Assistant.

This package contains database connection and model definitions.
"""

from typing import Dict, Any, Optional
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

logger = logging.getLogger(__name__)

Base = declarative_base()

class DatabaseService:
    """Database service for SQLAlchemy integration."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize database service.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.database_url = config.get('DATABASE_URL', 'sqlite:///app.db')
        self.engine = None
        self.session_factory = None
        self.Session = None
        
    def initialize(self):
        """Initialize database connection and session factory."""
        try:
            self.engine = create_engine(
                self.database_url,
                pool_pre_ping=True,
                pool_recycle=3600,
                connect_args={"check_same_thread": False} if self.database_url.startswith('sqlite') else {}
            )
            self.session_factory = sessionmaker(bind=self.engine)
            self.Session = scoped_session(self.session_factory)
            logger.info(f"Database initialized with URL: {self.database_url}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise
    
    def create_tables(self):
        """Create all tables defined in models."""
        Base.metadata.create_all(self.engine)
        logger.info("Database tables created")
    
    def get_session(self):
        """Get a new database session.
        
        Returns:
            SQLAlchemy session
        """
        if not self.Session:
            self.initialize()
        return self.Session()
    
    def close_session(self, session):
        """Close database session.
        
        Args:
            session: SQLAlchemy session
        """
        session.close()
