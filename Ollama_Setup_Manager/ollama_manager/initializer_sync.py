import os
import socket
import subprocess
import requests
import time

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

class OllamaInitialize_Sync:
    def __init__(self):
        self.in_distrobox = is_distrobox()
        self.cmd_prefix = ["distrobox-host-exec"] if self.in_distrobox else []

    def _cmd(self, *args):
        return self.cmd_prefix + list(args)

    def stop_ollama(self):
        subprocess.run(
            self._cmd("pkill", "ollama"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    def ollama_exists(self):
        try:
            result = subprocess.run(
                self._cmd("ollama", "--version"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def is_running(self):
        result = subprocess.run(
            self._cmd("pgrep", "ollama"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return result.returncode == 0

    def start_ollama(self):
        subprocess.Popen(
            self._cmd("ollama", "serve"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    def wait_until_ready(self, timeout=10):
        url = "http://localhost:11434/api/tags"

        for _ in range(timeout * 2):
            try:
                r = requests.get(url, timeout=1)
                if r.status_code == 200:
                    return True
            except:
                pass

            time.sleep(0.5)

        return False

    def list_models(self):
        url = "http://localhost:11434/api/tags"

        try:
            r = requests.get(url, timeout=2)
            if r.status_code != 200:
                return []
            data = r.json()
            return [m["name"] for m in data.get("models", [])]
        except:
            return []

    def initialize(self):
        report = {
            "environment": "distrobox" if self.in_distrobox else "host",
            "ollama_exists": False,
            "ollama_running": False,
            "ollama_started": False,
            "ready": False,
            "models": []
        }

        if report["environment"] == "distrobox":
            print(f"{Color.YELLOW}⚠️  DistroBox detected: You are running inside a DistroBox container.{Color.RESET}")

        if not self.ollama_exists():
            print(f"{Color.RED}❌ Ollama is not installed on this system.{Color.RESET}")
            print(f"{Color.YELLOW}   Please install Ollama and try again.{Color.RESET}")
            return report

        report["ollama_exists"] = True
        print(f"{Color.GREEN}✔ Ollama installation detected.{Color.RESET}")

        if self.is_running():
            print(f"{Color.BLUE}Ollama is already running. Skipping startup steps.{Color.RESET}")
            report["ollama_running"] = True
        else:
            print(f"{Color.CYAN}⏳ Starting Ollama...{Color.RESET}")
            self.start_ollama()
            report["ollama_started"] = True
            report["ollama_running"] = True
            print(f"{Color.GREEN}✔ Ollama started successfully.{Color.RESET}")

        print(f"{Color.CYAN}⏳ Waiting for Ollama to become ready...{Color.RESET}")
        report["ready"] = self.wait_until_ready()

        if report["ready"]:
            print(f"{Color.GREEN}✔ Ollama is ready for use!{Color.RESET}")
        else:
            print(f"{Color.RED}❌ Ollama did not become ready in time.{Color.RESET}")

        print(f"{Color.CYAN}⏳ Checking installed models...{Color.RESET}")
        models = self.list_models()
        report["models"] = models

        if not models:
            print(f"{Color.RED}❌ No models installed!{Color.RESET}")
            print(f"{Color.YELLOW}   Install a model using: ollama pull llama3{Color.RESET}")
        else:
            print(f"{Color.GREEN}✔ Installed models:{Color.RESET}")
            for m in models:
                print(f"   - {m}")

        # for debugging
        # return report
