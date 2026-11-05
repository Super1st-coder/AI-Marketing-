from pydantic import BaseModel, Field

class SampleRequest(BaseModel):
    name: str = Field(..., description="Name for the sample")
    value: int = Field(default=0, description="Some integer value")

class SampleResponse(BaseModel):
    message: str
    processed_value: int
