"""Custom exceptions"""
from typing import Optional, Dict, Any


class FuryException(Exception):
    """Base exception for Fury API"""
    
    def __init__(
        self,
        message: str,
        code: str = "FURY_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class StrapiException(FuryException):
    """Strapi related exceptions"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="STRAPI_ERROR",
            status_code=500,
            details=details
        )


class ValidationException(FuryException):
    """Validation exceptions"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=400,
            details=details
        )


class AIException(FuryException):
    """AI/LLM related exceptions"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="AI_ERROR",
            status_code=500,
            details=details
        )


class VectorStoreException(FuryException):
    """Vector store related exceptions"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="VECTORSTORE_ERROR",
            status_code=500,
            details=details
        )

