import json, sys
sys.path.insert(0, ".")
from collapse_intents import normalize, tokens, noise_label

REG="/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-registry/asks-ledger/register.json"
MARK=("AGENTS.md","<environment_context>","codex_internal_context","system-reminder","Project Instructions")

recs=json.load(open(REG))["records"]
quotes=[normalize(r["quote"]) for r in recs if (r.get("quote") or "").strip()]
asks=[normalize(r["ask"]) for r in recs if (r.get("ask") or "").strip()]
print(f"register quotes = {len(quotes)}  distinct = {len(set(quotes))}")
print(f"register asks   = {len(asks)}  distinct = {len(set(asks))}")

corpus=set()
for fn in ["jcode-occurrences.jsonl","codex_user_turns_v2.jsonl"]:
    for line in open(fn):
        d=json.loads(line); t=d.get("text") or ""
        if len(t.strip())<12: continue
        if d.get("is_human") is False: continue
        if d.get("display_role")=="system": continue
        if d.get("is_injected") is True or any(m in t for m in MARK): continue
        n=normalize(t)
        if n and not noise_label(n): corpus.add(n)
print(f"corpus distinct cleaned = {len(corpus)}")

def report(label, items):
    items=set(items)
    exact=corpus & items
    # substring: register text inside a corpus turn, or vice versa
    blob="\n".join(corpus)
    sub_in=sum(1 for x in items if len(x)>=25 and x in blob)
    cpre={c[:40] for c in corpus}
    pref=sum(1 for x in items if x[:40] in cpre)
    print(f"\n{label}: n={len(items)}")
    print(f"  exact normalized match  = {len(exact)} ({len(exact)/len(items)*100:.1f}%)")
    print(f"  40-char prefix match    = {pref} ({pref/len(items)*100:.1f}%)")
    print(f"  substring in a corpus ask = {sub_in} ({sub_in/len(items)*100:.1f}%)")

report("REGISTER QUOTE (verbatim anchor)", quotes)
report("REGISTER ASK (synthesized)", asks)
