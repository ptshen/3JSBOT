
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

/**
 * A dictionary of animations.
 *
 * @type {Object<string,Object>}
 */
/**
 * A dictionary of animations.
 *
 * @type {Object<string,Object>}
 */
this.animationsMap = {};

/**
 * A list of animations.
 *
 * @type {Array<Object>}
 */
/**
 * A list of animations.
 *
 * @type {Array<Object>}
 */
this.animationsList = [];

// prepare default animation
// (all frames played together in 1 second)
// prepare default animation
// (all frames played together in 1 second)

const numFrames = Object.keys(this.morphTargetDictionary).length;
const name = '__default';
const startFrame = 0;
const endFrame = numFrames - 1;
const fps = numFrames / 1;
this.createAnimation(name, startFrame, endFrame, fps);
this.setAnimationWeight(name, 1);
const animation = {
  start: start,
  end: end,
  length: end - start + 1,
  fps: fps,
  duration: (end - start) / fps,
  lastFrame: 0,
  currentFrame: 0,
  active: false,
  time: 0,
  direction: 1,
  weight: 1,
  directionBackwards: false,
  mirroredLoop: false
};
this.animationsMap[name] = animation;
this.animationsList.push(animation);
const pattern = /([a-z]+)_?(\d+)/i;
let firstAnimation;
const frameRanges = {};
let i = 0;
const key;
const chunks = key.match(pattern);
const name = chunks[1];
frameRanges[name] = {
  start: Infinity,
  end: -Infinity
};
const range = frameRanges[name];
range.start = i;
range.end = i;
firstAnimation = name;
i++;
const name;
const range = frameRanges[name];
this.createAnimation(name, range.start, range.end, fps);
this.firstAnimation = firstAnimation;
const animation = this.animationsMap[name];
animation.direction = 1;
animation.directionBackwards = false;
const animation = this.animationsMap[name];
animation.direction = -1;
animation.directionBackwards = true;
const animation = this.animationsMap[name];
animation.fps = fps;
animation.duration = (animation.end - animation.start) / animation.fps;
const animation = this.animationsMap[name];
animation.duration = duration;
animation.fps = (animation.end - animation.start) / animation.duration;
const animation = this.animationsMap[name];
animation.weight = weight;
const animation = this.animationsMap[name];
animation.time = time;
let time = 0;
const animation = this.animationsMap[name];
time = animation.time;
let duration = -1;
const animation = this.animationsMap[name];
duration = animation.duration;
const animation = this.animationsMap[name];
animation.time = 0;
animation.active = true;
console.warn('THREE.MorphBlendMesh: animation[' + name + '] undefined in .playAnimation()');
const animation = this.animationsMap[name];
animation.active = false;
let i = 0,
  il = this.animationsList.length;
const animation = this.animationsList[i];
const frameTime = animation.duration / animation.length;
animation.time += animation.direction * delta;
animation.direction *= -1;
animation.time = animation.duration;
animation.directionBackwards = true;
animation.time = 0;
animation.directionBackwards = false;
animation.time = animation.time % animation.duration;
animation.time += animation.duration;
const keyframe = animation.start + MathUtils.clamp(Math.floor(animation.time / frameTime), 0, animation.length - 1);
const weight = animation.weight;
this.morphTargetInfluences[animation.lastFrame] = 0;
this.morphTargetInfluences[animation.currentFrame] = 1 * weight;
this.morphTargetInfluences[keyframe] = 0;
animation.lastFrame = animation.currentFrame;
animation.currentFrame = keyframe;
let mix = animation.time % frameTime / frameTime;
mix = 1 - mix;
this.morphTargetInfluences[animation.currentFrame] = mix * weight;
this.morphTargetInfluences[animation.lastFrame] = (1 - mix) * weight;
this.morphTargetInfluences[animation.currentFrame] = weight;


// ===== Animation loop =====
function animate() {
  requestAnimationFrame(animate);
  renderer.render(scene, camera);
}
animate();
