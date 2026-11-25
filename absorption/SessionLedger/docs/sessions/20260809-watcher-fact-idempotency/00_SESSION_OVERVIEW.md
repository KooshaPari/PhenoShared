# Watcher fact idempotency

Goal: prevent repeated filesystem-event handling of unchanged transcript input from duplicating SQLite episodic facts.

Success: a focused ETL regression test fails before the fix, passes after it, and the daemon's relevant test suite remains green.
