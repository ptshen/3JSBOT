import * as THREE from 'three';

			import Stats from 'three/addons/libs/stats.module.js';

			import { GUI } from 'three/addons/libs/lil-gui.module.min.js';
			import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

			let camera, scene, renderer, controls, stats;
			let target;
			let postScene, postCamera, postMaterial;

			const params = {
				format: THREE.DepthFormat,
				type: THREE.UnsignedShortType,
				samples: 0,
			};

			const formats = { DepthFormat: THREE.DepthFormat, DepthStencilFormat: THREE.DepthStencilFormat };
			const types = { UnsignedShortType: THREE.UnsignedShortType, UnsignedIntType: THREE.UnsignedIntType, FloatType: THREE.FloatType };

			init();

			function init() {

				renderer = new THREE.WebGLRenderer();
				renderer.setPixelRatio( window.devicePixelRatio );
				renderer.setSize( window.innerWidth, window.innerHeight );
				renderer.setAnimationLoop( animate );
				document.body.appendChild( renderer.domElement );

				//

				stats = new Stats();
				document.body.appendChild( stats.dom );

				camera = new THREE.PerspectiveCamera( 70, window.innerWidth / window.innerHeight, 0.01, 50 );
				camera.position.z = 4;

				controls = new OrbitControls( camera, renderer.domElement );
				controls.enableDamping = true;

				// Create a render target with depth texture
				setupRenderTarget();

				// Our scene
				setupScene();

				// Setup post-processing step
				setupPost();

				onWindowResize();
				window.addEventListener( 'resize', onWindowResize );

				//
				const gui = new GUI( { width: 300 } );

				gui.add( params, 'format', formats ).onChange( setupRenderTarget );
				gui.add( params, 'type', types ).onChange( setupRenderTarget );
				gui.add( params, 'samples', 0, 16, 1 ).onChange( setupRenderTarget );
				gui.open();

			}

			function setupRenderTarget() {

				if ( target ) target.dispose();

				const format = parseInt( params.format );
				const type = parseInt( params.type );
				const samples = parseInt( params.samples );

				const dpr = renderer.getPixelRatio();
				target = new THREE.WebGLRenderTarget( window.innerWidth * dpr, window.innerHeight * dpr );
				target.texture.minFilter = THREE.NearestFilter;
				target.texture.magFilter = THREE.NearestFilter;
				target.texture.generateMipmaps = false;
				target.stencilBuffer = ( format === THREE.DepthStencilFormat ) ? true : false;
				target.samples = samples;

				target.depthTexture = new THREE.DepthTexture();
				target.depthTexture.format = format;
				target.depthTexture.type = type;

			}

			function setupPost() {

				// Setup post processing stage
				postCamera = new THREE.OrthographicCamera( - 1, 1, 1, - 1, 0, 1 );
				postMaterial = new THREE.ShaderMaterial( {
					vertexShader: document.querySelector( '#post-vert' ).textContent.trim(),
					fragmentShader: document.querySelector( '#post-frag' ).textContent.trim(),
					uniforms: {
						cameraNear: { value: camera.near },
						cameraFar: { value: camera.far },
						tDiffuse: { value: null },
						tDepth: { value: null }
					}
				} );
				const postPlane = new THREE.PlaneGeometry( 2, 2 );
				const postQuad = new THREE.Mesh( postPlane, postMaterial );
				postScene = new THREE.Scene();
				postScene.add( postQuad );

			}

			function setupScene() {

				scene = new THREE.Scene();

				const geometry = new THREE.TorusKnotGeometry( 1, 0.3, 128, 64 );
				const material = new THREE.MeshBasicMaterial( { color: 'blue' } );

				const count = 50;
				const scale = 5;

				const mesh = new THREE.InstancedMesh( geometry, material, count );
				const dummy = new THREE.Object3D();

				for ( let i = 0; i < count; i ++ ) {

					const r = Math.random() * 2.0 * Math.PI;
					const z = ( Math.random() * 2.0 ) - 1.0;
					const zScale = Math.sqrt( 1.0 - z * z ) * scale;

					dummy.position.set(
						Math.cos( r ) * zScale,
						Math.sin( r ) * zScale,
						z * scale
					);
					dummy.rotation.set( Math.random(), Math.random(), Math.random() );

					dummy.updateMatrix();
					mesh.setMatrixAt( i, dummy.matrix );

				}

				scene.add( mesh );

			}

			function onWindowResize() {

				const aspect = window.innerWidth / window.innerHeight;
				camera.aspect = aspect;
				camera.updateProjectionMatrix();

				const dpr = renderer.getPixelRatio();
				target.setSize( window.innerWidth * dpr, window.innerHeight * dpr );
				renderer.setSize( window.innerWidth, window.innerHeight );

			}

			function animate() {

				// render scene into target
				renderer.setRenderTarget( target );
				renderer.render( scene, camera );

				// render post FX
				postMaterial.uniforms.tDiffuse.value = target.texture;
				postMaterial.uniforms.tDepth.value = target.depthTexture;

				renderer.setRenderTarget( null );
				renderer.render( postScene, postCamera );

				controls.update(); // required because damping is enabled

				stats.update();

			}