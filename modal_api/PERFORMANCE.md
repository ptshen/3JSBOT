# Performance Optimization Guide

This guide explains how to optimize response times for your Ollama API on Modal.

## Current Configuration

- **GPU**: A10G
- **Model**: codellama:7b
- **Scaledown Window**: 300 seconds (5 minutes) - *recently optimized*
- **Container Idle Timeout**: 600 seconds (10 minutes) - *recently optimized*
- **Model Pre-warming**: Enabled - *recently added*

## Response Time Factors

### 1. **Cold Start Time** (Biggest Impact)
- **What it is**: Time to start container and load model into GPU memory
- **Current**: ~10-30 seconds on first request after container scales down
- **Solution**: Increased `scaledown_window` to 300 seconds (5 minutes)
  - Container stays warm longer, reducing cold starts
  - Trade-off: Slightly higher cost (container stays alive longer)

### 2. **Model Loading Time**
- **What it is**: Time to load model weights into GPU memory
- **Current**: ~5-15 seconds on first request
- **Solution**: Added model pre-warming in `@modal.enter()`
  - Model is loaded into GPU memory when container starts
  - First real request is much faster

### 3. **Inference Speed** (GPU Dependent)
- **What it is**: Time to generate tokens after model is loaded
- **Current**: A10G handles codellama:7b well (~20-50 tokens/second)
- **Solution**: Can upgrade GPU (see options below)

### 4. **Network Latency**
- **What it is**: Time for request/response to travel over network
- **Current**: Usually <100ms
- **Solution**: Minimal impact, usually not worth optimizing

## GPU Upgrade Options

### Current: A10G
- **Performance**: Good for 7b-13b models
- **Cost**: Moderate
- **Tokens/sec**: ~20-50 for codellama:7b
- **Best for**: Current setup is well-balanced

### Option 1: A100 (40GB or 80GB)
- **Performance**: 2-3x faster than A10G
- **Cost**: ~3-4x more expensive than A10G
- **Tokens/sec**: ~50-150 for codellama:7b
- **Best for**: High-traffic production, when speed is critical
- **When to upgrade**: If you need <1 second response times consistently

### Option 2: T4
- **Performance**: Slightly slower than A10G
- **Cost**: ~30% cheaper than A10G
- **Tokens/sec**: ~15-40 for codellama:7b
- **Best for**: Cost optimization, low-traffic scenarios
- **When to downgrade**: If cost is more important than speed

### Option 3: H100 (Most Powerful)
- **Performance**: 3-5x faster than A10G
- **Cost**: ~5-6x more expensive than A10G
- **Tokens/sec**: ~100-200+ for codellama:7b
- **Best for**: Enterprise production, maximum performance
- **When to upgrade**: Only if you need maximum speed and have budget

## Recommended Optimizations (Already Applied)

### ✅ 1. Increased Scaledown Window
```python
scaledown_window=300,  # Was 10, now 300 (5 minutes)
```
**Impact**: Reduces cold starts significantly
**Cost**: Slightly higher (container stays alive longer)

### ✅ 2. Model Pre-warming
```python
# In @modal.enter()
ollama.chat(model=MODEL, messages=[{"role": "user", "content": "// test"}], ...)
```
**Impact**: Eliminates model loading time on first request
**Cost**: Minimal (one small request on startup)

### ✅ 3. Container Idle Timeout
```python
container_idle_timeout=600,  # 10 minutes
```
**Impact**: Keeps container alive during idle periods
**Cost**: Moderate (container stays alive longer)

## When to Upgrade GPU

Upgrade to **A100** if:
- ✅ You need response times <2 seconds consistently
- ✅ You have high traffic (>10 requests/minute)
- ✅ Cost is not a primary concern
- ✅ Current A10G is maxed out (check Modal dashboard)

**Don't upgrade** if:
- ❌ Current response times are acceptable
- ❌ Traffic is low (<5 requests/minute)
- ❌ Cost is a concern
- ❌ Cold starts are your main issue (fix with scaledown_window instead)

## Performance Benchmarks

### With Current Optimizations (A10G)
- **Cold start** (first request after scale-down): ~15-25 seconds
- **Warm request** (container already running): ~2-5 seconds
- **Streaming first token**: ~1-3 seconds (warm)

### With A100 Upgrade
- **Cold start**: ~10-20 seconds
- **Warm request**: ~1-3 seconds
- **Streaming first token**: ~0.5-1.5 seconds (warm)

## Cost vs Performance Trade-offs

| Configuration | Monthly Cost* | Avg Response Time | Best For |
|--------------|---------------|-------------------|----------|
| T4 + 10s scaledown | $50-100 | 5-8s | Development, low traffic |
| A10G + 300s scaledown (current) | $150-300 | 2-5s | Production, balanced |
| A100 + 300s scaledown | $500-800 | 1-3s | High traffic, speed critical |
| A10G + 10s scaledown | $100-200 | 3-8s | Cost optimization |

*Estimated costs vary based on actual usage

## Monitoring Performance

### Check Modal Dashboard
1. Go to https://modal.com/apps
2. Select your "ollama" app
3. View metrics:
   - Request latency
   - GPU utilization
   - Container uptime
   - Cold start frequency

### Check Logs
```bash
modal app logs ollama
```
Look for:
- "Pre-warming model..." - confirms pre-warming is working
- Request timestamps - measure actual response times

## Additional Optimizations

### 1. Use Streaming Responses
Streaming reduces perceived latency:
```python
"stream": true
```
Users see results faster even if total time is similar.

### 2. Reduce Max Tokens
If responses are too long, limit generation:
```python
# In your request
"max_tokens": 500  # Limit response length
```

### 3. Batch Requests (Future)
If you have multiple requests, batch them to share GPU time.

## Quick GPU Upgrade

To upgrade to A100, change this line in `endpoint.py`:

```python
@app.cls(
    gpu="A100",  # Changed from "A10G"
    scaledown_window=300,
    container_idle_timeout=600,
)
```

Then redeploy:
```bash
modal deploy endpoint.py
```

## Testing Performance

Test your current setup:
```bash
# Time a warm request
time curl -X POST https://YOUR_ENDPOINT.modal.run/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "codellama:7b",
    "messages": [{"role": "user", "content": "Write a function to sort an array"}],
    "stream": false
  }'
```

Compare before/after optimizations to measure improvement.

## Summary

**For codellama:7b, the current optimizations (increased scaledown_window + pre-warming) will have a bigger impact than upgrading GPU.**

Upgrade to A100 only if:
1. You need <2 second response times consistently
2. You have high traffic
3. Cost is not a primary concern

The A10G is well-suited for 7b models. Focus on keeping the container warm (scaledown_window) rather than GPU upgrade unless you have specific performance requirements.

