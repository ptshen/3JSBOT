import * as THREE from 'three';

			import Stats from 'three/addons/libs/stats.module.js';
			import { unzipSync } from 'three/addons/libs/fflate.module.js';

			let camera, scene, mesh, renderer, stats;

			const planeWidth = 50;
			const planeHeight = 50;

			let depthStep = 0.4;

			init();

			function init() {

				const container = document.createElement( 'div' );
				document.body.appendChild( container );

				camera = new THREE.PerspectiveCamera( 45, window.innerWidth / window.innerHeight, 0.1, 2000 );
				camera.position.z = 70;

				scene = new THREE.Scene();

				// width 256, height 256, depth 109, 8-bit, zip archived raw data

				new THREE.FileLoader()
					.setResponseType( 'arraybuffer' )
					.load( 'textures/3d/head256x256x109.zip', function ( data ) {

						const zip = unzipSync( new Uint8Array( data ) );
						const array = new Uint8Array( zip[ 'head256x256x109' ].buffer );

						const texture = new THREE.DataArrayTexture( array, 256, 256, 109 );
						texture.format = THREE.RedFormat;
						texture.needsUpdate = true;

						const material = new THREE.ShaderMaterial( {
							uniforms: {
								diffuse: { value: texture },
								depth: { value: 55 },
								size: { value: new THREE.Vector2( planeWidth, planeHeight ) }
							},
							vertexShader: document.getElementById( 'vs' ).textContent.trim(),
							fragmentShader: document.getElementById( 'fs' ).textContent.trim(),
							glslVersion: THREE.GLSL3
						} );

						const geometry = new THREE.PlaneGeometry( planeWidth, planeHeight );

						mesh = new THREE.Mesh( geometry, material );

						scene.add( mesh );

					} );

				// 2D Texture array is available on WebGL 2.0

				renderer = new THREE.WebGLRenderer();
				renderer.setPixelRatio( window.devicePixelRatio );
				renderer.setSize( window.innerWidth, window.innerHeight );
				renderer.setAnimationLoop( animate );
				container.appendChild( renderer.domElement );

				stats = new Stats();
				container.appendChild( stats.dom );

				window.addEventListener( 'resize', onWindowResize );

			}

			function onWindowResize() {

				camera.aspect = window.innerWidth / window.innerHeight;
				camera.updateProjectionMatrix();

				renderer.setSize( window.innerWidth, window.innerHeight );

			}

			function animate() {

				if ( mesh ) {

					let value = mesh.material.uniforms[ 'depth' ].value;

					value += depthStep;

					if ( value > 109.0 || value < 0.0 ) {

						if ( value > 1.0 ) value = 109.0 * 2.0 - value;
						if ( value < 0.0 ) value = - value;

						depthStep = - depthStep;

					}

					mesh.material.uniforms[ 'depth' ].value = value;

				}

				render();
				stats.update();

			}

			function render() {

				renderer.render( scene, camera );

			}