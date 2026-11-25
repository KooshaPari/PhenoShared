# Testing strategy

Run a focused `sl-daemon` ETL unit test that transforms the same real JSONL fixture twice through a SQLite memory store, then run the daemon crate test suite with the SQLite feature.

Observed RED: 6 recalled durable facts after two identical transforms. Expected and observed GREEN: 3 facts.
