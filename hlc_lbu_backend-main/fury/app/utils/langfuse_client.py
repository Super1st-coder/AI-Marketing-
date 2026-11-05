"""Langfuse client wrapper"""
from typing import Optional
from langfuse import Langfuse
from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


class LangfuseClientWrapper:
    """Wrapper for Langfuse operations"""
    
    def __init__(
        self,
        public_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        self.public_key = public_key or settings.LANGFUSE_PUBLIC_KEY
        self.secret_key = secret_key or settings.LANGFUSE_SECRET_KEY
        self.base_url = base_url or settings.LANGFUSE_BASE_URL
        
        # Initialize Langfuse client
        self._client = Langfuse(
            public_key=self.public_key,
            secret_key=self.secret_key,
            host=self.base_url
        ) if self.public_key and self.secret_key else None
    
    @property
    def client(self) -> Optional[Langfuse]:
        """Get Langfuse client"""
        return self._client
    
    def get_prompt(
        self,
        name: Optional[str] = None,
        label: Optional[str] = None
    ) -> Optional[str]:
        """Get prompt template from Langfuse"""
        if not self._client:
            logger.warning("Langfuse client not initialized")
            return None
        
        prompt_name = name or settings.LANGFUSE_PROMPT_NAME
        prompt_label = label or settings.LANGFUSE_PROMPT_LABEL
        
        try:
            prompt = self._client.get_prompt(prompt_name, label=prompt_label)
            logger.info(f"Retrieved prompt: {prompt_name} (label: {prompt_label})")
            return prompt.prompt
        except Exception as e:
            logger.error(f"Failed to get prompt from Langfuse: {str(e)}")
            return None
    
    def get_langchain_prompt(
        self,
        name: Optional[str] = None,
        label: Optional[str] = None
    ) -> Optional[str]:
        """Get LangChain compatible prompt from Langfuse"""
        if not self._client:
            logger.warning("Langfuse client not initialized")
            return None
        
        prompt_name = name or settings.LANGFUSE_PROMPT_NAME
        prompt_label = label or settings.LANGFUSE_PROMPT_LABEL
        
        try:
            prompt = self._client.get_prompt(prompt_name, label=prompt_label)
            logger.info(f"Retrieved LangChain prompt: {prompt_name} (label: {prompt_label})")
            return prompt.get_langchain_prompt()
        except Exception as e:
            logger.error(f"Failed to get LangChain prompt from Langfuse: {str(e)}")
            return None

