import * as THREE from 'three';
import VolumeSlice from './script.js'; // replace with the object you want to test

// --- Scene setup ---
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x222222);

const camera = new THREE.PerspectiveCamera(
  75,
  window.innerWidth / window.innerHeight,
  0.1,
  1000
);
camera.position.z = 5;

// --- Renderer ---
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

// --- Light ---
const pointLight = new THREE.PointLight(0xffffff, 1);
pointLight.position.set(5, 5, 5);
scene.add(pointLight);

// --- Add object to scene ---
const testObj = new VolumeSlice();
scene.add(testObj);

// --- Animation loop ---
function animate() {
  requestAnimationFrame(animate);

  // optional: rotate the object to see it better
  testObj.rotation.y += 0.01;

  renderer.render(scene, camera);
}

animate();

// --- Optional QC checks ---
console.log('Object added to scene:', testObj);
console.log('Geometry count:', testObj.geometry ? testObj.geometry.attributes.position.count : 'N/A');
console.log('Material:', testObj.material ? testObj.material : 'N/A');
