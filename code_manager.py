from claude_agent_sdk import tool, create_sdk_mcp_server, ClaudeAgentOptions, ClaudeSDKClient
import asyncio
from pathlib import Path
from openai import AsyncOpenAI
import os
from pydantic import BaseModel, Field
from typing import Annotated,Union,List

openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
openai_model = "gpt-5"



async def do_prompt(conv)->List:
    """Run the calculator tool example"""

    class ServiceChanges(BaseModel):
        service_name: str
        required_update:str

    class UpdateService(BaseModel):
        updated_services: List[ServiceChanges]


    messages = [
        {
            "role": "system",
            "content": """you are an action chooser"""
        },] + conv

    response = await openai_client.beta.chat.completions.parse(
        model=openai_model,
        messages=messages,
        response_format=UpdateService
    )

    return []

if __name__ == "__main__":
    # Run the example
    inpt = input("what to code")
    conv = [{"role": "user", "content": inpt}]
    conv+=asyncio.run(do_prompt(conv))
