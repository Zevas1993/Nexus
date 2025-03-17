"""
Session service for Nexus AI Assistant.

This module provides session management functionality.
"""

from typing import Dict, Any, List, Optional
import logging
import uuid
import time
from ...infrastructure.context import ApplicationContext

logger = logging.getLogger(__name__)

class SessionService:
    """Service for session management."""
    
    def __init__(self, app_context: ApplicationContext):
        """Initialize session service.
        
        Args:
            app_context: Application context
        """
        self.app_context = app_context
        self.config = app_context.config
        self.cache_service = None
        self.session_ttl = self.config.get('SESSION_TTL', 86400)  # 24 hours by default
        
    def initialize(self):
        """Initialize session service."""
        # Get required services
        if self.app_context:
            from ...infrastructure.cache import RedisCacheService
            self.cache_service = self.app_context.get_service(RedisCacheService)
        
        logger.info("Session service initialized")
    
    def create_session(self, user_id: str, title: str = "Untitled") -> Dict[str, Any]:
        """Create new session.
        
        Args:
            user_id: User ID
            title: Session title
            
        Returns:
            Session data
        """
        session_id = str(uuid.uuid4())
        created_at = int(time.time())
        
        session_data = {
            "id": session_id,
            "user_id": user_id,
            "title": title,
            "created_at": created_at,
            "updated_at": created_at,
            "messages": []
        }
        
        # Cache session data
        if self.cache_service:
            self.cache_service.set(
                f"session:{session_id}:{user_id}", 
                session_data,
                ttl=self.session_ttl
            )
            
            # Add to user's sessions list
            user_sessions = self.cache_service.get(f"user_sessions:{user_id}") or []
            user_sessions.append({
                "id": session_id,
                "title": title,
                "created_at": created_at,
                "updated_at": created_at
            })
            self.cache_service.set(f"user_sessions:{user_id}", user_sessions)
        
        logger.info(f"Created session {session_id} for user {user_id}")
        return session_data
    
    def get_session(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID.
        
        Args:
            session_id: Session ID
            user_id: User ID
            
        Returns:
            Session data or None if not found
        """
        if not self.cache_service:
            return None
            
        session_data = self.cache_service.get(f"session:{session_id}:{user_id}")
        
        # Refresh TTL if session found
        if session_data:
            self.cache_service.set(
                f"session:{session_id}:{user_id}", 
                session_data,
                ttl=self.session_ttl
            )
            
        return session_data
    
    def update_session(self, session_id: str, user_id: str, 
                      updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update session.
        
        Args:
            session_id: Session ID
            user_id: User ID
            updates: Session data to update
            
        Returns:
            Updated session data or None if session not found
        """
        if not self.cache_service:
            return None
            
        session_data = self.cache_service.get(f"session:{session_id}:{user_id}")
        if not session_data:
            return None
            
        # Update session data
        session_data.update(updates)
        session_data["updated_at"] = int(time.time())
        
        # Save updated session
        self.cache_service.set(
            f"session:{session_id}:{user_id}", 
            session_data,
            ttl=self.session_ttl
        )
        
        # Update title in user's sessions list if changed
        if "title" in updates:
            user_sessions = self.cache_service.get(f"user_sessions:{user_id}") or []
            for session in user_sessions:
                if session["id"] == session_id:
                    session["title"] = updates["title"]
                    session["updated_at"] = session_data["updated_at"]
                    break
            self.cache_service.set(f"user_sessions:{user_id}", user_sessions)
        
        logger.info(f"Updated session {session_id} for user {user_id}")
        return session_data
    
    def add_message(self, session_id: str, user_id: str, 
                   message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Add message to session.
        
        Args:
            session_id: Session ID
            user_id: User ID
            message: Message data
            
        Returns:
            Updated session data or None if session not found
        """
        if not self.cache_service:
            return None
            
        session_data = self.cache_service.get(f"session:{session_id}:{user_id}")
        if not session_data:
            return None
            
        # Add message ID and timestamp if not provided
        if "id" not in message:
            message["id"] = str(uuid.uuid4())
        if "timestamp" not in message:
            message["timestamp"] = int(time.time())
            
        # Add message to session
        session_data["messages"].append(message)
        session_data["updated_at"] = message["timestamp"]
        
        # Save updated session
        self.cache_service.set(
            f"session:{session_id}:{user_id}", 
            session_data,
            ttl=self.session_ttl
        )
        
        # Update timestamp in user's sessions list
        user_sessions = self.cache_service.get(f"user_sessions:{user_id}") or []
        for session in user_sessions:
            if session["id"] == session_id:
                session["updated_at"] = session_data["updated_at"]
                break
        self.cache_service.set(f"user_sessions:{user_id}", user_sessions)
        
        logger.info(f"Added message to session {session_id} for user {user_id}")
        return session_data
    
    def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all sessions for user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of session summaries
        """
        if not self.cache_service:
            return []
            
        user_sessions = self.cache_service.get(f"user_sessions:{user_id}") or []
        
        # Sort by updated_at (most recent first)
        user_sessions.sort(key=lambda s: s.get("updated_at", 0), reverse=True)
        
        return user_sessions
    
    def delete_session(self, session_id: str, user_id: str) -> bool:
        """Delete session.
        
        Args:
            session_id: Session ID
            user_id: User ID
            
        Returns:
            True if session was deleted, False otherwise
        """
        if not self.cache_service:
            return False
            
        # Delete session data
        deleted = self.cache_service.delete(f"session:{session_id}:{user_id}")
        
        # Remove from user's sessions list
        if deleted:
            user_sessions = self.cache_service.get(f"user_sessions:{user_id}") or []
            user_sessions = [s for s in user_sessions if s["id"] != session_id]
            self.cache_service.set(f"user_sessions:{user_id}", user_sessions)
            logger.info(f"Deleted session {session_id} for user {user_id}")
            
        return deleted
