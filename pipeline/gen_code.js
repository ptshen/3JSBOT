import * as THREE from 'three';

// Create the scene and camera
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
camera.position.z = 5;

// Create a teapot geometry and material
const teapotGeometry = new THREE.TeapotBufferGeometry(1, 20, 20);
const teapotMaterial = new THREE.MeshBasicMaterial({ color: 0xffffff });
const teapot = new THREE.Mesh(teapotGeometry, teapotMaterial);
scene.add(teapot);

// Create a light source and add it to the scene
const pointLight = new THREE.PointLight(0xffffff, 1, 100, 2);
pointLight.position.set(5, 5, 5);
scene.add(pointLight);

// Create a renderer and add it to the DOM
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

// Start the animation loop
function animate() {
  requestAnimationFrame(animate);
  renderer.render(scene, camera);
}
animate();