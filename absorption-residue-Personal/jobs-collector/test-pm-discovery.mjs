// test-pm-discovery.mjs - PM/TPM discovery group fixtures (family-scoped seniority)
import {isDiscoveryTitle} from './index.js';
const cases = [
  ['Associate Product Manager', true],
  ['Product Analyst', true],
  ['Early-Career Technical Program Manager', true],
  ['APM', true],
  ['Product Manager I', true],
  ['Associate Director', false],
  ['Senior Product Manager', false],
  ['Staff Product Manager', false],
  ['Director of Product Management', false],
  ['Group Product Manager', false],
  ['Software Engineer', true],
  ['Senior Software Engineer', true],
  ['Staff Software Engineer', false],
  ['Software Engineering Intern', false],
];
let fails = 0;
for (const [t, want] of cases) {
  const got = isDiscoveryTitle(t);
  if (got !== want) { fails++; console.error('FAIL', t, '=>', got, 'wanted', want); }
}
console.log(fails === 0 ? `pm-discovery fixtures: ${cases.length}/${cases.length} pass` : `pm-discovery fixtures: ${fails} FAILURES`);
process.exit(fails ? 1 : 0);
