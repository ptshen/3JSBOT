
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
 * The renderer.
 *
 * @type {WebGPURenderer}
 */
this.renderer = renderer;

/**
 * The side-long dimension of the total lightmap.
 *
 * @type {number}
 * @default 1024
 */
/**
 * The side-long dimension of the total lightmap.
 *
 * @type {number}
 * @default 1024
 */
this.resolution = resolution;
this._lightMapContainers = [];
this._scene = new Scene();
this._buffer1Active = false;
this._labelMesh = null;
this._blurringPlane = null;

// Create the Progressive LightMap Texture
// Create the Progressive LightMap Texture

const type = /(Android|iPad|iPhone|iPod)/g.test(navigator.userAgent) ? HalfFloatType : FloatType;
this._progressiveLightMap1 = new RenderTarget(this.resolution, this.resolution, {
  type: type
});
this._progressiveLightMap2 = new RenderTarget(this.resolution, this.resolution, {
  type: type
});
this._progressiveLightMap2.texture.channel = 1;

// uniforms
// uniforms

this._averagingWindow = uniform(100);
this._previousShadowMap = texture(this._progressiveLightMap1.texture);

// materials
// materials

const uvNode = uv(1).flipY();
this._uvMat = new MeshPhongNodeMaterial();
this._uvMat.vertexNode = vec4(sub(uvNode, vec2(0.5)).mul(2), 1, 1);
this._uvMat.outputNode = vec4(mix(this._previousShadowMap.sample(uv(1)), output, float(1).div(this._averagingWindow)));
// Prepare list of UV bounding boxes for packing later...
const uv_boxes = [];
const padding = 3 / this.resolution;
let ob = 0;
const object = objects[ob];

// If this object is a light, simply add it to the internal scene
this._scene.attach(object);
console.warn('THREE.ProgressiveLightMap: All lightmap objects need uvs.');
console.warn('THREE.ProgressiveLightMap: All lightmap objects need normals.');
this._initializeBlurPlane();
// Apply the lightmap to the object
object.material.lightMap = this._progressiveLightMap2.texture;
object.material.dithering = true;
object.castShadow = true;
object.receiveShadow = true;
object.renderOrder = 1000 + ob;

// Prepare UV boxes for potpack (potpack will update x and y)
// TODO: Size these by object surface area
// Prepare UV boxes for potpack (potpack will update x and y)
// TODO: Size these by object surface area
uv_boxes.push({
  w: 1 + padding * 2,
  h: 1 + padding * 2,
  index: ob,
  x: 0,
  y: 0
});
this._lightMapContainers.push({
  basicMat: object.material,
  object: object
});
// Pack the objects' lightmap UVs into the same global space
const dimensions = potpack(uv_boxes);
uv_boxes.forEach(box => {
  const uv1 = objects[box.index].geometry.getAttribute('uv').clone();
  for (let i = 0; i < uv1.array.length; i += uv1.itemSize) {
    uv1.array[i] = (uv1.array[i] + box.x + padding) / dimensions.w;
    uv1.array[i + 1] = 1 - (uv1.array[i + 1] + box.y + padding) / dimensions.h;
  }
  objects[box.index].geometry.setAttribute('uv1', uv1);
  objects[box.index].geometry.getAttribute('uv1').needsUpdate = true;
});
const uv1 = objects[box.index].geometry.getAttribute('uv').clone();
let i = 0;
uv1.array[i] = (uv1.array[i] + box.x + padding) / dimensions.w;
uv1.array[i + 1] = 1 - (uv1.array[i + 1] + box.y + padding) / dimensions.h;
objects[box.index].geometry.setAttribute('uv1', uv1);
objects[box.index].geometry.getAttribute('uv1').needsUpdate = true;
this._progressiveLightMap1.dispose();
this._progressiveLightMap2.dispose();
this._uvMat.dispose();
this._blurringPlane.geometry.dispose();
this._blurringPlane.material.dispose();
this._labelMesh.geometry.dispose();
this._labelMesh.material.dispose();
// Store the original Render Target
const currentRenderTarget = this.renderer.getRenderTarget();

// The blurring plane applies blur to the seams of the lightmap
// The blurring plane applies blur to the seams of the lightmap
this._blurringPlane.visible = blurEdges;

// Steal the Object3D from the real world to our special dimension
let l = 0;
this._lightMapContainers[l].object.oldScene = this._lightMapContainers[l].object.parent;
this._scene.attach(this._lightMapContainers[l].object);
let l = 0;
this._averagingWindow.value = blendWindow;
this._lightMapContainers[l].object.material = this._uvMat;
this._lightMapContainers[l].object.oldFrustumCulled = this._lightMapContainers[l].object.frustumCulled;
this._lightMapContainers[l].object.frustumCulled = false;
// Ping-pong two surface buffers for reading/writing
const activeMap = this._buffer1Active ? this._progressiveLightMap1 : this._progressiveLightMap2;
const inactiveMap = this._buffer1Active ? this._progressiveLightMap2 : this._progressiveLightMap1;

// Render the object's surface maps
// Render the object's surface maps
this.renderer.setRenderTarget(activeMap);
this._previousShadowMap.value = inactiveMap.texture;
this._buffer1Active = !this._buffer1Active;
this.renderer.render(this._scene, camera);

// Restore the object's Real-time Material and add it back to the original world
let l = 0;
this._lightMapContainers[l].object.frustumCulled = this._lightMapContainers[l].object.oldFrustumCulled;
this._lightMapContainers[l].object.material = this._lightMapContainers[l].basicMat;
this._lightMapContainers[l].object.oldScene.attach(this._lightMapContainers[l].object);
// Restore the original Render Target
this.renderer.setRenderTarget(currentRenderTarget);
console.warn('THREE.ProgressiveLightMap: Call .showDebugLightmap() after adding the objects.');
const labelMaterial = new NodeMaterial();
labelMaterial.colorNode = texture(this._progressiveLightMap1.texture).sample(uv().flipY());
labelMaterial.side = DoubleSide;
const labelGeometry = new PlaneGeometry(100, 100);
this._labelMesh = new Mesh(labelGeometry, labelMaterial);
this._labelMesh.position.y = 250;
this._lightMapContainers[0].object.parent.add(this._labelMesh);
this._labelMesh.position.copy(position);
this._labelMesh.visible = visible;
const blurMaterial = new NodeMaterial();
blurMaterial.polygonOffset = true;
blurMaterial.polygonOffsetFactor = -1;
blurMaterial.polygonOffsetUnits = 3;
blurMaterial.vertexNode = vec4(sub(uv(), vec2(0.5)).mul(2), 1, 1);
const uvNode = uv().flipY().toVar();
const pixelOffset = float(0.5).div(float(this.resolution)).toVar();
const color = add(this._previousShadowMap.sample(uvNode.add(vec2(pixelOffset, 0))), this._previousShadowMap.sample(uvNode.add(vec2(0, pixelOffset))), this._previousShadowMap.sample(uvNode.add(vec2(0, pixelOffset.negate()))), this._previousShadowMap.sample(uvNode.add(vec2(pixelOffset.negate(), 0))), this._previousShadowMap.sample(uvNode.add(vec2(pixelOffset, pixelOffset))), this._previousShadowMap.sample(uvNode.add(vec2(pixelOffset.negate(), pixelOffset))), this._previousShadowMap.sample(uvNode.add(vec2(pixelOffset, pixelOffset.negate()))), this._previousShadowMap.sample(uvNode.add(vec2(pixelOffset.negate(), pixelOffset.negate())))).div(8);
blurMaterial.fragmentNode = color;
this._blurringPlane = new Mesh(new PlaneGeometry(1, 1), blurMaterial);
this._blurringPlane.name = 'Blurring Plane';
this._blurringPlane.frustumCulled = false;
this._blurringPlane.renderOrder = 0;
this._blurringPlane.material.depthWrite = false;
this._scene.add(this._blurringPlane);


// ===== Animation loop =====
function animate() {
  requestAnimationFrame(animate);
  renderer.render(scene, camera);
}
animate();
