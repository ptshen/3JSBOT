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

// Polyfill for deprecated THREE.Geometry class (removed in r125+)
class LegacyGeometry extends THREE.BufferGeometry {
    constructor() {
        super();
        this.vertices = [];
        this.faces = [];
        this.type = 'Geometry';
    }

    // Convert legacy vertices/faces to BufferGeometry attributes
    _updateBufferGeometry() {
        if (this.vertices.length === 0) return;

        const positions = new Float32Array(this.vertices.length * 3);
        for (let i = 0; i < this.vertices.length; i++) {
            positions[i * 3] = this.vertices[i].x;
            positions[i * 3 + 1] = this.vertices[i].y;
            positions[i * 3 + 2] = this.vertices[i].z;
        }
        this.setAttribute('position', new THREE.BufferAttribute(positions, 3));

        if (this.faces.length > 0) {
            const indices = new Uint16Array(this.faces.length * 3);
            for (let i = 0; i < this.faces.length; i++) {
                indices[i * 3] = this.faces[i].a;
                indices[i * 3 + 1] = this.faces[i].b;
                indices[i * 3 + 2] = this.faces[i].c;
            }
            this.setIndex(new THREE.BufferAttribute(indices, 1));
        }

        this.computeVertexNormals();
    }
}

// Wrap THREE.Mesh to auto-convert LegacyGeometry when used
const OriginalMesh = THREE.Mesh;
class MeshWrapper extends OriginalMesh {
    constructor(geometry, material) {
        // If geometry is LegacyGeometry and has vertices, convert it
        if (geometry instanceof LegacyGeometry && geometry.vertices.length > 0) {
            geometry._updateBufferGeometry();
        }
        super(geometry, material);
    }
}

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
    TorusKnotBufferGeometry: THREE.TorusKnotGeometry,
    // Add polyfill for removed Geometry class
    Geometry: LegacyGeometry,
    // Override Mesh to auto-convert legacy geometries
    Mesh: MeshWrapper
};

// Basic Three.js scene that creates a simple 3D book
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

// Scene setup
const scene = new window.THREE.Scene();
const camera = new window.THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new window.THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

// Controls
const controls = new OrbitControls(camera, renderer.domElement);

// Lighting
const ambientLight = new window.THREE.AmbientLight(0xffffff, 0.6);
scene.add(ambientLight);

const directionalLight = new window.THREE.DirectionalLight(0xffffff, 0.8);
directionalLight.position.set(5, 10, 7);
scene.add(directionalLight);

// Book dimensions
const coverWidth = 4;
const coverHeight = 6;
const coverDepth = 0.2;
const pagesDepth = 1.2;

// Materials
const coverMaterial = new window.THREE.MeshPhongMaterial({ color: 0x553311 });
const pagesMaterial = new window.THREE.MeshPhongMaterial({ color: 0xf5f5dc });

// Book cover (back)
const backCoverGeometry = new window.THREE.BoxGeometry(coverWidth, coverHeight, coverDepth);
const backCover = new window.THREE.Mesh(backCoverGeometry, coverMaterial);
backCover.position.z = -pagesDepth / 2;
scene.add(backCover);

// Book cover (front)
const frontCover = new window.THREE.Mesh(backCoverGeometry, coverMaterial);
frontCover.position.z = pagesDepth / 2;
scene.add(frontCover);

// Pages block
const pagesGeometry = new window.THREE.BoxGeometry(coverWidth * 0.98, coverHeight * 0.97, pagesDepth);
const pages = new window.THREE.Mesh(pagesGeometry, pagesMaterial);
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


// Auto-fix camera position if it's at origin (common mistake in generated code)
if (typeof camera !== 'undefined' && camera.position.x === 0 && camera.position.y === 0 && camera.position.z === 0) {
    camera.position.z = 5;
}
// Auto-fix camera lookAt if camera exists and hasn't been pointed at anything
if (typeof camera !== 'undefined') {
    camera.lookAt(0, 0, 0);
}
