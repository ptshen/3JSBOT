import * as THREE from 'three';
// Set up renderer and canvas
const container = document.querySelector('#scene');
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, container.clientWidth / container.clientHeight, 0.1, 1000);
camera.position.set(0, 10, 30);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(container.clientWidth, container.clientHeight);
container.append(renderer.domElement);
// Set up basic scene lighting
scene.add(new THREE.AmbientLight(0xffffff, 0.5));
const light = new THREE.DirectionalLight(0xffffff, 1.5);
light.position.set(0, 20, 30);
scene.add(light);
// Set up primary building geometry and material
const buildingGeometry = new THREE.BoxGeometry(4, 6, 8);
const buildingMaterial = new THREE.MeshStandardMaterial({ color: 0xFFC07B });
const primaryBuilding = new THREE.Mesh(buildingGeometry, buildingMaterial);
primaryBuilding.position.setX(-5).setZ(15);
scene.add(primaryBuilding);
// Set up secondary structure geometry and material
const structureGeometry = new THREE.BoxGeometry(4, 6, 8);
const structureMaterial = new THREE.MeshStandardMaterial({ color: 0xFFC07B });
const secondaryStructure = new THREE.Mesh(structureGeometry, structureMaterial);
secondaryStructure.position.setX(5).setZ(15);
scene.add(secondaryStructure);
// Set up terrain geometry and material
const terrainGeometry = new THREE.PlaneBufferGeometry(80, 80);
terrainGeometry.rotateX(- Math.PI / 2);
const terrainMaterial = new THREE.MeshStandardMaterial({ color: 0x59D1A3 });
const terrain = new THREE.Mesh(terrainGeometry, terrainMaterial);
scene.add(terrain);
// Set up sky geometry and material
const skyGeometry = new THREE.SphereBufferGeometry(10000, 64, 64);
const skyMaterial = new THREE.MeshStandardMaterial({ color: 0x7EAADB });
const sky = new THREE.Mesh(skyGeometry, skyMaterial);
scene.add(sky);
// Render and animate
renderer.setAnimationLoop(() => {
    renderer.render(scene, camera);
});