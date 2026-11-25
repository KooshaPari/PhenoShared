// Copy only the kit-owned input model and poster to this adapter's public assets.
import {mkdir,copyFile} from 'node:fs/promises';
await mkdir(new URL('./public/',import.meta.url),{recursive:true});
await copyFile(new URL('../../assets/concept-trainer.glb',import.meta.url),new URL('./public/trainer.glb',import.meta.url));
await copyFile(new URL('../../demo/poster.svg',import.meta.url),new URL('./public/poster.svg',import.meta.url));
console.log('Prepared kit-owned model/poster. No network calls.');
