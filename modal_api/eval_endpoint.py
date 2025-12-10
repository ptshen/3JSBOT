"""FastAPI endpoint for Qwen3VL image annotation with Ollama.

This module provides a FastAPI application for image annotation using Qwen3VL
vision-language model through Ollama. It accepts images and returns detailed annotations.
"""

import modal
import os
import subprocess
import time
import base64
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from typing import List, Any, Optional, AsyncGenerator, Union
from pydantic import BaseModel, Field


MODEL = os.environ.get("MODEL", "qwen3-vl:latest")
DEFAULT_MODELS = ["qwen3-vl:latest"]


async def download_image_as_base64(url: str) -> str:
    """Download an image from a URL and convert it to base64.

    :param url: URL of the image to download
    :return: Base64-encoded image string
    :raises HTTPException: If the image cannot be downloaded
    """
    import httpx
    from loguru import logger

    try:
        logger.info(f"Downloading image from URL: {url}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.google.com/",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            # Convert to base64
            image_data = response.content
            base64_image = base64.b64encode(image_data).decode('utf-8')
            logger.info(f"Successfully downloaded and encoded image ({len(image_data)} bytes)")
            return base64_image
    except httpx.HTTPError as e:
        logger.error(f"Failed to download image from {url}: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to download image from URL: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error processing image URL {url}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing image URL: {str(e)}"
        )


def load_system_prompt() -> str:
    """Load the system prompt from the eval_system_prompt.md file.

    :return: System prompt content as string
    """
    from loguru import logger

    try:
        # Try to read from the file in the container
        prompt_path = "/root/eval_system_prompt.md"
        if os.path.exists(prompt_path):
            with open(prompt_path, "r") as f:
                content = f.read()
                logger.info(f"Loaded system prompt from {prompt_path} ({len(content)} chars)")
                return content
        # Fallback: try current directory (for local development)
        prompt_path = "eval_system_prompt.md"
        if os.path.exists(prompt_path):
            with open(prompt_path, "r") as f:
                content = f.read()
                logger.info(f"Loaded system prompt from {prompt_path} ({len(content)} chars)")
                return content
        # If file doesn't exist, return default prompt
        logger.warning("System prompt file not found, using default prompt")
        return "You are an expert image annotation assistant. Analyze images and provide detailed, accurate annotations."
    except Exception as e:
        # Fallback to default prompt if file can't be read
        logger.error(f"Error loading system prompt: {e}")
        return "You are an expert image annotation assistant. Analyze images and provide detailed, accurate annotations."


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
    """Create the system prompt file for image evaluation from eval_system_prompt.md."""
    from loguru import logger
    import os

    # Read from the file that was copied into the image
    prompt_file_path = "/root/eval_system_prompt.md"
    
    try:
        if os.path.exists(prompt_file_path):
            with open(prompt_file_path, "r") as f:
                system_prompt_content = f.read()
            logger.info(f"Loaded system prompt from {prompt_file_path} ({len(system_prompt_content)} chars)")
        else:
            # Fallback to default evaluation prompt if file not found
            logger.warning(f"System prompt file not found at {prompt_file_path}, using default")
            system_prompt_content = """You are an expert image evaluation assistant powered by Qwen3VL. Your task is to compare images to reference descriptions and provide accurate, objective evaluations of how well they match.

CRITICAL RULES:
1. Provide clear, structured, and detailed descriptions of images
2. Identify key objects, people, actions, and spatial relationships
3. Note important visual attributes like colors, sizes, positions, and states
4. Be objective and precise in your descriptions
5. Organize your annotations in a logical, easy-to-parse format
6. If uncertain about something, indicate your confidence level
7. Focus on relevant details that would be useful for understanding the image

ANNOTATION FORMAT:
- Start with a brief overview of the entire image
- List key objects/elements with their attributes and positions
- Describe actions or interactions if present
- Note any text visible in the image
- Mention notable visual features (lighting, composition, etc.)

EXAMPLES OF GOOD ANNOTATIONS:
 "A red bicycle leaning against a white wall, handlebar facing left, with a wicker basket attached to the front"
 "Three people sitting at a wooden table: two women on the left side engaged in conversation, one man on the right looking at a laptop"
 "Kitchen scene: stainless steel refrigerator in background, marble countertop in foreground with cutting board, knife, and chopped vegetables (carrots, bell peppers)"

EXAMPLES OF POOR ANNOTATIONS:
 "A bike" (too vague, lacks detail)
 "Some stuff on a table" (imprecise, unhelpful)
 "I think maybe there's a person but I'm not sure what they're doing" (overly uncertain without analysis)

Remember: Be thorough, objective, and precise in your evaluations. Provide clear numerical ratings and detailed analysis.
"""
    except Exception as e:
        logger.error(f"Error reading system prompt file: {e}")
        # Use minimal fallback
        system_prompt_content = "You are an expert image evaluation assistant. Compare images to reference descriptions and provide ratings from 0.0 to 1.0."
    
    # Ensure the file exists (it should already be there from copy_local_file)
    os.makedirs("/root", exist_ok=True)
    with open("/root/eval_system_prompt.md", "w") as f:
        f.write(system_prompt_content)
    logger.info(f"System prompt file ready at /root/eval_system_prompt.md ({len(system_prompt_content)} chars)")


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
    .add_local_file("eval_system_prompt.md", "/root/eval_system_prompt.md", copy=True)
    .run_function(create_service_file)
    .run_function(create_system_prompt_file)  # This will verify/update the file
    .run_function(pull)
)
app = modal.App(name="qwen-vl-annotator", image=image)
api = FastAPI()


@api.get("/system-prompt")
async def get_system_prompt():
    """Debug endpoint to check if system prompt is loaded."""
    prompt = load_system_prompt()
    return {
        "prompt_length": len(prompt),
        "prompt_preview": prompt[:200] + "..." if len(prompt) > 200 else prompt,
        "file_exists": os.path.exists("/root/eval_system_prompt.md")
    }


class ImageInput(BaseModel):
    """Image input format for annotation requests."""

    # Image can be provided as base64 string or URL
    image_base64: Optional[str] = Field(
        default=None,
        description="Base64-encoded image data (without data:image prefix)"
    )
    image_url: Optional[str] = Field(
        default=None,
        description="URL to the image"
    )


class AnnotationRequest(BaseModel):
    """Request model for image annotation.

    Accepts an image and optional prompt for annotation guidance.
    """

    model: Optional[str] = Field(
        default=MODEL,
        description="The model to use for annotation"
    )
    image: ImageInput = Field(
        ...,
        description="Image to annotate (as base64 or URL)"
    )
    prompt: Optional[str] = Field(
        default="Please provide a detailed annotation of this image.",
        description="Optional prompt to guide the annotation"
    )
    stream: bool = Field(
        default=False,
        description="Whether to stream the response"
    )


class ChatMessage(BaseModel):
    """A single message in a chat completion request."""

    role: str = Field(
        ...,
        description="The role of the message sender (e.g. 'user', 'assistant', 'system')"
    )
    content: str = Field(
        ...,
        description="The content of the message"
    )
    images: Optional[List[str]] = Field(
        default=None,
        description="Optional list of base64-encoded images or image URLs"
    )


class ChatCompletionRequest(BaseModel):
    """Request model for chat completions with vision support."""

    model: Optional[str] = Field(
        default=MODEL,
        description="The model to use for completion"
    )
    messages: List[ChatMessage] = Field(
        ...,
        description="The messages to generate a completion for"
    )
    stream: bool = Field(
        default=False,
        description="Whether to stream the response"
    )


@api.post("/v1/annotate")
async def annotate_image(request: AnnotationRequest) -> Any:
    """Annotate an image using Qwen3VL.

    :param request: Annotation request with image and optional prompt
    :return: Annotation response
    :raises HTTPException: If the request is invalid or processing fails
    """
    import json
    import ollama
    from loguru import logger

    try:
        # Validate image input
        if not request.image.image_base64 and not request.image.image_url:
            raise HTTPException(
                status_code=400,
                detail="Either image_base64 or image_url must be provided"
            )

        # Load system prompt
        system_prompt = load_system_prompt()
        logger.info(f"System prompt loaded: {len(system_prompt)} characters")

        # Prepare image for Ollama
        # Ollama expects images as base64 strings
        images = []
        if request.image.image_base64:
            images.append(request.image.image_base64)
        elif request.image.image_url:
            # Download and convert URL to base64
            base64_image = await download_image_as_base64(request.image.image_url)
            images.append(base64_image)

        # Prepare messages with system prompt
        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": request.prompt,
                "images": images
            }
        ]

        logger.info(f"Prepared messages with {len(images)} image(s)")

        if request.stream:
            async def generate_stream() -> AsyncGenerator[str, None]:
                """Generate streaming response chunks."""
                response = ollama.chat(
                    model=request.model,
                    messages=messages,
                    stream=True,
                )

                for chunk in response:
                    chunk_data = {
                        "id": "annotation-" + str(int(time.time())),
                        "object": "annotation.chunk",
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
                    "id": "annotation-" + str(int(time.time())),
                    "object": "annotation.chunk",
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
            model=request.model,
            messages=messages
        )

        return {
            "id": "annotation-" + str(int(time.time())),
            "object": "annotation",
            "created": int(time.time()),
            "model": request.model,
            "annotation": response["message"]["content"],
            "usage": {
                "prompt_tokens": -1,  # Ollama doesn't provide token counts
                "completion_tokens": -1,
                "total_tokens": -1,
            },
        }

    except Exception as e:
        logger.error(f"Error processing annotation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing annotation: {str(e)}"
        )


@api.post("/v1/chat/completions")
async def v1_chat_completions(request: ChatCompletionRequest) -> Any:
    """Handle chat completion requests with vision support.

    :param request: Chat completion parameters
    :return: Chat completion response, or StreamingResponse if streaming
    :raises HTTPException: If the request is invalid or processing fails
    """
    import json
    import ollama
    from loguru import logger

    try:
        if not request.messages:
            raise HTTPException(
                status_code=400,
                detail="Messages array is required and cannot be empty",
            )

        # Load system prompt
        system_prompt = load_system_prompt()
        logger.info(f"System prompt loaded: {len(system_prompt)} characters")

        # Prepare messages with system prompt
        messages = [msg.model_dump() for msg in request.messages]

        # Process any image URLs in messages and convert to base64
        for message in messages:
            if message.get("images"):
                processed_images = []
                for img in message["images"]:
                    # Check if it's a URL (starts with http:// or https://)
                    if isinstance(img, str) and (img.startswith("http://") or img.startswith("https://")):
                        # Download and convert to base64
                        base64_img = await download_image_as_base64(img)
                        processed_images.append(base64_img)
                    else:
                        # Already base64, keep as is
                        processed_images.append(img)
                message["images"] = processed_images

        # Prepend system message
        messages.insert(0, {
            "role": "system",
            "content": system_prompt
        })

        logger.info(f"Messages prepared with system prompt. Total messages: {len(messages)}")

        if request.stream:
            async def generate_stream() -> AsyncGenerator[str, None]:
                """Generate streaming response chunks."""
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
            model=request.model,
            messages=messages
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
        logger.error(f"Error processing chat completion: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat completion: {str(e)}"
        )


@app.cls(
    gpu="A100",  # Qwen3VL requires more GPU memory
    scaledown_window=300,  # Keep container warm for 5 minutes
)
class QwenVLAnnotator:
    """Modal container class for running Qwen3VL annotation service.

    Handles initialization, startup, and serving of the Qwen3VL model through FastAPI.
    """

    @modal.enter()
    def enter(self):
        """Entry point for Modal container.

        Starts Ollama service and pulls the specified model.
        Pre-warms the model by making a dummy request.
        """
        from loguru import logger

        subprocess.run(["systemctl", "start", "ollama"])
        wait_for_ollama()
        subprocess.run(["ollama", "pull", MODEL])

        # Pre-warm the model
        try:
            import ollama
            logger.info("Pre-warming model...")
            ollama.chat(
                model=MODEL,
                messages=[{"role": "user", "content": "test"}],
                options={"num_predict": 1}
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
