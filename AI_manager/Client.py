import aiohttp
from typing import Optional, AsyncIterable, AsyncGenerator, Dict, Any
import json
from database import *

async def parse_ollama_stream(content: AsyncIterable[bytes]) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Universal parser for Ollama streaming responses.

    Yields dicts like:
      {"response": "text"}  (partial tokens)
      {"done": true, ...}   (final message)
    """
    async for raw_line in content:
        if not raw_line:
            continue

        line = raw_line.decode("utf-8").strip()
        if not line:
            continue

        # Handle Server-Sent Events style: "data: {...}"
        if line.startswith("data:"):
            line = line[len("data:"):].strip()

        # Some backends may send non-JSON lines (comments, pings, etc.)
        if not line or not (line.startswith("{") and line.endswith("}")):
            continue

        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue

        yield data

class AI_Client:
    def __init__(
            self,
            model: str = "qwen2.5:1.5b",
            host: str = "http://localhost:11434/api/generate",
            temperature: float = 0.4,
            top_p: float = 0.9,
            top_k: int = 20,
            repeat_penalty: float = 1.05,
            num_predict: int = 512,
        ):
        self.model = model
        self.host = host
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
        self.repeat_penalty = repeat_penalty
        self.num_predict = num_predict

    async def build_prompt_with_history(self, user_id: int, user_prompt: str, instruction: str):
        history = await get_history(user_id)
        system_memory = await get_system_memory(user_id)

        parts = []

        # System instructions
        parts.append(f"### System Instructions\n{instruction}")

        # System-level memory
        if system_memory:
            formatted = "\n".join(
                f"- {k}: {v}" for k, v in system_memory.items()
            )
            parts.append(f"### User Profile Memory\n{formatted}")

        # Conversation history
        if history:
            formatted = "\n".join(
                f"USER: {msg['content']}" if msg["role"] == "user"
                else f"ASSISTANT: {msg['content']}"
                for msg in history
            )
            parts.append(f"### Conversation History\n{formatted}")

        # Current user message
        parts.append(f"### User Prompt\n{user_prompt}")

        return "\n\n".join(parts)

    async def request(self, user_id: int, prompt: str, instruction: Optional[str] = None, stream: bool = True):
        full_prompt = await self.build_prompt_with_history(user_id, prompt, instruction)

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": stream,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "repeat_penalty": self.repeat_penalty,
            "num_predict": self.num_predict,
        }

        try:
            async with aiohttp.ClientSession() as sesh:
                async with sesh.post(self.host, json=payload, timeout=120) as resp:

                    # Non-stream mode
                    if not stream:
                        data = await resp.json()
                        return data.get("response", "")

                    # Stream mode
                    full_response = ""

                    async for data in parse_ollama_stream(resp.content):
                        if "response" in data:
                            full_response += data["response"]

                        if data.get("done"):
                            break

                    return full_response

        except Exception as e:
            print("AI Request Error:", e)
            return ""

    async def extract_memory(self, message: str) -> dict:
        prompt = f"""
    You are a memory extraction module.

    Your job is to read the user's message and decide if it contains a stable, long-term fact about the user.

    Extract ONLY facts that are:
    - biographical (job, age, background)
    - preferences (likes, dislikes)
    - personality traits
    - hobbies
    - long-term goals
    - relationship preferences
    - stable emotional tendencies

    DO NOT extract:
    - temporary feelings
    - one-time events
    - jokes
    - questions
    - things about other people

    Return ONLY a JSON object like:
    {{
    "job": "...",
    "likes": ["..."],
    "dislikes": ["..."],
    "hobbies": ["..."],
    "personality": ["..."],
    "other": {{}}
    }}

    If nothing should be saved, return: {{}}

    User message:
    {message}
    """

        result = await self.request_raw(prompt)
        try:
            return json.loads(result)
        except:
            return {}
        
    async def request_raw(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "temperature": 0.5,
            "top_p": 0.9,
            "top_k": 20,
            "repeat_penalty": 1.05,
            "num_predict": 256,
        }

        try:
            async with aiohttp.ClientSession() as sesh:
                async with sesh.post(self.host, json=payload, timeout=60) as resp:
                    data = await resp.json()
                    return data.get("response", "")
        except Exception as e:
            print("AI Memory Extract Error:", e)
            return "ERROR" 
