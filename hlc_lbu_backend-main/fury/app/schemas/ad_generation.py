"""Ad generation schemas"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, validator


class ElementSchema(BaseModel):
    """Element schema for ad generation"""
    intention: str = Field(..., description="Text intention type (headline, hook, cta, etc.)")
    payload: str = Field(..., description="Original or generated text")
    max_char: Optional[int] = Field(None, description="Maximum characters allowed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "intention": "headline",
                "payload": "Transform your marketing with AI",
                "max_char": 55
            }
        }


class IntentionMaxCharSchema(BaseModel):
    """Max characters configuration for each intention"""
    headline: int = 55
    hook: int = 55
    punchline: int = 55
    legal: int = 55
    description: int = 125
    discount: int = 55
    pricing: int = 55
    offer: int = 55
    benefit1: int = 55
    benefit2: int = 55
    benefit3: int = 55
    feature1: int = 55
    feature2: int = 55
    feature3: int = 55
    cta: int = 55


class AdGenerationRequest(BaseModel):
    """Request schema for ad text generation"""
    email: str = Field(..., description="User email")
    brand_id: str = Field(..., description="Brand ID")
    campaign_id: str = Field(..., description="Campaign ID")
    ad_id: int = Field(..., description="Ad ID")
    channel_id: int = Field(..., description="Channel ID")
    element: Dict[str, Any] = Field(..., description="Element to generate text for")
    
    @validator('element')
    def validate_element(cls, v):
        """Validate element has required fields"""
        if not isinstance(v, dict):
            raise ValueError("element must be a dictionary")
        if 'intention' not in v:
            raise ValueError("element must have 'intention' field")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "brand_id": "brand_123",
                "campaign_id": "campaign_456",
                "ad_id": 1,
                "channel_id": 2,
                "element": {
                    "intention": "headline",
                    "payload": "Original headline text",
                    "max_char": 55
                }
            }
        }


class AdGenerationResponse(BaseModel):
    """Response schema for ad text generation"""
    ok: int = Field(..., description="Status indicator (1 for success, 0 for error)")
    data: Dict[str, Any] = Field(..., description="Generated ad element")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ok": 1,
                "data": {
                    "intention": "headline",
                    "payload": "Generated headline text",
                    "max_char": 55
                }
            }
        }

