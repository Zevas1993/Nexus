"""
Authentication services for Nexus AI Assistant.

This module provides authentication and authorization functionality.
"""
import logging
import time
import json
from typing import Dict, Any, Optional
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    logger.warning("JWT library not available, authentication will be limited")

class AuthenticationService:
    """Base authentication service interface."""
    
    def __init__(self, app_context=None, config=None):
        """Initialize authentication service.
        
        Args:
            app_context: Application context
            config: Configuration dictionary
        """
        self.app_context = app_context
        self.config = config or {}
        
    async def authenticate(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Authenticate a user with credentials.
        
        Args:
            credentials: Authentication credentials
            
        Returns:
            Authentication result
        """
        raise NotImplementedError("Subclasses must implement this")
        
    async def authorize(self, token: str, required_scope: str = None) -> Dict[str, Any]:
        """Verify and authorize a token.
        
        Args:
            token: Authentication token
            required_scope: Required scope for authorization
            
        Returns:
            Authorization result
        """
        raise NotImplementedError("Subclasses must implement this")

class JwtAuthenticationService(AuthenticationService):
    """JWT-based authentication service."""
    
    def __init__(self, app_context=None, config=None):
        """Initialize JWT authentication service.
        
        Args:
            app_context: Application context
            config: Configuration dictionary
        """
        super().__init__(app_context, config)
        self.secret_key = self.config.get("SECRET_KEY", os.urandom(32).hex())
        self.token_expiration = self.config.get("TOKEN_EXPIRATION", 86400)  # 1 day in seconds
        self.algorithm = self.config.get("JWT_ALGORITHM", "HS256")
        self.google_client_id = self.config.get("GOOGLE_CLIENT_ID", "")
        
    async def authenticate(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Authenticate a user with credentials.
        
        Args:
            credentials: Authentication credentials
            
        Returns:
            Authentication result with JWT token
        """
        if not JWT_AVAILABLE:
            return {"status": "error", "message": "JWT library not available"}
            
        auth_type = credentials.get("type", "password")
        
        if auth_type == "password":
            return await self._authenticate_password(credentials)
        elif auth_type == "google":
            return await self._authenticate_google(credentials)
        else:
            return {"status": "error", "message": f"Unsupported authentication type: {auth_type}"}
            
    async def _authenticate_password(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Authenticate with username and password.
        
        Args:
            credentials: Authentication credentials
            
        Returns:
            Authentication result with JWT token
        """
        username = credentials.get("username", "")
        password = credentials.get("password", "")
        
        # In a real implementation, this would verify against a database
        # For this example, we'll accept any non-empty username/password
        if not username or not password:
            return {"status": "error", "message": "Invalid username or password"}
            
        # Create a token
        payload = {
            "sub": username,
            "exp": datetime.utcnow() + timedelta(seconds=self.token_expiration),
            "iat": datetime.utcnow(),
            "scope": "user",
            "email": username,
            "auth_type": "password"
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        return {
            "status": "success",
            "token": token,
            "user": {
                "username": username,
                "email": username,
                "scope": "user"
            }
        }
        
    async def _authenticate_google(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Authenticate with Google ID token.
        
        Args:
            credentials: Authentication credentials
            
        Returns:
            Authentication result with JWT token
        """
        id_token = credentials.get("id_token", "")
        
        if not id_token:
            return {"status": "error", "message": "No ID token provided"}
            
        try:
            # Verify the Google ID token
            # In a real implementation, this would use google.oauth2.id_token.verify_oauth2_token
            # For this example, we'll just decode the token without verification
            try:
                from google.oauth2 import id_token
                from google.auth.transport import requests as google_requests
                
                idinfo = id_token.verify_oauth2_token(
                    id_token, google_requests.Request(), self.google_client_id)
                    
                # Get user info from the token
                user_id = idinfo["sub"]
                email = idinfo["email"]
                name = idinfo.get("name", "")
                
            except ImportError:
                # Fall back to just decoding the token without verification
                logger.warning("Google Auth library not available, falling back to unsafe token decoding")
                
                # This is unsafe and should not be used in production!
                import base64
                import json
                
                # Decode the token parts
                token_parts = id_token.split(".")
                if len(token_parts) < 2:
                    return {"status": "error", "message": "Invalid token format"}
                    
                # Decode the payload
                padded_payload = token_parts[1] + "=" * (-len(token_parts[1]) % 4)
                payload_bytes = base64.b64decode(padded_payload)
                payload = json.loads(payload_bytes)
                
                # Extract user info
                user_id = payload.get("sub", "")
                email = payload.get("email", "")
                name = payload.get("name", "")
                
            # Create a new JWT token
            payload = {
                "sub": user_id,
                "exp": datetime.utcnow() + timedelta(seconds=self.token_expiration),
                "iat": datetime.utcnow(),
                "scope": "user",
                "email": email,
                "name": name,
                "auth_type": "google"
            }
            
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            
            return {
                "status": "success",
                "token": token,
                "user": {
                    "user_id": user_id,
                    "email": email,
                    "name": name,
                    "scope": "user"
                }
            }
        except Exception as e:
            logger.error(f"Error authenticating with Google: {str(e)}")
            return {"status": "error", "message": f"Google authentication failed: {str(e)}"}
            
    async def authorize(self, token: str, required_scope: str = None) -> Dict[str, Any]:
        """Verify and authorize a token.
        
        Args:
            token: Authentication token
            required_scope: Required scope for authorization
            
        Returns:
            Authorization result
        """
        if not JWT_AVAILABLE:
            return {"status": "error", "message": "JWT library not available"}
            
        try:
            # Decode and verify the token
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check if token is expired
            exp = payload.get("exp", 0)
            if exp < time.time():
                return {"status": "error", "message": "Token expired"}
                
            # Check scope if required
            if required_scope:
                token_scope = payload.get("scope", "")
                if required_scope not in token_scope.split():
                    return {"status": "error", "message": f"Insufficient scope, {required_scope} required"}
                    
            return {
                "status": "success",
                "user": {
                    "user_id": payload.get("sub", ""),
                    "email": payload.get("email", ""),
                    "name": payload.get("name", ""),
                    "scope": payload.get("scope", "")
                }
            }
        except jwt.ExpiredSignatureError:
            return {"status": "error", "message": "Token expired"}
        except jwt.InvalidTokenError as e:
            return {"status": "error", "message": f"Invalid token: {str(e)}"}
        except Exception as e:
            logger.error(f"Error authorizing token: {str(e)}")
            return {"status": "error", "message": f"Authorization failed: {str(e)}"}
            
    def create_token(self, user_id: str, email: str, scope: str = "user", 
                   expiration: int = None, **kwargs) -> str:
        """Create a new JWT token.
        
        Args:
            user_id: User ID
            email: User email
            scope: Token scope
            expiration: Token expiration in seconds
            **kwargs: Additional payload fields
            
        Returns:
            JWT token
        """
        if not JWT_AVAILABLE:
            raise ValueError("JWT library not available")
            
        expiration = expiration or self.token_expiration
        
        payload = {
            "sub": user_id,
            "exp": datetime.utcnow() + timedelta(seconds=expiration),
            "iat": datetime.utcnow(),
            "scope": scope,
            "email": email,
            **kwargs
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
    def refresh_token(self, token: str, expiration: int = None) -> Dict[str, Any]:
        """Refresh a JWT token.
        
        Args:
            token: Authentication token
            expiration: New token expiration in seconds
            
        Returns:
            Refresh result with new token
        """
        if not JWT_AVAILABLE:
            return {"status": "error", "message": "JWT library not available"}
            
        try:
            # Decode and verify the token
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Create a new token with the same payload but updated expiration
            expiration = expiration or self.token_expiration
            payload["exp"] = datetime.utcnow() + timedelta(seconds=expiration)
            payload["iat"] = datetime.utcnow()
            
            new_token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            
            return {
                "status": "success",
                "token": new_token,
                "user": {
                    "user_id": payload.get("sub", ""),
                    "email": payload.get("email", ""),
                    "name": payload.get("name", ""),
                    "scope": payload.get("scope", "")
                }
            }
        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}")
            return {"status": "error", "message": f"Token refresh failed: {str(e)}"}
