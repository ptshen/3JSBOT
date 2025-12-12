# 3JSBOT Final Report Brief
Project Metadata
Title: Text-to-3D: Optimizing LLMs for Three.js Code Generation
Course: COMS4705 NLP — Final Project
Team: Alexandra Duan (ad4376@columbia.edu), David Fu (dyf2101@columbia.edu), Patrick Shen (pts2125@columbia.edu)
Mentor: Daniel Zhang
Sharing: No external collaborators; not shared with other classes.
Problem & Motivation
Task: Generate runnable Three.js code from natural language scene descriptions.
Challenges: Low-resource domain (few public examples), brittle rendering (small syntax errors break output), spatial/visual fidelity is hard for LLMs; standard code metrics miss visual correctness.
Goal: Improve reliability and visual fidelity via prompt strategies, structured planning, and self-refinement; evaluate with execution + visual metrics and a failure taxonomy.
Data / Inputs
Prompts from training/training_data.json (scene descriptions).
Artifacts logged per run in evaluation_outputs/* (code, screenshots, results.json).
Aggregates: experiment_results.csv (all runs), failure_analysis_tagged.csv (tagged failures).
Models / Endpoints
Generation (GEN_API): https://patbshen--ollama-ollama-serve.modal.run/v1/chat/completions (defaults often codellama:7b; also llama-3.1/3.3, gpt_oss_120b, gemini, chatgpt in other conditions).
Visual evaluation (EVAL_API): https://patbshen--qwen-vl-annotator-qwenvlannotator-serve.modal.run/v1/annotate (Qwen-based VLM judge).
Pipeline
1) Generate code from prompt using chosen experiment config.
2) Render with Playwright (headless browser + local server), capture screenshot, collect console errors.
3) Evaluate:
Execution score s_exec (discrete): 1.0 clean; 0.5 runtime errors but rendered; 0.25 critical syntax/type but rendered (rare); 0.0 crash/timeout/blank.
Visual score s_vis ∈ [0,1]: Qwen VLM judges screenshot vs prompt with anchored rubric.
Final score: s_final = 0.7 * s_exec + 0.3 * s_vis.
4) Failure taxonomy (post-hoc): System Error (auth/timeout), Syntax Error (s_exec=0 non-system), Visual/Spatial Failure (s_exec=1 & s_vis<0.5), else None. Subtypes for visual failures are stubbed (mostly “Unknown”).
Prompt Strategies (in pipeline/run_experiments.py)
baseline, baseline_temp0
improved_prompt
fewshot
combined (improved + fewshot)
chain_of_thought
cot_combined (combined + CoT)
plan_then_code (two-stage plan → code)
plan_then_code_combined (plan + improved + fewshot)
self_refine (up to 2 iterations)
self_refine_combined
stacked_all (new): plan + improved + fewshot + CoT note in stage 2 + self-refine (max 2 iters).
Recent Run (stacked_all, N=10, temp=0)
Folder: evaluation_outputs/experiments_stacked_all_2025-12-11_19-38-02/stacked_all/
Averages: exec 0.75, visual 0.10, final 0.555; breakdown: runtime_errors 3, clean 6, crashed 1.
Examples:
Clean (1.0): 001_screenshot.jpg, 002, 005, 006, 007, 008.
Partial (0.5): 000 (“Cannot read properties of null…”), 003 (“objectsPlan.forEach is not a function”), 004 (“THREE[object.type] is not a constructor”).
Crash (0.0): 009 (“Invalid or unexpected token”, timeout).
No 0.25 instances in this or any logged runs.
Aggregate Failure Summary (all runs; taxonomy_failure_analysis.py --include-archived)
Conditions: baseline-temp0, chain-of-thought, codellama-7b, combined, fewshot, gemini baselines/temp0, gpt_oss_120b_temp0, llama33_70b_temp0, improved-prompt, plan-then-code, self-refine, meta-llama 70b turbo baseline.
Trends: System errors dominate gpt_oss_120b_temp0 and llama33_70b_temp0 (auth/connection). Gemini temp0 has many syntax failures plus some system errors. Visual/Spatial failures common in fewshot/plan/self-refine variants (low s_vis despite execution).
Overall totals (latest analysis): System 53, Syntax 33, Visual/Spatial 56, None 66.
Evaluation Metric (paper-ready)
Execution: discrete as above; 0.25 defined but not observed in practice.
Visual: Qwen VLM 0–1 anchored rubric.
Final: 0.7 * s_exec + 0.3 * s_vis.
Failure taxonomy used for analysis tables (system/syntax/visual).
Reproduction / Commands
Run a strategy: python pipeline/run_experiments.py --n 10 --experiment stacked_all
Failure analysis refresh:
python pipeline/taxonomy_failure_analysis.py --include-archived --output failure_analysis_tagged.csv
Artifacts: code/plan/screenshot per example in evaluation_outputs/<run>/.../.
Writing Requirements (Instructions)
Use provided LaTeX template; 6–8 pages (excl. refs). Sections: Abstract, Introduction, Related Work, Approach, Experiments (data, evaluation, details, results), Analysis (qualitative/error), Conclusion, Team Contributions, References (BibTeX). Appendices optional.
Emphasize clarity, consistent terminology, cite baselines/borrowed code.
What to Highlight in the Report
Core finding: Execution robustness is fair (clean or partial renders common), but visual fidelity is low (avg visual ~0.1 in stacked_all). Prompt stacking improved robustness but not visuals.
Failure analysis: dominant modes are system/auth for some models; syntax for gemini temp0; visual mismatch for others.
Qualitative: include representative screenshots for success, partial, crash; note absence of 0.25 cases.
Data scarcity and spatial reasoning as key challenges; VLM-based evaluation chosen over CLIP.
Gaps to Fill During Draft
Update abstract with actual numbers (execution/visual/final means) and main limitation (visual fidelity).
Add tables/plots for per-condition results and failure taxonomy.
Brief dataset description (prompt source and format).
Related work: LLM web code gen (e.g., WebBench), spatial reasoning (VisualCognition), CLIP vs VLM evaluation.


## Details to include
- Refined logging: `experiment_logger` now always appends to the root `experiment_results.csv` (no more per-workspace CSVs). Logging stays row-by-row with immediate flush.
- Temp=0 baselines runner (`run_temp0_baselines.py`): defaults to Gemini-only (uses `GEMINI_API_KEY`); `--all` adds Tinker models. Tinker auth still failing (401) despite `Authorization` and `X-Api-Key` headers.
- Gemini stability: added code sanitizer to strip addon-only classes (`OrbitControls`, `RoomEnvironment`, `PMREMGenerator`) and external texture loads to reduce render crashes; uses baseline prompt with temp=0.
- Gemini gen 404 fix: updated Gemini model list to current API-supported names (`gemini-1.5-flash`, `gemini-1.5-pro-latest`, `gemini-2.0-flash-exp`) to avoid 404s from v1beta-only names.
- Gemini model update: now tries `gemini-2.5-pro`, then `gemini-2.5-flash`, then `gemini-2.5-flash-lite` (current recommended stack).
- Gemini code hygiene: extractor now strips leftover ``` fences from generated JS to avoid syntax/runtime errors when models return fenced code blocks.
- Gemini extractor tightened: improved fence stripping to handle any lingering ``` fences (multi-line) before render.
- Gemini fence drop: extractor now drops first/last lines if they start with ``` to avoid fenced output breaking runtime.

- Baseline (codellama) failure patterns (from baseline_2025-12-11_13-56-50):
  - Frequent runtime errors: `PlaneBufferGeometry/BoxBufferGeometry is not a constructor`, `Bloom is not a constructor`, and init issues like `Cannot access 'cubeTexture' before initialization`.
  - Many black renders tied to missing/unsupported APIs or deprecated geometries; 5/10 runtime errors, 1 crash.
- Combined (codellama) findings (experiments_combined_2025-12-11_15-00-58):
  - Execution solid (10/10 clean), but visual scores low and flat (~0.18), indicating generic/off-target scenes despite no JS errors.

  For the “improved_prompt” run (experiments_prompt_2025-12-11_14-36-32):
Averages: exec 0.85, visual 0.18, final ~0.649.
Execution breakdown: 7 clean, 3 runtime_errors.
Typical failures:
Cannot read properties of undefined (reading 'push')
Cannot access 'window' before initialization
geometry1.translateZ is not a function
Visual scores are uniformly low (mostly 0.2, one at 0.6, three at 0.0), suggesting outputs are often off-target/too generic despite decent execution.
Patterns:
Runtime errors likely from uninitialized variables, referencing window before definition (possibly shadowed or in the wrong scope), and treating geometry variables as objects when undefined or wrong type.
Visual underperformance: scenes don’t match descriptions closely; outputs may be minimal/simplistic.
If you want, I can add a note to REPORT.md or adjust prompts to:
Emphasize correct variable initialization and avoid accessing window before setup.
Encourage direct scene fidelity to descriptions (avoid overly minimal scenes).
Let me know if you want those changes applied.

- Gemini temp0 run 2025-12-11_17-42-26:
  - n=10, exec avg 0.30, visual avg 0.00, final avg 0.21; breakdown: 6 runtime errors, 4 crashed.
  - Typical errors: `pmremGenerator is not defined`, `controls is not defined`, `Unexpected end of input / Page.wait_for_function timeout`.
  - Cause: generated code referenced PMREM/controls without initialization (and some fenced/partial output), so all scenes crashed before rendering → black/zero visual.

  How to read this:
System Errors: API/auth/timeout-like failures detected from error text.
Syntax Errors: code didn’t run at all (execution_score==0) and not a system issue.
Visual/Spatial (any): code ran but visual score < 0.5; subtypes stay in “Other/Unknown Visual” because the analyzer is a stub.
Rows are grouped by inferred experiment/model condition from each run folder’s metadata.
What likely went wrong:
gpt_oss_120b_temp0 and llama33_70b_temp0: all 20 cases are system errors—likely auth/rate-limit/connection failures (e.g., the earlier 401s).
gemini_temp0: mix of system errors (7) and many syntax failures (18) indicating generated code that doesn’t compile/run.
Several prompt/plan/fewshot variants executed but scored poorly on visuals (all counted as unknown visual failures because we don’t yet classify subtypes).
Overall counts across all runs: 53 system errors, 33 syntax errors, 56 visual/spatial failures, 66 runs with no detected failure.
To rerun:
python3 "pipeline/taxonomy_failure_analysis.py" --include-archived --output failure_analysis_tagged.csv
(omit --include-archived if you want only current runs).