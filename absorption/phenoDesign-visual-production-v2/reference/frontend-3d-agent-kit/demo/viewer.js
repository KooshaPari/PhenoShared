/* Original, dependency-free WebGL2 reference renderer. This is not a PBR engine.
   One normalized story progress owns the model pose. Input is a separate offset.
   No fetch, no CDN, no timers that render forever, no external telemetry. */
(() => {
  'use strict';
  const $ = s => document.querySelector(s), canvas = $('#product');
  const gl = canvas.getContext('webgl2', {alpha:true,antialias:true,powerPreference:'low-power'});
  const diagnostics = window.__DEMO__ = {ready:false, frames:0, progress:0, exploded:0, yaw:0, paused:false, contextLost:false, renderer:'WebGL2 reference'};
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const savedData = Boolean(navigator.connection && navigator.connection.saveData);
  let paused = reduced.matches || savedData, hidden = document.hidden, visible=true;
  if (!gl && window.PRODUCT_MESH && window.startSoftwareDemo && window.startSoftwareDemo()) {return;}
  if (!gl || !window.PRODUCT_MESH) {
    $('#render-status').textContent = 'Static preview · 3D unavailable';
    document.body.classList.add('static-mode');canvas.hidden=true;
    for(const b of document.querySelectorAll('.controls button')) b.disabled=true;
    return;
  }
  const vertex=`#version 300 es
  precision highp float;
  layout(location=0) in vec3 position;layout(location=1) in vec3 normal;
  uniform mat4 model,view,projection;uniform vec3 offset;
  out vec3 n;out vec3 world;out vec3 local;
  void main(){vec4 p=model*vec4(position+offset,1.);world=p.xyz;n=normalize(mat3(model)*normal);local=position;gl_Position=projection*view*p;}`;
  const fragment=`#version 300 es
  precision highp float;
  in vec3 n;in vec3 world;in vec3 local;
  uniform vec3 color,eye;uniform float roughness,metallic;
  out vec4 outColor;
  void main(){vec3 N=normalize(n);if(!gl_FrontFacing)N=-N;vec3 V=normalize(eye-world);vec3 L=normalize(vec3(-2.5,5.,4.));vec3 H=normalize(V+L);
  float ndl=max(dot(N,L),0.);float rim=pow(1.-max(dot(N,V),0.),3.);
  float spec=pow(max(dot(N,H),0.),mix(95.,7.,roughness));
  float knit=roughness>.85? .025*sin(local.x*140.)*sin(local.z*165.):0.;
  vec3 base=color*(.29+.71*ndl+.10*max(N.y,0.)+knit);
  base+=vec3(.98,1.,.96)*spec*(.08+.33*metallic)*(1.-roughness*.5);
  base+=vec3(.32,.40,.36)*rim*.19;
  outColor=vec4(pow(max(base,vec3(0.)),vec3(1./2.2)),1.);}`;
  function shader(type,source){const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;}
  let program;
  try{program=gl.createProgram();const vs=shader(gl.VERTEX_SHADER,vertex),fs=shader(gl.FRAGMENT_SHADER,fragment);gl.attachShader(program,vs);gl.attachShader(program,fs);gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));gl.deleteShader(vs);gl.deleteShader(fs);}catch(e){console.error(e);$('#render-status').textContent='Static preview · renderer error';canvas.hidden=true;document.body.classList.add('static-mode');return;}
  const u={};for(const n of ['model','view','projection','offset','color','eye','roughness','metallic'])u[n]=gl.getUniformLocation(program,n);
  const buffers=[];
  const parts=window.PRODUCT_MESH.parts.map(p=>{const vao=gl.createVertexArray();gl.bindVertexArray(vao);
    for(const [location,key] of [[0,'positions'],[1,'normals']]){const b=gl.createBuffer();buffers.push(b);gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(p[key]),gl.STATIC_DRAW);gl.enableVertexAttribArray(location);gl.vertexAttribPointer(location,3,gl.FLOAT,false,0,0);}
    const b=gl.createBuffer();buffers.push(b);gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,b);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint32Array(p.indices),gl.STATIC_DRAW);return {...p,vao,count:p.indices.length};});
  const normalize=v=>{const l=Math.hypot(...v);return v.map(x=>x/l);}, cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]], dot=(a,b)=>a.reduce((s,x,i)=>s+x*b[i],0);
  function lookAt(eye,target){const z=normalize(eye.map((v,i)=>v-target[i])),x=normalize(cross([0,1,0],z)),y=cross(z,x);return new Float32Array([x[0],y[0],z[0],0,x[1],y[1],z[1],0,x[2],y[2],z[2],0,-dot(x,eye),-dot(y,eye),-dot(z,eye),1]);}
  function perspective(fovy,aspect){const f=1/Math.tan(fovy/2),near=.1,far=80;return new Float32Array([f/aspect,0,0,0,0,f,0,0,0,0,(far+near)/(near-far),-1,0,0,2*far*near/(near-far),0]);}
  function multiply(a,b){const o=new Float32Array(16);for(let c=0;c<4;c++)for(let r=0;r<4;r++)o[c*4+r]=a[r]*b[c*4]+a[4+r]*b[c*4+1]+a[8+r]*b[c*4+2]+a[12+r]*b[c*4+3];return o;}
  function pose(yaw,tilt){const c=Math.cos(yaw),s=Math.sin(yaw),a=Math.cos(tilt),b=Math.sin(tilt);return multiply(new Float32Array([c,0,-s,0,0,1,0,0,s,0,c,0,0,0,0,1]),new Float32Array([1,0,0,0,0,a,b,0,0,-b,a,0,0,0,0,1]));}
  const clamp=x=>Math.max(0,Math.min(1,x));const smooth=x=>{x=clamp(x);return x*x*(3-2*x)};
  let progress=0, yawOffset=0, manualExplosion=null, accent=[.19,.49,.44], frame=0,disposed=false;
  const motionButton=$('#motion');
  function updateMotion(){diagnostics.paused=paused;motionButton.setAttribute('aria-pressed',String(paused));motionButton.textContent=paused?'Enable movement':'Pause movement';document.body.classList.toggle('static-mode',reduced.matches||savedData);}
  function request(){if(!frame&&!disposed&&!hidden&&visible&&!diagnostics.contextLost)frame=requestAnimationFrame(render);}
  function render(){frame=0;const rect=canvas.getBoundingClientRect(),dpr=Math.min(devicePixelRatio||1,1.65),w=Math.max(1,Math.round(rect.width*dpr)),h=Math.max(1,Math.round(rect.height*dpr));if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}gl.viewport(0,0,w,h);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.enable(gl.DEPTH_TEST);gl.disable(gl.CULL_FACE);gl.useProgram(program);
    const p=progress,storyYaw=-.28+smooth(p)*Math.PI*1.66;
    const explosion=manualExplosion===null?(smooth((p-.29)/.24)*(1-smooth((p-.75)/.19))):(manualExplosion?1:0);
    const angle=storyYaw+yawOffset,tilt=.03+Math.sin(p*Math.PI)*.15;
    const aspect=w/h,eye=aspect<1.05?[4.0,2.7,7.2]:[3.0,2.1,5.8];
    gl.uniformMatrix4fv(u.model,false,pose(angle,tilt));gl.uniformMatrix4fv(u.view,false,lookAt(eye,[0,.40,0]));gl.uniformMatrix4fv(u.projection,false,perspective(31*Math.PI/180,aspect));gl.uniform3fv(u.eye,eye);
    for(const p of parts){gl.bindVertexArray(p.vao);gl.uniform3fv(u.offset,p.explode.map(x=>x*explosion));gl.uniform3fv(u.color,p.accent?accent:p.color);gl.uniform1f(u.roughness,p.roughness);gl.uniform1f(u.metallic,p.metallic);gl.drawElements(gl.TRIANGLES,p.count,gl.UNSIGNED_INT,0);}
    gl.bindVertexArray(null);diagnostics.frames++;Object.assign(diagnostics,{progress:p,exploded:explosion,yaw:angle,ready:true,paused});
  }
  const chapters=[['An original concept','Made to <br>move you.','A study in softness, structure, and the space between. Scroll to turn the idea over.','Soft upper. Structured support.'],['Construction, revealed','Nothing <br>without purpose.','An airy upper. A sculpted midsole. A grounded outsole. Separate the parts to understand the whole.','One object. Three structural layers.'],['A considered finish','Find your <br>point of view.','Turn the form. Change the accent. Small, deliberate decisions give the object its character.','Material is part of the interaction.']];
  let chapter=-1;
  function scroll(){const r=$('#story').getBoundingClientRect(),range=Math.max(1,r.height-innerHeight),p=clamp(-r.top/range);if(!paused)progress=p;$('#progress-bar').style.width=`${p*100}%`;const next=p<.28?0:p<.76?1:2;if(next!==chapter){chapter=next;const c=chapters[next];$('#chapter').textContent=c[0];$('#headline').innerHTML=c[1];$('#description').textContent=c[2];$('#part-label').textContent=c[3];document.querySelectorAll('[data-jump]').forEach((el,i)=>{if(i===next)el.setAttribute('aria-current','step');else el.removeAttribute('aria-current');});}request();}
  addEventListener('scroll',scroll,{passive:true});addEventListener('resize',()=>{scroll();request();});
  document.querySelectorAll('[data-jump]').forEach(a=>a.addEventListener('click',e=>{e.preventDefault();const y=$('#story').offsetTop+Number(a.dataset.jump)*($('#story').offsetHeight-innerHeight);scrollTo({top:y,behavior:reduced.matches?'instant':'smooth'});}));
  const palette={sage:[.19,.49,.44],cobalt:[.075,.17,.58],ember:[.57,.13,.055]};
  document.querySelectorAll('[data-color]').forEach(b=>b.addEventListener('click',()=>{accent=palette[b.dataset.color];document.querySelectorAll('[data-color]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));request();}));
  $('#explode').addEventListener('click',()=>{manualExplosion=manualExplosion!==true;$('#explode').setAttribute('aria-pressed',String(manualExplosion));$('#explode').textContent=manualExplosion?'Rejoin layers':'Separate layers';request();});
  motionButton.addEventListener('click',()=>{paused=!paused;updateMotion();scroll();request();});
  $('#reset').addEventListener('click',()=>{yawOffset=0;manualExplosion=null;$('#explode').setAttribute('aria-pressed','false');$('#explode').textContent='Separate layers';request();});
  let pointer=null;
  canvas.addEventListener('pointerdown',e=>{pointer={id:e.pointerId,x:e.clientX,y:e.clientY,offset:yawOffset};canvas.setPointerCapture(e.pointerId);});
  canvas.addEventListener('pointermove',e=>{if(!pointer||pointer.id!==e.pointerId)return;const dx=e.clientX-pointer.x,dy=e.clientY-pointer.y;if(e.pointerType==='touch'&&Math.abs(dy)>Math.abs(dx))return;yawOffset=pointer.offset+dx*.009;request();});
  const end=e=>{if(pointer&&pointer.id===e.pointerId)pointer=null;};canvas.addEventListener('pointerup',end);canvas.addEventListener('pointercancel',end);
  canvas.addEventListener('keydown',e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();yawOffset+=e.key==='ArrowRight'?.15:-.15;request();}});
  const io=new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;if(visible)request();else if(frame){cancelAnimationFrame(frame);frame=0;}},{threshold:0});io.observe($('#stage'));
  const ro=new ResizeObserver(request);ro.observe(canvas);
  document.addEventListener('visibilitychange',()=>{hidden=document.hidden;if(hidden&&frame){cancelAnimationFrame(frame);frame=0;}else request();});
  reduced.addEventListener('change',()=>{paused=reduced.matches;updateMotion();scroll();});
  canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();diagnostics.contextLost=true;canvas.classList.remove('ready');$('#poster').classList.remove('loaded');$('#render-status').textContent='Static preview · context lost';if(frame)cancelAnimationFrame(frame);frame=0;});
  canvas.addEventListener('webglcontextrestored',()=>{$('#render-status').textContent='Reload to restore 3D';});
  addEventListener('pagehide',()=>{disposed=true;if(frame)cancelAnimationFrame(frame);io.disconnect();ro.disconnect();for(const p of parts)gl.deleteVertexArray(p.vao);for(const b of buffers)gl.deleteBuffer(b);gl.deleteProgram(program);});
  canvas.classList.add('ready');$('#poster').classList.add('loaded');$('#render-status').textContent='Live 3D · locally generated';updateMotion();scroll();request();
})();
