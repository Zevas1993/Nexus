"""
Authentication service for Nexus AI Assistant.

This module provides authentication services using JWT tokens 
and integration with Google OAuth.
"""
import jwt
import time
import logging
from typing import Dict, Any, Optional
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

logger = logging.getLogger(__name__)

class JwtAuthenticationService:
    """Authentication service using JWT tokens."""
    
    def __init__(self, config=None):
        """Initialize authentication service.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.secret_key = self.config.get("SECRET_KEY", "default_secret_key")
        self.token_expiry = self.config.get("TOKEN_EXPIRY", 3600)  # 1 hour
        self.google_client_id = self.config.get("GOOGLE_CLIENT_ID", "")
        logger.info("JWT Authentication service initialized")
        
    def generate_token(self, user_id: str, additional_claims: Dict[str, Any] = None) -> str:
        """Generate a JWT token for a user.
        
        Args:
            user_id: User ID
            additional_claims: Additional claims to include in the token
            
        Returns:
            JWT token
        """
        now = int(time.time())
        claims = {
            "sub": user_id,
            "iat": now,
            "exp": now + self.token_expiry
        }
        
        if additional_claims:
            claims.update(additional_claims)
            
        token = jwt.encode(claims, self.secret_key, algorithm="HS256")
        logger.info(f"Generated token for user {user_id}")
        return token
        
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify a JWT token.
        
        Args:
            token: JWT token
            
        Returns:
            Token claims if valid, None otherwise
        """
        try:
            claims = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            logger.info(f"Verified token for user {claims.get('sub')}")
            return claims
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            return None
            
    def verify_google_token(self, id_token_str: str) -> Optional[Dict[str, Any]]:
        """Verify a Google ID token.
        
        Args:
            id_token_str: Google ID token string
            
        Returns:
            Token claims if valid, None otherwise
        """
        try:
            if not self.google_client_id:
                logger.error("Google client ID not configured")
                return None
                
            idinfo = id_token.verify_oauth2_token(
                id_token_str, 
                google_requests.Request(), 
                self.google_client_id
            )
            
            # Check issuer
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                logger.warning("Invalid issuer")
                return None
                
            # Token is valid, extract user info
            user_id = idinfo.get('sub')
            email = idinfo.get('email')
            name = idinfo.get('name')
            picture = idinfo.get('picture')
            
            logger.info(f"Verified Google token for user {email}")
            
            return {
                "user_id": user_id,
                "email": email,
                "name": name,
                "picture": picture
            }
        except ValueError as e:
            logger.error(f"Invalid Google token: {str(e)}")
            return None
            
    def refresh_token(self, token: str) -> Optional[str]:
        """Refresh a JWT token.
        
        Args:
            token: JWT token
            
        Returns:
            New JWT token if valid, None otherwise
        """
        claims = self.verify_token(token)
        if not claims:
            return None
            
        # Get user ID from claims
        user_id = claims.get('sub')
        
        # Remove time-related claims
        for key in ['exp', 'iat']:
            if key in claims:
                del claims[key]
                
        # Generate new token
        return self.generate_token(user_id, claims)
