"""Apply the SAME normalization and collapse to the register's 2,259 asks."""
import json, sys
sys.path.insert(0, ".")
from collapse_intents import normalize, tokens, noise_label

REG = "/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-registry/asks-ledger/register.json"
recs = json.load(open(REG))["records"]
texts = [r.get("ask") or "" for r in recs]
print(f"register entries           = {len(recs)}")
print(f"empty ask field            = {sum(1 for t in texts if not t.strip())}")

norms = [normalize(t) for t in texts if t.strip()]
print(f"non-empty normalized       = {len(norms)}")

labeled = {}
for n in norms:
    lab = noise_label(n)
    if lab:
        labeled[lab] = labeled.get(lab, 0) + 1
print(f"harness-like in register   = {sum(labeled.values())} {labeled}")

uniq = sorted(set(norms))
print(f"distinct after normalize   = {len(uniq)}")

# method a: exact normalized
a = len(uniq)
# method b: prefix-40
b = len({u[:40] for u in uniq})
# method c: union-find jaccard>=0.8 within prefix-40 buckets
parent = {u: u for u in uniq}
def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x
def union(x, y):
    rx, ry = find(x), find(y)
    if rx != ry: parent[ry] = rx
buckets = {}
for u in uniq:
    buckets.setdefault(u[:40], []).append(u)
def jac(s1, s2):
    if not s1 or not s2: return 0.0
    return len(s1 & s2) / len(s1 | s2)
for members in buckets.values():
    if len(members) < 2: continue
    toks = {m: tokens(m) for m in members}
    for i in range(len(members)):
        for j in range(i + 1, len(members)):
            if jac(toks[members[i]], toks[members[j]]) >= 0.8:
                union(members[i], members[j])
c = len({find(u) for u in uniq})

corpus_lo, corpus_hi = 5216, 5799
print()
print(f"method a exact    = {a}")
print(f"method b prefix40 = {b}")
print(f"method c jaccard  = {c}")
print()
print("register vs corpus (corpus 5,216-5,799):")
for name, val in (("a", a), ("b", b), ("c", c)):
    print(f"  {name}: coverage {val/corpus_hi*100:5.1f}% - {val/corpus_lo*100:5.1f}%   ratio {corpus_lo/val:.2f}x - {corpus_hi/val:.2f}x")
