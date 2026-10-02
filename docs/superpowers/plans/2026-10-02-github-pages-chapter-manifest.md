# GitHub Pages Chapter Manifest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make UNBLACK automatically list PDFs named `numer-nazwa.pdf` on GitHub Pages, using the numeric prefix as the chapter number and the remaining filename as the title.

**Architecture:** GitHub Pages/Jekyll generates `chapters.json` from repository PDF files at publish time. `index.html` fetches that manifest, validates and normalizes filenames, sorts chapters numerically, then feeds the existing reader UI. Direct `file://` use keeps a documented single-file fallback to `0-wstęp.pdf`.

**Tech Stack:** Static HTML/CSS/JavaScript, GitHub Pages Jekyll/Liquid, Python 3 + Playwright integration tests.

**Spec:** `docs/superpowers/specs/2026-10-02-github-pages-chapter-manifest-design.md`

## Global Constraints

- Accepted filename format is `<non-negative integer>-<non-empty name>.pdf`, with lowercase `.pdf`.
- Numeric prefixes control sorting and displayed chapter numbers; gaps are allowed.
- Hyphens and underscores in the name become spaces; only the first title letter is automatically uppercased.
- Files outside the convention are ignored; duplicate numeric prefixes are a visible configuration error.
- Do not use GitHub API, external libraries, a server application, or `.nojekyll`.
- Preserve the existing black/red design, PDF reader, download/open actions, navigation, responsive layout, and accessibility behavior.
- The original filename is retained for PDF URLs and downloads.
- The current PDF is already named `0-wstęp.pdf`; do not rename or overwrite it again.

## Review Focus

- Unicode filenames such as `0-wstęp.pdf` must survive manifest generation and URL handling without mojibake.
- Numeric sorting must place `2-drugi.pdf` before `10-dziesiąty.pdf`.
- A duplicate prefix such as `1-a.pdf` plus `1-b.pdf` must stop ambiguous navigation and show the conflicting number.
- A missing, unprocessed, or malformed `chapters.json` must show a useful deployment/configuration error without leaving active reader controls.
- Project Pages paths such as `/unblack/0-wstęp.pdf` must remain valid rather than being rewritten as domain-root paths.

---

### Task 1: GitHub Pages manifest contract

**Files:**
- Create: `chapters.json`
- Verify: `0-wstęp.pdf`

**Interfaces:**
- Consumes: Jekyll `site.static_files`, each entry's `name`, `path`, and `extname`.
- Produces: a JSON array of `{ "name": string, "path": string }` for all lowercase `.pdf` files; paths use Jekyll `relative_url`.

- [ ] **Step 1: Verify the precondition**

Run: `Get-ChildItem -File *.pdf | Select-Object Name,Length`

Expected: `0-wstęp.pdf` exists and `0.pdf` does not.

- [ ] **Step 2: Create `chapters.json` as a Jekyll template**

Use YAML front matter with `layout: null`, filter `site.static_files` to entries whose `extname` equals `.pdf`, and serialize `name` plus `path | relative_url` with `jsonify`. The rendered result must be a valid JSON array with no trailing-comma dependency.

- [ ] **Step 3: Validate the manifest contract manually**

Check that a hypothetical `0-wstęp.pdf` entry renders with its Unicode name intact and a project-relative URL. Confirm the template's filtered loop uses `forloop.last` on the already-filtered PDF collection.

- [ ] **Step 4: Commit when a Git repository exists**

The current workspace has no `.git` directory. Do not initialize a repository implicitly. After the user initializes or clones the GitHub repository:

```bash
git add chapters.json 0-wstęp.pdf
git commit -m "feat: generate chapter manifest on GitHub Pages"
```

### Task 2: Manifest parsing and chapter data model

**Files:**
- Modify: `index.html` (inline script around the current chapter-discovery functions)
- Create: `tests/test_chapter_reader.py`

**Interfaces:**
- Consumes: `chapters.json` entries `{ name: string, path: string }`.
- Produces: `parseChapter(entry) -> { number: number, title: string, file: string } | null`, `prepareChapters(entries) -> chapter[]`, and `loadChapters() -> Promise<void>`.

- [ ] **Step 1: Write failing browser integration tests for parsing and sorting**

Create a local HTTP test server that serves the real `index.html`, a fixture manifest in deliberately unsorted order, and minimal PDF responses. Test these literal outcomes:

- `0-wstęp.pdf` → number `0`, title `Wstęp`;
- `2-drugi_rozdział.pdf` → number `2`, title `Drugi rozdział`;
- `10-dziesiąty.pdf` appears after number `2`;
- `not-a-chapter.pdf` is ignored;
- selected reader/download URLs use the manifest `path` unchanged.

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `python -m unittest tests.test_chapter_reader.ChapterManifestTests.test_parses_and_sorts_named_pdf_files -v`

Expected: FAIL because `index.html` still probes `0.pdf`, `1.pdf` and does not fetch `chapters.json`.

- [ ] **Step 3: Implement the manifest data flow in `index.html`**

Replace numeric URL probing (`MAX_CHAPTERS`, `probePdf`, `probePdfContent`, and their timeout helpers) with the three interfaces above. Match filenames with `/^(\d+)-(.+)\.pdf$/u`, parse numbers with `Number`, normalize repeated `-`/`_` separators to spaces, trim, uppercase the first Unicode character with Polish locale, and sort by `number` then original filename.

- [ ] **Step 4: Update the existing renderer to use `chapter.number`**

Change `chapterNumber` to format the manifest number with `padStart(2, "0")`. Keep array position for previous/next navigation and counters, while the displayed list/kicker uses the filename-derived number.

- [ ] **Step 5: Run the focused test and verify GREEN**

Run: `python -m unittest tests.test_chapter_reader.ChapterManifestTests.test_parses_and_sorts_named_pdf_files -v`

Expected: PASS.

- [ ] **Step 6: Commit when a Git repository exists**

```bash
git add index.html tests/test_chapter_reader.py
git commit -m "feat: load named chapters from generated manifest"
```

### Task 3: Failure states and local fallback

**Files:**
- Modify: `index.html` (manifest error/local fallback branches)
- Modify: `tests/test_chapter_reader.py`

**Interfaces:**
- Consumes: `prepareChapters(entries)` and `loadChapters()` from Task 2.
- Produces: deterministic empty, configuration-error, duplicate-index, and `file://` fallback states.

- [ ] **Step 1: Write failing tests for error and fallback behavior**

Add tests asserting:

- duplicate number `1` produces heading `Błąd konfiguracji` and mentions `1`;
- malformed JSON and HTTP 404 produce heading `Błąd konfiguracji` with reader actions disabled;
- an empty/fully ignored manifest produces `Brak rozdziałów` and mentions `0-wstęp.pdf`;
- opening the page via `file://` loads only `0-wstęp.pdf` and shows the GitHub Pages limitation note.

- [ ] **Step 2: Run the failure-state tests and verify RED**

Run: `python -m unittest tests.test_chapter_reader.ChapterManifestTests.test_duplicate_index tests.test_chapter_reader.ChapterManifestTests.test_manifest_failure tests.test_chapter_reader.ChapterManifestTests.test_file_fallback -v`

Expected: at least one FAIL because the new error contracts are not implemented yet.

- [ ] **Step 3: Implement the four states in `index.html`**

Use the existing loading, empty-state, and disabled-action helpers. Add one configuration-error helper accepting a human-readable message. In `file://`, bypass manifest fetch and add `{ number: 0, title: "Wstęp", file: "0-wstęp.pdf" }`.

- [ ] **Step 4: Run the failure-state tests and verify GREEN**

Run the same command as Step 2.

Expected: all listed tests PASS with no JavaScript page errors.

- [ ] **Step 5: Commit when a Git repository exists**

```bash
git add index.html tests/test_chapter_reader.py
git commit -m "fix: handle invalid chapter manifests"
```

### Task 4: Full regression and responsive verification

**Files:**
- Modify: `tests/test_chapter_reader.py` only if a regression test exposes a real defect
- Verify: `index.html`, `chapters.json`, `0-wstęp.pdf`

**Interfaces:**
- Consumes: the complete reader and manifest flow from Tasks 1–3.
- Produces: verification evidence for the shipped static site.

- [ ] **Step 1: Add the remaining high-risk integration assertions**

Cover the five Review Focus items, navigation between at least three chapters, original download filename, `aria-current`, and zero horizontal overflow at 390×844 and 1440×1000.

- [ ] **Step 2: Run the complete test suite**

Run: `python -m unittest discover -s tests -v`

Expected: all tests PASS, zero JavaScript page errors.

- [ ] **Step 3: Inspect responsive screenshots**

Capture one 390×844 screenshot and one 1440×1000 screenshot from the fixture-manifest server. Confirm that chapter numbers/titles, toolbar actions, PDF frame, and horizontal mobile chapter navigation remain usable.

- [ ] **Step 4: Verify repository deployment prerequisites**

Run: `Get-ChildItem -Force | Select-Object Name` and confirm `index.html`, `chapters.json`, and `0-wstęp.pdf` are at the publishing root, with no `.nojekyll` file.

- [ ] **Step 5: Commit when a Git repository exists**

```bash
git add index.html chapters.json tests/test_chapter_reader.py
git commit -m "test: verify automatic named chapters"
```

