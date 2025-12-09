// Basic Three.js scene that creates a simple 3D book
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

// Scene setup
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

// Controls
const controls = new OrbitControls(camera, renderer.domElement);

// Lighting
const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
scene.add(ambientLight);

const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
directionalLight.position.set(5, 10, 7);
scene.add(directionalLight);

// Book dimensions
const coverWidth = 4;
const coverHeight = 6;
const coverDepth = 0.2;
const pagesDepth = 1.2;

// Materials
const coverMaterial = new THREE.MeshPhongMaterial({ color: 0x553311 });
const pagesMaterial = new THREE.MeshPhongMaterial({ color: 0xf5f5dc });

// Book cover (back)
const backCoverGeometry = new THREE.BoxGeometry(coverWidth, coverHeight, coverDepth);
const backCover = new THREE.Mesh(backCoverGeometry, coverMaterial);
backCover.position.z = -pagesDepth / 2;
scene.add(backCover);

// Book cover (front)
const frontCover = new THREE.Mesh(backCoverGeometry, coverMaterial);
frontCover.position.z = pagesDepth / 2;
scene.add(frontCover);

// Pages block
const pagesGeometry = new THREE.BoxGeometry(coverWidth * 0.98, coverHeight * 0.97, pagesDepth);
const pages = new THREE.Mesh(pagesGeometry, pagesMaterial);
scene.add(pages);

// Camera position
camera.position.set(8, 8, 10);
camera.lookAt(0, 0, 0);

// Render loop
function animate() {
  requestAnimationFrame(animate);
  renderer.render(scene, camera);
}

animate();

// Resize handler
window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});
