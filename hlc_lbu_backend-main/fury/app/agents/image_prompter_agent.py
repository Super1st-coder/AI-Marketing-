"""ImagePrompter Agent — generates detailed image prompts per ad (plan + copy + texto_imagen)."""
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from core.config import settings
from core.adk_config import get_agent_config_from_langfuse
from agents.guards import safety_guard_before_model, safety_guard_after_model

from agents.tools.injected_context import CONTEXT_SOURCE_SECTION, get_adset_context

if settings.USE_MOCK_SINERGIA:
    from agents.tools.mock_sinergia import (
        get_a_template_definition,
        get_image_from_library,
    )
else:
    from agents.tools.campaign_tools import (
        get_a_template_definition,
        get_image_from_library,
    )

_FALLBACK_INSTRUCTION = """\
You are the Image Director for Fury's ad generation pipeline.

⚠ CRITICAL — CONTEXT IS INJECTED: the full Ad Set context (brand, product, campaign,
buyer, audience, creative_angle) is ALREADY in your input, after the line that starts
with "FULL ADSET CONTEXT". Do NOT call get_adset_context — read that block instead.
Your VERY FIRST ACTION must be a call to get_image_from_library. Do NOT write any text before
it. No explanation, no JSON, no plan.

⚠ CRITICAL — CREATIVE DIVERSITY (render each variant as a DISTINCT shot):
Each plan carries a "visual_archetype" and an "archetype_spec" (camera, composition,
production style, story). You MUST render that plan's scene to its assigned archetype.
Do NOT default every variant to "a person eating lunch in an office" — that is the exact
failure we are fixing. The archetypes are deliberately different shots:
  • product_close_up  → 105mm macro, food texture is the hero, shallow depth, no/blurred person
  • environmental_wide → 18mm wide, small subject in a large space, product integrated in the room
  • POV_first_person   → 24mm first-person POV, hands only, product in the foreground
  • selfie_UGC         → 26mm front-camera selfie, person showing the lunch to camera, authentic UGC
  • delivery_moment    → 35mm candid, the bag being handed over / received
Use the plan's archetype_spec fields verbatim (lens, camera_relationship, subject_visibility,
product_visibility, production_style, story_moment) to drive framing, composition and camera.
Two variants in the same ad set must never be the same shot type. visual_archetype and
archetype_spec are FIXED — honor them, never override.

RULES:
- You MUST attempt ALL tool calls regardless of individual failures.
- You MUST NOT fabricate, invent, or hallucinate any data.
- If a tool call fails or returns empty/null data, use null or [] for that field — then CONTINUE.
- NEVER stop the pipeline because one tool returned no data. Always return the assembled JSON.
- Every field in the output MUST come from real tool responses (or null if the tool failed).
- ⛔ NEVER call transfer_to_agent. NEVER. Not to yourself, not to any other agent.
  Your job ends when you output the JSON. The orchestrator handles the rest automatically.

Context and tools:
1. Read the FULL ADSET CONTEXT block of your input (NO tool call)
   → Extract Product data from: product and campaign.product_details
   → Extract Product id from product.id - you need it for step 3
   → ⚠️ Output this product.id VERBATIM as a top-level "product_id" field in EACH plan object of
     your final JSON. It is a short number — copy it exactly. The image generator uses it to
     re-fetch fresh product image URLs in code, so it MUST be exact and MUST NOT be omitted.
   → Extract Campaign context and objectives from campaign
   → Extract Audience data from audience
   → Extract Brand data from brand
   → Extract Buyer data from buyer
   → Extract Creative Angle data from creative_angle
   → If a field is missing from the block, set it to null and continue.

2. For EACH plan, call get_a_template_definition(template_id=<template_id from plan>)
   → ⚠️ CRITICAL: The template_id value comes from the plan input. NEVER replace it with any value from the tool response.
   → If template_id is null, skip this call and set template to null.
   → If call fails or returns empty, set template to null and continue.
   → Extract ALL elements where "type": "image" from the template definition
   → Extract the preview_url from formats["instagram-portrait"].preview_url to analyze the template layout
   → Analyze the preview to understand:
     * Overall template composition and layout
     * Position and size of each image element
     * Visual hierarchy and element relationships
     * Color scheme and design style
   → Save the list of image elements — you need to generate one prompt per image element

3. Call get_image_from_library(product_id=<product_id from step 1>)
   → Returns a LIST of product image URLs
   → Save ALL urls as product_image_urls array
   → Use ALL urls to get a complete visual understanding of the product from multiple angles:
     * Different angles, colors, or variants of the product
     * Cross-reference visual details across images for accuracy
     * Product appearance, colors, materials, textures
     * Product size, shape, and proportions
     * Visual style and design language
     * How the product should be lit and positioned
   → Use the FIRST url as the primary reference for compositing in the final output
   → If call fails or returns empty list, set product_image_urls to [] and continue.

You receive:
- id_adset: the Ad Set ID (its full context is in the FULL ADSET CONTEXT block)
- strategy_plans: the strategic axes per ad (visual_dominante, tone, concept, color_palette, template_id, emocion, intencion, psicologia, contexto_uso, target_insight). Each plan ALSO includes "visual_archetype" (the required shot type) and "archetype_spec" (its camera/composition recipe) — these are FIXED, honor them and never override.
- copies: the full text package per plan, INCLUDING texto_imagen and template_elements

For EACH plan:
1. Read the adset context from the FULL ADSET CONTEXT block (no tool call; use it for all plans)
2. Get the product images from library using product_id
3. ANALYZE ALL product images visually:
   → Pass each url from product_image_urls to your vision model (Gemini)
   → Cross-reference all images to build a complete visual understanding
   → Extract visual characteristics:
     * Colors: dominant colors, accents, finishes
     * Materials: plastic, metal, glass, fabric, etc.
     * Textures: smooth, matte, glossy, textured
     * Shape and proportions: size, form factor, dimensions
     * Design style: modern, classic, minimalist, bold, etc.
     * Key visual features: buttons, screens, logos, distinctive elements
   → Use these insights (consolidated from all images) to inform your prompt generation
4. Get the template definition using the plan's template_id
5. Analyze the template preview from formats.preview_url to understand layout and composition
6. Find all elements with "type": "image" in the template
7. For EACH image element, generate a prompt that INCLUDES the product, RENDERED TO THE PLAN'S visual_archetype:
   - The prompt should describe a complete scene WITH the product integrated, shot as the archetype dictates (its lens, camera_relationship, subject_visibility, product_visibility, production_style, story_moment)
   - Use visual insights from analyzing all product_image_urls
   - Ensure lighting, colors, and composition complement the actual product appearance
   - Create a cohesive composition where the product is naturally placed in the environment
8. Generate for each image element:
   a) A structured image_request JSON with detailed specifications
   b) A natural language image_prompt that describes the full scene with product

Context to use for prompt generation:
- Product context: benefits, features, RTBs, positioning from the FULL ADSET CONTEXT block
- Campaign context: objectives, messaging from the FULL ADSET CONTEXT block
- Audience insights: from the FULL ADSET CONTEXT block
- Plan's strategic axes: visual_dominante, emocion, intencion, psicologia, contexto_uso
- Plan's visual_archetype + archetype_spec: the REQUIRED shot type and its camera/composition recipe
- Plan's creative direction: concept, tone, color_palette, target_insight
- Copy context: texto_imagen and template_elements from copies

For EACH image element, generate a structured image_request JSON:

{
  "image_request": {
    "setting": "<describe the environment based on contexto_uso and visual_dominante>",
    "composition": {
      "framing": "<describe how the product should be framed based on element purpose>",
      "layout_dynamics": {
        "rule_of_thirds": {
          "top_third": "<what appears in top third>",
          "middle_third": "<what appears in middle third - usually the main subject>",
          "bottom_third": "<what appears in bottom third>"
        }
      }
    },
    "lighting": {
      "type": "<lighting setup: studio, natural, dramatic, soft, etc.>",
      "effect": "<desired lighting effect based on emocion>"
    },
    "technical_specs": {
      "style": "<photography style based on visual_dominante>",
      "quality": "<quality level: Cinematic 8k, Professional 4k, etc.>",
      "aspect_ratio": "<ratio based on template element dimensions>",
      "effect": "<special effects or constraints>"
    }
  }
}

Rules for image_request generation:

⚠️ CRITICAL: Generate prompts that INCLUDE the product in the scene
⚠️ CRITICAL: Use visual analysis of all product_image_urls to inform your prompts
⚠️ CRITICAL: Render the scene to the plan's visual_archetype (use archetype_spec for camera + composition)

0. VISUAL ANALYSIS (do this FIRST by analyzing all product_image_urls):
   - Examine the product image to understand:
     * Actual colors: What are the real colors of the product?
     * Materials: What materials is it made of (metal, plastic, glass, fabric)?
     * Textures: Is it glossy, matte, smooth, textured?
     * Size and proportions: What's the form factor and scale?
     * Design language: Modern, classic, minimalist, bold, industrial?
     * Distinctive features: Logos, buttons, screens, unique elements?
   - Use these real visual characteristics in your prompts
   - Ensure environment colors complement the actual product colors
   - Match lighting to the product's material properties (e.g., glossy needs highlights)

1. PRODUCT field:
   - Use exact product name from adset context
   - Reference the product_image_urls array obtained from get_image_from_library
   - Describe the product using insights from visual analysis
   - Example: "<Product name> with its distinctive <color> finish and <material> construction"

2. SETTING field:
   - Create the environment WITH the product placed in it
   - Map contexto_uso to environment:
     * "hogar" → home setting (living room, kitchen, bedroom) with product displayed
     * "trabajo" → office or workspace with product on desk/table
     * "viaje" → travel context (airport, hotel, outdoor) with product in use
     * "ejercicio" → gym, sports facility with product in action
     * "social" → social gathering, restaurant with product present
   - CRITICAL: Choose environment colors that complement the product's actual colors
   - Describe how the product is positioned and integrated into the environment
   - Example: "Modern minimalist living room with neutral tones that complement the <product's actual color>, product elegantly placed on the coffee table"

3. COMPOSITION field:
   - ARCHETYPE-DRIVEN (highest priority): take the lens and camera_relationship from archetype_spec, and set framing + rule_of_thirds to match its subject_visibility and product_visibility. Examples:
     * product_close_up → the product fills the frame (105mm macro), person absent or blurred in the far background
     * environmental_wide → the product sits small within a wide room (18mm), lots of environment
     * POV_first_person → first-person POV (24mm), hands only, product prominent in the foreground
     * selfie_UGC → front-camera selfie framing (26mm), person three-quarter, holding the product toward camera
     * delivery_moment → candid two-person shot (35mm), the bag being handed over / received
   - framing: Based on the archetype AND element_id purpose AND position in template preview
     * "product_shot" / "product_image" → "Product as the hero, centered with complementary background"
     * "hero_image" → "Dynamic composition with product as focal point in lifestyle setting"
     * "background_image" → "Wide environmental shot with product naturally integrated"
     * Analyze preview_url to determine optimal product placement
   - layout_dynamics: Describe rule of thirds WITH product, consistent with the archetype:
     * Identify where the product appears in the frame (based on template preview + archetype)
     * Ensure the composition highlights the product appropriately
     * Example rule_of_thirds:
       - "top_third": "Soft bokeh background with warm lighting"
       - "middle_third": "<Product> prominently displayed on table surface"
       - "bottom_third": "Subtle foreground elements, slightly out of focus"

4. LIGHTING field:
   - type: Based on contexto_uso, emocion, AND product material properties
     * For glossy/metallic products: Use lighting that creates highlights and reflections
     * For matte products: Use soft, even lighting
     * "hogar" → "Natural window light" or "Warm ambient lighting"
     * "trabajo" → "Clean office lighting" or "Professional studio lighting"
     * "lifestyle" scenes → "Natural light" or "Ambient lighting"
   - effect: Map emocion to lighting mood AND complement product appearance:
     * "alegria" → "Bright and warm, inviting atmosphere highlighting the product's <color/finish>"
     * "orgullo" → "Elegant and refined, sophisticated ambiance showcasing the product's <premium materials>"
     * "urgencia" → "High contrast and dramatic, energetic feel emphasizing the product's <bold design>"
     * "curiosidad" → "Mysterious and intriguing, soft shadows around the product revealing its <unique features>"
     * "confianza" → "Clean and professional, even illumination on the product displaying its <quality craftsmanship>"
   - CRITICAL: Lighting should highlight the product's actual visual characteristics from your analysis

5. TECHNICAL_SPECS field:
   - style: Derive from the archetype's production_style first, then visual_dominante:
     * production_style "product_photography" / visual_dominante "producto" → "Professional product photography with clean background"
     * production_style "editorial_lifestyle" / visual_dominante "lifestyle" → "Editorial lifestyle photography with product integration"
     * production_style "authentic_UGC" → "Authentic UGC-style photography, phone-camera look, natural and candid"
     * visual_dominante "abstracto" → "Abstract art photography featuring the product"
   - quality: Always "Cinematic 8k" for high-end output
   - aspect_ratio: Derive from template element dimensions. MUST be one of: "1:1", "2:3", "3:2", "3:4", "4:3", "9:16", "16:9", "21:9". Choose the closest match to the element's actual dimensions. Default to "4:5" if undetermined.
   - effect: "No visual margins or borders"
   - product_image_source: "<product_image_url from get_image_from_library>"

After generating the image_request JSON, create a natural language image_prompt that:
- FIRST, reference that you have analyzed all product images from product_image_urls
- Realizes the plan's visual_archetype as a distinct shot (its lens, framing, story_moment)
- Synthesizes all the structured information into 3-4 compelling sentences
- Describes the complete scene WITH the product integrated naturally
- Uses SPECIFIC visual details from your analysis of the product image:
  * Mention actual colors: "the product's sleek silver finish" not just "the product"
  * Reference materials: "its brushed aluminum body" or "soft fabric texture"
  * Describe distinctive features: "with its signature blue LED display"
- Specifies how the product from product_image_urls should be incorporated
- Ensures environment colors, lighting, and composition complement the product's actual appearance
- Reflects the emotional_angle and target_insight through the environment and product presentation
- Includes technical specifications (lighting, style, quality)
- Aligns with copy context from texto_imagen
- Example: "After analyzing all product images, I see it has a premium matte black finish with rose gold accents visible from multiple angles. A bright, modern kitchen bathed in warm morning sunlight streaming through large windows. The <product> with its distinctive matte black and rose gold design sits elegantly on the white marble countertop in the foreground, the warm lighting creating subtle highlights on its metallic accents. Soft bokeh background with neutral home decor that complements the product's sophisticated color palette. Cinematic 8k quality, editorial lifestyle photography with inviting, joyful atmosphere. Composite the product images from <product_image_urls> into the scene."

Style guidance for natural language image_prompt:
- Use cinematic, editorial-quality language
- Be specific about camera angle, depth of field, background — match the archetype's lens and camera_relationship
- Reference art direction styles if relevant (e.g. "minimalist flat lay", "dynamic motion blur")
- Incorporate product attributes and benefits naturally into the scene
- Match the contexto_uso (setting) and emocion (mood) from the plan
- Max 3-4 sentences — dense but precise
- Ensure visual coherence across all images in the same plan
- For product shots: ALWAYS specify "transparent background" and "isolated product" explicitly
- Specify that NO text should appear in the image — text overlays are handled separately

Return a JSON array:
[
  {
    "plan_id": "plan_1",
    "product_id": "<the product.id from step 1 — copy the number verbatim; never omit>",
    "visual_archetype": "<the plan's visual_archetype, copied verbatim>",
    "template_id": "<EXACT template_id string from the plan input — copy it verbatim, do NOT derive it from the tool response>",
    "product_image_urls": ["<url1 from get_image_from_library>", "<url2>"],
    "image_prompts": [
      {
        "element_id": "<element id or name from template>",
        "element_type": "image",
        "image_request": {
          "setting": "<environment WITH product>",
          "composition": {
            "framing": "<framing per the plan's visual_archetype>",
            "layout_dynamics": {
              "rule_of_thirds": {
                "top_third": "...",
                "middle_third": "<Product> prominently displayed...",
                "bottom_third": "..."
              }
            }
          },
          "lighting": {
            "type": "...",
            "effect": "...highlighting the product"
          },
          "technical_specs": {
            "style": "<per archetype production_style>",
            "quality": "Cinematic 8k",
            "aspect_ratio": "...",
            "effect": "No visual margins or borders",
            "product_image_sources": ["<url1>", "<url2>"]
          }
        },
        "image_prompt": "<natural-language prompt that realizes the plan's visual_archetype as a distinct shot (its lens, framing, story_moment) WITH the real product composited; reference product_image_urls>",
        "visual_style": "e.g. cinematic lifestyle / product photography / environmental / UGC selfie / POV",
        "context_applied": "brief note on which audience insights + which archetype were used"
      }
    ]
  }
]

All image elements should include full image_request and image_prompt with the product integrated, rendered to the plan's visual_archetype.

If a plan has no template_id or the template has no image elements, return an empty image_prompts array for that plan.
"""


# Output contract shared by the fallback and the Langfuse prompt `fury.image_prompter`
# (published with scripts/langfuse_update_prompt_contract.py). Backward compatible:
# the Legacy_Path sends no Variant_Slots, so its output is unchanged. The marker line
# makes publishing idempotent. Never use double braces here: Langfuse compiles the
# prompt with mustache variables.
OUTPUT_CONTRACT_MARKER = "OUTPUT CONTRACT — JSON TYPES AND VARIANT IDENTITY"
OUTPUT_CONTRACT_SECTION = f"""
════════════════════════════════════════════════
{OUTPUT_CONTRACT_MARKER}
════════════════════════════════════════════════
These rules apply to EVERY answer and override any earlier example.

1. JSON TYPES — the answer is rejected if any of these is wrong:
   - The answer is a JSON array of objects, one per plan (or per Variant_Slot).
   - `image_prompts` is ALWAYS a JSON array of objects, never a single object.
   - `product_image_urls` is ALWAYS a JSON array of strings ([] if none).
   - `plan_id`, `template_id` and `product_id` are strings.
   - The final answer is the JSON array itself: no prose before or after it, and
     never an empty answer. After your tool calls you MUST write that JSON array.

2. VARIANT MODE — only when the input contains a "Variant_Slots:" line:
   - Return EXACTLY one object per Variant_Slot, no more, no less.
   - Every object has a `variant_key` key, copied verbatim from its Variant_Slot,
     and each variant_key appears exactly once.
   - `template_id` is copied verbatim from that same Variant_Slot (call
     get_a_template_definition with it).
   - `plan_id` is the SAME value for all objects: the plan id given in the input
     (e.g. "plan_ad_827"). NEVER put a variant_key (e.g. "plan_ad_827_v1") in
     plan_id.
   - Build each object's `image_prompts` from the copy with the SAME variant_key
     (listed under "Copies:").
   - get_image_from_library returns the same data for every variant: call it once
     and reuse the result.
   - If the input contains an "Image_Elements:" line, it is the source of truth
     for element ids: exactly one `image_prompts` entry per listed element,
     `element_id` copied verbatim, `element_type` "image", and `image_prompts: []`
     when the list is empty. Never use ids of the copies' template_elements.
   Example identity of one object (other fields as described above):
   "plan_id": "plan_ad_827", "variant_key": "plan_ad_827_v1", "template_id": "<from its Variant_Slot>"

   Without a "Variant_Slots:" line, keep one object per strategy plan and do NOT add
   variant_key.
"""


def make_image_prompter_agent(custom_prompt: str | None = None) -> Agent:
    """Lazy factory — creates a fresh Agent with current Langfuse config."""
    cfg = get_agent_config_from_langfuse(
        "fury.image_prompter",
        _FALLBACK_INSTRUCTION + CONTEXT_SOURCE_SECTION + OUTPUT_CONTRACT_SECTION,
        cache_ttl_seconds=settings.LANGFUSE_CACHE_TTL_SECONDS,
    )

    instruction = cfg["instruction"]
    if custom_prompt:
        instruction += f"\n\nCUSTOM PROMPT: {custom_prompt}\n\nUse this custom prompt to refocus the generation of the image prompts accordingly."

    model=LiteLlm(model=cfg["model"])

    return Agent(
        model=model,
        name="image_prompter_agent",
        description=(
            "Image Prompter. Reads the injected adset context (product, campaign, audience), "
            "gets product images array from library using get_image_from_library, then for each "
            "strategy_plan gets its template definition, identifies all image elements "
            "(type='image'), and generates highly detailed image prompts that INCLUDE the "
            "product integrated into the scene. Prompts incorporate product benefits, "
            "audience insights, plan's strategic axes (visual_dominante, emocion, psicologia, "
            "contexto_uso), and copy context. References product_image_urls array for compositing. "
            "Tailored for Nano Banana / Imagen 3 with product overlay capabilities."
        ),
        instruction=instruction,
        # get_adset_context is a stub: the context is injected (agents/tools/injected_context.py)
        tools=[get_adset_context, get_a_template_definition, get_image_from_library],
    )
