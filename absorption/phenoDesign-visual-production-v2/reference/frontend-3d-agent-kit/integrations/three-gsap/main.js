/* Integration reference. Dependency/runtime NOT_RUN in the build environment.
   Install exact approved versions, then validate this path before production use. */
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import {gsap} from 'gsap';
import {ScrollTrigger} from 'gsap/ScrollTrigger';
gsap.registerPlugin(ScrollTrigger);
const $=s=>document.querySelector(s),viewport=$('#viewport');
const media=matchMedia('(prefers-reduced-motion: reduce)');
let renderer;
try{renderer=new THREE.WebGLRenderer({antialias:true,alpha:true,powerPreference:'low-power'});}catch(e){$('#status').textContent='3D unavailable; static illustration retained.';document.body.classList.add('static');for(const b of document.querySelectorAll('button'))b.disabled=true;throw e;}
renderer.setPixelRatio(Math.min(devicePixelRatio,1.6));renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.0;viewport.appendChild(renderer.domElement);
const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(31,1,.1,80),storyRoot=new THREE.Group();scene.add(storyRoot);
const room=new RoomEnvironment(),pmrem=new THREE.PMREMGenerator(renderer),env=pmrem.fromScene(room,.04);scene.environment=env.texture;room.dispose();pmrem.dispose();
scene.add(new THREE.HemisphereLight(0xffffff,0x9cafa3,1.5));const key=new THREE.DirectionalLight(0xffffff,2);key.position.set(-3,5,4);scene.add(key);
let parts=[],accentParts=[],progress=0,manual=null,cobalt=false,userYaw=0,paused=media.matches,raf=0,visible=true,disposed=false;
const clamp=x=>Math.max(0,Math.min(1,x)),smooth=x=>{x=clamp(x);return x*x*(3-2*x)};
function request(){if(!raf&&!disposed&&visible&&!document.hidden)raf=requestAnimationFrame(draw);}
function draw(){raf=0;storyRoot.rotation.set(.03+Math.sin(progress*Math.PI)*.15,-.28+smooth(progress)*Math.PI*1.66+userYaw,0);const explosion=manual===null?smooth((progress-.29)/.24)*(1-smooth((progress-.75)/.19)):(manual?1:0);for(const p of parts)p.object.position.copy(p.rest).addScaledVector(p.displacement,explosion);renderer.render(scene,camera);}
function resize(){const r=viewport.getBoundingClientRect();camera.aspect=r.width/Math.max(1,r.height);camera.position.set(...(camera.aspect<1.05?[4,2.7,7.2]:[3,2.1,5.8]));camera.lookAt(0,.4,0);camera.updateProjectionMatrix();renderer.setSize(r.width,r.height);request();}
const resizeObserver=new ResizeObserver(resize);resizeObserver.observe(viewport);
const observer=new IntersectionObserver(e=>{visible=e[0].isIntersecting;if(visible)request();else if(raf){cancelAnimationFrame(raf);raf=0;}});observer.observe($('#stage'));
const trigger=ScrollTrigger.create({trigger:'#story',start:'top top',end:'bottom bottom',invalidateOnRefresh:true,onUpdate:self=>{if(!paused)progress=self.progress;request();}});
new GLTFLoader().load('/trainer.glb',gltf=>{
 if(disposed)return;
 storyRoot.add(gltf.scene);const names=new Set();gltf.scene.traverse(o=>{if(!o.isMesh)return;names.add(o.name);const raw=o.userData.explode;if(Array.isArray(raw)&&raw.length===3)parts.push({object:o,rest:o.position.clone(),displacement:new THREE.Vector3(...raw)});if(o.userData.accent){o.material=o.material.clone();accentParts.push(o);}});
 for(const n of ['Upper','Midsole','Outsole'])if(!names.has(n))throw Error('Required semantic node missing: '+n);
 $('#poster').hidden=true;$('#status').textContent='Live Three.js scene. Scroll or focus and use arrow keys.';resize();ScrollTrigger.refresh();request();
},undefined,error=>{$('#status').textContent='Model failed to load; static illustration retained.';console.error(error);});
function updatePolicy(){document.body.classList.toggle('static',media.matches);$('#pause').textContent=paused?'Enable movement':'Pause movement';$('#pause').setAttribute('aria-pressed',String(paused));ScrollTrigger.refresh();request();}
media.addEventListener('change',()=>{paused=media.matches;updatePolicy()});updatePolicy();
$('#separate').addEventListener('click',()=>{manual=manual!==true;$('#separate').setAttribute('aria-pressed',String(manual));$('#separate').textContent=manual?'Rejoin layers':'Separate layers';request()});
$('#accent').addEventListener('click',()=>{cobalt=!cobalt;$('#accent').setAttribute('aria-pressed',String(cobalt));for(const o of accentParts)o.material.color.setRGB(...(cobalt?[.075,.17,.58]:[.19,.49,.44]));request()});
$('#pause').addEventListener('click',()=>{paused=!paused;if(!paused)progress=trigger.progress;updatePolicy()});
$('#reset').addEventListener('click',()=>{userYaw=0;manual=null;$('#separate').setAttribute('aria-pressed','false');$('#separate').textContent='Separate layers';request()});
let pointer=null;viewport.addEventListener('pointerdown',e=>{pointer={id:e.pointerId,x:e.clientX,y:e.clientY,yaw:userYaw};viewport.setPointerCapture(e.pointerId)});viewport.addEventListener('pointermove',e=>{if(!pointer||pointer.id!==e.pointerId)return;const dx=e.clientX-pointer.x,dy=e.clientY-pointer.y;if(e.pointerType==='touch'&&Math.abs(dy)>Math.abs(dx))return;userYaw=pointer.yaw+dx*.009;request()});for(const type of ['pointerup','pointercancel'])viewport.addEventListener(type,()=>pointer=null);
viewport.addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();userYaw+=e.key==='ArrowRight'?.15:-.15;request()}});
function visibility(){if(document.hidden&&raf){cancelAnimationFrame(raf);raf=0}else request()}document.addEventListener('visibilitychange',visibility);
renderer.domElement.addEventListener('webglcontextlost',e=>{e.preventDefault();$('#poster').hidden=false;$('#status').textContent='Graphics context lost; reload to restore 3D.';if(raf)cancelAnimationFrame(raf);raf=0;visible=false;});
function dispose(){disposed=true;if(raf)cancelAnimationFrame(raf);trigger.kill();observer.disconnect();resizeObserver.disconnect();document.removeEventListener('visibilitychange',visibility);const geometries=new Set(),materials=new Set(),textures=new Set();scene.traverse(o=>{if(o.geometry)geometries.add(o.geometry);if(o.material){const ms=Array.isArray(o.material)?o.material:[o.material];for(const m of ms){materials.add(m);for(const v of Object.values(m))if(v?.isTexture)textures.add(v);}}});for(const g of geometries)g.dispose();for(const m of materials)m.dispose();for(const t of textures)t.dispose();env.dispose();renderer.dispose();}
addEventListener('pagehide',dispose,{once:true});
