"""
OAuth integration for Nexus AI Assistant.

This module provides OAuth-based authentication with various providers.
"""

from typing import Dict, Any, Optional
import logging
import json
import requests
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

logger = logging.getLogger(__name__)

class OAuthService:
    """OAuth authentication service."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize OAuth service.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.google_client_id = config.get('GOOGLE_CLIENT_ID', '')
    
    def verify_google_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify Google ID token.
        
        Args:
            token: Google ID token
            
        Returns:
            User information if token is valid, None otherwise
        """
        try:
            idinfo = id_token.verify_oauth2_token(
                token, 
                google_requests.Request(), 
                self.google_client_id
            )
            
            # Verify issuer
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                logger.warning("Invalid issuer for Google token")
                return None
            
            # Get user information
            user_info = {
                'email': idinfo['email'],
                'name': idinfo.get('name', ''),
                'picture': idinfo.get('picture', ''),
                'sub': idinfo['sub']
            }
            
            logger.info(f"Verified Google token for user: {user_info['email']}")
            return user_info
        except ValueError as e:
            logger.warning(f"Invalid Google token: {str(e)}")
            return None
    
    def get_user_profile(self, provider: str, token: str) -> Optional[Dict[str, Any]]:
        """Get user profile from OAuth provider.
        
        Args:
            provider: OAuth provider (google, github, etc.)
            token: OAuth token
            
        Returns:
            User profile if token is valid, None otherwise
        """
        if provider == 'google':
            return self.verify_google_token(token)
        else:
            logger.warning(f"Unsupported OAuth provider: {provider}")
            return None
