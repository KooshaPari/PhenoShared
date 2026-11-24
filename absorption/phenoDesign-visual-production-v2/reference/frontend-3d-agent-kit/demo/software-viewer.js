/* CPU triangle preview when WebGL is unavailable. An inspection/demo fallback, NOT
   the suggested production fallback: production should normally retain a poster.
   Real mesh vertices are projected and shaded, with approximate painter ordering. */
window.startSoftwareDemo = function () {
  'use strict';
  const $=s=>document.querySelector(s),old=$('#product');
  const canvas=old.cloneNode();old.replaceWith(canvas);
  const ctx=canvas.getContext('2d',{alpha:true});
  if(!ctx)return false;
  const model=window.PRODUCT_MESH;
  const d=window.__DEMO__={ready:false,frames:0,progress:0,exploded:0,yaw:0,paused:false,contextLost:false,renderer:'CPU triangle preview (WebGL unavailable)'};
  const reduced=matchMedia('(prefers-reduced-motion: reduce)'),saveData=!!navigator.connection?.saveData;
  let paused=reduced.matches||saveData,progress=0,manual=null,yawOffset=0,accent=[.19,.49,.44],raf=0,visible=true,disposed=false,chapter=-1;
  const clamp=x=>Math.max(0,Math.min(1,x)),smooth=x=>{x=clamp(x);return x*x*(3-2*x)},dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2],norm=a=>{const n=Math.hypot(...a);return a.map(x=>x/n)},cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
  function request(){if(!raf&&visible&&!document.hidden&&!disposed)raf=requestAnimationFrame(render);}
  function render(){raf=0;const start=performance.now(),rect=canvas.getBoundingClientRect();canvas.width=Math.max(1,Math.round(rect.width));canvas.height=Math.max(1,Math.round(rect.height));const W=canvas.width,H=canvas.height,aspect=W/H;
    const eye=aspect<1.05?[4,2.7,7.2]:[3,2.1,5.8],z=norm([eye[0],eye[1]-.4,eye[2]]),x=norm(cross([0,1,0],z)),y=cross(z,x),f=H/(2*Math.tan(31*Math.PI/360));
    const yaw=-.28+smooth(progress)*Math.PI*1.66+yawOffset,tilt=.03+Math.sin(progress*Math.PI)*.15,c=Math.cos(yaw),s=Math.sin(yaw),a=Math.cos(tilt),b=Math.sin(tilt),explosion=manual===null?smooth((progress-.29)/.24)*(1-smooth((progress-.75)/.19)):(manual?1:0);
    function rotate(px,py,pz){const yy=py*a-pz*b,zz=py*b+pz*a;return [c*px+s*zz,yy,-s*px+c*zz]}
    const triangles=[];const light=norm([-2.5,5,4]);
    for(const part of model.parts){const points=[],normals=[],off=part.explode.map(v=>v*explosion);for(let i=0;i<part.positions.length;i+=3){const p=rotate(part.positions[i]+off[0],part.positions[i+1]+off[1],part.positions[i+2]+off[2]),q=[p[0]-eye[0],p[1]-eye[1],p[2]-eye[2]],depth=-dot(q,z);points.push([W/2+dot(q,x)*f/depth,H/2-dot(q,y)*f/depth,depth]);normals.push(rotate(part.normals[i],part.normals[i+1],part.normals[i+2]));}
      const color=part.accent?accent:part.color;
      for(let i=0;i<part.indices.length;i+=3){const ai=part.indices[i],bi=part.indices[i+1],ci=part.indices[i+2],A=points[ai],B=points[bi],C=points[ci];if(Math.min(A[2],B[2],C[2])<.1)continue;
        let n=norm([normals[ai][0]+normals[bi][0]+normals[ci][0],normals[ai][1]+normals[bi][1]+normals[ci][1],normals[ai][2]+normals[bi][2]+normals[ci][2]]);
        // Double-sided preview. Perspective winding flips in screen coordinates.
        if((B[0]-A[0])*(C[1]-A[1])-(B[1]-A[1])*(C[0]-A[0])>0)continue;
        const intensity=.29+.71*Math.max(0,dot(n,light))+.10*Math.max(0,n[1]);const rgb=color.map(v=>Math.round(Math.pow(Math.max(0,v*intensity),1/2.2)*255));triangles.push({A,B,C,depth:(A[2]+B[2]+C[2])/3,fill:`rgb(${rgb.join(',')})`});}
    }
    triangles.sort((a,b)=>b.depth-a.depth);ctx.clearRect(0,0,W,H);ctx.lineJoin='round';ctx.lineWidth=.5;
    for(const t of triangles){ctx.beginPath();ctx.moveTo(t.A[0],t.A[1]);ctx.lineTo(t.B[0],t.B[1]);ctx.lineTo(t.C[0],t.C[1]);ctx.closePath();ctx.fillStyle=t.fill;ctx.fill();ctx.strokeStyle=t.fill;ctx.stroke();}
    Object.assign(d,{ready:true,frames:d.frames+1,progress,exploded:explosion,yaw,paused,lastRenderMs:performance.now()-start});
  }
  const chapters=[['An original concept','Made to <br>move you.','A study in softness, structure, and the space between. Scroll to turn the idea over.','Soft upper. Structured support.'],['Construction, revealed','Nothing <br>without purpose.','An airy upper. A sculpted midsole. A grounded outsole. Separate the parts to understand the whole.','One object. Three structural layers.'],['A considered finish','Find your <br>point of view.','Turn the form. Change the accent. Small, deliberate decisions give the object its character.','Material is part of the interaction.']];
  function onScroll(){const r=$('#story').getBoundingClientRect(),p=clamp(-r.top/Math.max(1,r.height-innerHeight));if(!paused)progress=p;$('#progress-bar').style.width=p*100+'%';const next=p<.28?0:p<.76?1:2;if(next!==chapter){chapter=next;const c=chapters[next];$('#chapter').textContent=c[0];$('#headline').innerHTML=c[1];$('#description').textContent=c[2];$('#part-label').textContent=c[3];document.querySelectorAll('[data-jump]').forEach((e,i)=>{if(i===next)e.setAttribute('aria-current','step');else e.removeAttribute('aria-current')})}request();}
  function motion(){d.paused=paused;$('#motion').textContent=paused?'Enable movement':'Pause movement';$('#motion').setAttribute('aria-pressed',String(paused));document.body.classList.toggle('static-mode',reduced.matches||saveData);}
  addEventListener('scroll',onScroll,{passive:true});addEventListener('resize',onScroll);
  document.querySelectorAll('[data-jump]').forEach(e=>e.addEventListener('click',event=>{event.preventDefault();scrollTo({top:$('#story').offsetTop+Number(e.dataset.jump)*($('#story').offsetHeight-innerHeight),behavior:reduced.matches?'instant':'smooth'});}));
  const palette={sage:[.19,.49,.44],cobalt:[.075,.17,.58],ember:[.57,.13,.055]};
  document.querySelectorAll('[data-color]').forEach(b=>b.addEventListener('click',()=>{accent=palette[b.dataset.color];document.querySelectorAll('[data-color]').forEach(e=>e.setAttribute('aria-pressed',String(e===b)));request()}));
  $('#explode').addEventListener('click',()=>{manual=manual!==true;$('#explode').setAttribute('aria-pressed',String(manual));$('#explode').textContent=manual?'Rejoin layers':'Separate layers';request()});
  $('#motion').addEventListener('click',()=>{paused=!paused;motion();onScroll()});
  $('#reset').addEventListener('click',()=>{manual=null;yawOffset=0;$('#explode').setAttribute('aria-pressed','false');$('#explode').textContent='Separate layers';request()});
  let pointer=null;canvas.addEventListener('pointerdown',e=>{pointer={id:e.pointerId,x:e.clientX,y:e.clientY,offset:yawOffset};canvas.setPointerCapture(e.pointerId)});canvas.addEventListener('pointermove',e=>{if(!pointer||pointer.id!==e.pointerId)return;const dx=e.clientX-pointer.x,dy=e.clientY-pointer.y;if(e.pointerType==='touch'&&Math.abs(dy)>Math.abs(dx))return;yawOffset=pointer.offset+dx*.009;request()});for(const event of ['pointerup','pointercancel'])canvas.addEventListener(event,()=>pointer=null);
  canvas.addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();yawOffset+=e.key==='ArrowRight'?.15:-.15;request()}});
  const io=new IntersectionObserver(e=>{visible=e[0].isIntersecting;if(visible)request();else if(raf){cancelAnimationFrame(raf);raf=0}});io.observe($('#stage'));document.addEventListener('visibilitychange',()=>{if(document.hidden&&raf){cancelAnimationFrame(raf);raf=0}else request()});reduced.addEventListener('change',()=>{paused=reduced.matches;motion();onScroll()});
  addEventListener('pagehide',()=>{disposed=true;if(raf)cancelAnimationFrame(raf);io.disconnect()});
  canvas.classList.add('ready');$('#poster').classList.add('loaded');$('#render-status').textContent='Local 3D · CPU preview';motion();onScroll();return true;
};
