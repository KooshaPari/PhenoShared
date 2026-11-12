# E — Is the 2259-ask register a complete capture of the iMessage source?

Date: 2026-11-11 (UTC). All queries read-only (`mode=ro` URI). No copies made; chat.db opened
read-only without lock contention.

- iMessage: `/Users/kooshapari/Library/Messages/chat.db` (426.6 MB, mtime 2026-11-10 23:34; WAL live)
- Register: `.../phenotype-registry/asks-ledger/ledger.db` (11.7 MB, mtime 2026-11-10 21:10)

---

## Task 1 — chat.db volume and date range

Timestamp expression: `datetime(message.date/1000000000 + 978307200,'unixepoch')`.

| Metric | Value |
|---|---|
| Total messages | 248,532 |
| `is_from_me = 1` (operator outbound) | 121,247 |
| `is_from_me = 0` (inbound) | 127,285 |
| Date range, all | 2019-03-19 04:27:50 → 2026-11-11 07:34:06 |
| Date range, `is_from_me=1` | 2019-03-19 04:27:50 → 2026-11-11 07:32:16 |
| Date range, `is_from_me=0` | 2019-03-19 04:28:04 → 2026-11-11 07:34:06 |

Per-year (from_me=1 / from_me=0 / total):

| Year | out | in | total |
|---|---|---|---|
| 2019 | 1,663 | 1,342 | 3,005 |
| 2020 | 340 | 1,088 | 1,428 |
| 2021 | 2,754 | 4,859 | 7,613 |
| 2022 | 7,943 | 11,557 | 19,500 |
| 2023 | 13,795 | 16,699 | 30,494 |
| 2024 | 48,885 | 40,518 | 89,403 |
| 2025 | 30,934 | 27,399 | 58,333 |
| 2026 | 14,933 | 23,823 | 38,756 |

Note: only 8,983 of the 121,247 outbound rows carry non-empty `text`; the rest are reactions,
attachments, tapbacks and empty payloads. Text-bearing outbound is the meaningful corpus.

---

## Task 2 — Register capture window

`reg_asks` = **2,259 rows**. `first_asked_at` is a human string; derived from the `day` column:

| Metric | Value |
|---|---|
| min(day) | **2026-09-25** |
| max(day) | **2026-11-04** |
| distinct days | 38 (window spans 41 calendar days) |
| asks per day (min / max / avg) | 1 / 254 / 59.4 |
| `source_missing = 1` | 7 asks (all unlinked to any utterance) |
| reg_utterances | 8,042 (2,625 user, 5,417 assistant) |
| reg_tasks / reg_answers | 147 / 5,417 |

**Register provenance is NOT chat.db.** `reg_provenance` has exactly one source value for all
2,259 asks: `register.json`, restored from markdown files (`September252026-01.md`, method
`relinked:exact` / `relinked:contained`). Content lineage (`reg_utterances.conversation_id`):

| conversation_id | user utts | assistant utts | asks linked |
|---|---|---|---|
| `phoneconv-01M3D10S1REWYKC27825RK0JDT` | 2,269 | 4,347 | 1,894 |
| `phoneconv-01M5E89QP154YYM60H1H4CQZ6K` | 333 | 1,070 | 335 |
| `chatdb` | 23 | 0 | **0** |

So the register was built from two **phone-assistant conversation transcripts**, not from the
iMessage database. A `chatdb` conversation exists with 23 user utterances
(`Friday, September 25, 2026, 07:37:32 PM UTC` → `Wednesday, November 04, 2026, 10:21:18 PM UTC`)
and **zero** of them were promoted to asks.

---

## Task 3 — Asks per month

| Month | asks |
|---|---|
| 2026-09 | 79 |
| 2026-10 | 2,163 |
| 2026-11 | 17 |
| **total** | **2,259** |

Per-day detail (all days with asks):

```
2026-09-25  49   2026-10-13 134   2026-10-26  11
2026-09-26   3   2026-10-14 205   2026-10-27  54
2026-09-27   1   2026-10-15  81   2026-10-28  25
2026-09-28  20   2026-10-16 120   2026-10-29   7
2026-09-29   2   2026-10-17 215   2026-10-30  22
2026-09-30   4   2026-10-18  39   2026-10-31   1
2026-10-01  13   2026-10-19 103   2026-11-02   7
2026-10-02  10   2026-10-20   6   2026-11-03   7
2026-10-05  36   2026-10-21  64   2026-11-04   3
2026-10-06  55   2026-10-22  69
2026-10-07  27   2026-10-23  30
2026-10-08  93   2026-10-24  33
2026-10-09  78   2026-10-25  29
2026-10-10 196
2026-10-11 254
2026-10-12 153
```

**Missing days inside the register window:** `2026-10-03`, `2026-10-04`, `2026-11-01`.
The 2026-11 month bucket stops at 2026-11-04: 2026-11-05 through 2026-11-11 are absent.

---

## Task 4 — chat.db operator messages inside vs after the register window

Windows: inside = `[2026-09-25 00:00, 2026-11-05 00:00)`; after = `>= 2026-11-05`.

| Slice | inside | after max day | before window | total |
|---|---|---|---|---|
| `is_from_me=1`, all rows | 3,770 | **99** | 117,378 | 121,247 |
| `is_from_me=1`, non-empty text | 3,605 | **89** | 5,289 | 8,983 |
| `is_from_me=0` inbound | 9,220 | 243 | 117,822 | 127,285 |

Outbound days after the register cutoff (all rows / text-bearing):

| Day | outbound rows |
|---|---|
| 2026-11-05 | 26 |
| 2026-11-06 | 33 |
| 2026-11-07 | 10 |
| 2026-11-08 | 7 |
| 2026-11-09 | 10 |
| 2026-11-10 | 3 |
| 2026-11-11 | 10 |
| **total** | **99** (89 with text) |

Distinct days with text-bearing outbound inside the window: 41.

---

## Task 5 — Top 25 inbound handles (and bot detection)

Inbound messages in the register window, 2026-09-25 → 2026-11-04. **99 distinct inbound handles.**

| # | handle | service | msgs | with text |
|---|---|---|---|---|
| 1 | <PHONE-REDACTED> | iMessage | 6,163 | 6,100 |
| 2 | <PHONE-REDACTED> | iMessage | 1,548 | 1,547 |
| 3 | <PHONE-REDACTED> | iMessage | 307 | 282 |
| 4 | <PHONE-REDACTED> | SMS | 232 | 207 |
| 5 | <PHONE-REDACTED> | iMessage | 100 | 95 |
| 6 | <PHONE-REDACTED> | SMS | 56 | 50 |
| 7 | <PHONE-REDACTED> | iMessage | 55 | 55 |
| 8 | <PHONE-REDACTED> | iMessage | 50 | 47 |
| 9 | <PHONE-REDACTED> | iMessage | 46 | 34 |
| 10 | <PHONE-REDACTED> | SMS | 46 | 43 |
| 11 | <PHONE-REDACTED> | iMessage | 46 | 46 |
| 12 | <PHONE-REDACTED> | SMS | 44 | 44 |
| 13 | <PHONE-REDACTED> | iMessage | 41 | 40 |
| 14 | <PHONE-REDACTED> | iMessage | 38 | 37 |
| 15 | <PHONE-REDACTED> | iMessage | 37 | 36 |
| 16 | <PHONE-REDACTED> | iMessage | 32 | 30 |
| 17 | <PHONE-REDACTED> | RCS | 32 | 28 |
| 18 | <PHONE-REDACTED> | SMS | 30 | 30 |
| 19 | <PHONE-REDACTED> | SMS | 30 | 30 |
| 20 | <PHONE-REDACTED> | iMessage | 25 | 24 |
| 21 | **22395** | SMS | 25 | 25 |
| 22 | <PHONE-REDACTED> | iMessage | 22 | 21 |
| 23 | <PHONE-REDACTED> | iMessage | 16 | 16 |
| 24 | <PHONE-REDACTED> | SMS | 13 | 13 |
| 25 | <PHONE-REDACTED> | SMS | 13 | 13 |

Handle-class breakdown, inbound in window (9,216 rows classified / 9,220 total):

| class | msgs | share |
|---|---|---|
| full phone number (`+` + 10–15 digits) | 9,152 | 99.3% |
| email (iMessage) | 10 | 0.1% |
| shortcode / short numeric (4–6 digits) | 52 | 0.6% |
| other | 2 | 0.02% |

Top shortcode/automation senders in window: `22395` 25, `738245` 5, `74338` 3, `90817` 3,
`73202` 2, `78156` 2, `787473` 2, `88683` 2, then 8 handles with 1 each.

All-time top inbound handles (context for the two dominant threads): `<PHONE-REDACTED>` 37,641 msgs,
`<PHONE-REDACTED>` 7,363, `<PHONE-REDACTED>` 7,049, `<PHONE-REDACTED>` 6,644, `<PHONE-REDACTED>` 6,163
(1,336,642 chars — the assistant/agent endpoint), `<PHONE-REDACTED>` SMS 4,350, then a long tail.
The 2026-2025 volume sits heavily on `<PHONE-REDACTED>` and `<PHONE-REDACTED>`: the operator's assistant
channel, not human contacts.

---

## Task 6 — Plain conclusions

**(a) Is the register complete for its window? No, on two independent counts.**

1. *Against chat.db*: the register is not iMessage-derived at all. Its only provenance source is
   `register.json`, whose content came from two `phoneconv-*` assistant transcripts. The `chatdb`
   conversation in the ledger holds 23 user utterances and **zero** asks. So "the 2,259-ask
   register" is a capture of the phone-assistant conversation, and chat.db is an uncaptured source.
   If the question is "does the register cover iMessage in its window", the answer is: it covers
   0% of it by construction.
2. *Against its own source*: 2,625 user utterances exist, 805 are never promoted to any ask, and
   only **1,843 distinct** utterances are linked to the 2,252 `reg_ask_messages` rows — 238
   utterances were split into 2+ asks (dedup inflation), and 7 asks have `source_missing=1` with no
   link at all. Plus 3 calendar days are missing (`2026-10-03`, `2026-10-04`, `2026-11-01`).
   Net: 2,259 asks ≠ 2,259 distinct operator intents.

**(b) Operator messages after the register cutoff: 99 outbound rows total, 89 with non-empty text,
spanning 2026-11-05 → 2026-11-11.** Dense on 11-05 (26) and 11-06 (33), sparse after. So the
cutoff is small in volume but real: the register ends 2026-11-04 and ~89 typed operator messages
sit outside it, plus 243 inbound messages in the same span. Far larger is the *before* side —
117,378 outbound rows predate 2026-09-25 (5,289 with text), i.e. the register window is 41 days
out of a 7.6-year archive.

**(c) Are non-operator/shortcode messages polluting the register? No — but the bigger risk is the
opposite.** Shortcodes are only 52 of 9,216 inbound messages in the window (0.6%), all from 1–25
message senders; no Amazon/PayPal/bank 2FA volume at all. iMessage inbound is 99.3% the operator's
own assistant channel, so the register's pollution risk is *not* bot traffic. The actual
contamination is inside the register itself: 238 duplicated utterance→ask links and 805 dropped
user utterances, meaning the register both over-counts (splits) and under-counts (drops) relative
to its source, independent of iMessage.

---

## Reproduction

```sql
-- chat.db (read-only)
select count(*) from message;
select
  sum(is_from_me=1), sum(is_from_me=0),
  min(datetime(date/1000000000 + 978307200,'unixepoch')),
  max(datetime(date/1000000000 + 978307200,'unixepoch'))
from message;
select sum(case when datetime(date/1000000000+978307200,'unixepoch') >= '2026-09-25'
                 and datetime(date/1000000000+978307200,'unixepoch') < '2026-11-05' then 1 else 0 end) inside,
       sum(case when datetime(date/1000000000+978307200,'unixepoch') >= '2026-11-05' then 1 else 0 end) after_max
from message where is_from_me=1;

-- ledger.db (read-only)
select count(*), min(day), max(day), count(distinct day) from reg_asks;
select substr(day,1,7), count(*) from reg_asks group by 1 order by 1;
select source, count(*) from reg_provenance group by 1;
select conversation_id, role, count(*) from reg_utterances group by 1,2;
select count(distinct message_id) from reg_ask_messages;
```

## Evidence files

- `probe.txt`, `ledger2.txt`, `ledger3.txt`, `ledger4.txt`, `ledger5.txt` — ledger probes
- `chat.txt`, `chat2.txt` — chat.db probes

> Redaction note: 32 E.164 phone-number occurrences (26 distinct numbers) in this file were replaced with <PHONE-REDACTED> on 2026-11-12T12:09:32Z because the repository is public. Counts and conclusions are unaffected.
