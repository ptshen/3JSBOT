# Training Data Requirements for CodeLlama Three.js Fine-Tuning

## The Problem with Current Data

Your current training data has a **fundamental mismatch**:

1. **Input (Descriptions)**: Long, artistic descriptions of what the rendered scene *looks like*
   - Example: "A minimalist three.js scene featuring a single wooden crate... with realistic wood texture... black background..."
   - These are **output descriptions** (what the result should look like), not **instructions** (what code to write)

2. **Output (Code)**: Complex Three.js code with:
   - External dependencies (loaders, controls, etc.)
   - File paths that don't exist (`'textures/crate.gif'`)
   - Advanced features (GLTF loading, IK solvers, etc.)
   - Code that may not match the description

## What Data You Actually Need

For training CodeLlama to generate Three.js code, you need:

### Input Format: **Instructional Descriptions**

Clear, concise instructions about **what to create**, not what it looks like:

**Good Examples:**
- "Create a rotating cube with a texture"
- "Add a red sphere at position (0, 0, 0) with ambient lighting"
- "Create a scene with a blue box that rotates on the Y axis"
- "Add a plane with a checkerboard texture and a directional light"
- "Create a scene with multiple colored cubes arranged in a grid"

**Bad Examples (Current Format):**
- "A minimalist three.js scene featuring a single wooden crate..." ❌
- "This is a warmly-lit interior scene rendered in three.js..." ❌
- "The scene demonstrates professional three.js rendering with..." ❌

### Output Format: **Simple, Self-Contained Code**

The code should be:
- **Self-contained**: No external file dependencies (textures, models, etc.)
- **Simple**: Focus on basic Three.js concepts (geometries, materials, lighting, animation)
- **Working**: Code that actually runs and produces the described scene
- **Matched**: Code that clearly implements the instruction

**Good Example:**
```javascript
// Create scene, camera, renderer
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer();
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

// Create rotating cube
const geometry = new THREE.BoxGeometry();
const material = new THREE.MeshBasicMaterial({ color: 0x00ff00 });
const cube = new THREE.Mesh(geometry, material);
scene.add(cube);

camera.position.z = 5;

// Animation loop
function animate() {
    requestAnimationFrame(animate);
    cube.rotation.x += 0.01;
    cube.rotation.y += 0.01;
    renderer.render(scene, camera);
}
animate();
```

**Bad Example (Current Format):**
```javascript
// Has external dependencies
const texture = new THREE.TextureLoader().load('textures/crate.gif'); // File doesn't exist
// Complex setup with controls, loaders, etc.
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
// Code doesn't match description
```

## Where to Get Good Training Data

### Option 1: Create Your Own Dataset (Recommended)

Manually create 100-500 examples with:
- **Simple instructions** (1-2 sentences)
- **Simple code** (20-100 lines, self-contained)
- **Clear matching** (code implements the instruction)

**Example Pair:**
```json
{
  "description": "Create a rotating red cube in the center of the scene",
  "code": "const scene = new THREE.Scene();\nconst camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);\nconst renderer = new THREE.WebGLRenderer();\nrenderer.setSize(window.innerWidth, window.innerHeight);\ndocument.body.appendChild(renderer.domElement);\n\nconst geometry = new THREE.BoxGeometry();\nconst material = new THREE.MeshBasicMaterial({ color: 0xff0000 });\nconst cube = new THREE.Mesh(geometry, material);\nscene.add(cube);\n\ncamera.position.z = 5;\n\nfunction animate() {\n    requestAnimationFrame(animate);\n    cube.rotation.x += 0.01;\n    cube.rotation.y += 0.01;\n    renderer.render(scene, camera);\n}\nanimate();"
}
```

### Option 2: Use Three.js Official Examples (Filtered)

Filter the Three.js examples to:
- Only simple examples (no loaders, no external files)
- Rewrite descriptions as instructions
- Remove complex features

**Filtering Criteria:**
- ✅ Basic geometries (BoxGeometry, SphereGeometry, etc.)
- ✅ Basic materials (MeshBasicMaterial, MeshStandardMaterial)
- ✅ Basic lighting (AmbientLight, DirectionalLight)
- ✅ Simple animations
- ❌ No GLTF/OBJ/other loaders
- ❌ No external texture files
- ❌ No physics engines
- ❌ No post-processing

### Option 3: Use AI to Generate Synthetic Data

Use GPT-4/Claude to:
1. Generate simple Three.js instructions
2. Generate matching code
3. Verify code works
4. Create training pairs

**Prompt Template:**
```
Generate a simple Three.js code example with:
- A clear, one-sentence instruction
- Self-contained code (no external files)
- Basic Three.js features only
- Code that actually works
```

## Data Format for Training

Your training data should be a JSON array:

```json
[
  {
    "description": "Instructional description of what to create",
    "code": "Complete, self-contained Three.js JavaScript code",
    "filename": "example_1"
  },
  ...
]
```

## Quality Checklist

Each training example should:
- [ ] Description is an **instruction**, not a visual description
- [ ] Description is **clear and concise** (1-3 sentences)
- [ ] Code is **self-contained** (no external files)
- [ ] Code is **simple** (basic Three.js features)
- [ ] Code **matches the description** (implements the instruction)
- [ ] Code **actually works** (can be run and renders correctly)
- [ ] Code is **complete** (includes scene, camera, renderer, animation loop)

## Recommended Dataset Size

- **Minimum**: 100 examples
- **Good**: 300-500 examples
- **Excellent**: 1000+ examples

Focus on **quality over quantity**. 100 good examples is better than 1000 bad ones.

## Next Steps

1. **Create a small test dataset** (10-20 examples) manually
2. **Test training** on this small dataset
3. **Evaluate results** - does the model generate good code?
4. **Scale up** if results are good, or refine the format if not

