"""
Speech recognition service for Nexus AI Assistant.

This module provides speech-to-text functionality using various providers.
"""

from typing import Dict, Any, Optional
import logging
import speech_recognition as sr
from ..base import SyncService

logger = logging.getLogger(__name__)

class RecognitionService(SyncService):
    """Service for speech recognition."""
    
    def __init__(self, app_context=None, config=None):
        """Initialize speech recognition service.
        
        Args:
            app_context: Application context
            config: Configuration dictionary
        """
        super().__init__(app_context, config)
        self.recognizer = sr.Recognizer()
        self.provider = config.get('SPEECH_RECOGNITION_PROVIDER', 'google') if config else 'google'
        self.language = config.get('SPEECH_RECOGNITION_LANGUAGE', 'en-US') if config else 'en-US'
        
        # Configure recognizer
        self.recognizer.energy_threshold = config.get('ENERGY_THRESHOLD', 300) if config else 300
        self.recognizer.dynamic_energy_threshold = config.get('DYNAMIC_ENERGY_THRESHOLD', True) if config else True
        self.recognizer.pause_threshold = config.get('PAUSE_THRESHOLD', 0.8) if config else 0.8
    
    def _process_impl(self, request: str, **kwargs) -> Dict[str, Any]:
        """Implementation of request processing.
        
        Args:
            request: Request string (ignored)
            **kwargs: Additional parameters
                - audio_data: Audio data (bytes or AudioData)
                - timeout: Recognition timeout
                
        Returns:
            Recognition result
        """
        audio_data = kwargs.get('audio_data')
        timeout = kwargs.get('timeout', 10)
        
        if not audio_data:
            # If no audio data provided, try to listen from microphone
            try:
                with sr.Microphone() as source:
                    self.logger.info("Listening for speech...")
                    self.recognizer.adjust_for_ambient_noise(source)
                    audio_data = self.recognizer.listen(source, timeout=timeout)
                    self.logger.info("Audio captured")
            except Exception as e:
                self.logger.error(f"Error capturing audio: {str(e)}")
                return {
                    "success": False,
                    "error": f"Error capturing audio: {str(e)}"
                }
        
        # Convert bytes to AudioData if necessary
        if isinstance(audio_data, bytes):
            audio_data = sr.AudioData(audio_data, 16000, 2)
        
        # Recognize speech
        try:
            if self.provider == 'google':
                text = self.recognizer.recognize_google(audio_data, language=self.language)
            elif self.provider == 'sphinx':
                text = self.recognizer.recognize_sphinx(audio_data, language=self.language)
            elif self.provider == 'whisper':
                text = self.recognizer.recognize_whisper(audio_data, language=self.language)
            else:
                self.logger.warning(f"Unsupported provider: {self.provider}, falling back to Google")
                text = self.recognizer.recognize_google(audio_data, language=self.language)
                
            self.logger.info(f"Recognized text: {text}")
            return {
                "success": True,
                "text": text,
                "provider": self.provider
            }
        except sr.UnknownValueError:
            self.logger.warning("Speech not understood")
            return {
                "success": False,
                "error": "Speech not understood"
            }
        except sr.RequestError as e:
            self.logger.error(f"Recognition service error: {str(e)}")
            return {
                "success": False,
                "error": f"Recognition service error: {str(e)}"
            }
        except Exception as e:
            self.logger.error(f"Error recognizing speech: {str(e)}")
            return {
                "success": False,
                "error": f"Error recognizing speech: {str(e)}"
            }
