import os
import socket
import subprocess
import aiohttp
import asyncio

def is_distrobox() -> bool:
    if os.environ.get("DISTROBOX") == "1":
        return True
    if os.environ.get("container") == "distrobox":
        return True
    if os.path.exists("/run/.containerenv"):
        return True
    if "distrobox" in socket.gethostname() or "toolbox" in socket.gethostname():
        return True
    return False

class Color:
    RESET = "\033[0m"
    BOLD = "\033[1m"

    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"

class OllamaInitializer_Async:
    def __init__(self):
        self.in_distrobox = is_distrobox()
        self.cmd_prefix = ["distrobox-host-exec"] if self.in_distrobox else []

    def stop_ollama(self):
        """Stop Ollama cleanly."""
        print(f"{Color.YELLOW}\nStopping ollama...{Color.RESET}")
        try:
            subprocess.run(
                self._cmd("pkill", "ollama"),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print(f"{Color.GREEN}Ollama Stopped{Color.RESET}")
        except Exception as e:
            print(f"{Color.RED}Error accured:", e, f"{Color.RESET}")

    def _cmd(self, *args):
        """Build command with prefix if inside Distrobox."""
        return self.cmd_prefix + list(args)

    def ollama_exists(self):
        """Check if Ollama is installed."""
        try:
            result = subprocess.run(
                self._cmd("ollama", "--version"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False
        
    async def list_models(self):
        url = "http://localhost:11434/api/tags"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=2) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
                    return [m["name"] for m in data.get("models", [])]
            except:
                return []

    def is_running(self):
        """Check if Ollama is already running."""
        result = subprocess.run(
            self._cmd("pgrep", "ollama"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return result.returncode == 0

    def start_ollama(self):
        """Start Ollama in the background."""
        subprocess.Popen(
            self._cmd("ollama", "serve"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    async def wait_until_ready(self, timeout=10):
        url = "http://localhost:11434/api/tags"

        async with aiohttp.ClientSession() as session:
            for _ in range(timeout * 2):
                try:
                    async with session.get(url, timeout=1) as resp:
                        if resp.status == 200:
                            return True
                except:
                    pass

                await asyncio.sleep(0.5)

        return False
    
    async def initialize(self):
        """Run the full initialization sequence."""
        report = {
            "environment": "distrobox" if self.in_distrobox else "host",
            "ollama_exists": False,
            "ollama_running": False,
            "ollama_started": False,
            "ready": False
        }

        # Environment notice
        if report["environment"] == "distrobox":
            print(f"{Color.YELLOW}⚠️  DistroBox detected: You are running inside a DistroBox container.{Color.RESET}")

        # Check installation
        if not self.ollama_exists():
            print(f"{Color.RED}❌ Ollama is not installed on this system.{Color.RESET}")
            print(f"{Color.YELLOW}   Please install Ollama and try again.{Color.RESET}")
            return report

        report["ollama_exists"] = True
        print(f"{Color.GREEN}✔ Ollama installation detected.{Color.RESET}")

        # Check running state
        if self.is_running():
            print(f"{Color.BLUE}Ollama is already running. Skipping startup steps.{Color.RESET}")
            report["ollama_running"] = True
        else:
            print(f"{Color.CYAN}⏳ Starting Ollama...{Color.RESET}")
            self.start_ollama()
            report["ollama_started"] = True
            report["ollama_running"] = True
            print(f"{Color.GREEN}✔ Ollama started successfully.{Color.RESET}")

        # Wait for readiness
        print(f"{Color.CYAN}⏳ Waiting for Ollama to become ready...{Color.RESET}")
        report["ready"] = await self.wait_until_ready()

        if report["ready"]:
            print(f"{Color.GREEN}✔ Ollama is ready for use!{Color.RESET}")
        else:
            print(f"{Color.RED}❌ Ollama did not become ready in time.{Color.RESET}")

        print(f"{Color.CYAN}⏳ Checking installed models...{Color.RESET}")
        models = await self.list_models()

        if not models:
            print(f"{Color.RED}❌ No models installed!{Color.RESET}")
            print(f"{Color.YELLOW}   Install a model using: ollama pull llama3{Color.RESET}")
        else:
            print(f"{Color.GREEN}✔ Installed models:{Color.RESET}")
            for m in models:
                print(f"   - {m}")

        # Use this for potential debugging
        # return report