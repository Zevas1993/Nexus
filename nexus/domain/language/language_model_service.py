"""
Language Model Service for Nexus AI Assistant with hybrid local and cloud processing.
"""
import asyncio
import requests
import torch
import psutil
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class LanguageModelService:
    """Provides language model capabilities with hybrid local/cloud processing."""
    
    VERSION = "1.0.0"
    
    def __init__(self, config=None):
        """Initialize language model service.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.local_model = None
        self.tokenizer = None
        self.max_length = self.config.get("MAX_LENGTH", 512)
        self.context_window = self.config.get("CONTEXT_WINDOW", 5)
        self.hf_endpoint = self.config.get("HF_ENDPOINT", "https://api-inference.huggingface.co/models/gpt2")
        self.hf_api_token = self.config.get("HF_API_TOKEN", "")
        self.threshold_cpu = self.config.get("THRESHOLD_CPU", 80)
        self.threshold_gpu = self.config.get("THRESHOLD_GPU", 80)
        
    async def initialize(self):
        """Initialize language model service."""
        try:
            # Import here to avoid loading these heavy libraries if not needed
            from transformers import GPTNeoForCausalLM, GPT2Tokenizer
            
            # Load local model
            model_name = self.config.get("LOCAL_MODEL", "EleutherAI/gpt-neo-125M")
            logger.info(f"Loading local model: {model_name}")
            
            self.local_model = GPTNeoForCausalLM.from_pretrained(model_name).to(self.device)
            self.tokenizer = GPT2Tokenizer.from_pretrained(model_name)
            
            logger.info(f"Local model loaded successfully on {self.device}")
        except Exception as e:
            logger.error(f"Error loading local model: {str(e)}")
            self.local_model = None
            self.tokenizer = None
            
        logger.info("Language model service initialized")
    
    async def process(self, request: str, **kwargs) -> Dict[str, Any]:
        """Process a request.
        
        Args:
            request: Request string
            **kwargs: Additional parameters
                - context: Conversation context
                - model: Model name
                
        Returns:
            Processing result
        """
        context = kwargs.get('context', [])
        model = kwargs.get('model', 'default')
        
        # Check system resources
        cpu_usage = psutil.cpu_percent()
        gpu_usage = 0
        if torch.cuda.is_available():
            try:
                gpu_usage = torch.cuda.utilization()
            except:
                # If utilization method is not available
                gpu_usage = 0
        
        logger.info(f"System load: CPU={cpu_usage}%, GPU={gpu_usage}%")
        
        # Decide whether to use cloud based on system load
        use_cloud = (
            cpu_usage > self.threshold_cpu or 
            gpu_usage > self.threshold_gpu or
            self.local_model is None or
            model == 'cloud'
        )
        
        # Fall back to cloud if HF API token is available and we should use cloud
        if use_cloud and self.hf_api_token and self.hf_api_token != "YOUR_HF_TOKEN":
            logger.info("Using cloud model due to system load or configuration")
            return await self._process_cloud(request, context)
        
        # Otherwise use local model if available
        elif self.local_model is not None:
            logger.info("Using local model")
            return await self._process_local(request, context)
        
        # If neither is available, return an error
        else:
            logger.error("No language model available")
            return {
                "status": "error",
                "message": "No language model available. Check configuration."
            }
    
    def _build_context(self, context: List[Dict[str, str]]) -> str:
        """Build context string from conversation history.
        
        Args:
            context: List of conversation turns
            
        Returns:
            Formatted context string
        """
        if not context:
            return ""
            
        # If context is small enough, use full context
        if len(context) <= self.context_window:
            return "\n".join([
                f"User: {entry.get('user', '')}\nAssistant: {entry.get('assistant', '')}"
                for entry in context
            ])
            
        # If context is too large, summarize older context
        old_context = context[:-self.context_window]
        recent_context = context[-self.context_window:]
        
        # Generate a summary of older context
        old_context_text = "\n".join([
            f"User: {entry.get('user', '')}"
            for entry in old_context
        ])
        
        summary_prompt = f"Summarize this conversation:\n{old_context_text}"
        
        # Get summary
        try:
            # Use sync version to avoid nested event loop
            if self.local_model:
                summary = self._process_local_sync(summary_prompt, "")
            else:
                summary = "Previous conversation"  # Fallback if local model not available
        except Exception as e:
            logger.error(f"Error summarizing context: {str(e)}")
            summary = "Previous conversation"  # Fallback
        
        # Format recent context with summary
        recent_context_text = "\n".join([
            f"User: {entry.get('user', '')}\nAssistant: {entry.get('assistant', '')}"
            for entry in recent_context
        ])
        
        return f"Summary of earlier conversation: {summary}\n\n{recent_context_text}"
    
    async def _process_local(self, request: str, context: List[Dict[str, str]]) -> Dict[str, Any]:
        """Process request using local model.
        
        Args:
            request: User query
            context: Conversation context
            
        Returns:
            Processing result
        """
        context_str = self._build_context(context)
        prompt = f"{context_str}\nUser: {request}\nAssistant:"
        
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=self.max_length).to(self.device)
        
        # Generate response
        with torch.no_grad():
            outputs = self.local_model.generate(
                **inputs,
                max_new_tokens=100,
                do_sample=True,
                temperature=0.7,
                top_p=0.9
            )
        
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        # Extract just the assistant's part of the response
        response_text = response.split("Assistant:")[-1].strip()
        
        return {
            "status": "success",
            "text": response_text,
            "model": "local",
            "prompt_tokens": len(inputs["input_ids"][0]),
            "completion_tokens": len(outputs[0]) - len(inputs["input_ids"][0])
        }
    
    def _process_local_sync(self, request: str, context_str: str) -> str:
        """Synchronous version of local processing for internal use.
        
        Args:
            request: User query
            context_str: Context string
            
        Returns:
            Generated text
        """
        prompt = f"{context_str}\nUser: {request}\nAssistant:"
        
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=self.max_length).to(self.device)
        
        with torch.no_grad():
            outputs = self.local_model.generate(
                **inputs,
                max_new_tokens=50,  # Shorter for summaries
                do_sample=False  # Deterministic for summaries
            )
        
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        response_text = response.split("Assistant:")[-1].strip()
        
        return response_text
    
    async def _process_cloud(self, request: str, context: List[Dict[str, str]]) -> Dict[str, Any]:
        """Process request using cloud API.
        
        Args:
            request: User query
            context: Conversation context
            
        Returns:
            Processing result
        """
        context_str = self._build_context(context)
        prompt = f"{context_str}\nUser: {request}\nAssistant:"
        
        # Prepare request to Hugging Face API
        headers = {"Authorization": f"Bearer {self.hf_api_token}"}
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 100,
                "temperature": 0.7,
                "top_p": 0.9
            }
        }
        
        try:
            # Make request
            response = requests.post(self.hf_endpoint, headers=headers, json=payload)
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            
            if isinstance(result, list):
                generated_text = result[0]["generated_text"]
            else:
                generated_text = result["generated_text"]
                
            # Extract just the assistant's part
            response_text = generated_text.split("Assistant:")[-1].strip()
            
            return {
                "status": "success",
                "text": response_text,
                "model": "cloud",
                "prompt_tokens": len(prompt.split()),  # Approximate
                "completion_tokens": len(response_text.split())  # Approximate
            }
        except Exception as e:
            logger.error(f"Error with cloud API: {str(e)}")
            
            # Fall back to local model if available
            if self.local_model:
                logger.info("Falling back to local model")
                return await self._process_local(request, context)
            else:
                return {
                    "status": "error",
                    "message": f"Cloud API error: {str(e)}"
                }
