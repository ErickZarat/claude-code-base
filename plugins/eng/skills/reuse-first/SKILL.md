---
name: reuse-first
description: Use before creating any function, class, DTO, constant, utility or dependency: search for existing code to reuse or extend.
---

# Reuse first

Goal: never write something the codebase already has.

## Steps
1. **Name the capability** you are about to add in 2–4 plain words (e.g. "format money", "retry HTTP call", "invoice repository").
2. **Search by intent, not only by exact name.** Run several searches with synonyms:
   - Grep for verbs and nouns: `format|render|toString` + `money|amount|price|currency`.
   - Look in usual shared places: `common/`, `shared/`, `core/`, `lib/`, `util*/`, `support/`, `infrastructure/`, `domain/`.
   - Check existing interfaces (ports) that may already cover the capability.
   - Check dependencies already in the build file — the library may already do it.
3. **Decide and state the decision** in one line before coding:
   - `REUSE: <path:symbol>` — call it as is.
   - `EXTEND: <path:symbol>` — add a parameter/overload/strategy without breaking current callers.
   - `EXTRACT: <paths>` — two or more similar implementations exist; consolidate into one shared unit first.
   - `NEW: <proposed path>` — nothing suitable exists; explain in one sentence why the closest candidate does not fit.
4. **If NEW**, place it where the next person would look for it (same module as its siblings, shared module if used by 2+ modules),
   and give it a name that makes it findable by the searches in step 2.

## Red flags (stop and reconsider)
- You are copying a block from another file and tweaking it.
- You are writing a second HTTP client, retry helper, mapper, date formatter, or config loader.
- You are adding a library for something a current dependency already does.
