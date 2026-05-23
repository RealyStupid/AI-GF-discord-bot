import aiohttp
from typing import Optional
import json

class AI_Client:
    def __init__(
            self,
            model: str = "llama3",
            host: str = "http://localhost:11434/api/generate",
            temperature: float = 0.6,
            top_p: float = 0.85,
            top_k: int = 30,
            repeat_penalty: float = 1.25,
            num_predict: int = 256,
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
    
    async def request(
            self,
            prompt: str,
            instruction: Optional[str] = None,
            stream: bool = True
        ):
        """Send a request to Ollama asynchronously and return full response."""
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

                    # NON‑STREAM MODE (simple)
                    if not stream:
                        data = await resp.json()
                        return data.get("response", "")

                    # STREAM MODE (stitch chunks)
                    full_response = ""

                    async for line in resp.content:
                        if not line:
                            continue
                        try:
                            data = json.loads(line.decode("utf-8"))
                            if "response" in data:
                                full_response += data["response"]
                        except:
                            continue

                    return full_response

        except Exception as e:
            print("AI Request Error:", e)
            return ""

