
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
super(geometry, material);
this.type = 'MorphAnimMesh';

/**
 * The internal animation mixer.
 *
 * @type {AnimationMixer}
 */
/**
 * The internal animation mixer.
 *
 * @type {AnimationMixer}
 */
this.mixer = new AnimationMixer(this);

/**
 * The current active animation action.
 *
 * @type {?AnimationAction}
 * @default null
 */
/**
 * The current active animation action.
 *
 * @type {?AnimationAction}
 * @default null
 */
this.activeAction = null;
this.mixer.timeScale = 1.0;
this.mixer.timeScale = -1.0;
this.activeAction.stop();
this.activeAction = null;
const clip = AnimationClip.findByName(this, label);
const action = this.mixer.clipAction(clip);
action.timeScale = clip.tracks.length * fps / clip.duration;
this.activeAction = action.play();
this.mixer.update(delta);
super.copy(source, recursive);
this.mixer = new AnimationMixer(this);


// ===== Animation loop =====
function animate() {
  requestAnimationFrame(animate);
  renderer.render(scene, camera);
}
animate();
