# Ollama-Setup-Manager
This is a Ollama Setup manager allowing you to confirm ollama exists on your device, confirm it is working, and prepare it for integration to any application.

## How to use it?
This repo provides 2 scripts inside ollama_manager folder.

One is for async, and one for sync.

depending on your application you may use one of these.

step 1:
- Download the repo and unzip it
- Move this repo into your project
- Install the requirements found inside the repo
- finally import the scripts into your project
```python
# You will import the project
# imports will differ depending on where you placed it inside the project
from Ollama-Setup-Manager.ollama_manager import init_async, init_sync
```
and finally use them in your code:
```python
# Sync version
init_sync.initialize()

# Async version
# NOTE: make sure it is inside an async function
await init_async.initialize()
```

## Plans for the future (if this gets popular)
I would like to turn this into an actual package in pypl.