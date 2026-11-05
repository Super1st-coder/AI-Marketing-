"""Ad generation service - Business logic for text generation"""
import json
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langfuse import observe
from core.logging import get_logger

logger = get_logger(__name__) 

try:
    from langfuse.langchain import CallbackHandler
except ImportError:  # pragma: no cover
    logger.warning("Langfuse not installed, using dummy CallbackHandler")
    CallbackHandler = None

from utils.qdrant_client import QdrantClientWrapper
from utils.postgres_client import PostgresClientWrapper
from utils.langfuse_client import LangfuseClientWrapper
from services.campaign_service import CampaignService
from core.config import settings
from core.exceptions import ValidationException, AIException


# Default prompt template
DEFAULT_PROMPT_TEMPLATE = """***ROLE***
You are a copy expert refining a single promotional message. Use memory context to stay aligned with brand tone, target, product, and campaign.

***GOAL***
Regenerate only the selected text with subtle emotional variation:
- Make it either slightly **more aligned** or **less aligned** (choose randomly).

Message slot: {intention}    
Original: {text}

***RULES***

1. Keep within the length rules for the slot type:
{intention_limits}

2. Use memory to retain:
   - Brand context
   - Product and customer insight
   - Umbrella and specific campaign logic

***OUTPUT***
Return a JSON structure with the generated content, preserving original text slot keys. Example:
{{
  "Text 01": [
    "Save time. Work smarter."
  ]
}}

*** GENERAL INSTRUCTIONS ***
- Write it in {language}.
- Please omit any introductory comment before the answer. Do not include the "json" tag in the response.
- Use temperature 1.2."""


class AdGenerationService:
    """Service for ad text generation"""
    
    def __init__(
        self,
        campaign_service: CampaignService,
        qdrant_client: QdrantClientWrapper,
        postgres_client: PostgresClientWrapper,
        langfuse_client: LangfuseClientWrapper
    ):
        self.campaign_service = campaign_service
        self.qdrant = qdrant_client
        self.postgres = postgres_client
        self.langfuse = langfuse_client
        self.langfuse_handler = None
        
        if CallbackHandler:
            try:
                if getattr(self.langfuse, "client", None):
                    self.langfuse_handler = CallbackHandler(client=self.langfuse.client)
                else:
                    self.langfuse_handler = CallbackHandler()
            except TypeError:
                try:
                    self.langfuse_handler = CallbackHandler()
                except Exception as exc:
                    logger.warning(f"Failed to initialize Langfuse CallbackHandler (fallback): {exc}")
            except Exception as exc:
                logger.warning(f"Failed to initialize Langfuse CallbackHandler: {exc}")
    
    def _get_prompt_template(self) -> str:
        """Get prompt template from Langfuse or use default"""
        prompt = self.langfuse.get_prompt(name="ad_generation_prompt")
        if prompt:
            return prompt
        logger.warning("Using default prompt template")
        return DEFAULT_PROMPT_TEMPLATE
    
    def _format_intention_limits(self, intention_max_char: Dict[str, int]) -> str:
        """Format intention limits for prompt"""
        limits = []
        limits.append(f"- Headline → {intention_max_char['headline']}")
        limits.append(f"- Hook → {intention_max_char['hook']}")
        limits.append(f"- Punchline → {intention_max_char['punchline']}")
        limits.append(f"- Legal → {intention_max_char['legal']}")
        limits.append(f"- Description → {intention_max_char['description']}")
        limits.append(f"- Discount → {intention_max_char['discount']}")
        limits.append(f"- Pricing → {intention_max_char['pricing']}")
        limits.append(f"- Offer → {intention_max_char['offer']}")
        limits.append(f"- Benefit 1–3 → {intention_max_char['benefit1']}, {intention_max_char['benefit2']}, {intention_max_char['benefit3']}")
        limits.append(f"- Feature 1–3 → {intention_max_char['feature1']}, {intention_max_char['feature2']}, {intention_max_char['feature3']}")
        limits.append(f"- CTA → {intention_max_char['cta']}")
        return "\n".join(limits)
    
    def _prepare_prompt(self, agent_fields: Dict[str, Any]) -> str:
        """Prepare final prompt with variables replaced"""
        template = self._get_prompt_template()
        
        intention_limits = self._format_intention_limits(agent_fields["intention_max_char"])
        
        prompt_text = template.format(
            intention=agent_fields["intention"],
            text=agent_fields["text"],
            language=agent_fields["language"],
            intention_limits=intention_limits
        )
        
        return prompt_text
    
    def _get_vector_context(
        self,
        customer_collection_id: str,
        product_collection_id: str,
        query: str
    ) -> str:
        """Get context from vector stores"""
        context_parts = []
        
        if customer_collection_id != "empty":
            try:
                docs = self.qdrant.search(customer_collection_id, query, top_k=5)
                if docs:
                    customer_context = "\n".join([
                        doc.page_content if hasattr(doc, 'page_content') else str(doc)
                        for doc in docs
                    ])
                    context_parts.append(f"Customer/Buyer Persona Context:\n{customer_context}")
            except Exception as e:
                logger.warning(f"Failed to get customer context: {str(e)}")
        
        if product_collection_id != "empty":
            try:
                docs = self.qdrant.search(product_collection_id, query, top_k=5)
                if docs:
                    product_context = "\n".join([
                        doc.page_content if hasattr(doc, 'page_content') else str(doc)
                        for doc in docs
                    ])
                    context_parts.append(f"Product Context:\n{product_context}")
            except Exception as e:
                logger.warning(f"Failed to get product context: {str(e)}")
        
        return "\n\n".join(context_parts)
    
    def _parse_json_response(self, text: str) -> str:
        """Parse JSON from LLM response"""
        try:
            if "{" in text and "}" in text:
                start = text.find("{")
                end = text.rfind("}") + 1
                json_str = text[start:end]
                json_output = json.loads(json_str)
                return list(json_output.values())[0][0] if json_output else text
        except:
            pass
        return text
    
    @observe()
    def generate_text(
        self,
        email: str,
        brand_id: str,
        campaign_id: str,
        ad_id: int,
        channel_id: int,
        element: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate ad text using AI"""
        
        if not element or not isinstance(element, dict):
            raise ValidationException("Elements Missing")
        
        if "intention" not in element:
            raise ValidationException("Element must have 'intention' field")
        
        logger.info(f"Generating text for campaign={campaign_id}, ad={ad_id}, channel={channel_id}")
        
        try:
            # Step 1: Validate campaign
            validate_result = self.campaign_service.validate_campaign(campaign_id, email)

            logger.info(f"Validate campaign result: {validate_result}")
            
            # Step 2: Get ad channel
            ad_channel_data = self.campaign_service.get_ad_channel(ad_id, channel_id)
            
            # Step 3: Get campaign
            campaign_data = self.campaign_service.get_campaign(campaign_id)
            
            # Step 4: Calculate intention max char
            intention_max_char = self.campaign_service.calculate_intention_max_char(element)
            
            # Step 5: Prepare agent fields
            agent_fields = self.campaign_service.prepare_agent_fields(
                validate_result,
                campaign_data,
                ad_channel_data,
                element,
                intention_max_char
            )
            
            # Step 6: Get chat memory
            memory_key = agent_fields["chat_memory_key"]
            memory = self.postgres.get_chat_memory(memory_key)
            
            # Step 7: Prepare prompt
            prompt_text = self._prepare_prompt(agent_fields)
            
            # Step 8: Get vector context
            vector_context = self._get_vector_context(
                agent_fields["bperson_collection_id"],
                agent_fields["product_collection_id"],
                agent_fields["intention"]
            )

            logger.info(f"Vector context: {vector_context}")
            
            # Step 9: Enhance prompt with context
            if vector_context:
                enhanced_prompt = f"{prompt_text}\n\nContext from knowledge base:\n{vector_context}"
            else:
                enhanced_prompt = prompt_text
            
            logger.info(f"Enhanced prompt: {enhanced_prompt}")
            
            # Step 10: Generate with LLM
            llm = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                temperature=settings.OPENAI_TEMPERATURE
            )

            logger.info(f"LLM:")
            
            messages = memory.messages + [HumanMessage(content=enhanced_prompt)]
            invoke_kwargs = {}
            if self.langfuse_handler:
                invoke_kwargs["config"] = {"callbacks": [self.langfuse_handler]}
            response = llm.invoke(messages, **invoke_kwargs)
            generated_text = response.content
            
            logger.info(f"Generated text: {generated_text}")
            
            # Step 11: Save to memory
            memory.add_user_message(prompt_text)
            memory.add_ai_message(generated_text)

            logger.info(f"Saved to memory")
            
            # Step 12: Parse JSON response
            parsed_text = self._parse_json_response(generated_text)
            
            # Step 13: Combine with original element
            final_element = element.copy()
            final_element["payload"] = parsed_text
            
            logger.info(f"Successfully generated text for campaign={campaign_id}")
            
            return {"ok": 1, "data": final_element}
            
        except (ValidationException, AIException) as e:
            logger.error(f"Generation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during generation: {str(e)}")
            raise AIException(
                message="Failed to generate text",
                details={"error": str(e)}
            )

