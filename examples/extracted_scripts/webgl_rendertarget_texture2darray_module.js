import * as THREE from 'three';

			import Stats from 'three/addons/libs/stats.module.js';
			import { unzipSync } from 'three/addons/libs/fflate.module.js';
			import { GUI } from 'three/addons/libs/lil-gui.module.min.js';

			const DIMENSIONS = {
				width: 256,
				height: 256,
				depth: 109
			};

			const params = {
				intensity: 1
			};

			/** Post-processing objects */

			const postProcessScene = new THREE.Scene();
			const postProcessCamera = new THREE.OrthographicCamera( - 1, 1, 1, - 1, 0, 1 );

			const renderTarget = new THREE.WebGLArrayRenderTarget( DIMENSIONS.width, DIMENSIONS.height, DIMENSIONS.depth );
			renderTarget.texture.format = THREE.RedFormat;

			const postProcessMaterial = new THREE.ShaderMaterial( {
				uniforms: {
					uTexture: { value: null },
					uDepth: { value: 55 },
					uIntensity: { value: 1.0 }
				},
				vertexShader: document.getElementById( 'vertex-postprocess' ).textContent.trim(),
				fragmentShader: document.getElementById( 'fragment-postprocess' ).textContent.trim()
			} );

			let depthStep = 0.4;

			let camera, scene, mesh, renderer, stats;

			const planeWidth = 50;
			const planeHeight = 50;

			init();

			function init() {

				const container = document.createElement( 'div' );
				document.body.appendChild( container );

				camera = new THREE.PerspectiveCamera( 45, window.innerWidth / window.innerHeight, 0.1, 2000 );
				camera.position.z = 70;

				scene = new THREE.Scene();

				/** Post-processing scene */

				const planeGeometry = new THREE.PlaneGeometry( 2, 2 );
				const screenQuad = new THREE.Mesh( planeGeometry, postProcessMaterial );
				postProcessScene.add( screenQuad );

				// 2D Texture array is available on WebGL 2.0

				renderer = new THREE.WebGLRenderer();
				renderer.setPixelRatio( window.devicePixelRatio );
				renderer.setSize( window.innerWidth, window.innerHeight );
				container.appendChild( renderer.domElement );

				stats = new Stats();
				container.appendChild( stats.dom );

				window.addEventListener( 'resize', onWindowResize );

				const gui = new GUI();

				gui.add( params, 'intensity', 0, 1 ).step( 0.01 ).onChange( value => postProcessMaterial.uniforms.uIntensity.value = value );
				gui.open();

				// width 256, height 256, depth 109, 8-bit, zip archived raw data

				new THREE.FileLoader()
					.setResponseType( 'arraybuffer' )
					.load( 'textures/3d/head256x256x109.zip', function ( data ) {

						const zip = unzipSync( new Uint8Array( data ) );
						const array = new Uint8Array( zip[ 'head256x256x109' ].buffer );

						const texture = new THREE.DataArrayTexture( array, DIMENSIONS.width, DIMENSIONS.height, DIMENSIONS.depth );
						texture.format = THREE.RedFormat;
						texture.needsUpdate = true;

						const material = new THREE.ShaderMaterial( {
							uniforms: {
								diffuse: { value: renderTarget.texture },
								depth: { value: 55 },
								size: { value: new THREE.Vector2( planeWidth, planeHeight ) }
							},
							vertexShader: document.getElementById( 'vs' ).textContent.trim(),
							fragmentShader: document.getElementById( 'fs' ).textContent.trim()
						} );

						const geometry = new THREE.PlaneGeometry( planeWidth, planeHeight );

						mesh = new THREE.Mesh( geometry, material );

						scene.add( mesh );

						postProcessMaterial.uniforms.uTexture.value = texture;

						renderer.setAnimationLoop( animate );

					} );

			}

			function onWindowResize() {

				camera.aspect = window.innerWidth / window.innerHeight;
				camera.updateProjectionMatrix();

				renderer.setSize( window.innerWidth, window.innerHeight );

			}

			function animate() {

				let value = mesh.material.uniforms[ 'depth' ].value;

				value += depthStep;

				if ( value > 109.0 || value < 0.0 ) {

					if ( value > 1.0 ) value = 109.0 * 2.0 - value;
					if ( value < 0.0 ) value = - value;

					depthStep = - depthStep;

				}

				mesh.material.uniforms[ 'depth' ].value = value;

				render();

				stats.update();

			}

			/**
			 * Renders the 2D array into the render target `renderTarget`.
			 */
			function renderTo2DArray() {

				const layer = Math.floor( mesh.material.uniforms[ 'depth' ].value );
				postProcessMaterial.uniforms.uDepth.value = layer;
				renderer.setRenderTarget( renderTarget, layer );
				renderer.render( postProcessScene, postProcessCamera );
				renderer.setRenderTarget( null );

			}

			function render() {

				// Step 1 - Render the input DataArrayTexture into render target
				renderTo2DArray();

				// Step 2 - Renders the scene containing the plane with a material
				// sampling the render target texture.
				renderer.render( scene, camera );

			}