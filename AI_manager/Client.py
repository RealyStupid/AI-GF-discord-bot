import aiohttp
from typing import Optional, AsyncIterable, AsyncGenerator, Dict, Any
import json

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

    def build_prompt(
            self,
            user_prompt: str,
            instruction: Optional[str] = None
        ) -> str:
        """Builds a clean, structured prompt with hybrid memory."""

        parts = []

        # System instructions
        if instruction:
            parts.append(f"### System Instructions\n{instruction}")

        # Current user prompt
        parts.append(f"### User Prompt\n{user_prompt}")

        return "\n\n".join(parts)
    
    async def request(self, prompt: str, instruction: Optional[str] = None, stream: bool = True):
        full_prompt = self.build_prompt(prompt, instruction)

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

