"""Common schemas"""
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Error response schema"""
    ok: int = Field(0, description="Status indicator (0 for error)")
    message: Dict[str, str] = Field(..., description="Error message details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ok": 0,
                "message": {
                    "code": "ERROR_CODE",
                    "text": "Error description"
                }
            }
        }


class SuccessResponse(BaseModel):
    """Success response schema"""
    ok: int = Field(1, description="Status indicator (1 for success)")
    data: Any = Field(..., description="Response data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ok": 1,
                "data": {}
            }
        }


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = "healthy"
    version: str
    services: Dict[str, str] = Field(default_factory=dict)

