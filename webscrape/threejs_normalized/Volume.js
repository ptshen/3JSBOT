
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
 * Width of the volume in the IJK coordinate system.
 *
 * @type {number}
 * @default 1
 */
this.xLength = Number(xLength) || 1;

/**
 * Height of the volume in the IJK coordinate system.
 *
 * @type {number}
 * @default 1
 */
/**
 * Height of the volume in the IJK coordinate system.
 *
 * @type {number}
 * @default 1
 */
this.yLength = Number(yLength) || 1;

/**
 * Depth of the volume in the IJK coordinate system.
 *
 * @type {number}
 * @default 1
 */
/**
 * Depth of the volume in the IJK coordinate system.
 *
 * @type {number}
 * @default 1
 */
this.zLength = Number(zLength) || 1;

/**
 * The order of the Axis dictated by the NRRD header
 *
 * @type {Array<string>}
 */
/**
 * The order of the Axis dictated by the NRRD header
 *
 * @type {Array<string>}
 */
this.axisOrder = ['x', 'y', 'z'];

/**
 * The data of the volume.
 *
 * @type {TypedArray}
 */
/**
 * The data of the volume.
 *
 * @type {TypedArray}
 */
this.data;
this.data = new Uint8Array(arrayBuffer);
this.data = new Int8Array(arrayBuffer);
this.data = new Int16Array(arrayBuffer);
this.data = new Uint16Array(arrayBuffer);
this.data = new Int32Array(arrayBuffer);
this.data = new Uint32Array(arrayBuffer);
this.data = new Float32Array(arrayBuffer);
this.data = new Float64Array(arrayBuffer);
this.data = new Uint8Array(arrayBuffer);
/**
 * Spacing to apply to the volume from IJK to RAS coordinate system
 *
 * @type {Array<number>}
 */
this.spacing = [1, 1, 1];

/**
 * Offset of the volume in the RAS coordinate system
 *
 * @type {Array<number>}
 */
/**
 * Offset of the volume in the RAS coordinate system
 *
 * @type {Array<number>}
 */
this.offset = [0, 0, 0];

/**
 * The IJK to RAS matrix.
 *
 * @type {Martrix3}
 */
/**
 * The IJK to RAS matrix.
 *
 * @type {Martrix3}
 */
this.matrix = new Matrix3();
this.matrix.identity();

/**
 * The RAS to IJK matrix.
 *
 * @type {Martrix3}
 */
/**
 * The RAS to IJK matrix.
 *
 * @type {Martrix3}
 */
this.inverseMatrix = new Matrix3();
let lowerThreshold = -Infinity;
Object.defineProperty(this, 'lowerThreshold', {
  get: function () {
    return lowerThreshold;
  },
  /**
   * The voxels with values under this threshold won't appear in the slices.
   * If changed, geometryNeedsUpdate is automatically set to true on all the slices associated to this volume.
   *
   * @name Volume#lowerThreshold
   * @type {number}
   * @param {number} value
   */
  set: function (value) {
    lowerThreshold = value;
    this.sliceList.forEach(function (slice) {
      slice.geometryNeedsUpdate = true;
    });
  }
});
lowerThreshold = value;
this.sliceList.forEach(function (slice) {
  slice.geometryNeedsUpdate = true;
});
slice.geometryNeedsUpdate = true;
let upperThreshold = Infinity;
Object.defineProperty(this, 'upperThreshold', {
  get: function () {
    return upperThreshold;
  },
  /**
   * The voxels with values over this threshold won't appear in the slices.
   * If changed, geometryNeedsUpdate is automatically set to true on all the slices associated to this volume
   *
   * @name Volume#upperThreshold
   * @type {number}
   * @param {number} value
   */
  set: function (value) {
    upperThreshold = value;
    this.sliceList.forEach(function (slice) {
      slice.geometryNeedsUpdate = true;
    });
  }
});

/**
 * The list of all the slices associated to this volume
 *
 * @type {Array<VolumeSlice>}
 */
upperThreshold = value;
this.sliceList.forEach(function (slice) {
  slice.geometryNeedsUpdate = true;
});
slice.geometryNeedsUpdate = true;
/**
 * The list of all the slices associated to this volume
 *
 * @type {Array<VolumeSlice>}
 */
this.sliceList = [];

/**
 * Whether to use segmentation mode or not.
 * It can load 16-bits nrrds correctly.
 *
 * @type {boolean}
 * @default false
 */
/**
 * Whether to use segmentation mode or not.
 * It can load 16-bits nrrds correctly.
 *
 * @type {boolean}
 * @default false
 */
this.segmentation = false;

/**
 * This array holds the dimensions of the volume in the RAS space
 *
 * @type {Array<number>}
 */
/**
 * This array holds the dimensions of the volume in the RAS space
 *
 * @type {Array<number>}
 */
this.RASDimensions = [];
const z = Math.floor(index / (this.yLength * this.xLength));
const y = Math.floor((index - z * this.yLength * this.xLength) / this.xLength);
const x = index - z * this.yLength * this.xLength - y * this.xLength;
const length = this.data.length;
context = context || this;
let i = 0;
this.data[i] = functionToMap.call(context, this.data[i], i, this.data);
let firstSpacing, secondSpacing, positionOffset, IJKIndex;
const axisInIJK = new Vector3(),
  firstDirection = new Vector3(),
  secondDirection = new Vector3(),
  planeMatrix = new Matrix4().identity(),
  volume = this;
const dimensions = new Vector3(this.xLength, this.yLength, this.zLength);
axisInIJK.set(1, 0, 0);
firstDirection.set(0, 0, -1);
secondDirection.set(0, -1, 0);
firstSpacing = this.spacing[this.axisOrder.indexOf('z')];
secondSpacing = this.spacing[this.axisOrder.indexOf('y')];
IJKIndex = new Vector3(RASIndex, 0, 0);
planeMatrix.multiply(new Matrix4().makeRotationY(Math.PI / 2));
positionOffset = (volume.RASDimensions[0] - 1) / 2;
planeMatrix.setPosition(new Vector3(RASIndex - positionOffset, 0, 0));
axisInIJK.set(0, 1, 0);
firstDirection.set(1, 0, 0);
secondDirection.set(0, 0, 1);
firstSpacing = this.spacing[this.axisOrder.indexOf('x')];
secondSpacing = this.spacing[this.axisOrder.indexOf('z')];
IJKIndex = new Vector3(0, RASIndex, 0);
planeMatrix.multiply(new Matrix4().makeRotationX(-Math.PI / 2));
positionOffset = (volume.RASDimensions[1] - 1) / 2;
planeMatrix.setPosition(new Vector3(0, RASIndex - positionOffset, 0));
axisInIJK.set(0, 0, 1);
firstDirection.set(1, 0, 0);
secondDirection.set(0, -1, 0);
firstSpacing = this.spacing[this.axisOrder.indexOf('x')];
secondSpacing = this.spacing[this.axisOrder.indexOf('y')];
IJKIndex = new Vector3(0, 0, RASIndex);
positionOffset = (volume.RASDimensions[2] - 1) / 2;
planeMatrix.setPosition(new Vector3(0, 0, RASIndex - positionOffset));
firstDirection.applyMatrix4(volume.inverseMatrix).normalize();
secondDirection.applyMatrix4(volume.inverseMatrix).normalize();
axisInIJK.applyMatrix4(volume.inverseMatrix).normalize();
firstDirection.arglet = 'i';
secondDirection.arglet = 'j';
const iLength = Math.floor(Math.abs(firstDirection.dot(dimensions)));
const jLength = Math.floor(Math.abs(secondDirection.dot(dimensions)));
const planeWidth = Math.abs(iLength * firstSpacing);
const planeHeight = Math.abs(jLength * secondSpacing);
IJKIndex = Math.abs(Math.round(IJKIndex.applyMatrix4(volume.inverseMatrix).dot(axisInIJK)));
const base = [new Vector3(1, 0, 0), new Vector3(0, 1, 0), new Vector3(0, 0, 1)];
const iDirection = [firstDirection, secondDirection, axisInIJK].find(function (x) {
  return Math.abs(x.dot(base[0])) > 0.9;
});
const jDirection = [firstDirection, secondDirection, axisInIJK].find(function (x) {
  return Math.abs(x.dot(base[1])) > 0.9;
});
const kDirection = [firstDirection, secondDirection, axisInIJK].find(function (x) {
  return Math.abs(x.dot(base[2])) > 0.9;
});
function sliceAccess(i, j) {
  const si = iDirection === axisInIJK ? IJKIndex : iDirection.arglet === 'i' ? i : j;
  const sj = jDirection === axisInIJK ? IJKIndex : jDirection.arglet === 'i' ? i : j;
  const sk = kDirection === axisInIJK ? IJKIndex : kDirection.arglet === 'i' ? i : j;

  // invert indices if necessary

  const accessI = iDirection.dot(base[0]) > 0 ? si : volume.xLength - 1 - si;
  const accessJ = jDirection.dot(base[1]) > 0 ? sj : volume.yLength - 1 - sj;
  const accessK = kDirection.dot(base[2]) > 0 ? sk : volume.zLength - 1 - sk;
  return volume.access(accessI, accessJ, accessK);
}
const si = iDirection === axisInIJK ? IJKIndex : iDirection.arglet === 'i' ? i : j;
const sj = jDirection === axisInIJK ? IJKIndex : jDirection.arglet === 'i' ? i : j;
const sk = kDirection === axisInIJK ? IJKIndex : kDirection.arglet === 'i' ? i : j;

// invert indices if necessary
// invert indices if necessary

const accessI = iDirection.dot(base[0]) > 0 ? si : volume.xLength - 1 - si;
const accessJ = jDirection.dot(base[1]) > 0 ? sj : volume.yLength - 1 - sj;
const accessK = kDirection.dot(base[2]) > 0 ? sk : volume.zLength - 1 - sk;
const slice = new VolumeSlice(this, index, axis);
this.sliceList.push(slice);
this.sliceList.forEach(function (slice) {
  slice.repaint();
});
slice.repaint();
let min = Infinity;
let max = -Infinity;

// buffer the length
// buffer the length
const datasize = this.data.length;
let i = 0;
const value = this.data[i];
min = Math.min(min, value);
max = Math.max(max, value);
this.min = min;
this.max = max;


// ===== Animation loop =====
function animate() {
  requestAnimationFrame(animate);
  renderer.render(scene, camera);
}
animate();
