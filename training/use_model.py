"""
Example script showing how to use the fine-tuned CodeLlama model for Three.js code generation.

Usage:
    python use_model.py --model-path ./models/threejs_codellama/threejs_codellama_lora_merged
"""

import argparse
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch


def generate_threejs_code(model_path: str, description: str, max_new_tokens: int = 512):
    """
    Generate Three.js code from a scene description using the fine-tuned model.
    
    Args:
        model_path: Path to the fine-tuned model directory
        description: Scene description text
        max_new_tokens: Maximum number of tokens to generate
    
    Returns:
        Generated Three.js code as a string
    """
    print(f"Loading model from {model_path}...")
    
    # Load tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None,
    )
    
    # Create prompt in CodeLlama format
    prompt = f"""<s>[INST] Generate Three.js code for the following scene description:

{description}

Requirements:
- Use Three.js library (available as global THREE object)
- Create a scene, camera, and renderer
- Implement the described 3D scene
- Use appropriate geometries, materials, and lighting
- Include any animations or interactions if described

Return only the JavaScript code without markdown formatting. [/INST]"""
    
    # Tokenize
    inputs = tokenizer(prompt, return_tensors="pt")
    if torch.cuda.is_available():
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
    
    # Generate
    print("Generating code...")
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=0.7,
            do_sample=True,
            top_p=0.9,
            pad_token_id=tokenizer.eos_token_id,
        )
    
    # Decode
    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Extract code (everything after [/INST])
    if "[/INST]" in generated_text:
        code = generated_text.split("[/INST]")[-1].strip()
    else:
        code = generated_text
    
    return code


def main():
    parser = argparse.ArgumentParser(description="Generate Three.js code using fine-tuned CodeLlama")
    parser.add_argument(
        "--model-path",
        type=str,
        required=True,
        help="Path to the fine-tuned model directory"
    )
    parser.add_argument(
        "--description",
        type=str,
        default="A scene with a red cube rotating in the center",
        help="Scene description"
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=512,
        help="Maximum tokens to generate"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file to save generated code (optional)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Three.js Code Generation with Fine-tuned CodeLlama")
    print("=" * 60)
    print(f"\nDescription: {args.description}\n")
    
    # Generate code
    code = generate_threejs_code(args.model_path, args.description, args.max_tokens)
    
    print("\n" + "=" * 60)
    print("Generated Code:")
    print("=" * 60)
    print(code)
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            f.write(code)
        print(f"\n✓ Code saved to {args.output}")
    
    print("\n" + "=" * 60)
    print("Next steps:")
    print("1. Save the code to a .js file")
    print("2. Use pipeline/load_code.py to render it")
    print("3. Use pipeline/eval_screenshot.py to evaluate the result")
    print("=" * 60)


if __name__ == "__main__":
    main()

