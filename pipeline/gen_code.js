// Three.js Interactive Python Laptop with Terminal
// All-in-one script for localhost use

import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

// ---------- Scene setup ----------
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.style.margin = '0';
document.body.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
scene.add(new THREE.AmbientLight(0xffffff, 0.6));
const dir = new THREE.DirectionalLight(0xffffff, 0.8);
dir.position.set(5, 10, 7);
scene.add(dir);

// ---------- Laptop model ----------
const laptop = new THREE.Group();
scene.add(laptop);

// Base
const baseMat = new THREE.MeshStandardMaterial({ color: 0x222222, metalness: 0.2, roughness: 0.5 });
const baseGeom = new THREE.BoxGeometry(10, 0.4, 6.5);
const base = new THREE.Mesh(baseGeom, baseMat);
base.position.y = -0.2;
laptop.add(base);

// Screen hinge
const hingeGeom = new THREE.BoxGeometry(9.6, 0.25, 0.25);
const hinge = new THREE.Mesh(hingeGeom, baseMat);
hinge.position.set(0, 0.0, -3.25);
laptop.add(hinge);

// Screen with canvas texture
const screenWidth = 9.6, screenHeight = 6.0;
const screenCanvas = document.createElement('canvas');
screenCanvas.width = 1024; screenCanvas.height = 640;
const screenCtx = screenCanvas.getContext('2d');
function clearScreen() {
  screenCtx.fillStyle = '#1e1e1e';
  screenCtx.fillRect(0, 0, screenCanvas.width, screenCanvas.height);
  screenCtx.fillStyle = '#ffffff';
  screenCtx.font = '40px monospace';
  screenCtx.fillText('Type on the keyboard below', 40, 120);
}
clearScreen();
const screenTexture = new THREE.CanvasTexture(screenCanvas);
const screenMat = new THREE.MeshBasicMaterial({ map: screenTexture });
const screenGeom = new THREE.PlaneGeometry(screenWidth, screenHeight);
const screen = new THREE.Mesh(screenGeom, screenMat);
screen.position.set(0, 3.2, -3.5);
screen.geometry.translate(0, -screenHeight / 2, 0);

// Screen back
const screenBack = new THREE.Mesh(new THREE.BoxGeometry(screenWidth, 0.4, 0.2), baseMat);
screenBack.position.copy(screen.position);
screenBack.position.y -= screenHeight / 2;
laptop.add(screen); laptop.add(screenBack);
screen.rotation.x = -0.35; screenBack.rotation.x = -0.35;

// Keyboard
const keyboard = new THREE.Group();
keyboard.position.set(0, 0.15, 0.8);
const layout = [['Escape','F1','F2','F3','F4','F5'],['`','1','2','3','4','5','6','7','8','9','0','-','=','Backspace'],['Tab','q','w','e','r','t','y','u','i','o','p','[',']','\\'],['Caps','a','s','d','f','g','h','j','k','l',';','\'','Enter'],['Shift','z','x','c','v','b','n','m',',','.','/','Shift'],['Ctrl','Meta','Alt','Space','Alt','Meta','Menu','Ctrl']];
const keyWidth = 0.5, keyHeight = 0.12, keyDepth = 0.45, keyGap = 0.06;
const keyMaterial = new THREE.MeshStandardMaterial({ color: 0xdddddd, metalness: 0.1, roughness: 0.6 });
const keyPressedMaterial = new THREE.MeshStandardMaterial({ color: 0x999999 });
let keyMeshes = [];
function createKey(label, x, y, w = 1) {
  const geom = new THREE.BoxGeometry(keyWidth * w + (w - 1) * keyGap, keyHeight, keyDepth);
  const mesh = new THREE.Mesh(geom, keyMaterial.clone());
  mesh.userData = { label };
  mesh.position.set(x, 0, -y);
  const c = document.createElement('canvas'); c.width=128; c.height=128; const ctx=c.getContext('2d');
  ctx.fillStyle='#222'; ctx.fillRect(0,0,c.width,c.height);
  ctx.fillStyle='#fff'; ctx.font='40px sans-serif'; ctx.textAlign='center'; ctx.textBaseline='middle';
  ctx.fillText(label.length>2?label.slice(0,2):label,c.width/2,c.height/2);
  const tex=new THREE.CanvasTexture(c);
  const labelPlane=new THREE.Mesh(new THREE.PlaneGeometry((keyWidth*w)*0.9,keyDepth*0.6),new THREE.MeshBasicMaterial({map:tex}));
  labelPlane.rotation.x=-Math.PI/2; labelPlane.position.set(0,keyHeight/2+0.01,0);
  mesh.add(labelPlane);
  keyboard.add(mesh); keyMeshes.push(mesh);
}
let startX=-3.8, startZ=0;
for(let row=0;row<layout.length;row++){ const cols=layout[row]; let x=startX;
  for(let col=0;col<cols.length;col++){ const label=cols[col]; let w=1;
    if(label==='Backspace') w=2; if(label==='Tab'||label==='Caps'||label==='Enter') w=1.5;
    if(label==='Shift') w=2; if(label==='Space') w=6;
    createKey(label, x+(keyWidth*w+keyGap*(w-1))/2, startZ+row*(keyDepth+0.12), w);
    x+=keyWidth*w+keyGap*w;
  }
}
laptop.add(keyboard);

// Typing
let typedText='';
function wrapText(text,maxChars){ const words=text.split(' '); const lines=[]; let cur='';
  for(const w of words){ if((cur+' '+w).trim().length<=maxChars) cur=(cur+' '+w).trim(); else {lines.push(cur); cur=w;}} if(cur!=='') lines.push(cur); return lines;}
function updateScreen(){ screenCtx.fillStyle='#0b1220'; screenCtx.fillRect(0,0,screenCanvas.width,screenCanvas.height);
  screenCtx.fillStyle='#7fffd4'; screenCtx.font='36px monospace'; const lines=wrapText(typedText,48);
  for(let i=0;i<lines.length;i++) screenCtx.fillText(lines[i],30,60+i*44);
  screenTexture.needsUpdate=true;}
updateScreen();
const raycaster=new THREE.Raycaster(); const pointer=new THREE.Vector2();
function findKeyMeshForChar(char){ char=char.toLowerCase(); for(const m of keyMeshes){ const label=String(m.userData.label).toLowerCase(); if(label===char) return m;
if(char===' '&&label==='space') return m; if(char==='\n'&&label==='enter') return m;} return null;}
function pressKeyMesh(mesh){ if(!mesh) return; const originalY=mesh.position.y; mesh.position.y=originalY-0.06; mesh.material=keyPressedMaterial;
setTimeout(()=>{mesh.position.y=originalY; mesh.material=keyMaterial;},140);}
window.addEventListener('keydown',(e)=>{e.preventDefault(); const key=e.key; if(key.length===1) typedText+=key; else if(key==='Backspace') typedText=typedText.slice(0,-1);
else if(key==='Enter') typedText+='
'; else if(key==='Tab') typedText+='	'; updateScreen(); let matchLabel=key; if(key===' ') matchLabel='Space'; const mesh=findKeyMeshForChar(matchLabel); if(mesh) pressKeyMesh(mesh);});
renderer.domElement.addEventListener('pointerdown',(event)=>{ const rect=renderer.domElement.getBoundingClientRect(); pointer.x=((event.clientX-rect.left)/rect.width)*2-1; pointer.y=-((event.clientY-rect.top)/rect.height)*2+1;
raycaster.setFromCamera(pointer,camera); const intersects=raycaster.intersectObjects(keyMeshes,true); if(intersects.length>0){ let mesh=intersects[0].object; while(mesh&&!mesh.userData.label) mesh=mesh.parent; if(!mesh) return; pressKeyMesh(mesh);
const label=mesh.userData.label; if(label==='Backspace') typedText=typedText.slice(0,-1); else if(label==='Enter') typedText+='
'; else if(label==='Space') typedText+=' '; else if(label.length===1) typedText+=label; updateScreen();}});

// Cursor blinking
let cursorVisible=true; setInterval(()=>{ cursorVisible=!cursorVisible; const displayText=typedText+(cursorVisible?'_':''); screenCtx.fillStyle='#0b1220'; screenCtx.fillRect(0,0,screenCanvas.width,screenCanvas.height);
screenCtx.fillStyle='#7fffd4'; screenCtx.font='36px monospace'; const lines=wrapText(displayText,48);
for(let i=0;i<lines.length;i++) screenCtx.fillText(lines[i],30,60+i*38); screenTexture.needsUpdate=true;},500);

// Typing click sound
const clickAudio=new Audio('https://assets.mixkit.co/active_storage/sfx/2007/2007-preview.mp3'); function playClick(){clickAudio.currentTime=0; clickAudio.play();}
window.addEventListener('keydown',()=>playClick()); renderer.domElement.addEventListener('pointerdown',()=>playClick());

// Export typed text
const exportBtn=document.createElement('button'); exportBtn.innerText='Export Text'; exportBtn.style.position='fixed'; exportBtn.style.left='12px'; exportBtn.style.bottom='12px'; exportBtn.style.padding='8px 14px'; exportBtn.style.background='#222'; exportBtn.style.color='white'; exportBtn.style.border='1px solid #555'; exportBtn.style.borderRadius='5px'; exportBtn.style.cursor='pointer';
exportBtn.onclick=()=>{ const blob=new Blob([typedText],{type:'text/plain'}); const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download='typed.txt'; a.click(); URL.revokeObjectURL(url);}; document.body.appendChild(exportBtn);

// Python terminal (Pyodide)
const terminal=document.createElement('div'); terminal.style.position='fixed'; terminal.style.left='50%'; terminal.style.top='10%'; terminal.style.transform='translateX(-50%)'; terminal.style.width='720px'; terminal.style.maxWidth='90%'; terminal.style.background='rgba(8,12,20,0.95)'; terminal.style.color='#cfe'; terminal.style.border='1px solid #334'; terminal.style.borderRadius='8px'; terminal.style.padding='12px'; terminal.style.zIndex='9999'; terminal.style.fontFamily='monospace';
const termTitle=document.createElement('div'); termTitle.innerText='Python Terminal (Pyodide)'; termTitle.style.marginBottom='8px'; terminal.appendChild(termTitle);
const outputArea=document.createElement('pre'); outputArea.style.height='180px'; outputArea.style.overflow='auto'; outputArea.style.background='#041018'; outputArea.style.padding='8px'; outputArea.style.borderRadius='6px'; outputArea.style.marginBottom='8px'; outputArea.innerText='Pyodide loading...'; terminal.appendChild(outputArea);
const codeInput=document.createElement('textarea'); codeInput.style.width='100%'; codeInput.style.height='120px'; codeInput.style.fontFamily='monospace'; codeInput.style.fontSize='13px'; codeInput.style.padding='8px'; codeInput.style.borderRadius='6px'; codeInput.style.background='#001018'; codeInput.style.color='#cfe'; codeInput.placeholder='# Write Python here\nprint("hello")'; terminal.appendChild(codeInput);
const controlsRow=document.createElement('div'); controlsRow.style.display='flex'; controlsRow.style.gap='8px'; controlsRow.style.marginTop='8px';
const runBtn=document.createElement('button'); runBtn.innerText='Run'; runBtn.style.padding='8px 12px'; runBtn.style.cursor='pointer'; runBtn.style.borderRadius='6px'; runBtn.style.border='none'; runBtn.style.background='#2b6'; runBtn.style.color='#012'; controlsRow.appendChild(runBtn);
const clearBtn=document.createElement('button'); clearBtn.innerText='Clear Output'; clearBtn.style.padding='8px 12px'; clearBtn.style.cursor='pointer'; clearBtn.style.borderRadius='6px'; clearBtn.style.border='none'; clearBtn.style.background='#446'; clearBtn.style.color='#cfe'; controlsRow.appendChild(clearBtn);
const closeBtn=document.createElement('button'); closeBtn.innerText='Close'; closeBtn.style.marginLeft='auto'; closeBtn.style.padding='6px 10px'; closeBtn.style.cursor='pointer'; closeBtn.style.borderRadius='6px'; closeBtn.style.border='none'; closeBtn.style.background='#822'; closeBtn.style.color='#fff'; controlsRow.appendChild(closeBtn);
terminal.appendChild(controlsRow); document.body.appendChild(terminal);
let pyodide=null; let pyodideReady=false;
async function loadPyodideAndPackages(){ outputArea.innerText='Loading Pyodide...'; const script=document.createElement('script'); script.src='https://cdn.jsdelivr.net/pyodide/v0.23.4/full/pyodide.js'; document.head.appendChild(script);
await new Promise((res)=>{script.onload=res; script.onerror=res;}); pyodide=await loadPyodide({stdout:()=>{},stderr:()=>{}}); pyodideReady=true; outputArea.innerText='Pyodide ready.'; }
loadPyodideAndPackages();
async function runPython(code){ if(!pyodideReady){ outputArea.innerText+='\nPyodide not ready'; return;} try{ const wrapped=`import sys, io\n_buf=io.StringIO()\nsys.stdout=_buf\nsys.stderr=_buf\n${code}\nres=_buf.getvalue()`;
await pyodide.runPythonAsync(wrapped); const res=pyodide.globals.get('res'); outputArea.innerText+='\n>>> '+code.split('\n')[0]+'\n'+String(res); pyodide.runPython('del res',{});}catch(err){outputArea.innerText+='\nError:'+err;} outputArea.scrollTop=outputArea.scrollHeight;}
runBtn.onclick=async()=>{ const code=codeInput.value; if(!code.trim()) return; await runPython(code);};
clearBtn.onclick=()=>{outputArea.innerText='';}; closeBtn.onclick=()=>{terminal.style.display='none';};
window.addEventListener('keydown',(e)=>{ if(e.key==='F2') terminal.style.display=(terminal.style.display==='none'?'block':'none');});
function updateScreenWithTerminalPreview(){ const preview=outputArea.innerText.split('\n').slice(-3).join('\n'); const displayText=typedText+'\n\n'+preview; screenCtx.fillStyle='#0b1220'; screenCtx.fillRect(0,0,screenCanvas.width,screenCanvas.height);
screenCtx.fillStyle='#7fffd4'; screenCtx.font='28px monospace'; const lines=wrapText(displayText,48); for(let i=0;i<lines.length;i++) screenCtx.fillText(lines[i],30,60+i*38); screenTexture.needsUpdate=true;}
setInterval(updateScreenWithTerminalPreview,500);

// Camera & render loop
camera.position.set(12,6,10); camera.lookAt(0,0.5,0);
function animate(){ requestAnimationFrame(animate); controls.update(); renderer.render(scene,camera);} animate();

// Resize
window.addEventListener('resize',()=>{ camera.aspect=window.innerWidth/window.innerHeight; camera.updateProjectionMatrix(); renderer.setSize(window.innerWidth,window.innerHeight);});
