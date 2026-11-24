import {createHash} from 'node:crypto';
import {open, mkdir, lstat, realpath, copyFile, stat} from 'node:fs/promises';
import {join, resolve, relative, extname, sep} from 'node:path';
import {constants} from 'node:fs';
import {localAssetName} from './contracts.mjs';

export async function containedFile(root, name) {
  localAssetName(name);
  const base = await realpath(root);
  let cursor = base;
  for(const segment of name.split('/')) {
    cursor = join(cursor,segment);
    if((await lstat(cursor)).isSymbolicLink()) throw new Error('Symlinked asset rejected');
  }
  const path = await realpath(cursor), rel = relative(base,path);
  if(!rel || rel.startsWith('..'+sep) || rel==='..' || rel.startsWith(sep)) throw new Error('Asset escaped root');
  if(!(await stat(path)).isFile()) throw new Error('Asset is not a regular file');
  return path;
}
export async function hashFile(file) {
  const h=createHash('sha256'), handle=await open(file,'r');
  try { for await(const chunk of handle.createReadStream({autoClose:false})) h.update(chunk); }
  finally { await handle.close(); }
  return h.digest('hex');
}
/** Input root must remain immutable during staging. A path check is not an OS sandbox. */
export async function stageAsset(root, name, stagingDir, {maxBytes=256*1024*1024}={}) {
  const source=await containedFile(root,name), info=await stat(source);
  if(info.size===0 || info.size>maxBytes) throw new Error('Asset size outside budget');
  const digest=await hashFile(source), basename=digest+extname(name).toLowerCase();
  await mkdir(stagingDir,{recursive:true});
  const target=join(stagingDir,basename);
  try { await copyFile(source,target,constants.COPYFILE_EXCL); }
  catch(e) { if(e.code!=='EEXIST') throw e; }
  if(await hashFile(target)!==digest) throw new Error('Staged content mismatch / input changed');
  return {name:basename, sha256:digest, bytes:info.size, source:name};
}
