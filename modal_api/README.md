# Ollama FastAPI Deployment on Modal

A production-ready FastAPI deployment of Ollama models on Modal, providing an OpenAI-compatible API interface for accessing open-source language models.

## Features

- ✅ OpenAI-compatible API endpoint (`/v1/chat/completions`)
- ✅ Support for both streaming and non-streaming responses
- ✅ Automatic model pulling and service initialization
- ✅ GPU support (A10G) for running large models
- ✅ Easy to extend with additional models and endpoints

## Table of Contents

- [Prerequisites](#prerequisites)
- [Basic Setup](#basic-setup)
- [Deployment](#deployment)
- [Adding More Models](#adding-more-models)
- [Adding New Endpoints](#adding-new-endpoints)
- [Usage Examples](#usage-examples)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

## Prerequisites

1. **Python 3.8+** installed on your local machine
2. **Modal account** - Sign up at [modal.com](https://modal.com) if you don't have one
3. **Modal CLI** installed and authenticated

## Basic Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Authenticate with Modal

```bash
modal token new
```

This will open a browser window for you to authenticate. Follow the instructions to complete the setup.

### 3. Verify Installation

```bash
modal --version
```

## Deployment

### Initial Deployment

Deploy the application to Modal:

```bash
modal deploy generate_endpoint.py
```

The deployment process will:
1. Build the container image with Ollama and all dependencies
2. Pull the default model (`gemma2:27b`) during image build
3. Deploy the FastAPI application
4. Provide you with a unique endpoint URL

### Deployment Output

After successful deployment, you'll see:

```
✓ App deployed in XXX.XXXs! 🎉

View Deployment: https://modal.com/apps/YOUR_USERNAME/main/deployed/ollama
Web endpoint: https://YOUR_USERNAME--ollama-ollama-serve.modal.run
```

### Updating Deployment

To update your deployment after making changes:

```bash
modal deploy generate_endpoint.py
```

Modal will automatically detect changes and rebuild only what's necessary.

## Adding More Models

There are several ways to add more models to your deployment:

### Method 1: Change Default Model (Recommended for Single Model)

Edit `generate_endpoint.py` and modify the `MODEL` variable:

```python
# Line 18 in generate_endpoint.py
MODEL = os.environ.get("MODEL", "llama2:13b")  # Change from gemma2:27b
```

You can also set it via environment variable:

```bash
MODEL=llama2:13b modal deploy generate_endpoint.py
```

### Method 2: Pre-pull Multiple Models

To have multiple models available, modify the `pull()` function to pull multiple models:

```python
def pull() -> None:
    """Initialize and pull the Ollama models."""
    subprocess.run(["systemctl", "daemon-reload"])
    subprocess.run(["systemctl", "enable", "ollama"])
    subprocess.run(["systemctl", "start", "ollama"])
    wait_for_ollama()
    
    # Pull multiple models
    models_to_pull = ["gemma2:27b", "llama2:13b", "mistral:7b"]
    for model in models_to_pull:
        subprocess.run(["ollama", "pull", model], stdout=subprocess.PIPE)
```

**Note:** Pre-pulling multiple large models will significantly increase build time and image size.

### Method 3: Dynamic Model Pulling (Runtime)

Models can be pulled at runtime when requested. The current implementation will automatically pull a model if it's specified in the API request but not available. However, this adds latency to the first request.

### Popular Models to Try

- `llama2:7b` - Smaller, faster model
- `llama2:13b` - Balanced performance
- `llama2:70b` - Large, high-quality (requires significant GPU memory)
- `mistral:7b` - Fast and efficient
- `codellama:7b` - Specialized for code
- `gemma2:27b` - Current default (large model)

## Adding New Endpoints

### Adding a Simple GET Endpoint

Add new endpoints to the FastAPI `api` object. Here's an example:

```python
@api.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "ollama-api"}

@api.get("/models")
async def list_models():
    """List available models."""
    import ollama
    models = ollama.list()
    return {
        "models": [model["name"] for model in models.get("models", [])]
    }
```

### Adding a Custom POST Endpoint

```python
@api.post("/v1/embeddings")
async def create_embeddings(request: EmbeddingRequest):
    """Create embeddings for text."""
    import ollama
    
    response = ollama.embeddings(
        model=request.model,
        prompt=request.input
    )
    
    return {
        "object": "list",
        "data": [{
            "object": "embedding",
            "embedding": response["embedding"],
            "index": 0
        }],
        "model": request.model
    }
```

### Adding Endpoints with Different Models

You can create endpoints that use specific models:

```python
@api.post("/v1/code/completions")
async def code_completion(request: ChatCompletionRequest):
    """Code completion endpoint using CodeLlama."""
    import ollama
    
    # Force use of code-specific model
    request.model = "codellama:7b"
    
    # Reuse existing chat completion logic
    return await v1_chat_completions(request)
```

### Adding Streaming Endpoints

The existing `/v1/chat/completions` endpoint already supports streaming. To add another streaming endpoint:

```python
@api.post("/v1/stream/chat")
async def stream_chat(request: ChatCompletionRequest):
    """Custom streaming endpoint."""
    import ollama
    import json
    
    async def generate():
        response = ollama.chat(
            model=request.model,
            messages=[msg.model_dump() for msg in request.messages],
            stream=True,
        )
        
        for chunk in response:
            yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")
```

### Best Practices for Adding Endpoints

1. **Use Pydantic models** for request validation:
   ```python
   class CustomRequest(BaseModel):
       text: str = Field(..., description="Input text")
       temperature: float = Field(default=0.7, ge=0, le=2)
   ```

2. **Add proper error handling**:
   ```python
   try:
       # Your logic here
   except Exception as e:
       raise HTTPException(status_code=500, detail=str(e))
   ```

3. **Document your endpoints** with docstrings (they appear in `/docs`)

4. **Use type hints** for better code clarity

## Usage Examples

### Using the API Directly

#### Non-streaming Request

```bash
curl -X POST https://YOUR_ENDPOINT.modal.run/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma2:27b",
    "messages": [
      {"role": "user", "content": "Explain quantum computing in simple terms"}
    ],
    "stream": false
  }'
```

#### Streaming Request

```bash
curl -X POST https://YOUR_ENDPOINT.modal.run/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma2:27b",
    "messages": [
      {"role": "user", "content": "Write a short story"}
    ],
    "stream": true
  }'
```

### Using with Python Requests

```python
import requests

url = "https://YOUR_ENDPOINT.modal.run/v1/chat/completions"
response = requests.post(url, json={
    "model": "gemma2:27b",
    "messages": [
        {"role": "user", "content": "Hello!"}
    ],
    "stream": False
})

print(response.json())
```

### Using with OpenAI Client Library

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://YOUR_ENDPOINT.modal.run/v1",
    api_key="not-needed"  # API key not required
)

response = client.chat.completions.create(
    model="gemma2:27b",
    messages=[
        {"role": "user", "content": "What is Python?"}
    ]
)

print(response.choices[0].message.content)
```

### Using with LangChain

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gemma2:27b",
    openai_api_base="https://YOUR_ENDPOINT.modal.run/v1",
    openai_api_key="not-needed"
)

response = llm.invoke("Tell me a joke")
print(response.content)
```

## Configuration

### Environment Variables

You can configure the deployment using environment variables:

- `MODEL`: Default model to use (default: `gemma2:27b`)

Set during deployment:
```bash
MODEL=llama2:13b modal deploy generate_endpoint.py
```

### GPU Configuration

To change the GPU type, modify the `@app.cls` decorator:

```python
@app.cls(
    gpu="T4",  # Change from "A10G" to "T4" (smaller, cheaper)
    scaledown_window=10,
)
```

Available GPU options:
- `"T4"` - Smaller, more cost-effective
- `"A10G"` - Current default (good balance)
- `"A100"` - Most powerful (for very large models)

### Container Settings

Adjust container behavior:

```python
@app.cls(
    gpu="A10G",
    scaledown_window=30,  # Keep container alive for 30s after last request
    timeout=300,  # Request timeout in seconds
)
```

## API Documentation

Once deployed, access interactive API documentation:

- **Swagger UI**: `https://YOUR_ENDPOINT.modal.run/docs`
- **ReDoc**: `https://YOUR_ENDPOINT.modal.run/redoc`

## Troubleshooting

### Deployment Issues

**Problem**: Build fails with "Ollama service failed to start"
- **Solution**: Check Modal logs with `modal app logs ollama`. The model might be too large for the selected GPU.

**Problem**: "Model not found" errors
- **Solution**: Ensure the model name is correct. Check available models at [ollama.com/library](https://ollama.com/library)

**Problem**: Timeout errors
- **Solution**: Increase the `timeout` parameter in `@app.cls` or use a smaller model.

### Runtime Issues

**Problem**: First request is very slow
- **Solution**: This is normal - the model needs to load into GPU memory. Subsequent requests will be faster.

**Problem**: "Out of memory" errors
- **Solution**: Use a smaller model or upgrade to a larger GPU (e.g., A100).

**Problem**: Container scales down too quickly
- **Solution**: Increase `scaledown_window` in the `@app.cls` decorator.

### Checking Logs

View real-time logs:
```bash
modal app logs ollama
```

View specific function logs:
```bash
modal app logs ollama --function Ollama.serve
```

## Project Structure

```
modal_api/
├── generate_endpoint.py          # Main application file
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Cost Considerations

- **GPU costs**: Charged per second of GPU usage
- **Container idle time**: Containers scale down after `scaledown_window` seconds
- **Model size**: Larger models require more GPU memory (and cost)
- **Build time**: Pre-pulling models increases build time but reduces cold start latency

**Tip**: Use smaller models and shorter `scaledown_window` for cost optimization.

## Next Steps

1. **Customize the default model** for your use case
2. **Add custom endpoints** for your specific needs
3. **Set up monitoring** via Modal's dashboard
4. **Configure autoscaling** if you expect high traffic
5. **Add authentication** if you need to secure your API

## Resources

- [Modal Documentation](https://modal.com/docs)
- [Ollama Models Library](https://ollama.com/library)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)

## License

This project is provided as-is for educational and development purposes.

## Support

For issues related to:
- **Modal**: Check [Modal's documentation](https://modal.com/docs) or their Discord
- **Ollama**: Visit [Ollama's GitHub](https://github.com/ollama/ollama)
- **This deployment**: Open an issue in your repository

