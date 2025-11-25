import * as THREE from 'three';
const scene = new THREE.Scene();

// Add a box to the scene
const geometry = new THREE.BoxGeometry(1, 1, 1);
const material = new THREE.MeshBasicMaterial({ color: 0x00ff00 });
const mesh = new THREE.Mesh(geometry, material);
scene.add(mesh);

// Add a bowl to the scene
const geometry2 = new THREE.TorusGeometry(1, 0.3, 64, 64);
const material2 = new THREE.MeshBasicMaterial({ color: 0xffffff });
const mesh2 = new THREE.Mesh(geometry2, material2);
mesh2.position.set(0, 1, 0);
scene.add(mesh2);

// Add a camera to the scene
const fov = 75;
const aspect = window.innerWidth / window.innerHeight;
const near = 0.1;
const far = 1000;
const camera = new THREE.PerspectiveCamera(fov, aspect, near, far);
camera.position.z = 5;
scene.add(camera);

// Add a renderer to the scene
const renderer = new THREE.WebGLRenderer({ antialias: true });
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