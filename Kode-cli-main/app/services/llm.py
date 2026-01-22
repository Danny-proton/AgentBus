from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionChunk
import os
from typing import List, Dict, AsyncGenerator, Any, Optional
from dotenv import load_dotenv

load_dotenv()

class LLMClient:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def stream_chat(
        self, 
        messages: List[Dict[str, Any]], 
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[Any, None]:
        """
        Yields chunks. 
        If it's content, yields string.
        If it's a tool call, accumulates and yields the final tool call object (simulated for simplicity or yield chunks).
        To keep it compatible with the Agent loop, we will yield raw chunks and let Agent handle accumulation, 
        OR we simplify and yield specific events.
        
        For this implementation: 
        We yield the raw Request object or special logic. 
        Actually, let's just return the stream and let the Agent handle the complexity of tool accumulation vs text.
        """
        try:
            stream = await self.client.chat.completions.create(
                model="gpt-4o", # Upgrade to 4o for better tool use
                messages=messages,
                tools=tools,
                stream=True
            )
            async for chunk in stream:
                yield chunk
        except Exception as e:
            # yield error string? Or raise?
            # Let's yield a mock chunk-like object or string implies error
            # For type safety in Agent, we'll let exception propagate or handle there.
            raise e
