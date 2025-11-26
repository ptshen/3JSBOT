
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
const slice = this;

/**
 * The associated volume.
 *
 * @type {Volume}
 */
/**
 * The associated volume.
 *
 * @type {Volume}
 */
this.volume = volume;
Object.defineProperty(this, 'index', {
  get: function () {
    return index;
  },
  /**
   * The index of the slice, if changed, will automatically call updateGeometry at the next repaint.
   *
   * @name VolumeSlice#index
   * @type {number}
   * @default 0
   * @param {number} value
   * @return {number}
   */
  set: function (value) {
    index = value;
    slice.geometryNeedsUpdate = true;
    return index;
  }
});

/**
 * The normal axis.
 *
 * @type {('x'|'y'|'z')}
 */
index = value;
slice.geometryNeedsUpdate = true;
/**
 * The normal axis.
 *
 * @type {('x'|'y'|'z')}
 */
this.axis = axis;

/**
 * The final canvas used for the texture.
 *
 * @type {HTMLCanvasElement}
 */
/**
 * The final canvas used for the texture.
 *
 * @type {HTMLCanvasElement}
 */
this.canvas = document.createElement('canvas');

/**
 * The rendering context of the canvas.
 *
 * @type {CanvasRenderingContext2D}
 */
/**
 * The rendering context of the canvas.
 *
 * @type {CanvasRenderingContext2D}
 */
this.ctx;

/**
 * The intermediary canvas used to paint the data.
 *
 * @type {HTMLCanvasElement}
 */
/**
 * The intermediary canvas used to paint the data.
 *
 * @type {HTMLCanvasElement}
 */
this.canvasBuffer = document.createElement('canvas');

/**
 * The rendering context of the canvas buffer,
 *
 * @type {CanvasRenderingContext2D}
 */
/**
 * The rendering context of the canvas buffer,
 *
 * @type {CanvasRenderingContext2D}
 */
this.ctxBuffer;
this.updateGeometry();
const canvasMap = new Texture(this.canvas);
canvasMap.minFilter = LinearFilter;
canvasMap.generateMipmaps = false;
canvasMap.wrapS = canvasMap.wrapT = ClampToEdgeWrapping;
canvasMap.colorSpace = SRGBColorSpace;
const material = new MeshBasicMaterial({
  map: canvasMap,
  side: DoubleSide,
  transparent: true
});

/**
 * The mesh ready to get used in the scene.
 *
 * @type {Mesh}
 */
/**
 * The mesh ready to get used in the scene.
 *
 * @type {Mesh}
 */
this.mesh = new Mesh(this.geometry, material);
this.mesh.matrixAutoUpdate = false;

/**
 * If set to `true`, `updateGeometry()` will be triggered at the next repaint.
 *
 * @type {boolean}
 * @default true
 */
/**
 * If set to `true`, `updateGeometry()` will be triggered at the next repaint.
 *
 * @type {boolean}
 * @default true
 */
this.geometryNeedsUpdate = true;
this.repaint();

/**
 * Width of slice in the original coordinate system, corresponds to the width of the buffer canvas.
 *
 * @type {number}
 * @default 0
 */
/**
 * Width of slice in the original coordinate system, corresponds to the width of the buffer canvas.
 *
 * @type {number}
 * @default 0
 */
this.iLength = 0;

/**
 * Height of slice in the original coordinate system, corresponds to the height of the buffer canvas.
 *
 * @type {number}
 * @default 0
 */
/**
 * Height of slice in the original coordinate system, corresponds to the height of the buffer canvas.
 *
 * @type {number}
 * @default 0
 */
this.jLength = 0;

/**
 * Function that allow the slice to access right data.
 *
 * @type {?Function}
 * @see {@link Volume#extractPerpendicularPlane}
 */
/**
 * Function that allow the slice to access right data.
 *
 * @type {?Function}
 * @see {@link Volume#extractPerpendicularPlane}
 */
this.sliceAccess = null;
this.updateGeometry();
const iLength = this.iLength,
  jLength = this.jLength,
  sliceAccess = this.sliceAccess,
  volume = this.volume,
  canvas = this.canvasBuffer,
  ctx = this.ctxBuffer;

// get the imageData and pixel array from the canvas
// get the imageData and pixel array from the canvas
const imgData = ctx.getImageData(0, 0, iLength, jLength);
const data = imgData.data;
const volumeData = volume.data;
const upperThreshold = volume.upperThreshold;
const lowerThreshold = volume.lowerThreshold;
const windowLow = volume.windowLow;
const windowHigh = volume.windowHigh;

// manipulate some pixel elements
// manipulate some pixel elements
let pixelCount = 0;
console.error('THREE.VolumeSlice.repaint: label are not supported yet');

// This part is currently useless but will be used when colortables will be handled

// for ( let j = 0; j < jLength; j ++ ) {

// 	for ( let i = 0; i < iLength; i ++ ) {

// 		let label = volumeData[ sliceAccess( i, j ) ];
// 		label = label >= this.colorMap.length ? ( label % this.colorMap.length ) + 1 : label;
// 		const color = this.colorMap[ label ];
// 		data[ 4 * pixelCount ] = ( color >> 24 ) & 0xff;
// 		data[ 4 * pixelCount + 1 ] = ( color >> 16 ) & 0xff;
// 		data[ 4 * pixelCount + 2 ] = ( color >> 8 ) & 0xff;
// 		data[ 4 * pixelCount + 3 ] = color & 0xff;
// 		pixelCount ++;

// 	}

// }
let j = 0;
let i = 0;
let value = volumeData[sliceAccess(i, j)];
let alpha = 0xff;
//apply threshold
//apply threshold
alpha = upperThreshold >= value ? lowerThreshold <= value ? alpha : 0 : 0;
//apply window level
//apply window level
value = Math.floor(255 * (value - windowLow) / (windowHigh - windowLow));
value = value > 255 ? 255 : value < 0 ? 0 : value | 0;
data[4 * pixelCount] = value;
data[4 * pixelCount + 1] = value;
data[4 * pixelCount + 2] = value;
data[4 * pixelCount + 3] = alpha;
pixelCount++;
ctx.putImageData(imgData, 0, 0);
this.ctx.drawImage(canvas, 0, 0, iLength, jLength, 0, 0, this.canvas.width, this.canvas.height);
this.mesh.material.map.needsUpdate = true;
const extracted = this.volume.extractPerpendicularPlane(this.axis, this.index);
this.sliceAccess = extracted.sliceAccess;
this.jLength = extracted.jLength;
this.iLength = extracted.iLength;
this.matrix = extracted.matrix;
this.canvas.width = extracted.planeWidth;
this.canvas.height = extracted.planeHeight;
this.canvasBuffer.width = this.iLength;
this.canvasBuffer.height = this.jLength;
this.ctx = this.canvas.getContext('2d');
this.ctxBuffer = this.canvasBuffer.getContext('2d');
this.geometry.dispose();
// dispose existing geometry

this.geometry = new PlaneGeometry(extracted.planeWidth, extracted.planeHeight);
this.mesh.geometry = this.geometry;
//reset mesh matrix
//reset mesh matrix
this.mesh.matrix.identity();
this.mesh.applyMatrix4(this.matrix);
this.geometryNeedsUpdate = false;


// ===== Animation loop =====
function animate() {
  requestAnimationFrame(animate);
  renderer.render(scene, camera);
}
animate();
