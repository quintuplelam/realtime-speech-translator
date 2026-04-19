# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

## Project-Specific: FunASR Speech Translation

### Overview
**Realtime Conference Speech Translator (RCST)** — A low-latency speech-to-text translation system for conferences, providing real-time English ↔ Chinese bidirectional translation with bilingual subtitle display.

### Core Technology
- **ASR**: FunASR nano 0.8B (https://github.com/modelscope/FunASR)
  - Direct library call (no separate server)
  - Built-in VAD
  - Streaming transcription
- **Translation**: Argos Translate (EN↔ZH)
- **UI**: Web-based bilingual subtitle display (horizontal split, auto-scroll)

### Architecture
```
[Microphone/Broadcast] → Audio Chunking (6s) → FunASR (ASR) → Argos Translate (EN→ZH) → [Web UI]
```

### Two Modes
- **Demo Mode**: WNYC FM broadcast stream capture
- **Real Mode**: Microphone input capture

### Key Conventions
- **All code in English** — variable names, function names, comments, commit messages
- **Latency-first** — all optimizations prioritize reducing latency
- **Streaming inference** — models use streaming/incremental modes
- **Local inference only** — no cloud API dependencies
- **Apache 2.0 license** — all source code
