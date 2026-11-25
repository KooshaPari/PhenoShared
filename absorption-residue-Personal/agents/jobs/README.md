# agents/jobs — sweep scripts

Rebuilt 2026-10-16 after the Oct 15 04:19 sandbox wipe lost the originals.
Behavior contract: ghlist.py (Simplify JSON tier) -> ghmd.py + ghmd2.py
(markdown tier, ghmd-final.json with ghmd-prev.json rotation) -> ats.py
(Greenhouse/Lever/Ashby public board APIs, LA rank 3, SD/Chicago/Seattle/remote
rank 1, SpaceX dedupe vs submitted titles) -> post_ingest.py (POST rows in
batches of 25 to the job-collector Worker /ingest with the agent-minted
INGEST_TOKEN from ingest.tok; never print the token).

Run from the desk copy at C:\Users\example\agents\jobs.
