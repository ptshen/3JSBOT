"""FastAPI endpoint for Ollama chat completions with OpenAI-compatible API.

This module provides a FastAPI application that serves as a bridge between clients
and Ollama models, offering an OpenAI-compatible API interface. It supports both
streaming and non-streaming responses.
"""

import modal
import os
import subprocess
import time
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from typing import List, Any, Optional, AsyncGenerator
from pydantic import BaseModel, Field


MODEL = os.environ.get("MODEL", "codellama:7b")
DEFAULT_MODELS = ["codellama:7b"]


def load_system_prompt() -> str:
    """Load the system prompt from the markdown file.
    
    :return: System prompt content as string
    """
    from loguru import logger
    
    try:
        # Try to read from the file in the container
        prompt_path = "/root/system_prompt.md"
        if os.path.exists(prompt_path):
            with open(prompt_path, "r") as f:
                content = f.read()
                logger.info(f"Loaded system prompt from {prompt_path} ({len(content)} chars)")
                return content
        # Fallback: try current directory (for local development)
        prompt_path = "system_prompt.md"
        if os.path.exists(prompt_path):
            with open(prompt_path, "r") as f:
                content = f.read()
                logger.info(f"Loaded system prompt from {prompt_path} ({len(content)} chars)")
                return content
        # If file doesn't exist, return default prompt
        logger.warning("System prompt file not found, using default prompt")
        return "You are a specialized JavaScript code generation assistant. Generate ONLY JavaScript code. Do not generate code in any other programming language."
    except Exception as e:
        # Fallback to default prompt if file can't be read
        logger.error(f"Error loading system prompt: {e}")
        return "You are a specialized JavaScript code generation assistant. Generate ONLY JavaScript code. Do not generate code in any other programming language."


def pull() -> None:
    """Initialize and pull the Ollama model.

    Sets up the Ollama service using systemctl and pulls the specified model.
    """
    subprocess.run(["systemctl", "daemon-reload"])
    subprocess.run(["systemctl", "enable", "ollama"])
    subprocess.run(["systemctl", "start", "ollama"])
    wait_for_ollama()
    subprocess.run(["ollama", "pull", MODEL], stdout=subprocess.PIPE)


def create_service_file() -> None:
    """Create the systemd service file for Ollama."""
    service_content = """[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/bin/ollama serve
User=ollama
Group=ollama
Restart=always
RestartSec=3
Environment="OLLAMA_HOST=0.0.0.0:11434"

[Install]
WantedBy=default.target
"""
    import os
    os.makedirs("/etc/systemd/system", exist_ok=True)
    with open("/etc/systemd/system/ollama.service", "w") as f:
        f.write(service_content)
    subprocess.run(["systemctl", "daemon-reload"])
    subprocess.run(["systemctl", "enable", "ollama"])


def create_system_prompt_file() -> None:
    """Create the system prompt file for JavaScript code generation."""
    from loguru import logger
    
    system_prompt_content = """You are a JavaScript code generator. Your ONLY job is to output JavaScript code. Nothing else.

CRITICAL RULES - YOU MUST FOLLOW THESE:
1. Output ONLY JavaScript code. No explanations, no descriptions, no markdown code fences.
2. Do NOT use markdown formatting like ```javascript or ```. Just output the raw code.
3. Do NOT add any text before or after the code. No "Here's the code:" or "This code does X".
4. If you need to explain something, use JavaScript comments (// or /* */) INSIDE the code.
5. Do NOT generate code in any other language (Python, Java, C++, etc.). ONLY JavaScript.
6. Output complete, runnable JavaScript code when possible.
7. Use modern ES6+ JavaScript syntax and best practices.

EXAMPLES OF CORRECT OUTPUT:
// Good - just code with comments
import * as THREE from 'three';
const scene = new THREE.Scene();
// ... rest of code

EXAMPLES OF WRONG OUTPUT:
❌ ```javascript
   // code here
   ```
❌ Here's the code to create a sphere:
   // code here
❌ // code here
   This code creates a 3D sphere...

Remember: Output ONLY JavaScript code. No markdown, no explanations, no extra text. Just code.
"""
    import os
    os.makedirs("/root", exist_ok=True)
    with open("/root/system_prompt.md", "w") as f:
        f.write(system_prompt_content)
    logger.info(f"Created system prompt file at /root/system_prompt.md ({len(system_prompt_content)} chars)")


def wait_for_ollama(timeout: int = 30, interval: int = 2) -> None:
    """Wait for Ollama service to be ready.

    :param timeout: Maximum time to wait in seconds
    :param interval: Time between checks in seconds
    :raises TimeoutError: If the service doesn't start within the timeout period
    """
    import httpx
    from loguru import logger

    start_time = time.time()
    while True:
        try:
            response = httpx.get("http://localhost:11434/api/version")
            if response.status_code == 200:
                logger.info("Ollama service is ready")
                return
        except httpx.ConnectError:
            if time.time() - start_time > timeout:
                raise TimeoutError("Ollama service failed to start")
            logger.info(
                f"Waiting for Ollama service... ({int(time.time() - start_time)}s)"
            )
            time.sleep(interval)


# Configure Modal image with Ollama dependencies
image = (
    modal.Image.debian_slim()
    .apt_install("curl", "systemctl")
    .run_commands(  # from https://github.com/ollama/ollama/blob/main/docs/linux.md
        "curl -L https://ollama.com/download/ollama-linux-amd64.tgz -o ollama-linux-amd64.tgz",
        "tar -C /usr -xzf ollama-linux-amd64.tgz",
        "useradd -r -s /bin/false -U -m -d /usr/share/ollama ollama",
        "usermod -a -G ollama $(whoami)",
    )
    .pip_install("ollama", "httpx", "loguru", "fastapi", "pydantic")
    .run_function(create_service_file)
    .run_function(create_system_prompt_file)
    .run_function(pull)
)
app = modal.App(name="ollama", image=image)
api = FastAPI()


@api.get("/system-prompt")
async def get_system_prompt():
    """Debug endpoint to check if system prompt is loaded."""
    prompt = load_system_prompt()
    return {
        "prompt_length": len(prompt),
        "prompt_preview": prompt[:200] + "..." if len(prompt) > 200 else prompt,
        "file_exists": os.path.exists("/root/system_prompt.md")
    }


class ChatMessage(BaseModel):
    """A single message in a chat completion request.

    Represents one message in the conversation history, following OpenAI's chat format.
    """

    role: str = Field(
        ..., description="The role of the message sender (e.g. 'user', 'assistant')"
    )
    content: str = Field(..., description="The content of the message")


class ChatCompletionRequest(BaseModel):
    """Request model for chat completions.

    Follows OpenAI's chat completion request format, supporting both streaming
    and non-streaming responses.
    """

    model: Optional[str] = Field(
        default=MODEL, description="The model to use for completion"
    )
    messages: List[ChatMessage] = Field(
        ..., description="The messages to generate a completion for"
    )
    stream: bool = Field(default=False, description="Whether to stream the response")


@api.post("/v1/chat/completions")
async def v1_chat_completions(request: ChatCompletionRequest) -> Any:
    """Handle chat completion requests in OpenAI-compatible format.

    :param request: Chat completion parameters
    :return: Chat completion response in OpenAI-compatible format, or StreamingResponse if streaming
    :raises HTTPException: If the request is invalid or processing fails
    """
    import json

    try:
        if not request.messages:
            raise HTTPException(
                status_code=400,
                detail="Messages array is required and cannot be empty",
            )

        # Load system prompt and inject it into messages
        import ollama
        from loguru import logger
        
        system_prompt = load_system_prompt()
        logger.info(f"System prompt loaded: {len(system_prompt)} characters")
        
        # Prepare messages with system prompt
        messages = [msg.model_dump() for msg in request.messages]
        
        # Prepend system prompt to ensure it's always included
        # We'll add it as both a system message AND prepend to first user message
        # to ensure maximum compatibility with different Ollama versions
        
        # Find the first user message
        first_user_idx = None
        for i, msg in enumerate(messages):
            if msg.get("role") == "user":
                first_user_idx = i
                break
        
        if first_user_idx is not None:
            # Prepend system prompt to the first user message
            messages[first_user_idx]["content"] = system_prompt + "\n\nUser request: " + messages[first_user_idx].get("content", "")
            logger.info(f"Prepended system prompt to user message at index {first_user_idx}")
        else:
            # If no user message found, prepend to first message
            if messages:
                messages[0]["content"] = system_prompt + "\n\n" + messages[0].get("content", "")
            else:
                # Insert as first message
                messages.insert(0, {
                    "role": "user",
                    "content": system_prompt
                })
        
        # Also add as system message for models that support it
        messages.insert(0, {
            "role": "system",
            "content": system_prompt
        })
        
        logger.info(f"Messages prepared with system prompt. Total messages: {len(messages)}, first role: {messages[0].get('role')}")

        if request.stream:

            async def generate_stream() -> AsyncGenerator[str, None]:
                """Generate streaming response chunks.

                :return: AsyncGenerator yielding SSE-formatted JSON strings
                """
                response = ollama.chat(
                    model=request.model,
                    messages=messages,
                    stream=True,
                )

                for chunk in response:
                    chunk_data = {
                        "id": "chat-" + str(int(time.time())),
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": request.model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {
                                    "role": "assistant",
                                    "content": chunk["message"]["content"],
                                },
                                "finish_reason": None,
                            }
                        ],
                    }
                    yield f"data: {json.dumps(chunk_data)}\n\n"

                # Send final chunk with finish_reason
                final_chunk = {
                    "id": "chat-" + str(int(time.time())),
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": request.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop",
                        }
                    ],
                }
                yield f"data: {json.dumps(final_chunk)}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream",
            )

        # Non-streaming response
        response = ollama.chat(
            model=request.model, messages=messages
        )

        return {
            "id": "chat-" + str(int(time.time())),
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response["message"]["content"],
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": -1,  # Ollama doesn't provide token counts
                "completion_tokens": -1,
                "total_tokens": -1,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing chat completion: {str(e)}"
        )


@app.cls(
    gpu="A100",  # Options: "T4" (cheaper), "A10G" (current), "A100" (faster, more expensive)
    scaledown_window=300,  # Keep container warm for 5 minutes (was 10 seconds) - reduces cold starts
)
class Ollama:
    """Modal container class for running Ollama service.

    Handles initialization, startup, and serving of the Ollama model through FastAPI.
    """

    @modal.enter()
    def enter(self):
        """Entry point for Modal container.

        Starts Ollama service and pulls the specified model.
        Pre-warms the model by making a dummy request to load it into GPU memory.
        """
        from loguru import logger
        
        subprocess.run(["systemctl", "start", "ollama"])
        wait_for_ollama()
        subprocess.run(["ollama", "pull", MODEL])
        
        # Pre-warm the model by making a small request to load it into GPU memory
        # This reduces latency for the first real request
        try:
            import ollama
            logger.info("Pre-warming model...")
            ollama.chat(
                model=MODEL,
                messages=[{"role": "user", "content": "// test"}],
                options={"num_predict": 1}  # Generate only 1 token to minimize cost
            )
            logger.info("Model pre-warmed successfully")
        except Exception as e:
            logger.warning(f"Model pre-warming failed (non-critical): {e}")

    @modal.asgi_app()
    def serve(self):
        """Serve the FastAPI application.

        :return: FastAPI application instance
        """
        return api