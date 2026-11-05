import openai
import logging
from core.config import settings
from schemas.llm_schemas import HypothesisResponse

logger = logging.getLogger(__name__)

# Initialize async client
client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

class LLMService:
    @staticmethod
    async def extract_marketing_hypothesis_variables(instruction: str) -> HypothesisResponse:
        """
        Extracts structured marketing variables from a free-text marketing hypothesis
        using OpenAI's structured outputs.
        """
        if not settings.OPENAI_API_KEY:
            raise Exception("OpenAI API key not configured in environment")

        prompt = (
            "Extract three marketing variables named buyer_persona, element_to_test and prediction "
            "from the following input:\n\n"
            f"\"{instruction}\"\n\n"
            "Return each variable as a key-value pair."
        )

        try:
            completion = await client.beta.chat.completions.parse(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert marketing data extractor."},
                    {"role": "user", "content": prompt}
                ],
                response_format=HypothesisResponse,
                temperature=0.0  # Force deterministic extraction
            )
            
            return completion.choices[0].message.parsed
            
        except Exception as e:
            logger.error(f"Error extracting hypothesis variables: {str(e)}")
            raise Exception(f"LLM Processing Error: {str(e)}")
