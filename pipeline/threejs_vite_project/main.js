import * as THREE from 'three';

// Import common three.js addons
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { TeapotGeometry } from 'three/examples/jsm/geometries/TeapotGeometry.js';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js';
import { FBXLoader } from 'three/examples/jsm/loaders/FBXLoader.js';
import { FontLoader } from 'three/examples/jsm/loaders/FontLoader.js';
import { TextGeometry } from 'three/examples/jsm/geometries/TextGeometry.js';

// Make THREE globally available with addons by extending it
window.THREE = {
    ...THREE,
    OrbitControls,
    TeapotGeometry,
    TeapotBufferGeometry: TeapotGeometry, // Alias for older code
    RoundedBoxGeometry,
    GLTFLoader,
    OBJLoader,
    FBXLoader,
    FontLoader,
    TextGeometry,
    // Add aliases for deprecated BufferGeometry classes (for backwards compatibility)
    BoxBufferGeometry: THREE.BoxGeometry,
    SphereBufferGeometry: THREE.SphereGeometry,
    PlaneBufferGeometry: THREE.PlaneGeometry,
    CylinderBufferGeometry: THREE.CylinderGeometry,
    ConeBufferGeometry: THREE.ConeGeometry,
    TorusBufferGeometry: THREE.TorusGeometry,
    TorusKnotBufferGeometry: THREE.TorusKnotGeometry
};

const scene = new window.THREE.Scene();

// Add a box to the scene
const geometry = new window.THREE.BoxGeometry(1, 1, 1);
const material = new window.THREE.MeshBasicMaterial({ color: 0x00ff00 });
const mesh = new window.THREE.Mesh(geometry, material);
scene.add(mesh);

// Add a bowl to the scene
const geometry2 = new window.THREE.TorusGeometry(1, 0.3, 64, 64);
const material2 = new window.THREE.MeshBasicMaterial({ color: 0xffffff });
const mesh2 = new window.THREE.Mesh(geometry2, material2);
mesh2.position.set(0, 1, 0);
scene.add(mesh2);

// Add a camera to the scene
const fov = 75;
const aspect = window.innerWidth / window.innerHeight;
const near = 0.1;
const far = 1000;
const camera = new window.THREE.PerspectiveCamera(fov, aspect, near, far);
camera.position.z = 5;
scene.add(camera);

// Add a renderer to the scene
const renderer = new window.THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

// Animate the bowl
function animate() {
  requestAnimationFrame(animate);
  mesh2.rotation.x += 0.01;
  mesh2.rotation.y += 0.01;
  renderer.render(scene, camera);
}
animate();