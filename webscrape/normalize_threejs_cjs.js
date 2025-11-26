// normalize_threejs_cjs.js
const fs = require("fs");
const path = require("path");
const parser = require("@babel/parser");
const traverse = require("@babel/traverse").default;
const generate = require("@babel/generator").default;

// ===== CONFIG =====
const INPUT_DIR = "./temporary";           // folder with raw JS examples
const OUTPUT_DIR = "./threejs_normalized"; // folder for normalized output
if (!fs.existsSync(OUTPUT_DIR)) fs.mkdirSync(OUTPUT_DIR);

// ===== Helper: wrap code in standard Three.js scaffold =====
function wrapInScene(code) {
  return `
import * as THREE from 'three';

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth/window.innerHeight, 0.1, 1000);
camera.position.z = 5;

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

const pointLight = new THREE.PointLight(0xffffff, 1, 100, 2);
pointLight.position.set(5, 5, 5);
scene.add(pointLight);

// ===== Original code =====
${code}

// ===== Animation loop =====
function animate() {
  requestAnimationFrame(animate);
  renderer.render(scene, camera);
}
animate();
`;
}

// ===== Helper: extract only the top-level Three.js code =====
function extractThreeJS(rawCode) {
  // Parse the code
  const ast = parser.parse(rawCode, { sourceType: "module", plugins: ["jsx"] });

  let extracted = "";

  traverse(ast, {
    enter(path) {
      // Keep only expressions and variable declarations
      if (
        path.isVariableDeclaration() ||
        path.isExpressionStatement() ||
        path.isFunctionDeclaration()
      ) {
        extracted += generate(path.node).code + "\n";
      }
    }
  });

  return extracted;
}

// ===== Main processing =====
fs.readdirSync(INPUT_DIR).forEach(file => {
  if (!file.endsWith(".js")) return;

  const inputPath = path.join(INPUT_DIR, file);
  const rawCode = fs.readFileSync(inputPath, "utf-8");

  const extractedCode = extractThreeJS(rawCode);
  const normalizedCode = wrapInScene(extractedCode);

  const outputPath = path.join(OUTPUT_DIR, file);
  fs.writeFileSync(outputPath, normalizedCode, "utf-8");

  console.log(`✅ Normalized: ${file}`);
});

console.log("All files processed and normalized!");
