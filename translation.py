"""
Example translation plugin for Nexus AI Assistant.

This plugin provides translation capabilities between different languages.
"""

from typing import Dict, Any
import logging
from nexus.domain.base import AsyncService
from nexus.features.improved_plugins import hook

logger = logging.getLogger(__name__)

class TranslationService(AsyncService):
    """Translation service plugin."""
    
    async def initialize(self):
        """Initialize translation service."""
        logger.info("Translation plugin initialized")
        self.supported_languages = {
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "zh": "Chinese",
            "ja": "Japanese",
            "ko": "Korean",
            "ar": "Arabic"
        }
    
    async def _process_impl(self, request: str, **kwargs) -> Dict[str, Any]:
        """Process translation request.
        
        Args:
            request: Text to translate
            **kwargs: Additional parameters
                - text: Text to translate (overrides request)
                - source_lang: Source language code (auto-detect if not provided)
                - target_lang: Target language code
                
        Returns:
            Translation result
        """
        # Get parameters
        text = kwargs.get('text', request)
        source_lang = kwargs.get('source_lang', 'auto')
        target_lang = kwargs.get('target_lang', 'es')
        
        if not text:
            return {
                "status": "error",
                "message": "No text provided for translation"
            }
        
        if target_lang not in self.supported_languages:
            return {
                "status": "error",
                "message": f"Unsupported target language: {target_lang}",
                "supported_languages": self.supported_languages
            }
        
        # In a real implementation, this would call a translation API
        # For this example, we'll use a simple simulation
        translated_text = self._simulate_translation(text, target_lang)
        
        return {
            "status": "success",
            "result": {
                "original_text": text,
                "translated_text": translated_text,
                "source_language": source_lang,
                "target_language": target_lang,
                "target_language_name": self.supported_languages[target_lang]
            }
        }
    
    def _simulate_translation(self, text: str, target_lang: str) -> str:
        """Simulate translation for demonstration purposes.
        
        Args:
            text: Text to translate
            target_lang: Target language code
            
        Returns:
            Simulated translated text
        """
        # This is a simple simulation - in a real plugin, you would use a translation API
        translations = {
            "es": {
                "Hello": "Hola",
                "How are you?": "¿Cómo estás?",
                "Thank you": "Gracias",
                "Goodbye": "Adiós"
            },
            "fr": {
                "Hello": "Bonjour",
                "How are you?": "Comment allez-vous?",
                "Thank you": "Merci",
                "Goodbye": "Au revoir"
            },
            "de": {
                "Hello": "Hallo",
                "How are you?": "Wie geht es dir?",
                "Thank you": "Danke",
                "Goodbye": "Auf Wiedersehen"
            }
        }
        
        # Check if we have a predefined translation
        if target_lang in translations and text in translations[target_lang]:
            return translations[target_lang][text]
        
        # For unknown text, append a language indicator
        lang_indicators = {
            "es": "[texto en español]",
            "fr": "[texte en français]",
            "de": "[Text auf Deutsch]",
            "it": "[testo in italiano]",
            "pt": "[texto em português]",
            "ru": "[текст на русском]",
            "zh": "[中文文本]",
            "ja": "[日本語テキスト]",
            "ko": "[한국어 텍스트]",
            "ar": "[نص باللغة العربية]"
        }
        
        return f"{text} {lang_indicators.get(target_lang, '')}"
    
    @hook('before_response')
    async def log_translation(self, response):
        """Log translation before sending response.
        
        Args:
            response: Response data
            
        Returns:
            Modified response
        """
        if response.get("status") == "success":
            result = response.get("result", {})
            logger.info(f"Translated: {result.get('original_text')} -> {result.get('translated_text')}")
        
        return response
