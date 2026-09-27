/* Host-specific prototype. Syntax checked here; must be qualified in installed Photoshop.
   Commands accept data jobs, never script strings. Only the selected workspace is accessible.
   Native session must be dedicated: executeAsModal is not invisible/headless operation. */
const {entrypoints,storage}=require('uxp');
const {app,core,action}=require('photoshop');
const fs=storage.localFileSystem;
let busy=false;
const key='phenoDesign.workspace.v1';
function name(value){if(typeof value!=='string'||!/^[-A-Za-z0-9_][ A-Za-z0-9_.-]{0,150}$/.test(value)||value==='.'||value==='..')throw new Error('Unsafe flat filename');return value;}
async function authorize(){const folder=await fs.getFolder();if(!folder)throw new Error('Workspace authorization cancelled');localStorage.setItem(key,await fs.createPersistentToken(folder));}
async function workspace(){const token=localStorage.getItem(key);if(!token)throw new Error('Authorize a dedicated workspace first');return fs.getEntryForPersistentToken(token);}
function validate(j){
 if(!j||!/^[-A-Za-z0-9_]{1,96}$/.test(j.id))throw new Error('Unsafe id');
 for(const k of ['width','height'])if(!Number.isInteger(j[k])||j[k]<16||j[k]>8192)throw new Error('Invalid dimensions');
 if(!Array.isArray(j.layers)||j.layers.length<1||j.layers.length>32)throw new Error('1..32 input layers required');
 for(const l of j.layers){name(l.file);if(!/\.(png|jpe?g|tiff?)$/i.test(l.file))throw new Error('Only local raster inputs');if(typeof l.name!=='string'||l.name.length>200)throw new Error('Invalid layer name');if(l.opacity!==undefined&&(!Number.isFinite(l.opacity)||l.opacity<0||l.opacity>100))throw new Error('Invalid opacity');}
}
async function compose(root,j){
 validate(j);
 const all=await root.getEntries();
 if(all.some(x=>x.name===j.id+'.result'))return; // Idempotence by unique job directory, including failed attempts. Use a new id for retries.
 const out=await root.createFolder(j.id+'.result');
 const receipt=await out.createFile('receipt.json',{overwrite:false});
 try{
  const inputFiles=[];
  for(const l of j.layers){const e=await root.getEntry(l.file);if(!e.isFile)throw new Error('Input not a file');inputFiles.push(e);}
  await core.executeAsModal(async context=>{
   const doc=await app.documents.add({width:j.width,height:j.height,resolution:72,mode:'RGBColorMode',fill:'transparent'});
   await context.hostControl.registerAutoCloseDocument(doc.id);
   for(let i=0;i<inputFiles.length;i++){
    if(context.isCancelled)throw new Error('Cancelled');
    await action.batchPlay([{_obj:'select',_target:[{_ref:'document',_id:doc.id}]},
     {_obj:'placeEvent',null:{_path:fs.createSessionToken(inputFiles[i]),_kind:'local'},freeTransformCenterState:{_enum:'quadCenterState',_value:'QCSAverage'}}],{});
    const layer=doc.activeLayers[0];layer.name=j.layers[i].name;layer.opacity=j.layers[i].opacity??100;
   }
   const psd=await out.createFile(j.id+'.psd',{overwrite:false});
   const png=await out.createFile(j.id+'.png',{overwrite:false});
   await doc.saveAs.psd(psd);
   await doc.saveAs.png(png);
   // Auto-close only the newly created document on leaving the modal scope.
   await receipt.write(JSON.stringify({id:j.id,status:'EXPORTED_UNVERIFIED',hostVersion:app.version,dimensions:[j.width,j.height],layerCount:doc.layers.length,source:'bounded local raster composition',nativeReopen:'NOT_RUN',visualReview:'INCONCLUSIVE'},null,2));
  },{commandName:'phenoDesign bounded composition'});
 }catch(e){await receipt.write(JSON.stringify({id:j.id,status:'FAIL',message:String(e)},null,2));throw e;}
}
async function processJobs(){
 if(busy)throw new Error('Another worker job is active');busy=true;
 try{const root=await workspace();const entries=await root.getEntries();const jobs=entries.filter(e=>e.isFile&&e.name.endsWith('.job.json')).sort((a,b)=>a.name.localeCompare(b.name));
  if(jobs.length>32)throw new Error('Queue exceeds 32-job canary budget');
  for(const file of jobs){const metadata=await file.getMetadata();if(metadata.size>256*1024)throw new Error('Job too large');await compose(root,JSON.parse(await file.read()));}
 }finally{busy=false;}
}
entrypoints.setup({commands:{authorize,processJobs}});
