# Testing Corpus Layout

Use this reference only for explicit Skill development, evaluation, calibration-case, or corpus-maintenance requests. Ordinary template execution stays in the current workspace and never writes to this corpus or the installed Skill.

## Relationship to the installed Skill

Resolve paths from the installed Skill root; do not store a machine-specific home path:

```text
seedream-template-spec-v2-1/                 # current Skill root
../../skill-testing/seedream-template-spec-v2-1/
```

For an uninstalled workspace development copy, use <workspace>/skill-testing/seedream-template-spec-v2-1/ so the installed-layout relative path is not misresolved. For installed Skills, both directories live below the same Codex home. The Skill is replaceable package code; the testing corpus is persistent user data and must survive Skill reinstall or upgrade.

## Corpus structure

```text
seedream-template-spec-v2-1/
├── TESTING.md
├── cases/
│   └── <case-slug>/
│       ├── CASE.md
│       ├── run-001/
│       │   ├── 0.reference/
│       │   ├── 1.define/
│       │   ├── 2.fit/
│       │   ├── 3.tune/
│       │   ├── 4.calibrate/
│       │   └── 5.release/
│       └── run-002/
└── archive/
    └── <historical-case-slug>/
```

- `cases/` contains active, reusable template directions. A case is the stable identity shared by repeated tests.
- `CASE.md` is the case-level index: purpose, stable slug, and a run catalog. Do not put run-specific analysis in it.
- `run-###/` contains one independent testing attempt and its ordered Reference → DEFINE → FIT → TUNE → CALIBRATE → RELEASE lineage. Create numbered stage folders only; legacy unnumbered folders remain readable but should be migrated only on explicit request. Run directories sit directly under the case; do not add a redundant `runs/` container. Stage folders belong inside a run, never directly under the case root.
- A stopped or incomplete attempt remains a numbered run. `archive/` is only for material that does not belong to an active case lineage, not for earlier or incomplete runs of the same case.
- Use monotonically increasing, zero-padded run IDs (`run-001`, `run-002`, ...). Choose the next unused ID; do not renumber, overwrite, merge, or silently continue an older run.
- Continue an existing run only when the user explicitly identifies it or the current conversation has already established it unambiguously. Otherwise, an explicit request for a new test creates the next run.
- `archive/` contains superseded or legacy workflow evidence retained for comparison.
- Use stable lowercase kebab-case slugs. Do not include dates in the corpus root; record dates in case metadata when needed.
- Preserve each case's authoritative JSON, evidence lineage, generated reports, prompts, and source references.
- Add a new case directory for every distinct template direction. Add a new run directory when testing the same direction again. Continue an existing run only when both its lineage and the user's selection identify that exact attempt.

## Case and run routing

- A new template creates a stable lowercase kebab-case case directory, `CASE.md`, and `run-001/`; write its normal DEFINE materials inside that run.
- For an existing direction, resolve the user's name against `CASE.md` title, slug, and aliases. One unique match may be selected; zero or multiple matches require clarification.
- “New round” always creates the next unused `run-###`; it never continues the highest run in place.
- Choose references from the user's current request and established conversation context. Reuse prior-run references only when requested or confirmed; otherwise collect a fresh valid set. When reused, copy rather than move them and note their source run.
- After creating a case or run, update both its `CASE.md` run table and the corpus-relative `TESTING.md` catalog. Paths recorded in metadata and indexes are relative to the corpus root or case root.

## Maintenance boundary

- Creating and indexing a case or run is part of normal Skill execution. Renaming, archiving, or deleting existing material still requires an explicit request.
- Do not scan or select existing cases unless the user names an existing template, asks for a new round, or explicitly requests discovery.
- Bundled `cases/` remain small deterministic regression fixtures used by automated checks; do not use them as the human testing corpus.
- When moving a case into the corpus, verify file counts and hashes before removing the old copy.
