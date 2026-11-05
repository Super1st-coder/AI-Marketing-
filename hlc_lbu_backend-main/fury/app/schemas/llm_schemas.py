from pydantic import BaseModel, Field

class HypothesisRequest(BaseModel):
    instruction: str = Field(..., description="The marketing hypothesis text to analyze")

class HypothesisResponse(BaseModel):
    buyer_persona: str = Field(default="", description="The target buyer persona extracted")
    element_to_test: str = Field(default="", description="The element to test extracted")
    prediction: str = Field(default="", description="The expected prediction or outcome extracted")
