# Deploying Qwen3VL Evaluation API to Modal

## Prerequisites

1. **Install Modal CLI**:
```bash
pip install modal
```

2. **Authenticate with Modal**:
```bash
modal token new
```
This will open a browser for authentication.

3. **Verify Installation**:
```bash
modal --version
```

## Deployment Steps

1. **Navigate to the modal_api directory**:
```bash
cd modal_api
```

2. **Deploy the application**:
```bash
modal deploy eval_endpoint.py
```

## What Happens During Deployment

1. **Image Build**: Modal builds a container image with:
   - Ollama service
   - Qwen3VL model (will be pulled on first run)
   - FastAPI application
   - System prompt file (`eval_system_prompt.md`)

2. **Model Download**: On first container start, the `qwen3-vl:latest` model will be pulled from Ollama (this may take several minutes)

3. **Service Initialization**: 
   - Ollama service starts
   - Model is pre-warmed
   - FastAPI endpoints become available

## Deployment Output

After successful deployment, you'll see:
```
✓ App deployed in XXX.XXXs! 🎉

View Deployment: https://modal.com/apps/YOUR_USERNAME/qwen-vl-annotator/deployed
Web endpoint: https://YOUR_USERNAME--qwen-vl-annotator-qwenvlannotator-serve.modal.run
```

## Updating Deployment

After making changes to `eval_endpoint.py` or `eval_system_prompt.md`:

```bash
modal deploy eval_endpoint.py
```

Modal will rebuild the image and redeploy.

## Testing the Deployment

1. **Check health**:
```bash
curl https://YOUR_USERNAME--qwen-vl-annotator-qwenvlannotator-serve.modal.run/system-prompt
```

2. **Test evaluation** (using the eval_screenshot.py script):
```bash
cd ../pipeline
python3 eval_screenshot.py test.jpg "A red bicycle leaning against a white wall"
```

## Monitoring

- **View logs**:
```bash
modal app logs qwen-vl-annotator
```

- **View app status**:
```bash
modal app list
```

- **View in Modal dashboard**:
Visit https://modal.com/apps to see your deployed apps

## Configuration

- **GPU**: Currently configured for A100 GPU
- **Model**: `qwen3-vl:latest` (can be changed via `MODEL` environment variable)
- **Scaledown**: Container stays warm for 5 minutes after last request
- **System Prompt**: Loaded from `eval_system_prompt.md`

## Troubleshooting

1. **Model not loading**: Check logs for Ollama pull errors
2. **System prompt not found**: Ensure `eval_system_prompt.md` is in the same directory as `eval_endpoint.py`
3. **Timeout errors**: First request may take longer as model loads
4. **GPU unavailable**: Check your Modal account has access to A100 GPUs

## Cost Considerations

- A100 GPUs are expensive - monitor usage in Modal dashboard
- Container scales down after 5 minutes of inactivity
- Model stays in memory while container is warm

