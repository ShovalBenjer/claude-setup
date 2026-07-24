# SOTA Video Testing Pyramid 2026

## Overview

A how-to video is not a waveform and it is not a string. It is three modalities baked into one mp4 (the rendered pixels, the narration track, and the on-screen text) that all have to agree with each other at every second. A test architecture that grades only one modality against itself will pass a video that is individually clean and jointly wrong: a crisp frame showing the wrong screen, a varied-pitch narration that says the wrong brand name, captions that match a narration that contradicts the picture. Video QA needs its own pyramid because the highest-value failures live in the seams between modalities, and no single-modality metric looks there.

This doc layers three evaluation regimes, the same split the voice companion uses. First, objective signal metrics computed straight off pixels and audio samples with no language model in the loop (VMAF, SSIM, LPIPS, variance-of-Laplacian sharpness, EBU R128 loudness, F0 monotone, AudioSet-class disfluency detection). These are deterministic and cheap and catch what a vision-LLM judge is bad at. Second, cross-modal AI-judge evaluation that grounds a VO claim at second `t` against the screen shown at second `t`, the regime that owns the wrong-screen defect a viewer notices instantly and a single-modality gate never sees. Third, production-derived regression: every reviewer-found defect becomes a permanent golden fixture, and a fused output-aware scorecard re-runs on the rendered output so the grader judges what actually shipped.

The repo already has the load-bearing center of this: one fused scorecard, `generator/ship_gate.py`, where `merge_scorecard` combines `generator/brand_qa.py`, `extractor/quality_gates.py`, and `generator/video_qa.py` into a single verdict in which `passed == all HARD checks ok`, and `self_analyze` re-runs split to STT to voice to OCR on the rendered mp4, not the source. Voice acoustics live in `extractor/voice_analysis.py`. This pyramid extends that scorecard, it does not replace it. This doc exists so the generator can do both halves of the loop: grade its own output against these layers, and read a failed gate name back into a generator action that repairs the defect and re-renders, with no human in the path.

***

## Layer 0: Architecture, The Video Testing Pyramid

The 2026 layered test taxonomy (Static, Unit, Property, Component, Contract, Integration, E2E, Non-Functional) maps cleanly onto a deterministic render pipeline, but a how-to video adds two things a backend service does not have: a cross-modal plane (does the narration agree with the picture) and an audio sub-stack (is the VO clean, on-level, and free of disfluency). The pyramid below is the eight-layer base plus those two planes.

| Layer | What it tests | Method / Tool | Repo status |
|---|---|---|---|
| Static and Formal | Pre-render source invariants: logo lands on the correct edge, RTL mirror, no caption/screen contradiction in the `.tsx` source | `.tsx` source parse | have: `generator/howto_consistency.py:check_component` |
| Unit | Pure scorer logic: scorecard fusion, caption alignment math, content-token extraction | pytest over pure functions | have: `generator/ship_gate.py:merge_scorecard`, `extractor/quality_gates.py:_content_tokens` |
| Property | Invariants that must hold on every render: F0 std floor, segment energy-drift bound, palette on-brand fraction | numeric assertions over measured signal | have: `gate_monotone`, `gate_ai_feel`, `brand_qa.py:palette_fidelity` |
| Component | A real classifier over real output, no mock: vision defect detection, OCR text QA, audio disfluency tagging | gpt-5.4-SIU vision, OCR scan, PANNs / gpt-audio-1.5 | partial: `extractor/visual_qa.py`, `generator/video_qa.py:text_qa`; audio disfluency is gap |
| Contract | Cross-modal agreement at the modality boundary: caption == spoken, VO claim == screen shown | text match + grounded judge | partial: `caption_qa.py:caption_speech_ok` have; claim-grounding gap |
| Integration | Fused scorecard over the assembled output | `ship_gate` self-analyze on the mp4 | have: `generator/ship_gate.py:ship_gate` / `self_analyze` |
| System / E2E | The shipped cut behaves end to end: loudness, av-sync, brand, visual major-defect gates | full HARD set over the rendered mp4 | have: `generator/ship_gate.py` HARD set |
| Non-Functional | Delivery constraints: loudness window, dynamics, encode conformance, per-frame VMAF floor | EBU R128, ffmpeg `libvmaf` | partial: loudness have; VMAF/encode-conformance gap |
| Cross-Modal plane | VO claim semantics at time `t` vs frame OCR/screen identity at time `t` | claim decomposition + screen-identity + agreement judge | gap (Layer 5) |
| Audio sub-stack | Prosodic/level signal plus non-speech disfluency over the VO track | EBU R128, F0, PANNs CNN14, gpt-audio-1.5 | partial: signal have; disfluency gap |
| Golden Master / Regression | Deterministic per-frame diff vs a blessed render; every past bug frozen as a must-FAIL fixture | per-frame VMAF/SSIM/LPIPS, fixture suite | gap (Layer 9) |

The repo covers the spine (Static, Unit, Property, the fused Integration/E2E scorecard). The two planes and the Golden-Master layer are where the reviewer defects live and where the pyramid extends the current stack.

***

## Layer 1: Visual and Frame Signal

This layer is the video analogue of the voice signal layer (PESQ / ViSQOL / UTMOS): objective, per-frame and per-shot measurements computed directly off pixels, with no language model in the loop. It catches the failure modes a vision-LLM judge is bad at (blur, banding, compression artifacts, a frozen frame, a brand color that drifted off-palette, a one-frame transition glitch) and that an OCR-plus-LLM brief writer never looks at. These metrics split the same way audio metrics do: full-reference (you have a known-good baseline frame or master and measure distance to it: VMAF, SSIM, MS-SSIM, PSNR, LPIPS) versus no-reference (you only have the rendered frame and score it intrinsically: variance-of-Laplacian sharpness, RMS/Michelson contrast, palette delta-E, frame-to-frame difference for motion and scene-cut detection). For a synthetic how-to pipeline that re-renders from a deterministic Remotion source, the highest-value subtype is the golden-master frame snapshot: render is deterministic, so a per-frame SSIM/LPIPS diff against a blessed baseline is the cheapest deterministic regression gate available, and it is exactly the layer that is missing today.

The repo today covers two cells of this matrix and leaves the rest open. Brand-color fidelity is real and gated (`generator/brand_qa.py:palette_fidelity`, ΔE76 against the brand palette). On-screen text correctness (typos, English-leak lines, Arabic ratio) is real and gated from OCR (`generator/video_qa.py:text_qa`). Per-frame layout defects (collision/clipping/low-contrast/off-safe) are aggregated and gated (`extractor/visual_qa.py:aggregate_visual_qa` feeding `extractor/quality_gates.py:gate_visual`), but every flag is the vision model's self-report, not a deterministic pixel metric, so this is model-bound rather than signal-bound. Frozen-scene detection exists as an OCR-token-stability heuristic (`extractor/quality_gates.py:gate_static_scenes`), advisory only. Everything in the reference-metric family (VMAF, SSIM, MS-SSIM, PSNR, LPIPS), no-reference image quality (blur/sharpness, banding, compression), and frame-diff/optical-flow motion QA is absent from the gate path. Note one trap: VMAF, SSIM, MS-SSIM, PSNR, and LPIPS are full-reference; they need a baseline frame or master, which this pipeline can produce deterministically (a blessed render) but currently does not snapshot, so the cheapest deterministic regression layer is open.

### Reference-based frame metrics (need a baseline frame or master)

| Capability | What it measures | SOTA tool | Repo status | Where |
|---|---|---|---|---|
| VMAF | Perceptual full-reference video quality, fused VIF + DLM + temporal-info via learned regression; codec/encode-ladder QA | Netflix `libvmaf` (ffmpeg `libvmaf` filter), NEG mode to resist enhancement-gaming | gap | (gap) |
| SSIM / MS-SSIM | Structural similarity to a reference frame; multi-scale for resolution robustness | ffmpeg `ssim`, `torchmetrics` MS-SSIM | gap | (gap) |
| PSNR | Pixel error vs reference (codec/bitrate floor sanity) | ffmpeg `psnr` | gap | (gap) |
| LPIPS | Learned perceptual patch distance; tolerant of sub-pixel shift where SSIM/PSNR over-penalize | `pip install lpips` (richzhang/PerceptualSimilarity), `torchmetrics` LPIPS | gap | (gap) |
| Golden-master frame snapshot diff | Deterministic per-frame regression vs a blessed render (the natural fit for a deterministic Remotion source) | SSIM/LPIPS per sampled frame against committed baseline | gap | (gap) |

### No-reference frame metrics (intrinsic, no baseline)

| Capability | What it measures | SOTA tool | Repo status | Where |
|---|---|---|---|---|
| Palette / brand-color fidelity | Fraction of dominant frame colors within ΔE76 ≤ 22 of brand palette; gated ≥ 0.55 (0.15 b-roll) | in-repo ΔE76 on quantized dominant colors | have | `generator/brand_qa.py:palette_fidelity` / `delta_e76` |
| OCR typo + language-leak detection | Baked-typo blocklist hard-fail; Latin-run lines off the allowlist as English leaks; on-screen Arabic ratio | in-repo OCR-string scan | partial | `generator/video_qa.py:text_qa` (fixed blocklist, not a real spell/lexicon check) |
| Per-frame layout defects (contrast/clipping/collision/off-safe) | Vision-model defect flags aggregated, ranked, time-ranged; gated on `counts.major > 0` | gpt-5.4-SIU vision (model-bound, not pixel metric) | partial | `extractor/visual_qa.py:aggregate_visual_qa` -> `extractor/quality_gates.py:gate_visual` |
| Text legibility / contrast metric (deterministic) | Per-region luminance-contrast ratio (WCAG-style) independent of the vision model | stroke-width + Michelson/RMS contrast over the OCR bbox | gap | (gap) |
| Blur / sharpness | High-frequency energy per frame; flags soft renders, scaling mush, focus loss | variance-of-Laplacian (`cv2.Laplacian(g,CV_64F).var()`); BRISQUE/NIQE/CLIP-IQA via `pyiqa` | gap | (gap) |
| Banding / compression artifact | Blockiness, contour banding, mosquito noise | `pyiqa` NR models; ffmpeg `bbox`/gradient checks | gap | (gap) |
| Frozen / static-scene detection | A screen that does not change while the VO keeps talking | in-repo OCR-token Jaccard stability (≥0.7 for >3s during speech), advisory | partial | `extractor/quality_gates.py:gate_static_scenes` (OCR-content based, misses pure-graphic motion; 1 fps; advisory) |

### Per-shot motion and transition metrics

| Capability | What it measures | SOTA tool | Repo status | Where |
|---|---|---|---|---|
| Frame-difference / scene-cut detection | Mean-abs frame delta or histogram diff to find cuts, flashes, one-frame glitches | inter-frame diff, PySceneDetect-style content detector | gap | (gap) |
| Optical-flow / motion-smoothness | Flow-field magnitude continuity; flags teleport, whip, dropped frames, bad easing | `cv2.calcOpticalFlowFarneback` (exists as a one-off DEV-5011 logo-track script, not wired) | gap | `video-gen/DEV-5011/scripts/*` (not in `ship_gate`) |
| Jitter / shake | Per-frame translation RMS (shake floor) | in-repo metric exists but unwired | partial | `video-gen/DEV-5011/scripts/jitter_metric.py` (one-off, not in `ship_gate`) |
| Logo-motion invariant (no-teleport, RTL-mirror) | Static `.tsx` parse: intro logo lands on the same edge as the persistent corner logo; corner edge matches reading direction | in-repo source parse, pre-render | have | `generator/howto_consistency.py:check_component` |
| Transition-smoothness / easing | Easing-curve sanity, no abrupt spacing jumps between frames | contact-sheet by eye (manual) | gap | (gap) |

Motion/transition QA is the weakest cell: the only automated motion check in the gate path is `gate_static_scenes` (detects too-static, not bad-motion, and only via OCR-token change so a pure-graphic animation reads as frozen), plus the pre-render static parse in `howto_consistency.py`. Everything dynamic (frame-diff, optical flow, jitter, easing) is either a detached one-off DEV-5011 script or done by hand. The established manual method is the contact sheet: sample every 2 to 4 frames across a transition, tile them, and read the spacing and the easing curve by eye (this is how the HowToARv2 logo-whip was caught). Promoting that to a wired frame-diff metric (mean-abs delta spike at cuts, flow-magnitude continuity through transitions) is the single highest-leverage gap to close.

### Defect ownership in this band: Seekapa pronunciation (on-screen-text side)

This band does not own the cross-modal claim defect or the cough defect (those sit in the cross-modal and audio bands). It owns the on-screen half of the brand-rendering defect: the wordmark as drawn on the frame. OCR mis-reads the gradient-K wordmark as `SEEHAPA`/`Seehapa` (already allow-listed as a logo-OCR warn in `generator/video_qa.py:_LOGO_OCR`), so the visual layer cannot today confirm the rendered brand text is correct, only that no baked typo from the fixed `_TYPOS` list is present. The audio-side `seekpa` dropped-syllable slip is graded by the pronunciation band (Layer 4), not here.

Detector + auto-fix (on-screen brand-text fidelity): add a deterministic golden-glyph check for the wordmark region. The Remotion source places the logo as a known `Img` at a known position (the same anchor `howto_consistency.py` already parses), so crop that bbox per sampled frame and run a full-reference SSIM/LPIPS compare against the committed brand-logo PNG instead of trusting OCR. If SSIM drops below a tuned threshold (wrong asset, wrong color, squashed aspect, dropped glyph) the gate FAILs and names the frame range. Auto-fix is mechanical because the source is deterministic: the gate emits the offending frame timestamps and the expected asset path, the loop re-points the `Img` src in the `.tsx` (or restores the correct brand PNG) and re-renders only the failing composition, then re-runs the same glyph check until SSIM passes. This also closes the broader "no logo-presence/placement detection on rendered frames" gap with one reference metric, and it is the deterministic counterpart to the phoneme-aware audio brand gate the pronunciation band adds.

***

## Layer 2: Audio Signal and Disfluency

The voice-testing companion (`SOTA Voice Testing Pipeline 2026`) already lays out the signal regime for a voice *agent*: PESQ / ViSQOL / UTMOS perceptual MOS, a `gpt-audio-1.5` prosody judge, and WER-on-proper-nouns. This layer does not re-run those tables. The video-VO problem is narrower and more tractable: the VO is a single rendered, mono-take narration baked into an mp4, not a live duplex call, so codec/packet-loss/latency-percentile concerns mostly fall away and the failure set collapses to two bands. Band one is the prosodic and level failures the repo already measures objectively in `extractor/voice_analysis.py` (loudness EBU R128, WPM pacing, word-gap pauses, per-segment energy drift, F0 monotone, dynamics/clipping, and the `ai_feel` robotic-risk heuristic). Band two is the band the repo does not touch at all: non-speech vocal disfluencies (cough, throat-clear, breath, lip-smack, swallow) that a TTS take or a human pickup can introduce and that pass every existing gate untouched. This layer owns reviewer defect #2 (cough).

The structural reason the cough slips is verifiable in code. `ffmpeg_silences` (`extractor/voice_analysis.py:98`) and `pause_stats` (line 48) only measure absence of energy. A cough is energy, so it is not a silence and not a word-gap pause; it lands inside or between words and is invisible to both. `ai_feel` (line 217) keys only on `f0_std` / WPM / LRA / drift, so a narrator with a clean pitch contour who coughs once still scores `low`. And the ElevenLabs STT call sets `tag_audio_events="false"` (`extractor/pipeline.py:187`, verified), which actively suppresses the provider's own `(cough)` / `(breath)` event tokens before they ever reach `transcript.json`. There are zero matches for `cough|breath|throat|disfluency|filler` across `extractor`, `generator`, and `scripts`. So the defect is not under-tuned, it is undetected: nothing in the pipeline can name it.

### Band 1: prosodic and level signal (extends the voice doc, repo already covers)

| Capability | What it catches | Repo status | Where |
|---|---|---|---|
| Integrated loudness EBU R128 | LUFS outside the -16..-12 delivery window, measured on program audio not the mono-16k extract | have | `extractor/quality_gates.py:gate_loudness` over `extractor/voice_analysis.py:ffmpeg_loudness` |
| Loudness range (LRA) + true peak | Over-compressed dynamics (LRA < 3 LU feeds AI-feel), peak headroom | partial (measured, only LRA->ai_feel gated) | `extractor/voice_analysis.py:ffmpeg_loudness` |
| Pacing (WPM) | Narration outside the per-language natural band (en 120-175, ar 95-150) | have (feeds ai_feel) | `extractor/voice_analysis.py:speaking_rate_wpm` + `WPM_BANDS` |
| Word-gap pauses | Pause count/total/longest, speech ratio | have | `extractor/voice_analysis.py:pause_stats` |
| Per-segment energy drift | "Voice sounds different between segments" (>6 dB range = noticeable drift) | have | `extractor/voice_analysis.py:segment_loudness` + `consistency` |
| F0 monotone | Flat robotic contour (f0 std < 2.0 semitones) | have (HARD) | `extractor/quality_gates.py:gate_monotone` over `pitch_profile` |
| Dynamics / clipping | Crest/flat factor, noise floor, peak >= -0.1 dBFS clip flag | partial (measured, not gated) | `extractor/voice_analysis.py:extract_dynamics` |
| AI-feel composite | Weighted robotic-risk (flat pitch + off-band WPM + compressed LRA + drift) | have (HARD on `level==high`) | `extractor/quality_gates.py:gate_ai_feel` over `voice_analysis.py:ai_feel` |
| Perceptual MOS (PESQ / ViSQOL / UTMOS) | Codec/spectral distortion, no-reference naturalness MOS | gap | (gap), voice doc Layer 1; absent here |
| `gpt-audio-1.5` prosody/emotion judge | Tone mismatch, pacing-by-ear, brand-voice consistency | gap | (gap), only the `ai_feel` heuristic exists |

### Band 2: non-speech disfluency detection (the gap this layer owns)

The 2026 detector menu is mature and AudioSet-grounded. AudioSet's 527-class ontology already contains the relevant non-speech classes (Cough, Breathing, Throat clearing, Sneeze, Gasp), so any AudioSet-trained tagger emits cough/breath probabilities out of the box. Frame-level (decision-level) variants give onset/offset timestamps, which is exactly what an auto-fix edit-list needs.

| Detector | Mechanism | Why it fits VO disfluency QA | 2026 status | Repo status | Where |
|---|---|---|---|---|---|
| PANNs CNN14 (decision-level) | CNN on log-mel, AudioSet 527-class, `Cnn14_DecisionLevelMax/Att` give frame-wise onsets | mAP 0.431 audio tagging; `panns_inference` pip package, CPU-runnable, dep-light, returns timestamped cough/breath | mature baseline, still the default offline tagger | gap | (gap) |
| YAMNet | MobileNetV1 on AudioSet, 1 s frames, 1024-d embeddings | Lightweight first-stage segmenter; commonly used to slice cough segments before a heavier classifier | mature, lightweight | gap | (gap) |
| AST (Audio Spectrogram Transformer) | Convolution-free attention on spectrogram patches | 0.485 mAP on AudioSet; higher-accuracy second stage behind a YAMNet segmenter | strong | gap | (gap) |
| BEATs | SSL with iterative acoustic tokenizer | SOTA 50.6 mAP on AudioSet-2M, no external data; best ceiling if accuracy matters | SOTA | gap | (gap) |
| `gpt-audio-1.5` non-speech judge | Native-audio LLM, no transcription bottleneck | Detects laughs/sighs/hesitations natively; SCENEBench scores non-speech vocalization recognition (cough/laugh/sneeze) directly; pairs with the prosody judge proposed in the voice doc | SOTA semantic judge | gap | (gap) |
| ElevenLabs STT event tags | Provider emits `(cough)`/`(laughter)`/`(breath)` tokens | Free if enabled; first cheap signal, currently suppressed | available, disabled | gap (flag is off) | `extractor/pipeline.py:187` (`tag_audio_events="false"`) |
| Transcript-gap-with-energy heuristic | Pure ffmpeg: a word-gap region (from `pause_stats`) that has high RMS instead of silence is a non-speech vocal event | Zero new deps, reuses existing functions; cheap pre-filter to flag suspect windows for a heavier detector | derivable now | partial (both halves exist, not joined) | `voice_analysis.py:pause_stats` + `extract_dynamics`/`volumedetect` |

### Detector + auto-fix (reviewer defect #2: cough)

Two parts, cheapest first.

1. Cheap signal, enable plus heuristic. Flip `tag_audio_events` to `"true"` in `extractor/pipeline.py:stage_transcribe` so ElevenLabs emits `(cough)`/`(breath)` tokens, then add a gate over `transcript["words"]` that fails on any entry where `type != "word"` matching a cough/throat-clear/breath label. In parallel, add a dep-free pre-filter in `extractor/voice_analysis.py`: for every inter-word region that `pause_stats` would call a gap, run `volumedetect` (the same call `segment_loudness` already uses) over that window; a "gap" whose mean RMS is within roughly 12 dB of speech RMS (energy where there should be silence) is a candidate non-speech event. This catches the common case with no model and no auth.

2. Reliable detector, classifier. Add a non-speech-event detector that runs `panns_inference` (CNN14 decision-level) over `audio.wav` and returns `[{label, start, end, score}]` for cough/breath/throat-clear classes above a probability floor, or, for the SOTA path, a `gpt-audio-1.5` judge pass that returns timestamped non-speech events directly (reusing the audio-judge wiring the voice doc specifies). Either feeds a new HARD gate `no_nonspeech_events` in `run_gates()`, alongside `gate_loudness`/`gate_monotone`.

3. Auto-fix, then re-pin. The detector's timestamps drive an edit-list of `(start, end)` spans. The repair has two modes: (a) micro-splice, when the cough sits in a pause, cut the `(start, end)` span with an ffmpeg `atrim`+`concat` and crossfade the seam; (b) segment regen, when the cough overlaps a word, re-synthesize only the affected VO beat via `generator/narrate.py` (same voice + pronunciation dict), since the generator already builds VO per beat. Because the splice or the regen changes segment duration, the fix must end by re-running the beat-pinning step (`repin_beats.py`) so captions and on-screen highlights stay aligned, then re-run `ship_gate` to confirm `no_nonspeech_events` now passes. This closes the loop without a human listening pass.

### Where this band sits in the pyramid

Mapped to the eight-layer taxonomy: the Band-1 signal metrics are Non-Functional checks (delivery constraints: loudness window, dynamics) plus a Property invariant (F0 std floor, segment-drift bound). Band-2 disfluency detection is the missing Component check on the audio track: a real classifier over real audio, no mock, deterministic for PANNs and semantic for the `gpt-audio-1.5` judge. The single highest-leverage gap is that there is no audio Golden-master / Regression fixture: once the cough detector ships, the offending clip and its fixed cut should become a permanent regression case so the defect cannot silently return.

***

## Layer 3: Brand Pronunciation and Lexicon

Every layer above this one treats speech as either a waveform (signal metrics) or a bag of words (fuzzy text match). The brand-pronunciation defect lives in the gap between them: the narrator says SEEK-pa, dropping the middle `KAH` syllable, and the rendered wordmark on screen still reads SEEKAPA. The audio is clean (no clipping, on-target loudness, varied pitch), the transcript is intelligible, and the brand token is even present. The only thing wrong is one missing vowel nucleus in a proper noun the dictionary never taught the model. This is a lexicon problem, not an acoustics problem, and it is the failure mode that fuzzy string matching is structurally blind to.

The repo's current brand gate proves exactly this blindness. `brand_spoken_score` (`extractor/quality_gates.py:85`) slides a `difflib.SequenceMatcher` window over the punctuation-stripped transcript and reports the best ratio against the canonical spelling. For `seekapa` (7 chars) versus a spoken `seekpa` (6 chars), the measured ratio is 0.9230769 (verified by running the exact code), well above the `BRAND_SPOKEN_MIN=0.66` floor. A single dropped syllable moves one character out of thirteen in the matcher, so the gate passes the defect and reports it as matched. The looseness is not a bug, it is a deliberate concession: the pipeline STT splits and garbles brand tokens even on known-good cuts (the gate comment at `extractor/quality_gates.py:112` says so), which forces the threshold low enough that a real mispronunciation hides inside the same tolerance band. The fix is to stop matching graphemes against a mangled transcript and start matching phonemes against an expected pronunciation lexicon, where SEEK-pa and SEEK-AH-pa are two phoneme strings of different syllable count, not two spellings one character apart.

The 2026 SOTA stack for this is well established. A grapheme-to-phoneme front end (`g2p_en` for English via the CMU dictionary plus a neural OOV net, or `espeak-ng` for IPA across languages) converts both the canonical brand spelling and any alias into a reference phoneme string. A forced aligner (Montreal Forced Aligner via Kaldi Viterbi alignment, or WhisperX via a wav2vec2 phoneme-recognition model finetuned for word-level timing at roughly +/-50 ms) recovers what was actually spoken at the brand timestamp and where each phone sits. A phonetic distance metric (PanPhon's feature-weighted edit distance, or a syllable-nucleus count) then scores the spoken phone sequence against the reference, so that a dropped syllable scores a large distance while an articulatorily trivial difference (aspiration, vowel length) scores near zero. None of this exists in the repo today; the only phoneme-aware artifact is the ElevenLabs alias rule on the generation side.

### Capability matrix

| Capability | 2026 SOTA method | Repo status | Where it lives |
|---|---|---|---|
| Grapheme-to-phoneme reference for the brand | `g2p_en` (CMU dict + neural OOV) for EN; `espeak-ng` IPA for multilingual | gap | (gap) |
| Expected-pronunciation lexicon (canonical + accepted aliases) | Per-brand phoneme/syllable entry, language-keyed | partial (spelling-only, generation side) | `generator/narrate.py:PRON_RULE` (alias "See cah pah"), `PRON_DICT_NAME` "seekapa-alias" |
| Per-phoneme / per-word timing of the actual VO | Montreal Forced Aligner (Kaldi Viterbi); WhisperX (wav2vec2, +/-50 ms); aeneas (MFCC+DTW sync map) | gap | (gap) |
| Phonetic-distance / syllable-count check vs reference | PanPhon feature-weighted edit distance (PFER, 1/24 per feature); vowel-nucleus count | gap | (gap) |
| Fuzzy grapheme brand-in-VO proxy | difflib best-window ratio (the thing that lets SEEK-pa pass at 0.9231) | partial (advisory, too loose) | `extractor/quality_gates.py:brand_spoken_score` / `gate_brand` (BRAND_SPOKEN_MIN=0.66) |
| STT brand round-trip (gross-collapse catch) | Scribe round-trip + garbage-token blocklist | partial (AR-only, manual, gross collapse only) | `scripts/verify_ar_brand.py:main` (GARBAGE list) |
| STT brand round-trip (alias-changes-audio proof) | Scribe with/without pron-dict A/B | partial (fixed phrase, not shipped VO, not gated) | `scripts/verify_pronunciation.py:main` (hardcoded PHRASE) |
| WER-on-proper-nouns metric (SOTA voice Layer 3) | WER restricted to brand/proper-noun tokens | gap | (gap) |
| Auto-fix: pin pronunciation + re-synthesize brand segment | TTS lexicon/alias entry -> regen failing segment -> re-pin | partial (alias dict exists; no detector triggers it) | `generator/narrate.py:ensure_dict` / `_tts(locator=...)` |
| Promote pronunciation check from advisory to hard | Syllable-exact gate wired into ship_gate | gap | (gap) |

### Detector + auto-fix (owns the SEEK-pa defect)

The current `gate_brand` is advisory and fuzzy by design (verified `advisory: True` at `extractor/quality_gates.py:121`), and the two `verify_*` scripts are manual, language-split, and run against fixed phrases rather than the shipped VO. Replace the grapheme fuzzy ratio with a phoneme-aware per-video gate:

1. Locate the brand utterances. From the rendered VO transcript word list, find each window where the brand is spoken (reuse the OCR-derived brand tokens and the brand-mention windows already encoded in `scripts/verify_ar_brand.py:BRAND_WINDOWS`).
2. Recover the spoken phone string. Run a forced aligner over `audio.wav` for those windows (WhisperX wav2vec2 for the EN cuts, where +/-50 ms word timing is enough to isolate the brand token; MFA where tighter phone boundaries are wanted). The aligner returns the actual phone sequence and its syllable count for the brand token, not a mangled spelling.
3. Build the reference once per brand/language. Run `g2p_en` (EN) or `espeak-ng` (AR and others) on the canonical `Seekapa` and on the accepted alias `See cah pah` to get the reference phoneme string and the expected vowel-nucleus count (three for see-KAH-pa).
4. Score with a phonetic metric, not difflib. Compute PanPhon feature-weighted edit distance between spoken and reference phone strings, and assert the spoken syllable/vowel-nucleus count equals the reference. A dropped `KAH` fails the syllable-count check outright and posts a large feature distance; an articulatorily trivial drift (vowel length, final-vowel reduction) stays under threshold and passes. This is the gate, replacing the 0.66 difflib floor.
5. Auto-fix loop. On failure, the alias machinery is already in place: `generator/narrate.py:ensure_dict` creates-or-reuses the `seekapa-alias` ElevenLabs pronunciation dictionary, and `_tts(..., locator=locator)` applies it. The repair is to (a) confirm or strengthen the alias entry for the failing language (the see-KAH-pa alias exists for EN; AR needs its own respelled-token entry, tracked in the AR brand-pronunciation work), (b) re-synthesize only the failing brand segment through `_tts` with the locator attached, (c) re-pin the regenerated segment into the timeline (the same repin step used after VO regen elsewhere), and (d) re-run the phoneme gate on the new audio to confirm the syllable count and distance now pass.
6. Promote to hard. Once the gate is syllable-exact and per-video (so it no longer cries wolf the way the fuzzy proxy did), move it from advisory into `run_gates()` / ship_gate's HARD set alongside loudness and monotone, so a dropped-syllable brand slip blocks the autonomous render loop instead of slipping through it.

This closes the loop the existing scripts only gesture at: `verify_pronunciation.py` already proves the alias changes the audio, and `verify_ar_brand.py` already proves the gross al-Kaaba collapse is catchable. The missing piece is a phoneme-level, per-video, both-language detector that catches the subtle drop and then drives the alias-and-regen repair automatically.

***

## Layer 4: Cross-Modal Semantic (VO claim vs on-screen evidence)

Every layer before this one checks a single modality against itself: the audio waveform against a loudness target, the caption string against the spoken string, the brand wordmark against a fuzzy transcript. None of them answer the one question that actually defines a how-to video: at second `t`, does the screen show the thing the narrator just said it shows? This is the "support team is one tap away" defect: the narrator claims a support screen while the frame still holds the trade ticket, and it is the single highest-value gap in the stack because it is the failure a viewer notices instantly and a gate never sees. The reason it slips is structural, not a tuning miss. `generator/caption_qa.py:caption_speech_ok` proves caption-text equals ASR-of-audio (both are the same narration string, so any claim matches itself perfectly regardless of the picture), and `extractor/quality_gates.py:gate_callout_coverage` only fires off `brief.steps[].callout` tokens with an any-token-overlap rule (`if not (want & shown)`, set-intersection presence, verified at `extractor/quality_gates.py:226`) inside a +/-1s window. A free VO sentence about "support" is not a step callout, has no brief entry, and "support" is not an OCR-extractable token on a non-support screen, so nothing is evaluated. The synthesis stage (`extractor/pipeline.py:stage_synthesize`) does feed OCR, vision, and transcript to a model, but only to write the brief, never to gate a claim against the frame.

The 2026 research framing is direct: multimodal hallucination is cross-modal inconsistency between generated text and the visual content, and the established external-verification recipe is to decompose the text into atomic claims and validate each against the visual evidence with an auxiliary checker (object detector, scene graph, or an LLM judge). FaithSCAN states exactly this decomposition pattern and extends LLM-as-a-Judge to VQA via a Visual-NLI label, and NOAH benchmarks narrative-prior-driven hallucination and omission, the model describing what "should" be on screen instead of what is, which is the same prior that produces a confident-sounding wrong-screen VO line. The screen-identity half is now a solved-enough subproblem: ScreenSpot-Pro (GUI grounding from high-resolution screenshots, 1,581 expert-annotated tasks across 23 professional apps) puts frontier models at 0.86 to 0.88, well past the demo threshold for "what screen is this frame." The detector this band proposes is the marriage of the two: ground each VO claim's UI subject, classify the frame's screen identity, and judge agreement. It generalizes `gate_callout_coverage` from a brief-driven token-Jaccard heuristic into a semantic claim gate that needs no brief entry and no literal OCR token overlap.

| Capability (cross-modal semantic) | Repo status | Where it lives | What it catches / why it is short |
|---|---|---|---|
| Caption text == spoken text (text_match, drift) | have | `generator/caption_qa.py:caption_speech_ok` | Catches captions bound to the wrong VO and desync. Self-referential for claims: compares narration to itself, never to the screen. Also not in the default `ship_gate` fusion path (needs `caption_words`+`asr_words`). |
| Step-callout subject shown in OCR window | partial | `extractor/quality_gates.py:gate_callout_coverage` | Each `brief.step` callout's content tokens must appear in OCR within step +/-1s. Only brief steps, only any-token overlap, advisory; a free "support team" VO line is neither a callout nor an OCR token, so the wrong-screen defect is unguarded. |
| Static-scene during speech (Jaccard-stable OCR) | partial | `extractor/quality_gates.py:gate_static_scenes` | Catches a frozen screen while the VO keeps talking. Detects too-static, not wrong-screen; OCR-content based, advisory, 1 fps. |
| OCR-wordmark spelling correction at synth time | have (gen-side only) | `extractor/pipeline.py:stage_synthesize` | Uses on-screen OCR to fix brand spelling when writing the brief. Generation-side, gates nothing, never compares VO claim to shown screen. |
| Frame -> structured screen identity (which screen is this) | gap | (gap) | No vision-language pass that maps a frame to a screen-identity label (`login` / `trade_ticket` / `support` / `chart`). `extractor/visual_qa.py` flags layout defects only, not screen identity. |
| VO claim -> claimed UI subject (claim decomposition) | gap | (gap) | No step that extracts the claimed subject per VO sentence. `_content_tokens` + `_speech_windows` exist as raw material in `quality_gates.py`, but no claim extractor consumes them. |
| Claim <-> screen agreement judge (grounded: bool) | gap | (gap) | No `gpt-audio`/vision judge over (VO sentence, frame OCR, frame thumbnail). This is the wrong-support-screen defect's home and is entirely absent. |
| Semantic claim gate wired into `run_gates`/`ship_gate` | gap | (gap) | `gate_callout_coverage` is the closest hook point; no `gate_claim_grounding` exists alongside it. |

### Detector + auto-fix (owns the wrong-support-screen reviewer defect)

Add `gate_claim_grounding` next to `gate_callout_coverage` in `extractor/quality_gates.py:run_gates`. Build it in three stages, reusing what is already there:

1. Claim decomposition. Window the transcript into sentences from `transcript.json` word timings (reuse `_speech_windows`). For each sentence, extract the claimed UI subject. Start with a deterministic keyword map (`support|help|contact -> support`, `email|inbox|link -> email_sent`, `stop loss|take profit|SL|TP -> trade_ticket`, `password|login|sign in -> auth`) so the gate runs offline; escalate ambiguous sentences to an LLM extractor returning `{subject, claim_text}`. This is the brief-free generalization of `gate_callout_coverage`: no `brief.steps[]` entry required.

2. Frame screen-identity. For each VO window, take the frames inside it (the pipeline already samples at 1 fps and runs OCR + vision). Classify each frame to a screen-identity label with a ScreenSpot-class vision pass over (frame thumbnail, frame OCR), returning `{screen: <label>, evidence_tokens: [...]}`. Cache per frame so the judge cost is bounded.

3. Agreement judge. Run the sandwich-pattern judge over (claim_text, frame OCR, frame thumbnail) returning `{grounded: bool, shown_screen, reason}`, the Visual-NLI / claim-vs-evidence pattern from FaithSCAN. `grounded == false` when the claimed subject's screen is not the screen shown in that window. Promote to HARD once agreement with a human review set clears the 75 to 90 percent band that the voice doc sets for judge rubrics; ship as ADVISORY first to avoid the cried-wolf problem that already pushed `gate_brand` and `gate_static_scenes` to advisory.

Auto-fix is mechanical because the defect is almost always a mis-pinned beat, not a missing asset. The gate emits the failing window `(start_s, end_s)`, the `claimed_subject`, and the `shown_screen`. The repair searches the available screenshot/asset set (and other beats) for the frame whose screen-identity matches `claimed_subject`; if one exists, re-pin the beat to that screenshot (swap the source asset behind the time window and re-render the affected segment only). If no matching screen exists in the asset set, the claim is unsupported by any captured footage, so the fallback is to flag for an asset shoot rather than silently re-pin, and, where the claim is incidental, trigger a VO regen of that one sentence via `generator/narrate.py` to drop the unsupported reference. This mirrors the re-pin-then-regen escalation the repo already uses for pronunciation, but keyed on screen identity instead of phonetics.

***

## Reviewer Regression Cases (the 3 Amit defects)

Three reviewer-found defects shipped through a PASS verdict. Each is confirmed code-true against the current gates, each gets a detector, an auto-fix, and a permanent golden fixture so it cannot return.

### Case 1: wrong-support-screen (cross-modal claim)

What shipped: the narrator says "our support team is one tap away" while the frame at that moment still holds the trade ticket, not the support screen.

Why current gates miss it (verified): `gate_callout_coverage` (`extractor/quality_gates.py:210-232`) builds want-tokens from `s.get("callout","")` (line 218), the brief steps, not the VO content, and passes on set-intersection presence `if not (want & shown)` (line 226). A "support team is one tap away" line has no brief step entry and "support" is not an OCR token on a non-support screen, so nothing is evaluated; the gate is also `advisory: True` (line 232), so even a fired flag cannot block. The active caption gate in `ship_gate` is `generator/brand_qa.py:caption_coverage` (lines 40-49), which measures only timing-coverage fraction. `generator/caption_qa.py:align_captions_to_asr` compares narration to itself (SequenceMatcher over the same tokens) and is not wired into `ship_gate` (referenced only by `tests/test_caption_qa.py`). `extractor/visual_qa.py` flags layout defects only (collisions/clipping/low_contrast/off_safe, lines 24-31), no semantic truth. A repo-wide grep across ship_gate/video_qa/brand_qa/quality_gates/visual_qa for claim-vs-screen alignment returns nothing: no cross-modal claim-vs-screen alignment exists.

Detector to add: `gate_claim_grounding` (Layer 4): claim decomposition over `_speech_windows`, ScreenSpot-class frame screen-identity, FaithSCAN-style agreement judge returning `{grounded, shown_screen}`.

Auto-fix: re-pin the beat to the screenshot whose screen-identity matches the claimed subject, or swap the asset; if no such screen exists in the captured set, flag for a shoot and (for incidental claims) regen the one VO sentence.

Permanent golden test: freeze the broken render in the adversarial tier with the assertion that `gate_claim_grounding` FAILs on it. A version that starts passing means the gate regressed.

### Case 2: cough (non-speech disfluency)

What shipped: the narrator coughs several times in the VO; the coughs should be detected and removed.

Why current gates miss it (verified): a repo-wide grep over `extractor`, `generator`, and `scripts` returns zero matches for `cough|coughs|coughing|disfluency|filler` and zero for `breath`. `extractor/pipeline.py:187` sets `"tag_audio_events": "false"`, which disables the one ElevenLabs feature that could surface a cough. Even if events were tagged, `voice_analysis.py:32` and `quality_gates.py:173` both filter to `w.get("type")=="word"`, dropping any non-word event. `pause_stats` (`voice_analysis.py:48-61`) counts only inter-word gaps as silence, so a cough (energy, not silence) is invisible. `ai_feel` (`voice_analysis.py:217-246`) keys only on pitch f0_std, WPM, LRA, and consistency, so a clean-toned narrator who coughs scores `low` risk. No raw audio reaches a model; the LLM voice stage is fed the numeric feature dict plus the (tagless) transcript text.

Detector to add: `no_nonspeech_events` HARD gate (Layer 2): enable `tag_audio_events`, add the transcript-gap-with-energy pre-filter, and run `panns_inference` (CNN14 decision-level) or a `gpt-audio-1.5` non-speech judge to return timestamped cough/breath/throat-clear events.

Auto-fix: drive an ffmpeg edit-list off the timestamps. Micro-splice the span when the cough sits in a pause; regen the affected VO beat via `generator/narrate.py` when it overlaps a word. Re-pin beats so captions stay aligned, then re-gate.

Permanent golden test: freeze the coughing clip and its fixed cut as a paired adversarial fixture; the gate must FAIL on the original and PASS on the fixed cut.

### Case 3: seekpa (dropped-syllable brand pronunciation)

What shipped: at the end she says SEEKPA instead of SEEKAPA, a dropped middle syllable.

Why current gates miss it (verified): `brand_spoken_score` returns `difflib.SequenceMatcher(None,"seekapa","seekpa").ratio() == 0.9230769` (computed this session), well above `BRAND_SPOKEN_MIN=0.66` (`extractor/quality_gates.py:42`), so `gate_brand` (lines 107-124) returns `pass=True` with detail "on-screen brands {'seekapa': 0.92} matched in VO", and the gate is `advisory: True` (line 121) so it cannot block regardless. The manual scripts also miss it: `scripts/verify_ar_brand.py` is AR-only (`language_code="ara"`, line 37), manual CLI, points at `video-gen/remotion/public/ar/voice.mp3` not an EN reset-password VO, and its `GARBAGE` list (line 27) only catches the gross al-Kaaba collapse, not a dropped syllable. `scripts/verify_pronunciation.py` runs a hardcoded `PHRASE="Welcome to Seekapa..."` (line 27) through fresh TTS, never the shipped VO, and only substring-checks `seekapa`/`koppa`/`ckapa` (lines 55-58).

Detector to add: syllable/phoneme-exact brand gate (Layer 3): forced-align the brand window, build a g2p reference, score with PanPhon feature-weighted edit distance, and assert the spoken vowel-nucleus count equals three (see-KAH-pa). Promote from ADVISORY to HARD once it is per-video and no longer cries wolf.

Auto-fix: re-synthesize only the brand-window segment through `generator/narrate.py`'s pronunciation-dict locator (the see-KAH-pa alias already exists), splice it back, re-pin, re-gate.

Permanent golden test: freeze the SEEKPA render in the adversarial tier with the assertion that the syllable-exact gate FAILs; a regression to the 0.66-fuzzy behavior is then caught on the next CI run.

***

## The Self-Evaluate to Self-Fix Loop

The previous layers each emit a verdict. This layer closes the circuit: it turns a verdict into a permanent test and turns a failed gate into a generator action that repairs the defect without a human in the path. The repo already has the load-bearing half. `generator/ship_gate.py:ship_gate` re-runs the extractor on the rendered mp4 (`self_analyze` does split to STT to voice to OCR on the output, not the source) and fuses three previously-separate scorecards (`brand_qa` + `extractor.quality_gates` + `video_qa`) into one `merge_scorecard` verdict where `passed == all HARD checks ok`. That self-analysis-on-output design is the substrate a self-fix loop needs, because the grader is looking at what actually shipped. What is missing is the other half: a defect-to-action mapping that feeds a FAIL back into the generator, a tiered golden dataset of past-bug fixtures, and a CI strategy that runs the right gates at the right trigger. Golden-master and regression are the clearest gap in the current stack: the testing-pyramid taxonomy lists Golden Master (section 2.10) and Regression Suites (section 2.11) as the layers where mature systems stabilize, and the repo wires neither into the gate path.

The discipline is the one the testing-pyramid doc states in section 2.11 and restates as the SOTA mindset in section 7: every reviewer-found defect becomes a permanent test, and the voice doc's CI section (Layer 6) makes the corollary operational by feeding every failure back into the golden dataset on each run. The loop is two arrows. The forward arrow (self-fix) reads the failed gate name, looks up the repair surface, calls the generator, and re-renders until `ship_gate` returns PASS or a retry budget is exhausted. The backward arrow (regression capture) takes the defect the reviewer or the loop found, freezes the offending output as a fixture with the gate that should have caught it, and adds it to the golden set so the same defect can never ship twice. The three reviewer defects are the seed rows of that golden set.

```
                         +-----------------------------+
                         |  RENDER (Remotion -> mp4)   |
                         +--------------+--------------+
                                        |
                                        v
                  +-------------------------------------------+
                  |  SELF-ANALYZE on the OUTPUT mp4           |
                  |  split -> STT -> voice -> OCR -> vision   |
                  |  (generator/ship_gate.py:self_analyze)   |
                  +--------------------+----------------------+
                                       |
                                       v
                  +-------------------------------------------+
                  |  MERGE_SCORECARD: brand_qa + quality_gates|
                  |  + video_qa  ==> passed == all HARD ok   |
                  +-----------+-------------------+-----------+
                              |                   |
                       passed |                   | FAIL
                              v                   v
                       +-------------+   +-----------------------------+
                       |  SHIP       |   |  REPAIR_MAP[verdict.failed] |  <-- forward arrow
                       +-------------+   |  resynth / splice / re-pin  |
                                         |  / swap asset / renormalize |
                                         +--------------+--------------+
                                                        |
                                          tries < N, set must shrink
                                                        |
                                                        v
                                              re-render (back to top)
                              |
                  exhausted / set not shrinking  -->  HUMAN REVIEW
                                       |
                                       v  (backward arrow)
                  +-------------------------------------------+
                  |  FREEZE output + failed-gate name as a    |
                  |  must-FAIL fixture in the adversarial tier|
                  +-------------------------------------------+
```

The loop wrapper is small: `while not ship_gate(...).passed and tries < N: action = REPAIR_MAP[verdict.failed[0]]; action(); re-render`. Cap N (3 is enough for these defects), require monotone progress (the failed-gate set must shrink each iteration or the loop aborts to human review), and on abort write the output to the adversarial golden tier so the unfixable case is captured.

### Per-defect fix-surface table

| Failed gate | Auto-fix action | Generator surface | Repo status |
|---|---|---|---|
| `gates.gate_loudness` (program LUFS outside -16..-12) | Two-pass `loudnorm` re-normalize the mixed track, re-render | ffmpeg normalize step (recipe exists in mastering scripts) | partial: measured by `extractor/voice_analysis.py:ffmpeg_loudness`; no auto-renormalize wired (gap) |
| brand pronunciation FAIL (seekpa) | Re-synthesize the failing VO segment via the pronunciation-dict locator (see-KAH-pa alias present), splice back | `generator/narrate.py` pronunciation dict | partial: alias exists; segment-level resynth+splice not wired (gap) |
| non-speech event FAIL (cough) | Emit an ffmpeg edit-list cutting (start,end) of the event, or trigger VO regen of the affected segment | VO regen + ffmpeg splice | gap (gap) |
| claim-grounding FAIL (wrong-support-screen) | Re-pin the beat so the VO sentence aligns to the correct screen, or swap the asset to the screen the claim names | beat re-pin (`repin_beats`-class step) + asset swap | gap (gap) |
| `text.no_typos` / `text.no_english_leaks` | Patch the caption/screen string in props, re-render | props edit + re-render | partial: detected by `generator/video_qa.py:text_qa`; no auto-patch (gap) |
| `gates.gate_monotone` / `gate_ai_feel` | Regenerate VO with higher prosody variation (voice settings / audio tags), re-render | `generator/narrate.py` | partial: detected by `extractor/voice_analysis.py:pitch_profile`/`ai_feel`; no auto-regen (gap) |

### Tiered golden dataset for video

Mirror the voice doc's tiered split (Layer 4: 60% happy / 25% edge / 15% adversarial). For a screenshot how-to pipeline the tiers are concrete render scenarios, not synthetic audio. Build the suite as a directory of `(fixture.mp4, props.json, brief.json, expected.json)` rows, where `expected.json` is the frozen `merge_scorecard` output (the exact `failed` list and `passed` bool). A regression run is then deterministic: re-run `ship_gate` on each fixture and assert the verdict equals the frozen one. Pin the known-good renders with a per-frame VMAF/SSIM golden-master diff against the frozen baseline (Netflix `libvmaf` via `ffmpeg-quality-metrics`); a confirmed-good encoder-CI recipe uses per-rendition floors of `vmaf_avg >= 85, vmaf_min >= 65` at 720p with the per-frame JSON kept as a build artifact, so a two-second dip is visible even when the global average passes.

| Tier | Share | Contents (video how-to) | Gates exercised | Repo status |
|---|---|---|---|---|
| Happy paths | 60% | The shipped golden cuts: EN/AR sign-up, open-position, reset-password (all `ship_gate` PASS) | Full HARD set | partial: known-good renders exist as files, not wired as fixtures (gap) |
| Edge cases | 25% | RTL mirror (AR), English-UI screenshots under AR captions, long single-take VO, b-roll variant (palette floor 0.15) | `video_qa.text_qa` (arabic_ratio/english_leaks), `howto_consistency` (rtl_mirror), `brand_qa.palette_fidelity` | partial: gates exist, no fixture set (gap) |
| Adversarial | 15% | The three reviewer defects frozen as must-FAIL fixtures: wrong-support-screen, cough, seekpa, plus prior bugs (logo teleport, al-Kaaba outro) | claim-grounding, non-speech-event, syllable-exact brand (all to-build) | gap (gap) |

The adversarial tier is where the reviewer defects live, and it is the tier the repo lacks entirely. Each adversarial fixture is a deliberately broken render plus the assertion that a specific gate FAILs on it; a fixture that starts passing means the gate regressed.

***

## CI/CD Regression Gates

Adapted from the testing-pyramid CI section (5: on-commit lint/unit/property, on-PR component/contract/integration, nightly fuzz/mutation/perf, pre-release full regression + E2E) and the voice doc's concrete blocking thresholds (Layer 6: WER regression > 5% blocks, UTMOS drop > 0.2 blocks, P99 over threshold blocks, judge-score drop > 10% triggers human review). Renders are batch artifacts, so latency percentiles are n/a; the encode-conformance and per-frame VMAF gates take that slot.

| Trigger | What runs | Blocking threshold | Repo status |
|---|---|---|---|
| On commit (fast, no render) | Pure scorers + static parse: `merge_scorecard`/`_text_qa_checks` logic, `howto_consistency` tsx parse, `caption_qa` align logic | Any HARD pure-check FAIL blocks; `no_teleport`/`rtl_mirror` FAIL blocks | have: pure modules import-clean (`ship_gate.py:merge_scorecard`, `generator/howto_consistency.py`) |
| On PR (one render of changed cut) | Full `ship_gate` self-analyze on the rendered mp4 (brand + extractor gates + text QA) | `ship_gate.passed == False` blocks the merge; loudness outside -16..-12, palette < 0.55 (0.15 b-roll), caption_coverage < 0.80, av_sync < 1.0, monotone (F0 std < 2.0 st), ai_feel == high, visual major > 0, any baked typo | have for HARD gates (`generator/ship_gate.py:ship_gate`); claim-grounding + non-speech-event + syllable-exact brand are gap |
| Nightly (whole golden set) | Regression: re-run `ship_gate` on every golden fixture; per-frame VMAF/SSIM golden-master diff vs frozen baseline | Any fixture verdict != frozen `expected.json` blocks; VMAF dip below per-rendition floor (e.g. `vmaf_min < 65` at 720p) blocks; new defect auto-captured to adversarial tier | gap: no fixture suite, no VMAF diff wired (gap) |
| Pre-release (all cuts + cross-modal judges) | Full regression + cross-modal claim-grounding judge over every VO sentence vs frame OCR/thumbnail; brand STT round-trip on every cut | Any claim ungrounded == HARD FAIL; any non-speech event FAIL; brand not syllable-exact FAIL; judge-score drop > 10% vs last release triggers human review | gap (gap) |

The two adversarial-tier judges in the pre-release column should be a two-judge ensemble (GPT-class + Gemini-class) to cut single-model perception-bias, per the 2026 MLLM-as-judge literature, since these are the highest-stakes gates (brand sign-off and claim truth) and the failure mode is exactly the judge fabricating or missing visual grounding.

***

## Coverage Matrix

Status legend: have (gated and working), partial (exists but model-bound, advisory, unwired, or generation-side only), gap (absent from the gate path).

| Layer | Capability | Status | Where (file:symbol) |
|---|---|---|---|
| Visual | Palette / brand-color fidelity (ΔE76 on-brand fraction) | have | `generator/brand_qa.py:palette_fidelity` |
| Visual | OCR typo + English-leak + Arabic-ratio text QA | partial | `generator/video_qa.py:text_qa` |
| Visual | Per-frame layout-defect aggregation (model-bound) | partial | `extractor/visual_qa.py:aggregate_visual_qa` |
| Visual | Visual hard gate on major defects | partial | `extractor/quality_gates.py:gate_visual` |
| Visual | Frozen / static-scene detection (OCR-token Jaccard, advisory) | partial | `extractor/quality_gates.py:gate_static_scenes` |
| Visual | Logo-motion invariant (no-teleport / RTL-mirror, source parse) | have | `generator/howto_consistency.py:check_component` |
| Visual | Jitter / shake metric (exists, unwired) | partial | `video-gen/DEV-5011/scripts/jitter_metric.py` |
| Visual | VMAF reference video-quality metric | gap | (gap) |
| Visual | SSIM / MS-SSIM reference frame similarity | gap | (gap) |
| Visual | PSNR reference pixel-error metric | gap | (gap) |
| Visual | LPIPS learned perceptual frame distance | gap | (gap) |
| Visual | Golden-master frame snapshot diff (deterministic) | gap | (gap) |
| Visual | No-reference blur / sharpness (var-of-Laplacian / BRISQUE / NIQE) | gap | (gap) |
| Visual | Banding / compression-artifact metric | gap | (gap) |
| Visual | Deterministic per-region text-legibility / contrast metric | gap | (gap) |
| Visual | Frame-difference / scene-cut detection | gap | (gap) |
| Visual | Optical-flow / motion-smoothness in gate path | gap | (gap) |
| Visual | Transition-smoothness / easing metric (manual only) | gap | (gap) |
| Visual | On-screen wordmark glyph fidelity (golden-glyph SSIM/LPIPS) | gap | (gap) |
| Audio | Integrated loudness EBU R128 gate | have | `extractor/quality_gates.py:gate_loudness` (over `voice_analysis.py:ffmpeg_loudness`) |
| Audio | Loudness range (LRA) + true peak measurement | partial | `extractor/voice_analysis.py:ffmpeg_loudness` |
| Audio | Pacing WPM by language band | have | `extractor/voice_analysis.py:speaking_rate_wpm` + `WPM_BANDS` |
| Audio | Word-gap pause stats | have | `extractor/voice_analysis.py:pause_stats` |
| Audio | Per-segment energy drift / consistency | have | `extractor/voice_analysis.py:segment_loudness` + `consistency` |
| Audio | F0 monotone gate | have | `extractor/quality_gates.py:gate_monotone` (over `voice_analysis.py:pitch_profile`) |
| Audio | Dynamics / clipping (crest, flat, noise floor, peak clip) | partial | `extractor/voice_analysis.py:extract_dynamics` |
| Audio | AI-feel robotic-risk composite gate | have | `extractor/quality_gates.py:gate_ai_feel` (over `voice_analysis.py:ai_feel`) |
| Audio | Perceptual MOS (PESQ / ViSQOL / UTMOS) | gap | (gap) |
| Audio | gpt-audio-1.5 prosody/emotion semantic judge | gap | (gap) |
| Audio | Non-speech disfluency detector (cough/breath/throat-clear) | gap | (gap) |
| Audio | ElevenLabs STT non-speech event tags | gap | `extractor/pipeline.py:187` (`tag_audio_events="false"`) |
| Audio | Transcript-gap-with-energy disfluency heuristic | partial | `voice_analysis.py:pause_stats` + `extract_dynamics`/`segment_loudness` (halves exist, not joined) |
| Audio | `no_nonspeech_events` HARD gate in `run_gates()` | gap | (gap) |
| Audio | Auto-fix: locate cough timestamps, splice/regen, re-pin | gap | (gap), `narrate.py` per-beat VO + `repin_beats.py` exist but not wired to a detector |
| Audio | Audio golden-master / regression fixture for disfluency | gap | (gap) |
| Pronunciation | Grapheme-to-phoneme reference (g2p_en / espeak-ng) | gap | (gap) |
| Pronunciation | Expected-pronunciation lexicon (canonical + alias) | partial | `generator/narrate.py:PRON_RULE`, `PRON_DICT_NAME` "seekapa-alias" |
| Pronunciation | Per-phoneme forced-alignment timing (MFA / WhisperX / aeneas) | gap | (gap) |
| Pronunciation | Phonetic-distance / syllable-count check (PanPhon PFER) | gap | (gap) |
| Pronunciation | Fuzzy grapheme brand-in-VO proxy (lets SEEK-pa pass at 0.9231) | partial | `extractor/quality_gates.py:brand_spoken_score` / `gate_brand` (BRAND_SPOKEN_MIN=0.66) |
| Pronunciation | STT brand round-trip, gross-collapse catch (AR-only, manual) | partial | `scripts/verify_ar_brand.py:main` (GARBAGE list) |
| Pronunciation | STT brand round-trip, alias-changes-audio proof (fixed phrase) | partial | `scripts/verify_pronunciation.py:main` (hardcoded PHRASE) |
| Pronunciation | WER-on-proper-nouns metric | gap | (gap) |
| Pronunciation | Auto-fix: pin pronunciation + re-synth brand segment | partial | `generator/narrate.py:ensure_dict` / `_tts(locator=...)` |
| Pronunciation | Promote pronunciation check from advisory to hard | gap | (gap) |
| Cross-modal | Caption text == spoken text (text_match + drift) | have | `generator/caption_qa.py:caption_speech_ok` |
| Cross-modal | Caption-speech alignment scorer | have | `generator/caption_qa.py:align_captions_to_asr` |
| Cross-modal | Step-callout subject shown in OCR window | partial | `extractor/quality_gates.py:gate_callout_coverage` |
| Cross-modal | Static-scene-during-speech detection | partial | `extractor/quality_gates.py:gate_static_scenes` |
| Cross-modal | VO speech-window extraction (raw material) | have | `extractor/quality_gates.py:_speech_windows` |
| Cross-modal | Content-token / OCR-row extraction (raw material) | have | `extractor/quality_gates.py:_content_tokens` + `_ocr_rows` |
| Cross-modal | OCR-wordmark spelling correction at synth time (gen-side, no gate) | have | `extractor/pipeline.py:stage_synthesize` |
| Cross-modal | Frame -> structured screen-identity classification | gap | (gap) |
| Cross-modal | VO claim -> claimed UI subject (claim decomposition) | gap | (gap) |
| Cross-modal | Claim <-> screen agreement judge (grounded: bool) | gap | (gap) |
| Cross-modal | Semantic claim gate wired into run_gates / ship_gate | gap | (gap) |
| Cross-modal | Auto-fix: re-pin beat to matching screenshot or swap asset | gap | (gap) |
| Self-fix loop | Single output-aware scorecard where PASS == shippable | have | `generator/ship_gate.py:merge_scorecard` |
| Self-fix loop | Self-analysis on the rendered output (not source) | have | `generator/ship_gate.py:self_analyze` |
| Self-fix loop | HARD vs ADVISORY routing (advisories surfaced, never block) | have | `generator/ship_gate.py:merge_scorecard` / `_text_qa_checks` |
| Self-fix loop | HARD blocking gate set (loudness/palette/caption/av-sync/monotone/ai-feel/visual/typos) | have | `generator/ship_gate.py:ship_gate` (fuses brand_qa + quality_gates + video_qa) |
| Self-fix loop | Self-fix loop (failed gate -> repair -> re-render until PASS) | gap | (gap) |
| Self-fix loop | Tiered golden dataset (happy/edge/adversarial fixtures) | partial | known-good renders exist as files only, not wired as fixtures |
| Self-fix loop | Failure-to-golden capture (auto-freeze a FAIL) | gap | (gap) |
| Self-fix loop | Golden-master per-frame VMAF/SSIM diff vs baseline | gap | (gap) |
| Self-fix loop | Auto-fix: re-normalize loudness | partial | `extractor/voice_analysis.py:ffmpeg_loudness` (measured); auto-renormalize not wired |
| Self-fix loop | Auto-fix: re-synth brand-window VO via pron dict + splice | partial | `generator/narrate.py` (see-KAH-pa alias exists); resynth+splice not wired |
| Self-fix loop | Auto-fix: cut/regen non-speech event segment | gap | (gap) |
| Self-fix loop | Auto-fix: re-pin beat / swap asset for claim-grounding | gap | (gap) |
| Self-fix loop | Syllable/phoneme-exact brand gate (replaces 0.66 fuzzy) | gap | `extractor/quality_gates.py:gate_brand`/`brand_spoken_score` is the loose proxy (0.9231 > 0.66); exact gate not built |
| Self-fix loop | Cross-modal claim-grounding gate (VO claim vs frame OCR/thumbnail) | gap | (gap) |
| Self-fix loop | Non-speech-event detector (cough/breath/throat-clear) | gap | (gap); `extractor/pipeline.py` sets `tag_audio_events=false` |
| Self-fix loop | On-commit fast CI tier (pure scorers + static tsx parse) | have | `generator/ship_gate.py:merge_scorecard`, `generator/howto_consistency.py` |
| Self-fix loop | On-PR render + full ship_gate tier | have | `generator/ship_gate.py:ship_gate` |
| Self-fix loop | Nightly full-golden regression tier | gap | (gap) |
| Self-fix loop | Pre-release cross-modal judge ensemble tier | gap | (gap) |

***

## Recommended SOTA Stack (2026)

```
Visual signal:    ffmpeg libvmaf + ssim/psnr + torchmetrics LPIPS (full-reference, vs blessed render)
Visual no-ref:    var-of-Laplacian sharpness + pyiqa (BRISQUE/NIQE/CLIP-IQA) + ΔE76 palette (in-repo)
Motion/transition: inter-frame mean-abs delta + PySceneDetect cuts + cv2 Farneback optical flow
Audio signal:     EBU R128 loudnorm + F0 monotone + dynamics (in-repo voice_analysis)
Audio disfluency: PANNs CNN14 decision-level (offline) | gpt-audio-1.5 non-speech judge (SOTA)
Pronunciation:    g2p_en / espeak-ng reference + WhisperX/MFA forced align + PanPhon PFER
Cross-modal:      claim decomposition + ScreenSpot-class screen-identity + FaithSCAN agreement judge
Judge ensemble:   GPT-class + Gemini-class two-judge vote on the pre-release claim-grounding gate
Golden master:    per-frame VMAF/SSIM diff vs frozen baseline (vmaf_avg>=85, vmaf_min>=65 @720p)
Fused scorecard:  generator/ship_gate.py self_analyze + merge_scorecard (extend, do not replace)
CI tiers:         on-commit pure scorers | on-PR ship_gate render | nightly golden | pre-release judges
```

This stack extends the existing fused `ship_gate` scorecard rather than replacing it: the in-repo loudness, palette, monotone, text-QA, and consistency gates stay as the HARD spine, and the additions (reference frame metrics, disfluency detection, phoneme brand gate, cross-modal claim grounding, the golden-master fixture suite) fill the gaps the three reviewer defects exposed.

***

## References

1. Video Multimethod Assessment Fusion (VMAF). https://en.wikipedia.org/wiki/Video_Multimethod_Assessment_Fusion
2. Netflix/vmaf (libvmaf reference implementation). https://github.com/Netflix/vmaf
3. richzhang/PerceptualSimilarity (LPIPS, `pip install lpips`). https://github.com/richzhang/PerceptualSimilarity
4. Learned Perceptual Image Patch Similarity (LPIPS), TorchMetrics. https://torchmetrics.readthedocs.io/en/v0.8.0/image/learned_perceptual_image_patch_similarity.html
5. Blur detection with OpenCV (variance of Laplacian), PyImageSearch. https://pyimagesearch.com/2015/09/07/blur-detection-with-opencv/
6. The No-Reference Avenger: BRISQUE, NIQE and CLIP-IQA (pyiqa). https://dataworlds.substack.com/p/the-no-reference-avenger-battling
7. FaithSCAN: Model-Driven Single-Pass Hallucination Detection for Faithful Visual Question Answering (arXiv 2601.00269). https://arxiv.org/html/2601.00269v1
8. NOAH: Benchmarking Narrative Prior driven Hallucination and Omission in Video Large Language Models (arXiv 2511.06475). https://arxiv.org/pdf/2511.06475
9. ScreenSpot-Pro: GUI Grounding for Professional High-Resolution Computer Use (benchmark + leaderboard). https://llm-stats.com/benchmarks/screenspot-pro
10. ScreenSpot-Pro Benchmark Overview (EmergentMind). https://www.emergentmind.com/topics/screenspot-pro-benchmark
11. A vision-language approach for foundational UI understanding (Google Research). https://research.google/blog/a-vision-language-approach-for-foundational-ui-understanding/
12. Multimodal LLM Hallucination Survey 2025 (Libertify), cross-modal inconsistency framing. https://www.libertify.com/interactive-library/multimodal-llm-hallucination-survey/
13. LLM-as-a-Judge sandwich-pattern + groundedness rubric (Langfuse). https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge
14. PANNs: Large-Scale Pretrained Audio Neural Networks for Audio Pattern Recognition (arXiv 1912.10211). https://arxiv.org/pdf/1912.10211
15. audioset_tagging_cnn (qiuqiangkong) + `panns_inference`. https://github.com/qiuqiangkong/audioset_tagging_cnn
16. BEATs: Audio Pre-Training with Acoustic Tokenizers (arXiv 2212.09058, ICML 2023). https://arxiv.org/abs/2212.09058
17. AST: Audio Spectrogram Transformer (GitHub, Interspeech 2021). https://github.com/YuanGongND/ast
18. Audio Spectrogram Transformer model card (Hugging Face Transformers). https://huggingface.co/docs/transformers/model_doc/audio-spectrogram-transformer
19. Hybrid deep learning and YAMNet features for asthma diagnosis from respiratory sounds (Scientific Reports). https://www.nature.com/articles/s41598-026-49247-y
20. gpt-audio Model (OpenAI API docs). https://developers.openai.com/api/docs/models/gpt-audio
21. Introducing gpt-realtime and Realtime API updates (OpenAI). https://openai.com/index/introducing-gpt-realtime/
22. SCENEBench: An Audio Understanding Benchmark Grounded in Assistive and Industrial Use Cases (arXiv 2603.09853). https://arxiv.org/abs/2603.09853
23. Montreal Forced Aligner, G2P models (3.X docs). https://montreal-forced-aligner.readthedocs.io/en/latest/reference/g2p_modeling/index.html
24. WhisperX (m-bain/whisperX). https://github.com/m-bain/whisperX
25. g2p_en (Kyubyong/g2p). https://github.com/Kyubyong/g2p
26. PanPhon (dmort27/panphon), feature-weighted phoneme edit distance. https://github.com/dmort27/panphon
27. Transparent pronunciation scoring using articulatorily weighted phoneme edit distance (arXiv 1905.02639). https://arxiv.org/pdf/1905.02639
28. aeneas (readbeyond/aeneas) forced aligner. https://github.com/readbeyond/aeneas
29. Voice Agent Evaluation Metrics (Hamming), WER-on-proper-nouns. https://hamming.ai/resources/voice-agent-evaluation-metrics-guide
30. Wiring VMAF (and PSNR) into your encoder CI with FFmpeg 8.1 and ffmpeg-quality-metrics. https://dev.to/masonwritescode/wiring-vmaf-and-psnr-into-your-encoder-ci-with-ffmpeg-81-and-ffmpeg-quality-metrics-1g6i
31. Automate Your CI Fixes: Self-Healing Pipelines with AI Agents (Dagger). https://dagger.io/blog/automate-your-ci-fixes-self-healing-pipelines-with-ai-agents/
32. MLLM-as-a-Judge: Assessing Multimodal LLM-as-a-Judge with Vision-Language Benchmark (arXiv 2402.04788). https://arxiv.org/pdf/2402.04788
33. Mitigating Perceptual Judgment Bias in Multimodal LLM-as-a-Judge via Perceptual Perturbation and Reward Modeling (arXiv 2606.02578). https://arxiv.org/html/2606.02578
34. SOTA Voice Testing Pipeline 2026 (companion doc): Layer 1 signal metrics, Layer 2 gpt-audio-1.5 judge, Layer 4 tiered dataset, Layer 6 CI gates. file:///home/shovalbe/docs/SOTA%20Voice%20Testing%20Pipeline%202026.md
35. testing_practices.txt (companion doc): sections 2.10 golden master, 2.11 regression, 5 CI strategy, 7 SOTA mindset. file:///home/shovalbe/docs/testing_practices.txt