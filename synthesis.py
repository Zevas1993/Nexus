"""
Text-to-speech service for Nexus AI Assistant.

This module provides text-to-speech functionality using various providers.
"""

from typing import Dict, Any, Optional, Union
import logging
import os
import tempfile
import pyttsx3
from ..base import SyncService

logger = logging.getLogger(__name__)

class SynthesisService(SyncService):
    """Service for text-to-speech synthesis."""
    
    def __init__(self, app_context=None, config=None):
        """Initialize text-to-speech service.
        
        Args:
            app_context: Application context
            config: Configuration dictionary
        """
        super().__init__(app_context, config)
        self.provider = config.get('TTS_PROVIDER', 'pyttsx3') if config else 'pyttsx3'
        self.voice_id = config.get('TTS_VOICE_ID') if config else None
        self.rate = config.get('TTS_RATE', 200) if config else 200
        self.volume = config.get('TTS_VOLUME', 1.0) if config else 1.0
        
        # Initialize engine if using pyttsx3
        self.engine = None
        if self.provider == 'pyttsx3':
            self._init_pyttsx3()
    
    def _init_pyttsx3(self):
        """Initialize pyttsx3 engine."""
        try:
            self.engine = pyttsx3.init()
            
            # Set properties
            self.engine.setProperty('rate', self.rate)
            self.engine.setProperty('volume', self.volume)
            
            # Set voice if specified
            if self.voice_id:
                self.engine.setProperty('voice', self.voice_id)
            
            self.logger.info("Initialized pyttsx3 engine")
        except Exception as e:
            self.logger.error(f"Error initializing pyttsx3 engine: {str(e)}")
            self.engine = None
    
    def _process_impl(self, request: str, **kwargs) -> Dict[str, Any]:
        """Implementation of request processing.
        
        Args:
            request: Text to synthesize
            **kwargs: Additional parameters
                - output_file: Path to save audio file
                - wait: Whether to wait for speech to complete
                
        Returns:
            Synthesis result
        """
        output_file = kwargs.get('output_file')
        wait = kwargs.get('wait', True)
        
        if not request:
            return {
                "success": False,
                "error": "No text provided for synthesis"
            }
        
        # Synthesize speech
        try:
            if self.provider == 'pyttsx3':
                return self._synthesize_pyttsx3(request, output_file, wait)
            else:
                self.logger.warning(f"Unsupported provider: {self.provider}, falling back to pyttsx3")
                return self._synthesize_pyttsx3(request, output_file, wait)
        except Exception as e:
            self.logger.error(f"Error synthesizing speech: {str(e)}")
            return {
                "success": False,
                "error": f"Error synthesizing speech: {str(e)}"
            }
    
    def _synthesize_pyttsx3(self, text: str, output_file: Optional[str] = None, 
                           wait: bool = True) -> Dict[str, Any]:
        """Synthesize speech using pyttsx3.
        
        Args:
            text: Text to synthesize
            output_file: Path to save audio file
            wait: Whether to wait for speech to complete
            
        Returns:
            Synthesis result
        """
        if not self.engine:
            self._init_pyttsx3()
            
        if not self.engine:
            return {
                "success": False,
                "error": "Failed to initialize pyttsx3 engine"
            }
        
        # Add text to be spoken
        self.engine.say(text)
        
        # Save to file if requested
        if output_file:
            try:
                self.engine.save_to_file(text, output_file)
                self.logger.info(f"Saved speech to file: {output_file}")
            except Exception as e:
                self.logger.error(f"Error saving speech to file: {str(e)}")
                return {
                    "success": False,
                    "error": f"Error saving speech to file: {str(e)}"
                }
        
        # Run and wait if requested
        if wait:
            self.engine.runAndWait()
        else:
            # Start in non-blocking mode
            self.engine.startLoop(False)
            self.engine.iterate()
        
        return {
            "success": True,
            "text": text,
            "provider": "pyttsx3",
            "output_file": output_file
        }
    
    def get_available_voices(self) -> Dict[str, Any]:
        """Get available voices.
        
        Returns:
            Dictionary of available voices
        """
        if self.provider == 'pyttsx3':
            if not self.engine:
                self._init_pyttsx3()
                
            if not self.engine:
                return {
                    "success": False,
                    "error": "Failed to initialize pyttsx3 engine"
                }
            
            voices = self.engine.getProperty('voices')
            voice_list = []
            
            for voice in voices:
                voice_list.append({
                    "id": voice.id,
                    "name": voice.name,
                    "languages": voice.languages,
                    "gender": voice.gender,
                    "age": voice.age
                })
            
            return {
                "success": True,
                "provider": "pyttsx3",
                "voices": voice_list
            }
        else:
            return {
                "success": False,
                "error": f"Unsupported provider: {self.provider}"
            }
