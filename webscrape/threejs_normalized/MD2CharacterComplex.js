
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
/**
 * The mesh scale.
 *
 * @type {number}
 * @default 1
 */
this.scale = 1;

/**
 * The FPS
 *
 * @type {number}
 * @default 6
 */
/**
 * The FPS
 *
 * @type {number}
 * @default 6
 */
this.animationFPS = 6;

/**
 * The transition frames.
 *
 * @type {number}
 * @default 15
 */
/**
 * The transition frames.
 *
 * @type {number}
 * @default 15
 */
this.transitionFrames = 15;

/**
 * The character's maximum speed.
 *
 * @type {number}
 * @default 275
 */
/**
 * The character's maximum speed.
 *
 * @type {number}
 * @default 275
 */
this.maxSpeed = 275;

/**
 * The character's maximum reverse speed.
 *
 * @type {number}
 * @default - 275
 */
/**
 * The character's maximum reverse speed.
 *
 * @type {number}
 * @default - 275
 */
this.maxReverseSpeed = -275;

/**
 * The character's front acceleration.
 *
 * @type {number}
 * @default 600
 */
/**
 * The character's front acceleration.
 *
 * @type {number}
 * @default 600
 */
this.frontAcceleration = 600;

/**
 * The character's back acceleration.
 *
 * @type {number}
 * @default 600
 */
/**
 * The character's back acceleration.
 *
 * @type {number}
 * @default 600
 */
this.backAcceleration = 600;

/**
 * The character's front deceleration.
 *
 * @type {number}
 * @default 600
 */
/**
 * The character's front deceleration.
 *
 * @type {number}
 * @default 600
 */
this.frontDeceleration = 600;

/**
 * The character's angular speed.
 *
 * @type {number}
 * @default 2.5
 */
/**
 * The character's angular speed.
 *
 * @type {number}
 * @default 2.5
 */
this.angularSpeed = 2.5;

/**
 * The root 3D object
 *
 * @type {Object3D}
 */
/**
 * The root 3D object
 *
 * @type {Object3D}
 */
this.root = new Object3D();

/**
 * The body mesh.
 *
 * @type {?Mesh}
 * @default null
 */
/**
 * The body mesh.
 *
 * @type {?Mesh}
 * @default null
 */
this.meshBody = null;

/**
 * The weapon mesh.
 *
 * @type {?Mesh}
 * @default null
 */
/**
 * The weapon mesh.
 *
 * @type {?Mesh}
 * @default null
 */
this.meshWeapon = null;

/**
 * The movement controls.
 *
 * @type {?Object}
 * @default null
 */
/**
 * The movement controls.
 *
 * @type {?Object}
 * @default null
 */
this.controls = null;

/**
 * The body skins.
 *
 * @type {Array<Texture>}
 */
/**
 * The body skins.
 *
 * @type {Array<Texture>}
 */
this.skinsBody = [];

/**
 * The weapon skins.
 *
 * @type {Array<Texture>}
 */
/**
 * The weapon skins.
 *
 * @type {Array<Texture>}
 */
this.skinsWeapon = [];

/**
 * The weapon meshes.
 *
 * @type {Array<Mesh>}
 */
/**
 * The weapon meshes.
 *
 * @type {Array<Mesh>}
 */
this.weapons = [];

/**
 * The current skin.
 *
 * @type {Texture}
 * @default undefined
 */
/**
 * The current skin.
 *
 * @type {Texture}
 * @default undefined
 */
this.currentSkin = undefined;

//
//

this.onLoadComplete = function () {};

// internals
// internals

this.meshes = [];
this.animations = {};
this.loadCounter = 0;

// internal movement control variables
// internal movement control variables

this.speed = 0;
this.bodyOrientation = 0;
this.walkSpeed = this.maxSpeed;
this.crouchSpeed = this.maxSpeed * 0.5;

// internal animation parameters
// internal animation parameters

this.activeAnimation = null;
this.oldAnimation = null;

// API
let i = 0;
this.meshes[i].castShadow = enable;
this.meshes[i].receiveShadow = enable;
let i = 0;
this.meshes[i].visible = enable;
this.meshes[i].visible = enable;
this.animations = original.animations;
this.walkSpeed = original.walkSpeed;
this.crouchSpeed = original.crouchSpeed;
this.skinsBody = original.skinsBody;
this.skinsWeapon = original.skinsWeapon;

// BODY
// BODY

const mesh = this._createPart(original.meshBody.geometry, this.skinsBody[0]);
mesh.scale.set(this.scale, this.scale, this.scale);
this.root.position.y = original.root.position.y;
this.root.add(mesh);
this.meshBody = mesh;
this.meshes.push(mesh);

// WEAPONS
let i = 0;
const meshWeapon = this._createPart(original.weapons[i].geometry, this.skinsWeapon[i]);
meshWeapon.scale.set(this.scale, this.scale, this.scale);
meshWeapon.visible = false;
meshWeapon.name = original.weapons[i].name;
this.root.add(meshWeapon);
this.weapons[i] = meshWeapon;
this.meshWeapon = meshWeapon;
this.meshes.push(meshWeapon);
const scope = this;
function loadTextures(baseUrl, textureUrls) {
  const textureLoader = new TextureLoader();
  const textures = [];
  for (let i = 0; i < textureUrls.length; i++) {
    textures[i] = textureLoader.load(baseUrl + textureUrls[i], checkLoadingComplete);
    textures[i].mapping = UVMapping;
    textures[i].name = textureUrls[i];
    textures[i].colorSpace = SRGBColorSpace;
  }
  return textures;
}
const textureLoader = new TextureLoader();
const textures = [];
let i = 0;
textures[i] = textureLoader.load(baseUrl + textureUrls[i], checkLoadingComplete);
textures[i].mapping = UVMapping;
textures[i].name = textureUrls[i];
textures[i].colorSpace = SRGBColorSpace;
function checkLoadingComplete() {
  scope.loadCounter -= 1;
  if (scope.loadCounter === 0) scope.onLoadComplete();
}
scope.loadCounter -= 1;
scope.onLoadComplete();
this.animations = config.animations;
this.walkSpeed = config.walkSpeed;
this.crouchSpeed = config.crouchSpeed;
this.loadCounter = config.weapons.length * 2 + config.skins.length + 1;
const weaponsTextures = [];
let i = 0;
weaponsTextures[i] = config.weapons[i][1];
// SKINS

this.skinsBody = loadTextures(config.baseUrl + 'skins/', config.skins);
this.skinsWeapon = loadTextures(config.baseUrl + 'skins/', weaponsTextures);

// BODY
// BODY

const loader = new MD2Loader();
loader.load(config.baseUrl + config.body, function (geo) {
  const boundingBox = new Box3();
  boundingBox.setFromBufferAttribute(geo.attributes.position);
  scope.root.position.y = -scope.scale * boundingBox.min.y;
  const mesh = scope._createPart(geo, scope.skinsBody[0]);
  mesh.scale.set(scope.scale, scope.scale, scope.scale);
  scope.root.add(mesh);
  scope.meshBody = mesh;
  scope.meshes.push(mesh);
  checkLoadingComplete();
});

// WEAPONS
const boundingBox = new Box3();
boundingBox.setFromBufferAttribute(geo.attributes.position);
scope.root.position.y = -scope.scale * boundingBox.min.y;
const mesh = scope._createPart(geo, scope.skinsBody[0]);
mesh.scale.set(scope.scale, scope.scale, scope.scale);
scope.root.add(mesh);
scope.meshBody = mesh;
scope.meshes.push(mesh);
checkLoadingComplete();
// WEAPONS

const generateCallback = function (index, name) {
  return function (geo) {
    const mesh = scope._createPart(geo, scope.skinsWeapon[index]);
    mesh.scale.set(scope.scale, scope.scale, scope.scale);
    mesh.visible = false;
    mesh.name = name;
    scope.root.add(mesh);
    scope.weapons[index] = mesh;
    scope.meshWeapon = mesh;
    scope.meshes.push(mesh);
    checkLoadingComplete();
  };
};
const mesh = scope._createPart(geo, scope.skinsWeapon[index]);
mesh.scale.set(scope.scale, scope.scale, scope.scale);
mesh.visible = false;
mesh.name = name;
scope.root.add(mesh);
scope.weapons[index] = mesh;
scope.meshWeapon = mesh;
scope.meshes.push(mesh);
checkLoadingComplete();
let i = 0;
loader.load(config.baseUrl + config.weapons[i][0], generateCallback(i, config.weapons[i][0]));
this.meshBody.duration = this.meshBody.baseDuration / rate;
this.meshWeapon.duration = this.meshWeapon.baseDuration / rate;
this.meshBody.material = this.meshBody.materialWireframe;
this.meshWeapon.material = this.meshWeapon.materialWireframe;
this.meshBody.material = this.meshBody.materialTexture;
this.meshWeapon.material = this.meshWeapon.materialTexture;
this.meshBody.material.map = this.skinsBody[index];
this.currentSkin = index;
let i = 0;
this.weapons[i].visible = false;
const activeWeapon = this.weapons[index];
activeWeapon.visible = true;
this.meshWeapon = activeWeapon;
activeWeapon.playAnimation(this.activeAnimation);
this.meshWeapon.setAnimationTime(this.activeAnimation, this.meshBody.getAnimationTime(this.activeAnimation));
this.meshBody.setAnimationWeight(animationName, 0);
this.meshBody.playAnimation(animationName);
this.oldAnimation = this.activeAnimation;
this.activeAnimation = animationName;
this.blendCounter = this.transitionFrames;
this.meshWeapon.setAnimationWeight(animationName, 0);
this.meshWeapon.playAnimation(animationName);
this.updateMovementModel(delta);
this.updateBehaviors();
this.updateAnimations(delta);
let mix = 1;
mix = (this.transitionFrames - this.blendCounter) / this.transitionFrames;
this.blendCounter -= 1;
this.meshBody.update(delta);
this.meshBody.setAnimationWeight(this.activeAnimation, mix);
this.meshBody.setAnimationWeight(this.oldAnimation, 1 - mix);
this.meshWeapon.update(delta);
this.meshWeapon.setAnimationWeight(this.activeAnimation, mix);
this.meshWeapon.setAnimationWeight(this.oldAnimation, 1 - mix);
const controls = this.controls;
const animations = this.animations;
let moveAnimation, idleAnimation;

// crouch vs stand
moveAnimation = animations['crouchMove'];
idleAnimation = animations['crouchIdle'];
moveAnimation = animations['move'];
idleAnimation = animations['idle'];
moveAnimation = animations['jump'];
idleAnimation = animations['jump'];
moveAnimation = animations['crouchAttack'];
idleAnimation = animations['crouchAttack'];
moveAnimation = animations['attack'];
idleAnimation = animations['attack'];
this.setAnimation(moveAnimation);
this.setAnimation(idleAnimation);
this.meshBody.setAnimationDirectionForward(this.activeAnimation);
this.meshBody.setAnimationDirectionForward(this.oldAnimation);
this.meshWeapon.setAnimationDirectionForward(this.activeAnimation);
this.meshWeapon.setAnimationDirectionForward(this.oldAnimation);
this.meshBody.setAnimationDirectionBackward(this.activeAnimation);
this.meshBody.setAnimationDirectionBackward(this.oldAnimation);
this.meshWeapon.setAnimationDirectionBackward(this.activeAnimation);
this.meshWeapon.setAnimationDirectionBackward(this.oldAnimation);
function exponentialEaseOut(k) {
  return k === 1 ? 1 : -Math.pow(2, -10 * k) + 1;
}
const controls = this.controls;

// speed based on controls
this.maxSpeed = this.crouchSpeed;
this.maxSpeed = this.walkSpeed;
this.maxReverseSpeed = -this.maxSpeed;
this.speed = MathUtils.clamp(this.speed + delta * this.frontAcceleration, this.maxReverseSpeed, this.maxSpeed);
this.speed = MathUtils.clamp(this.speed - delta * this.backAcceleration, this.maxReverseSpeed, this.maxSpeed);
// orientation based on controls
// (don't just stand while turning)

const dir = 1;
this.bodyOrientation += delta * this.angularSpeed;
this.speed = MathUtils.clamp(this.speed + dir * delta * this.frontAcceleration, this.maxReverseSpeed, this.maxSpeed);
this.bodyOrientation -= delta * this.angularSpeed;
this.speed = MathUtils.clamp(this.speed + dir * delta * this.frontAcceleration, this.maxReverseSpeed, this.maxSpeed);
const k = exponentialEaseOut(this.speed / this.maxSpeed);
this.speed = MathUtils.clamp(this.speed - k * delta * this.frontDeceleration, 0, this.maxSpeed);
const k = exponentialEaseOut(this.speed / this.maxReverseSpeed);
this.speed = MathUtils.clamp(this.speed + k * delta * this.backAcceleration, this.maxReverseSpeed, 0);
// displacement

const forwardDelta = this.speed * delta;
this.root.position.x += Math.sin(this.bodyOrientation) * forwardDelta;
this.root.position.z += Math.cos(this.bodyOrientation) * forwardDelta;

// steering
// steering

this.root.rotation.y = this.bodyOrientation;
const materialWireframe = new MeshLambertMaterial({
  color: 0xffaa00,
  wireframe: true
});
const materialTexture = new MeshLambertMaterial({
  color: 0xffffff,
  wireframe: false,
  map: skinMap
});

//
//

const mesh = new MorphBlendMesh(geometry, materialTexture);
mesh.rotation.y = -Math.PI / 2;

//
//

mesh.materialTexture = materialTexture;
mesh.materialWireframe = materialWireframe;

//
//

mesh.autoCreateAnimations(this.animationFPS);


// ===== Animation loop =====
function animate() {
  requestAnimationFrame(animate);
  renderer.render(scene, camera);
}
animate();
