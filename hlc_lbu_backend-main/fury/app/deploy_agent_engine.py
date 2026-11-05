"""
Deployment Script for Gemini Enterprise Agent Platform.
This script packages the local ADK agents (with the mocked tools) and deploys
them to Vertex AI Agent Engine for shadow testing.

Requires: pip install google-adk google-cloud-aiplatform
"""
import os
import asyncio
import logging
from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool
from google.adk.platform import deploy_agent

from agents.data_collector_agent import make_data_collector_agent
from agents.estratega_agent import make_estratega_agent
from agents.copywriter_agent import make_copywriter_agent
from agents.image_prompter_agent import make_image_prompter_agent
from agents.validador_agent import make_validador_agent

# Import Mock Agents/Tools for Shadow Testing
from agents.tools.cloud_mock_tools import mock_nano_banana_generation, mock_abyssale_submission

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def deploy_shadow_pipeline():
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "hiluca-prod")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    
    logger.info("Building shadow orchestrator graph...")
    
    # 1. We use the real agents for the first 5 steps
    # Note: In Agent Engine, tools that call local functions must be configured as OpenAPI tools.
    # The ADK deployer will automatically attempt to map functions to endpoints if configured.
    
    # 2. We mock the final generation steps
    mock_nano_banana = Agent(
        name="mock_nano_banana_agent",
        instruction="You are a mock image generator for shadow testing.",
        tools=[mock_nano_banana_generation]
    )
    
    mock_template_mapper = Agent(
        name="mock_template_mapper_agent",
        instruction="You are a mock abyssale mapper for shadow testing.",
        tools=[mock_abyssale_submission]
    )

    # 3. Build the Shadow Orchestrator
    shadow_orchestrator = Agent(
        name="fury_orchestrator_shadow",
        description="Shadow testing orchestrator for Fury 7-agent pipeline.",
        instruction="Run the pipeline. Do NOT skip any steps.",
        tools=[
            AgentTool(agent=make_data_collector_agent()),
            AgentTool(agent=make_estratega_agent()),
            AgentTool(agent=make_copywriter_agent()),
            AgentTool(agent=make_image_prompter_agent()),
            AgentTool(agent=make_validador_agent()),
            AgentTool(agent=mock_nano_banana),
            AgentTool(agent=mock_template_mapper),
        ],
    )

    logger.info(f"Deploying fury_orchestrator_shadow to {project_id}/{location}...")
    
    # 4. Deploy to Agent Engine
    deployment = await deploy_agent(
        agent=shadow_orchestrator,
        project=project_id,
        location=location,
        # Define the base URL for the OpenAPI extensions we just created
        tool_base_url="https://api.yourdomain.com/api/v2/agent-tools"
    )
    
    logger.info(f"Deployment successful!")
    logger.info(f"Agent Engine Endpoint ID: {deployment.endpoint_id}")
    logger.info(f"To run this agent, call the Vertex AI Execution API with this Endpoint ID.")

if __name__ == "__main__":
    asyncio.run(deploy_shadow_pipeline())
