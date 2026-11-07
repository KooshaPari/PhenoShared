# Emergent Garden Wave 1 Source Manifest

**Campaign:** `eg-nested-corpus-2026-09`  
**Manifest:** [`../data/wave-1-source-manifest.json`](../data/wave-1-source-manifest.json)  
**State:** partial frozen wave; not the full channel corpus

## What this freezes

The manifest identifies the exact bounded source set used for the current Wave 1 research:

- 16 public YouTube video locators;
- the creator project-gallery root;
- revision-pinned creator repository files and trees where exact Git object identifiers were recovered;
- the current Mindcraft repository as a partially pinned repository source;
- the primary MineCollab paper;
- the explicitly named `autoresearch` upstream influence.

Each record distinguishes its evidence scope and analysis state. A video locator does not imply that its full transcript, description, chapters, or audiovisual content were captured. Repository records with exact Git blob or tree identifiers have stronger revision precision than sources currently recorded only by retrieval date or branch.

## What this does not freeze

The manifest is deliberately not represented as:

- the official uploads-playlist inventory;
- a complete description graph;
- a transcript corpus;
- proof that every creator-gallery project identity is resolved;
- reproduction evidence for any creator experiment;
- a final campaign manifest.

Those remain explicit gaps inside the machine-readable manifest.

## Hash contract

A generated sibling file, `../data/wave-1-source-manifest.sha256`, records the SHA-256 digest of the exact JSON bytes committed to this branch. Downstream dossiers must identify both:

1. campaign ID `eg-nested-corpus-2026-09`;
2. the source-manifest digest or the exact ResearchLedger commit containing it.

A downstream projection becomes stale when the manifest bytes, claim set, source-version state, or destination repository observation changes.

## Publication boundary

This manifest stores identifiers, URLs, evidence scopes, status, and Git object references. It does not store full transcripts, video/audio media, browser state, credentials, or raw temporary YouTube API responses.

## Downstream gate

The partial freeze is sufficient for bounded documentation or experiment-proposal dossiers that cite only the listed evidence. It is not sufficient for claims about the complete channel, corpus-wide frequencies, total transcript coverage, or universal applicability across the portfolio.
