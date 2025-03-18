"""
AI model configuration for Nexus AI Assistant.
"""
from typing import Dict, Any, List
from .base import config_provider

class ModelConfig:
    """AI model configuration."""
    
    def __init__(self):
        """Initialize model configuration."""
        # Hugging Face configuration
        self.HF_API_TOKEN = config_provider.get_env('HF_API_TOKEN', '')
        self.HF_ENDPOINT = config_provider.get_env('HF_ENDPOINT', 'https://api-inference.huggingface.co/models/gpt2')
        
        # Local model configuration
        self.LOCAL_MODEL = config_provider.get_env('LOCAL_MODEL', 'EleutherAI/gpt-neo-125M')
        
        # Mistral configuration (new)
        self.MISTRAL_SMALL_API_KEY = config_provider.get_env('MISTRAL_SMALL_API_KEY', '')
        self.MISTRAL_ENDPOINT = config_provider.get_env('MISTRAL_ENDPOINT', 'https://api.mistral.ai/v1/models/mistral-small-3.1')
        
        # System resource thresholds
        self.THRESHOLD_CPU = config_provider.get_typed_env('THRESHOLD_CPU', 80, int)
        self.THRESHOLD_GPU = config_provider.get_typed_env('THRESHOLD_GPU', 80, int)
        self.CONTEXT_WINDOW = config_provider.get_typed_env('CONTEXT_WINDOW', 5, int)
        
        # Model selection strategy
        self.MODEL_SELECTION_STRATEGY = config_provider.get_env('MODEL_SELECTION_STRATEGY', 'auto')
        
    def get_model_preference_order(self) -> List[str]:
        """Get model preference order based on available API keys.
        
        Returns:
            List of model names in preference order
        """
        # Default preference: Mistral > HuggingFace > Local
        preference = []
        
        # Add Mistral if API key is available
        if self.MISTRAL_SMALL_API_KEY:
            preference.append('mistral')
            
        # Add HuggingFace if API token is available
        if self.HF_API_TOKEN:
            preference.append('huggingface')
            
        # Always add local as fallback
        preference.append('local')
        
        return preference
        
    def as_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary.
        
        Returns:
            Configuration dictionary
        """
        result = {k: v for k, v in vars(self).items() 
                  if not k.startswith('_')}
        
        # Remove sensitive values
        for key in ('HF_API_TOKEN', 'MISTRAL_SMALL_API_KEY'):
            if key in result and result[key]:
                result[key] = '***' 
                
        return result

# Create and register model config
model_config = ModelConfig()
config_provider.register_component('model', model_config)
