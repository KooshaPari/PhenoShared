/* Source-specific normalization for authenticated, read-only discovery ingestion.
 * Never accepts experience, salary, or applicant-eligibility claims from indexes.
 */
import {isPalantirPosting} from './employer-policy.js';
const WHATNOT='https://www.whatnot.com/careers/roles/';
const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function normalizeWhatnotObservation(row) {
 if (!row || row.source!=='whatnot-official' || isPalantirPosting(row)) return null;
 const id=String(row.id||'').toLowerCase();
 if (!UUID.test(id)) return null;
 const url=String(row.official_url||'');
 if(url !== WHATNOT+id) return null;
 const title=String(row.title||'').trim();
 if(!title || title.length>180 || /<|>|\n|\r/.test(title)) return null;
 const locations=Array.isArray(row.locations)?row.locations:[];
 if(locations.length<1 || locations.length>12 || locations.some(x=>typeof x!=='string'||x.length>95))return null;
 const unique=[...new Set(locations.map(x=>x.trim()).filter(Boolean))];
 if(!unique.length)return null;
 return {id:'ashby:whatnot:'+id,ext:id,employer:'Whatnot',title,
   location:unique.join(' | '),url,source:'whatnot-official',
   flags:'experience_unknown,graduation_unknown,applicant_eligibility_unverified'};
}
