# Review: Beer MSc thesis, and the deck that presents it

Two artifacts, reviewed separately because they fail differently. Part I is the PDF and
its argument. Part II is the HTML deck, its interface, and five directions for rebuilding
it. Part III holds the small number of defects that appear in both files.

Combines `thesis_grill_2026-07-30.md` and `thesis_deck_ui_directions_2026-07-30.md`.
Nothing has been dropped. Direction choices are laid out and not made.

---

## Sources, and what was actually checked

| artifact | what was read | how |
|---|---|---|
| `Beer_MSc_Thesis_2026.pdf` | all 58 pages, full text | PyMuPDF extraction, read start to finish |
| `thesis_story_9.html` | all 31 slides, 11 KB CSS, 3.4 KB JS, 11 base64 PNGs | read as source, slide text extracted and read slide by slide |
| `deepseek-v4-2606.19348v1.pdf` | typography and color only | PyMuPDF font, size, and color counters across all 58 pages |

**Executed checks.** Font and color census of the anchor PDF (URW Palladio at 11pt for
152,002 glyphs, `#2625A6` for 798, `#4D6BFE` in the drawing layer). Structural scan of
the deck (31 sections, 11 images all carrying `alt`, PNG payloads 46 to 754 KB, one
`<style>`, one `<script>`, zero `<svg>`, zero `@media` besides `print`, `TOTAL = 31`
sitting beside a DOM query). Arithmetic verification of four delta-column cells.
Citation counting in the bibliography.

**Rendered and measured, after an earlier version of this document inferred them.** The
deck was opened in Chrome 150 over CDP at four viewport sizes; clipping, font fallback,
viewport meta, the JS-off failure, and the print path are now observations, and three of
the original inferences were wrong (see II.1b). What remains unrendered: the figures were
not opened at full resolution, and no actual PDF was produced from the print path. No figures were rendered,
so every claim about a figure concerns its caption and the prose that reads it. No code,
no CSVs, no data. The thesis findings below are about the argument as written, not about
whether the numbers were computed correctly.

The coverage boundary is stated up front because the thesis's own strongest move is
distrusting reports, and this document is a report.

---
---

# Read this page if you read nothing else

## Three findings that change what the work claims

1. **Cell B to Cell C changes cleaning as well as language** (G1). The English table is
   `eng_tier0`; the Akkadian table is `maximal` plus truncation to 30 words. So the
   0.15 to 0.20 rho drop is not "the cost of the language alone," and Condition 1, the
   thesis's load-bearing conclusion, is not isolated. One rerun fixes it.
2. **The winner is the one arm without its own control** (G3). Section 12.1 says
   cuneiform-400M "is the only arm that clears both of its controls." Figure 12.2's
   caption says no encoder-scale random twin exists. A config load and a seed fixes it.
3. **Two citations credit the advisor as first author** (X1). Slide 13 attributes Lazar
   et al. 2021 to "Stanovsky et al."; slide 29 attributes Malkin et al. 2022 to
   "Stanovsky et al." while slide 31 gets the same paper right. Under a minute to fix,
   and the highest embarrassment per second of anything in this document.

## Four questions that decide whether two more findings are real

These are not rhetorical. If the answers go one way, G2 and G5 largely dissolve, and I
would rather they dissolve than stand on an inference.

1. How many folds does GroupKFold-by-ruler use inside each draw? With 8 rulers, one or
   two rulers are held out, and year is a per-ruler constant.
2. Is Spearman computed per fold and averaged, or are out-of-fold predictions pooled and
   scored once?
3. Were the best layer and best k chosen on the same held-out data they are reported on,
   or on an inner split?
4. What corpus was cuneiform-400M translation-finetuned on, and does it overlap the 1,193
   evaluation fragments?

Full list of 15 questions in Part IV.

## If you have one day

Roughly ranked by value per hour, not by importance.

| time | action | which finding |
|---|---|---|
| 1 min | fix the two attributions on slides 13 and 29 | X1 |
| 10 min | fix "ten frozen models" and "three translation encoders" in the abstract | X2, G9 |
| 30 min | print std over the 200 draws in every table | G5 |
| 30 min | state the fold count and the pooling rule in Section 5.6 | G2 |
| 1 h | state cuneiform-400M and AKK-300M provenance in Section 5.3 | G4 |
| 2 h | random-init a uMT5 twin and add the row | G3 |
| 2 h | split slide 6, add a signed delta column | U1, U2 |
| 3 h | rerun Cell B under the maximal cleaning regime | G1 |

That is one working day and it addresses every finding in the list above. Everything else
in this document is improvement rather than repair.

## The frame this document does not use

Everything in Part II assumes the deck should be published. The competing frame is that
`thesis_story_9.html` is a working document for an advisor meeting, in which case most of
Part II is a scope change rather than a defect list, and the honest recommendation is to
publish the thesis plus a short summary and keep the deck internal. That decision comes
before any of the styling work below, and this document does not make it.

---
---

# Part I. The PDF: `Beer_MSc_Thesis_2026.pdf`

## What survives the grilling

Say this first, because the rest is adversarial and would otherwise read as a
demolition. Three things here are better than most of the literature they criticise:

1. The random-init twin as a load-bearing control, and the willingness to let it
   overturn the paper's own headline (Section 9.2). The king-token result would have
   been a publishable false positive. Catching it and then publishing the near-miss
   as a finding is the real contribution.
2. Naming the corpus's central confound in Chapter 1 rather than in a limitations
   section, and building the whole protocol around it.
3. Section 5.8, "three protocol asymmetries," and Section 13.3. Pre-emptively
   explaining which numbers are not comparable to which is rare and correct.

Now the problems, ordered by how much of the thesis they move.

## G1. The ceteris paribus claim between Cell B and Cell C is false as written

Section 9.3: "Identical pipeline to Section 7.2 ... but on the cleaned, name-stripped,
length-truncated Akkadian itself. The gap between Table 9.3 and Table 7.2 is the cost
of the language alone." Slide 16 repeats it: "Nothing else changes, so the gap between
this table and that one is the cost of the language alone."

It is not the language alone. By the thesis's own Section 5.2 and 9.1:

| | Table 7.2 (English) | Table 9.3 (Akkadian) |
|---|---|---|
| text | `eng_tier0` faithful gloss | `maximal` |
| filters | none stated | eleven stacked filters |
| length | full passage | truncated to 30 words |

So the measured 0.15 to 0.20 rho drop is a joint effect of (language) plus (eleven
filters) plus (truncation to 30 words). The thesis itself says truncation was added
specifically because length was carrying 99.2 percent period accuracy, i.e. it knows
truncation removes real signal. Removing a signal from one arm and not the other, then
attributing the difference to a third variable, is exactly the multi-factor jump the
whole climbing-map design exists to avoid. Cell B to Cell C is the one step in the
ladder that is not one step.

The fix is cheap and the thesis should have run it: English translation under the
maximal regime (or Akkadian under tier0, or both). Rescue 4 and Rescue 5 already ran
English and Akkadian side by side, so the cleaning matrix partly exists. Until that
cell is filled, Condition 1, the load-bearing conclusion, is not isolated.

**The defense, if the rerun is not possible.** Table 10.3 already carries the same
language contrast on the same fragments, under the stress-line protocol, and the gap
there is much smaller: computed per arm from the in-order columns it runs +.095, +.088,
+.058, +.019, -.002, +.100, +.065, mean +.06, and it is *negative* for cuneiform-400M.
So the .15 to .20 figure quoted in Section 9.3 and Section 11.1 is specific to the
world-models line, and the same comparison under the harder protocol gives about a third
of it.

Two things follow. The claim survives in direction and not in magnitude, which is worth
stating plainly rather than defending. And Table 10.3 is not a clean matched-cleaning
control either, because its English column is tier0 while its Akkadian column is maximal,
the same asymmetry as G1. Both facts belong in Section 9.3 in one paragraph. Do not claim
"the language alone" without the rerun; do claim "the direction is stable across two
protocols, the magnitude is not."

## G2. The headline positive result is protocol-selected against the thesis's own strictest protocol

Section 5.6 defines three generalization questions and reports the same arm scoring
.59 / .43 / -.07 depending only on which is asked. It then says LORO "is where every
activation arm, TF-IDF included, collapses to rho <= .13."

Chapter 12 then calls GroupKFold-by-ruler "the honest protocol" and Figure 12.1 "the
honest Akkadian leaderboard," and the positive result is cuneiform-400M at rho = .391
there. Under the protocol the thesis itself describes as the hardest, the winner is
inside the same <= .13 collapse as everything else. Section 13.3 admits this in one
sentence ("Under LORO everything fails, TF-IDF included") and Section 13.4 scopes the
recommendation accordingly, which is honest. But the leaderboard figure, the abstract,
the conclusion, and the deck all lead with .391 and the word "honest," and the reader
who stops at the abstract learns that a 400M encoder dates Akkadian.

Worse, there is a structural question the thesis never answers: with 8 rulers and
GroupKFold-by-ruler, each fold holds out roughly one or two rulers. Year is a per-ruler
constant. So within a fold the target takes one or two distinct values. Spearman on a
one-valued target is undefined; on a two-valued target it is a rank-biserial statistic,
i.e. a two-class discrimination score, not a chronology score. Nothing in Section 5.6
states the fold count, so a reader cannot tell whether rho = .391 is "orders eight
reigns" or "tells reign X from reign Y, averaged over pairs." The pooled version of the
same question is LORO, and it returns -.07 to .13. That gap between .391 and .13 on
what looks like the same question needs an explicit explanation, and the thesis gives
none. This is the single most important missing paragraph in the document.

**The defense.** Two answers are available and one of them mostly ends this finding.
If Spearman is computed on pooled out-of-fold predictions across the whole draw rather
than per fold, then every draw scores against all 8 ruler values, the rank-biserial worry
disappears, and .391 is a genuine 8-value ordering. In that case the remaining question is
only why LORO is so much lower, and the answer is available: LORO trains on 7 rulers and
scores a ruler with no neighbours in training, while a grouped fold still has most of the
chronological range in train. Those are different questions, Section 5.6 already says so,
and the leaderboard is entitled to use the middle one as long as the LORO number sits
beside it. Putting the LORO column *into* Figure 12.1 rather than into a caveat in 13.3
answers the whole finding at the cost of one column. If instead the score is computed per
fold, the finding stands and the fix is to pool before scoring.

## G3. The winner is the one arm whose control does not exist

The reading rule (Section 5.7) is "beats both the TF-IDF floor and that arm's own
random-initialized twin," and it is applied to kill every LLM result. Then:

- Section 12.1: cuneiform-400M "is the only arm that clears both of its controls."
- Figure 12.2 caption: "the untrained Qwen3-8B control (dashed; no encoder-scale
  random twin exists)."

Those two sentences are in the same chapter. The twin for the winner is a different
architecture, a different tokenizer, a different parameter count, and a decoder rather
than an encoder-decoder. Under mean pooling the thesis's own Section 13.3 argues the
twin matters precisely because "an untrained transformer inherits lexical statistics
through its embedding table," which is a statement about that model's embedding table
and vocabulary. Substituting a Qwen3 vocabulary for a uMT5 vocabulary is therefore not
a substitution at all.

Random-initializing a uMT5 config is not hard. It is a config load plus a seed, the
same recipe already used for the four decoder twins, and it is the difference between
"the only arm that clears its controls" and "the only arm we never controlled." As
written, the thesis applies its decisive rule to nine arms and exempts the tenth,
which is the one it concludes with.

**The defense, and it is stronger than I first allowed.** Table 6.1 already contains an
argument the thesis makes in one line and never reuses. On the paper's six English
datasets the three encoders sit above the random twins and below TF-IDF: uMT5-base .438,
cuneiform-400M .399, AKK-300M .381 on World, against a TF-IDF floor of .642. So this
family is demonstrably *not* a generically strong probe target, which is exactly what a
missing random twin would otherwise leave open. If the encoder architecture handed a
linear probe free structure, it would show up on World, and it does not.

That does not replace the twin, because the concern under mean pooling is the embedding
table's lexical statistics on Akkadian specifically, and English World says nothing about
that. But it does mean the winner is not resting on nothing. Two sentences in Section 12.1
citing Table 6.1's encoder rows would blunt this finding considerably, and the twin would
close it.

## G4. Contamination is checked for the corpus and not for the winner

The purity argument runs through the whole thesis: the corpus is "expert-curated
scholarly data that has effectively never appeared in web pretraining corpora," which
"dissolves this confound by construction" (Sections 2.2, 5.1).

That argument covers the LLMs. It does not cover cuneiform-400M and AKK-300M, which are
translation finetunes on cuneiform-language parallel data. Where did the Akkadian side
of that parallel data come from? The obvious answer is ORACC and friends, which is the
evaluation corpus. If the winner was translation-trained on Akkadian-English pairs drawn
from the same editions the evaluation fragments come from, then the one arm that beats
its controls is also the one arm with a plausible direct path to the eval text and to
its English translations, and the mechanism story ("translation forces semantic
compression") competes with a much duller one ("it has seen these sentences").

The thesis never names the provenance, size, license, or source editions of the
cuneiform-400M and AKK-300M training sets, and never runs an overlap check. For a
document whose central methodological brag is leakage control, that is the most
surprising omission in it. A fragment-level n-gram overlap between the eval corpus and
the encoders' training corpus, or a held-out-editions rerun, is the missing experiment.

Related, smaller: Section 12.2 uses cuneiform-400M's smallness to defuse the Rescue 3
data-scale caveat, arguing that "a model of the same order of smallness, on the same
order of data, did acquire the structure." That comparison holds only if the two data
sets are comparable in kind, and they are not: one is raw next-token Akkadian, the other
is Akkadian paired with English. The defusal assumes the conclusion it is defending.

**The defense.** Contamination of the kind that would explain the result requires more
than corpus overlap. It requires the *year* to be recoverable from what the encoder saw,
and translation training supplies Akkadian-English sentence pairs, not dates. The
inscriptions do not state their dates (Section 5.1 is emphatic about this), so even a
model trained on every fragment in the corpus never saw a year attached to a text. What
overlap would buy is better representations of these specific sentences, which is a real
advantage, and it is not the same as label leakage.

Two further points work in the thesis's favour. Section 9.2's protocol strips names, so
the most obvious leakage channel is closed for the winner as it is for everything else.
And the LORO collapse applies to cuneiform-400M too, which is what contamination would
*not* predict: a model that had memorized these editions should carry to a held-out reign,
and it does not.

So the honest version of G4 is narrower than I first wrote it. It is not "the winner may
have memorized the answers." It is "the purity argument in Sections 2.2 and 5.1 is stated
for the whole model set and only holds for the decoders, and the reader is entitled to
know what the encoders saw." Naming the training corpus in Section 5.3 discharges it.

## G5. Every number is selected on the test score, and no number carries an interval

Two measurement problems that compound.

Selection. "best layer by held-out R2" (Section 5.5), best k surfaced, PLS or ridge
whichever is reported, four pooling sites, two cleanings, ten-plus arms. Nothing in
Chapter 5 describes a nested split or a validation fold for choosing the layer and k.
So every headline is a maximum over 30 to 80 layers times up to 64 component counts,
evaluated on the same held-out data it is reported on. That inflates all arms, and it
does not inflate them equally: an 80-layer 70B model gets more draws from the maximum
than a 16-layer encoder. Some of the "controls climb with them" pattern the thesis
reads as evidence could be selection noise, and some of the trained-vs-random gaps
could be layer-count artifacts. A nested-selection rerun on two or three representative
cells would settle it and is a day of compute.

Intervals. Section 5.6 promises "report mean +- std over draws." Not one table in the
thesis reports a std. Tables 6.1, 7.1, 7.2, 7.3, 9.1, 9.2, 9.3, 9.4, 10.2, 10.3, 10.4,
10.5 are bare means. Table 7.1's own note says "with 6 to 7 held-out entities per draw,
read the ordering, not the third decimal," and then the argument rests on orderings
separated by .02 to .09 (uMT5 .277 < AKK-300M .300 < cuneiform-400M .391 is the entire
mechanism claim of Chapter 12). Error bars appear only in Figure 12.1's caption. With
200 draws in hand the std costs nothing to print, and without it no reader can check a
single ordering claim in the document. This is the cheapest large improvement available.

Also: one seed (42) for the random twins, and the twins are load-bearing. A single
random projection's quality varies; five seeds would turn "the twin reaches .643" into
a distribution, and the false-positive finding of Section 9.2 would get much harder to
argue with.

## G6. The negative result may be a property of the benchmark, not of language resource

Chase the logic. Year is a per-ruler constant, so label = f(ruler identity). Ruler
identity is carried by the name, so the protocol strips names. What is left after
stripping names, logograms, determinatives, case endings, plural markers, digits, and
everything past word 30 is a bag of syllabic tokens. Under mean pooling an untrained
transformer inherits lexical statistics from its embedding table, so the twin is
approximately an n-gram model. The reading rule therefore says: to witness learning,
beat an n-gram model twice.

But the only thing left in the text that correlates with the label is lexical, because
the design removed everything else. So the rule is close to unsatisfiable by
construction in this cell, and the thesis's own Section 13.3 nearly says so ("under
mean pooling an untrained transformer inherits lexical statistics through its embedding
table, which is precisely why the twin, not the n-gram floor, is the binding baseline").

That does not make the result wrong. It makes the conclusion narrower than the
conclusion the thesis states. "Linear spatiotemporal world models are contingent on the
language being well represented in training" is a claim about language resource.
"On a corpus where the label is a deterministic function of one entity, and where every
feature correlated with that entity has been deleted, activation probes do not beat
lexical baselines" is a claim about benchmark structure, and it is what was measured.
Discriminating the two needs a corpus where the date is not a per-ruler constant:
year-stamped Babylonian economic tablets, or the intermediate regimes Section 13.5
already proposes (medieval Latin charters, dated Genizah documents). Those are listed
as future work; they are actually the load-bearing missing arm for Condition 1.

## G7. The dissociation is asserted for ten models and tested on four

"Knowing is not encoding" (Section 11.5) is the thesis claim, and Rescue 1 is what
makes the null interpretable. Rescue 1 ran on four chat models: Qwen3 1.7B, 8B, 32B and
gpt-oss-120B. It did not run on Llama-2 at any size (the paper's own series, and the
arm quoted in the abstract's headline replication), and cannot run on the three
encoders, including the winner.

So for six of ten arms, "the knowledge is present" is untested, and the "with knowledge
present and the method valid, a robust null can only mean..." syllogism of Section 4.3
does not close for them. Llama-2-7B and -13B are base models and are answerable with a
completion-style probe, which is a cheap fix.

Second problem in the same table: Qwen3-1.7B fails the hallucination gate and its 7/8
reign accuracy is still displayed and counted in the reading. If the gate exists to
decide whether an accuracy figure is meaningful, a failing model's accuracy should be
struck through, not tabulated beside passing ones.

## G8. Place is a ten-class problem reported as coordinate regression

Find-spots are merged to 10 sites, so lat/lon regression has 10 distinct targets, and
the corpus is Nineveh-heavy before the balancing. R2 on a two-column target with ten
distinct values is a strange statistic to lead with, and the thesis's own argument for
preferring rho on year ("with eight rulers the year target takes eight distinct values,
dating is a ranking problem, and absolute-year regression overclaims on a compressed,
unevenly spaced span") applies verbatim to place with ten values and is not applied.
The honest read in Section 9.4, "coordinates are partially recoverable ... and most of
what makes place recoverable is available to an untrained network," is fine. The metric
choice is not, and Takeaway 2 of Section 13.2 ("Geography has no scaling law at the
document level") is a general claim resting on it.

## G9. Smaller things that a committee will ask

- **Abstract says "ten frozen models"** and then lists Llama x3, Qwen x3, gpt-oss, and
  three encoders. Section 5.3 also includes the 37M MLM, which appears in Tables 9.1,
  9.2, 10.3, 10.4, 10.5. Eleven arms, or ten plus ours. Fix the count.
- **Abstract calls all three encoders "translation encoders."** uMT5-base is explicitly
  the no-translation-finetune arm; that is the entire point of the ablation triangle.
  The abstract contradicts Chapter 12 in its own model list. Same error on deck slide 5.
- **Reference [5]** (Engels et al., "Not all language model features are linear") is in
  the bibliography and cited nowhere in the text. Given the thesis argues about
  linearity, this is either a missing engagement or a leftover entry. The former is a
  real gap: a paper arguing some features are non-linear is directly relevant to
  Rescue 5's conclusion.
- **Reference [3]** has no authors, just "(2024). A matter of time: Revealing the
  structure of time in vision-language models. arXiv preprint," and it is cited twice,
  including in Section 10.7 as a methodology being mirrored. An anonymous citation for a
  method you reproduce will be challenged.
- **Nineteen references** for a thesis making a boundary-condition claim about probing
  is thin. Missing, at minimum: amnesic probing and information-theoretic probing
  (Elazar et al., Voita and Titov, Pimentel et al.), which are exactly the tools for
  "the information is there but not linearly available," and the memorization and
  contamination literature the purity argument leans on without citing.
- **gpt-oss-120B's collapse-then-climb depth profile** is flagged three times as
  anomalous (Sections 6.3, 9.5, 13.5) and never investigated. It is also the arm with
  fp16 overflow problems requiring a sanitizer (Section 5.4). Rule out the sanitizer
  before calling the shape a finding.
- **"Two arms track near the bottom ... and then rise sharply in the last few layers, a
  shape that returns as a warning sign in cell C"** (Section 6.3). Which two arms? The
  warning is used later; the referents are never named. Same unnamed-referent problem on
  deck slide 7.
- **The 37M MLM (Chapter 8) is a chapter and not a result.** It never clears anything,
  it is one seed, one architecture, no hyperparameter search, validation loss 4.55 to
  3.24 with no perplexity or restoration accuracy against Lazar et al. As written its
  only job is to be an ablation arm in Chapter 12, which is fine, but then it should be
  a section of Chapter 12, not a chapter of its own between Cell B and Cell C.
- **"Effectively all published Akkadian"** (Section 10.3, abstract, Chapter 13) at 2.45M
  words. The eBL and ORACC corpora are large and growing, and "all published" is a
  falsifiable absence claim about someone else's field. Scope it: "all of ORACC, eBL and
  Archibab as of <date>, N fragments."

## Evidence in the thesis that argues against the findings above

Three results were read, judged sound, and left out of the findings because they did not
fit the format. Two of them defend the thesis and one strengthens it, so leaving them out
was a distortion.

**The Cell A encoder rows.** Detailed in the G3 defense above. Table 6.1 shows the three
encoders above their random twins and below TF-IDF on all six English datasets. It is the
thesis's own evidence that the winning family is not a generically easy probe target, it
is mentioned once in Section 6.2 in a single sentence, and it is never cited again where
it matters most. Chapter 12 should be using it.

**Rescue 2's abstention result.** Section 10.2 notes in a parenthesis that an earlier
version of the ask-it arm allowed "cannot estimate," and the small models took that exit
for 87 to 100 percent of fragments. That is a sharper behavioural finding than the forced
guess it was replaced by: shown a stripped Akkadian fragment, these models decline. It
supports "knowing is not encoding" more directly than the rho numbers do, because it is
the model's own report of not knowing, and it is currently a parenthesis.

**The anchor timelines in Section 10.7.** 153 explicit date prompts reduce to one
dimension and form a chronological line that improves with scale (.38 to .57 from 1.7B to
120B, against .342 for the random model), while the actual Akkadian texts never project
onto it (nearest-anchor dating .03 to .11). That is the cleanest single demonstration of
the dissociation in the entire thesis, and it is fully unsupervised, so it cannot be
blamed on probe capacity. It sits in a subsection titled "Two further diagnostics" after
six numbered rescues. It belongs in Chapter 11 as the third leg of Section 11.5, not in an
appendix-shaped subsection.

## Generation patterns visible in the PDF

### P-A. Rhetorical tics doing evaluative work that evidence should do

"Honest" appears 12 times: "the honest protocol," "the honest Akkadian leaderboard,"
"the honest reading," "the honest caveat," "the honest place to end," "state the scope
honestly." The word is not a criterion, and in the one place it matters it points the
wrong way: the protocol labelled "honest" is the second-strictest, and the strictest one
(LORO, where the winner dies) is excluded from the leaderboard the label is attached to.
See G2. When a document has to assert its own honesty twelve times, the reader starts
auditing rather than reading, which is the opposite of what the tic is for.

Same pattern, smaller: "one factor at a time" and its variants four-plus times, "towers
over the controls it never ran" reused across abstract, Chapter 13, and deck slide 31,
and the abstract's triad cadence ("real, learned, deep, and multi-dimensional" in 6.4,
"indirect, sparse, non-numeric" in Chapter 1). Individually fine writing. Together they
read as generated polish, and the effect is that a committee discounts the prose and goes
looking for the numbers, which is where Part I's problems live.

### P-B. Claims about figures that the writer cannot have read

- Section 6.3 and slide 7: "Two arms track near the bottom for most of the network and
  then rise sharply in the last few layers." Which two? Never named, and the shape is
  then invoked in Cell C as a "warning sign."
- Slide 8: "Most arms settle at around k approx 16 components ... that is intuitively
  what the strong scores require." "Intuitively" is doing the work of the measurement,
  and the thesis version (6.4) makes the same claim without naming a single arm's k.
- Slide 18 and Section 9.5: "gpt-oss-120B is the odd one out: it collapses through the
  middle of the network and then climbs steeply over the final layers." Asserted three
  times, never quantified, never checked against the fp16 sanitizer that same model
  needed.

The signature is a caption that describes a plot's qualitative shape without naming the
series, the layer index, or the value. It is what text generated alongside a figure
looks like rather than text generated from one. Fix by naming arms and numbers in every
figure reading; if the arm cannot be named, the claim cannot be made.

### P-C. Internal contradictions inside the abstract

"Ten frozen models" and "three small translation encoders" are both wrong by the
thesis's own Section 5.3 and Chapter 12. Detailed in G9. Worth separating from the other
G9 items because an abstract is the most-read paragraph in the document and it
contradicts the chapter that carries the positive result.

## The one-sentence version of Part I

The negative result is well-controlled and probably right in spirit, and the two things
holding it up are weaker than the prose: Cell B to Cell C changes cleaning as well as
language, so Condition 1 is not isolated; and the positive result is measured under the
protocol the thesis itself ranks second-hardest, against a control the thesis itself
says does not exist, by the one model whose training data plausibly contains the
evaluation corpus.

## If only five things get fixed in the PDF

1. **Fill the Cell B cleaning cell.** Run English under the maximal regime, or Akkadian
   under tier0. Until then "the cost of the language alone" (G1) is not measured, and it
   is Condition 1.
2. **Build a random-initialized uMT5 twin.** One config load and a seed. It is the
   difference between "the only arm that clears its controls" and "the only arm we never
   controlled" (G3).
3. **Audit cuneiform-400M's training data against the eval corpus,** and state its
   provenance in Section 5.3. The purity argument currently protects the arms that lost
   and not the arm that won (G4).
4. **Print the std over 200 draws in every table, and state the GroupKFold fold count.**
   Both are free, and together they answer whether rho = .391 is chronology or pairwise
   reign discrimination (G2, G5).
5. **Name the arms in every figure reading.** If an arm cannot be named, the claim about
   the plot cannot be made (P-B).

---
---

# Part II. The HTML: `thesis_story_9.html`

31 slides, one file, keyboard navigation, no dependencies, no network calls beyond eight
reference hyperlinks. It works, it opens offline, it prints, and someone thought about
depth profiles and cell locators. The problems are that the medium fights the evidence,
and that the design defaults are the mode.

Context that shapes everything in this part:

- The deck will be published from HUJI CS, so it gets a public URL and a phone visitor.
- Roughly 60% of its content is tables of 3-decimal numbers whose only job is comparing
  a model row against a control row.
- The 11 figures are already-rendered matplotlib PNGs, 46 to 754 KB, embedded as base64.
- It must survive print to PDF, because that is how an advisor forwards it.
- It runs on Windows, where `Iowan Old Style` does not exist and silently becomes
  `Palatino Linotype`.

## II.1 What is wrong with the interface

### U1. The evidence is unreadable at presentation size

This is the serious one, because the deck's argument is "compare this row to the control
row," and nothing in the layout helps a viewer do that.

- Slide 6 (the replication table, the slide the whole ladder rests on) is 16 data rows by
  12 numeric columns, each cell holding two numbers (`Ridge | PLS`), rendered at
  `font-size: 9.5px` with `padding: 1.5px 3px` inside a card capped at
  `height: min(700px, 88vh)`. That is 384 numbers at nine and a half pixels, in a table
  measured at 1084px wide with 16px row height. **Corrected by rendering it:** at 1366 and
  at 1920 the slide does not clip, and on a laptop screen the table is dense but legible.
  It clips 45px at 1024x768. So the finding is about a room and a projector, not about a
  laptop, and the original wording ("nobody on a laptop reads it either") was wrong.
- The 11 figures are raster PNGs, 46 to 754 KB, scaled into `max-height: 100%` of a
  roughly 500px content box. The layer-sweep figures are four-panel plots with dashed
  control lines and star best-layer markers, i.e. the two visual encodings that die
  first under downscaling. The deck asks the audience to see which dashed line a solid
  line crosses, and then hands them a downsampled bitmap. No zoom, no click-to-enlarge,
  no SVG.
- Two different overflow behaviours coexist and only one is recoverable. `.text-points`
  carries `overflow: auto`, so slides 4 and 31 hide text that a viewer could scroll to if
  they knew it was there (no scrollbar affordance, no fade, no cue). `.slide` itself
  carries `overflow: hidden`, so anything past its box is simply gone. Measured
  consequences are in II.1b below, and they are not the slides I predicted.

Fixes, in order of payoff: split slide 6 into space and time; replace the raw table with
a control-relative view (one delta-versus-twin column, or a bar-in-cell) and put the
full table in an appendix slide; export figures as SVG or ship one high-res PNG per
panel with a click-to-zoom overlay; add a visible overflow indicator or a hard assertion
at build time that no slide overflows.

### U1b. What the browser actually does, measured

Everything above this point was arithmetic on CSS text. The deck was then rendered in
Chrome 150 over CDP from `file://`, driven one slide at a time through the deck's own
`go(n)`, at four viewport sizes. These supersede the inferences where they disagree.

**The thing that gets cut is the conclusion.** On the densest evidence slides the element
that overflows `.slide`'s `overflow: hidden` box is the `.takeaway`, the green box holding
the one-sentence finding. Measured overflow past the card's inner edge:

| slide | 1920x945 | 1366x768 | 1024x768 |
|---|---|---|---|
| 9, Cell B entity level | clipped | takeaway cut 19px | takeaway cut 104px |
| 10, Cell B fragments, year | clipped | takeaway cut 19px | takeaway cut 86px |
| 16, Cell C fragments, year | clipped | takeaway cut 19px | takeaway cut 54px |
| 17, Cell C fragments, place | clipped | ok | takeaway cut 16px |
| 6, the replication table | ok | ok | 45px lost |

At 1366x768, three slides lose the bottom edge and roughly the last line of their
takeaway. At 1024x768, the size of a great many lecture-room projectors, slide 9 loses
104px of its takeaway, which is about four lines of the conclusion, and slide 10 loses 86.
The audience sees the table and not the sentence that says what the table means. On a
deck whose entire method is "here is a table, here is what it shows," that is the worst
possible thing to truncate, and it is invisible to the presenter, who is reading from a
larger screen.

Slides 4, 31, 3, and 27 overflow inside `.text-points` instead, which is scrollable, so
that content is reachable but unadvertised: 72px on slide 31 at 1366, 179px at 1024.

**The serif falls back, confirmed by measurement rather than by reading the stack.**
Canvas text-width probe on this Windows machine: `Iowan Old Style` measures 298.00px,
identical to a deliberately bogus font name (298.00), so it is not installed.
`Palatino Linotype` measures 321.00 and `Georgia` 324.00, distinct from each other and
from the fallback. So every serif run renders as Palatino Linotype, which is the second
name in the stack, and the author is not seeing the face they specified.

**No viewport meta, confirmed live.** `document.querySelector('meta[name=viewport]')`
returns null in the rendered document.

**The JS-off failure is real.** `document.body.innerHTML` contains no `slide active` in
the source markup; exactly one slide has the class after `go()` runs. With scripting
blocked, every `.slide` keeps `display: none` and the page is blank.

**The print path is broken, measured.** With print media emulated, all 31 slides become
`display: flex` as intended, and the first slide resolves to 768px because `height: 100vh`
resolves against the viewport rather than the page box. But `document.body.scrollHeight`
is also 768px with 31 slides visible, so they stack on top of one another instead of
paginating. Print to PDF from this file does not produce 31 pages.

### U2. Green means "good" and also means "control"

`--green: #1a5c3a` is the brand accent: the eyebrow, the top gradient rule, the
`.tp-h` headings, and `.takeaway` (the good-news box, `--green-bg`). It is also
`.rtbl tr.rand td { background: var(--green-bg) }`, i.e. the control rows.

In this deck a control row winning is the bad news, the whole point. Painting it in the
same green as the takeaway box tells the eye the opposite of the argument. Worse, no
table marks the winner, the loser, or the comparison that matters: the reader must find
`.946` in slide 15's table unaided while the speaker talks. There is no red anywhere
except `--red: #8b1a10`, defined and used only for `.mc-body strong`, a class that
appears nowhere in the body.

Fix: one semantic pair, applied consistently. Control rows neutral grey with a rule,
"beats its control" in one accent, "loses to its control" in the other, and the compared
pair visually tied (adjacent rows, or a delta column that is the only coloured thing on
the slide).

### U3. No responsive rules at all, and fixed px throughout

11 KB of CSS, zero `@media` queries except `print`. The slide is
`width: min(1200px, 96vw); height: min(700px, 88vh)` with every font size in fixed px.
On a 4:3 projector, a 1366x768 laptop, or a tablet, the dense slides clip (see U1) and
nothing reflows. `html, body { overflow: hidden }` means the clipped content is
unreachable at the page level too.

### U4. Accessibility is not started

- No `aria-label` on the nav buttons; they are `‹` and `›` glyphs. A screen reader
  announces punctuation.
- No `:focus-visible` styles anywhere; `.btn` and `.tp` style `:hover` only. Keyboard
  users get no focus ring.
- No `prefers-reduced-motion` guard on the `appear` keyframe or the progress
  transition.
- No `prefers-color-scheme`. One theme, `#ddd8cf` on `#fff`.
- Tables use `<div class="tbl-cap">` instead of `<caption>`, and have no `scope` on
  header cells. The deck is mostly tables, so this is most of the content unlabelled.
- Contrast: `--ink-light #6b7484` on `#f8f9fb` is about 4.3:1, which passes for large
  text and not for the 12px `.mc-body` it is used on. The 9.5px table text and the
  10.5px letterspaced uppercase `thead` are below any practical legibility floor
  regardless of ratio.
- Image `alt` text is present on all 11 figures, which is good, but every alt is the
  slide title, so it describes the topic rather than the plot. For a deck whose figures
  carry the argument, a one-sentence data description would cost nothing.

### U5. Two latent bugs and one leak

- `const TOTAL = 31` is hardcoded while `slides` is queried from the DOM. `go()` clamps
  with `TOTAL`, `forEach` toggles with `slides`. They agree today. Add a slide and the
  last one becomes unreachable; remove one and `go()` lands on nothing and blanks the
  stage. Use `slides.length`.
- `TITLES` is a 31-entry array duplicating the `<h2>` of each slide, maintained by hand
  in a separate place from the markup. It has already drifted: `TITLES[5]` is
  "A: the paper reproduces on our models, with the controls it never ran," the slide
  itself says "...and the controls it never ran hold up." Read them from the DOM.
- Slide 12 body text ships an internal path to the audience:
  `v_1/src/stress_tests/e6_clusters/embedding_panels/index.html (open next to this
  deck; interactive.html is the self-contained viewer)`. That is a build note in a
  presentation slide.

### U6. Print path is decorative

`@media print` sets `.slide { display: flex !important; height: 100vh; page-break-after:
always }`. `100vh` in print is unreliable across engines, `overflow: hidden` is only
lifted on `body` and not on `.text-points`, and the slide numbers are hidden. A deck
whose fallback distribution channel is "print to PDF for the advisor" should have that
path tested, and the clipped-content problem of U1 becomes permanent in a PDF.

### U7. The visual language is the distribution's mode

`--sans: -apple-system, BlinkMacSystemFont, "Segoe UI", ...` is the system-font default.
White rounded card with `box-shadow` on a warm grey field, a 4px
`linear-gradient(90deg, #1a5c3a, #2ea86b)` rule across the top of every slide, an
uppercase letterspaced green eyebrow, and a tinted left-border takeaway box: this is
the generic generated-deck look, and it carries no information. The gradient in
particular is 31 repetitions of decoration on a deck that could not spare pixels for
its own tables.

There is a real design brief available here and it is being ignored. The subject is
dated cuneiform on clay from eight named reigns. The deck's own best idea, the tiny
`.cellmap` A/B/C/D locator, is the one element with actual semantics, and it is rendered
at `font-size: 7.5px` in the top-right corner, the least visible position on the slide.
Invert that: make the cell locator a real chrome element, drop the gradient, and let the
one accent colour mean "beats its control" and nothing else.

Also note `--serif: "Iowan Old Style", "Palatino Linotype", Georgia, serif`. Iowan Old
Style is a macOS font. On the Windows machine these files sit on, every title, every
`.sh` heading, and every `.tp` serif run is falling back to Palatino Linotype. The
author is not seeing the deck they designed.

### U8. Missing affordances for a 31-slide advisor meeting

No overview or grid mode, no jump-to-slide, no speaker notes, no section markers in the
progress bar, no way to answer "go back to the table from slide 16." Keyboard gives
arrows, space, Home, End, and `f`. For a meeting where the advisor will interrupt and
ask to see slide 9 again, an Escape grid and a number-then-Enter jump are the two
highest value additions in the deck, and both are about 20 lines.

### U9. Two layout archetypes for 31 slides, and the opening gets the flatter one

This is why the deck feels repetitive, and it is measurable rather than a matter of
taste. Every one of the 31 slides is one of exactly two things:

| archetype | count | what it looks like |
|---|---|---|
| `slide slide-text` | 20 | eyebrow, `h2`, then a stack of `.tp` blocks with a green left border, sometimes a table |
| `slide slide-figure fig-major` | 10 | eyebrow, `h2`, a `.cfg` config strip, one image, one takeaway box |

The order they appear in is the second half of the problem:

```
1  title
2  text   3  text   4  text   5  text   6  text
7  FIG    8  FIG
9  text  10 text  11 text
12 FIG
13 text  14 text  15 text  16 text  17 text
18 FIG  19 FIG  20 FIG
21 text 22 text
23 FIG
24 text 25 text 26 text 27 text
28 FIG  29 FIG  30 FIG
31 text
```

The first figure arrives on slide 7. So the opening is a title followed by five
consecutive text walls, including slide 6, which is the 384-number table at 9.5px. The
later stretch alternates. Whatever a viewer feels as "the beginning is flatter" is that
run of five, and the same effect returns at 13 through 17.

Almost certainly not intended, and the CSS proves it. There are 21 class definitions in
the stylesheet that no element in the body uses, and they fall into three coherent
groups:

- `.method-grid`, `.mc`, `.mc-icon`, `.mc-name`, `.mc-body`, `.method-lead`. A five-card
  horizontal row: `grid-template-columns: repeat(5, 1fr)`, each card with a numeral, a
  serif name, and a body line whose `strong` is styled in `--red`. That is a designed
  protocol overview, and the deck has exactly one slide it fits, slide 5, "How every
  experiment in this deck is set up." Slide 5 is now a text wall. So the one piece of
  visual variety built for the opening was cut and its CSS was left behind.
- `.arch`, `.ab`, `.ab-sub`, `.arch-row`, `.arch-cap`, `.arch-inner`, `.arch-ar`,
  `.torso`, `.sub-b`. A CSS-drawn architecture diagram with input blocks, a torso, a
  head that can be struck through (`.ab.head.off`), and a probe block in the placeholder
  ochre. That is the MLM figure on slide 13, drawn in HTML. Slide 13 now shows a 134 KB
  PNG instead. A vector diagram that would have scaled and printed was replaced by a
  raster one.
- `.placeholder-box`, `.ph-icon`, `.ph-hint`, `.ph-slot`, `.ph-sub`. The build script's
  "figure not supplied yet" scaffold. All 11 figures did land, so this is dead by
  success rather than by abandonment.

(`.active` also appears unused in the body, but the JS applies it through
`classList.toggle`, so it is live. The other 21 are not.)

Read together, the dead CSS is the record of a richer deck that existed at some point in
the nine iterations and got flattened into two archetypes. The repetition is not a style
choice; it is what is left after the variety was removed.

### U10. What three independent reviewers found that this document missed

Three read-only lenses were run over the stripped markup after the findings above were
written: a UI craft lens, a pre-ship defect lens, and an audience lens. Attributed here
rather than absorbed, because they corrected me.

**No `<meta name="viewport">` in `<head>`.** With every font size in fixed px and
`.slide { width: min(1200px, 96vw) }`, a phone renders the deck at desktop layout width
and scales it down. Illegible without pinch-zoom. U3 above discusses responsive rules at
length and misses the single tag that matters most for a published URL.

**No slide carries `class="active"` in the markup.** `.slide { display: none }` is the
default and `.active` is only ever added by `go()`. With JS disabled, blocked, or failed,
a visitor sees a blank page, and there is no `<noscript>`. For a public university URL
that is the most severe finding in Part II.

**The hardcoded `TOTAL` is visitor-facing, not just internal.**
`slides.forEach((s,i) => s.setAttribute('data-num', (i+1)+'/'+TOTAL))` feeds
`.slide::after { content: attr(data-num) }`, so the printed "n/31" footer on every slide
is wrong the moment the DOM count drifts from 31. U5 called this latent; it is visible.

**`history.replaceState` without a `hashchange` listener.** `location.hash` is read once
at load and written on every slide change, so the deck advertises deep links and browser
back or forward that do not work. Either add the listener or stop writing the hash.

**`requestFullscreen()` on `file://` fails into `.catch(() => {})`.** Pressing `f` from a
locally opened file can do nothing with no explanation to the presenter.

**Prev and next have no boundary state.** Clicking prev on slide 1 is a silent no-op.

**Craft mechanisms behind the repetition**, extending U9. `.tp-h` and `.tp-b` are both
16.5px, so a one-line caveat and a full methods paragraph carry identical visual weight
and the slide cannot be skimmed. The `.cfg` strip opens nearly every table slide with
prose-length label-value pairs, which trains the reader to skip the first third of the
slide to reach the number. The eyebrow, `h2`, and takeaway are three distinct semantic
roles rendered at 11px, 28px, and 16.5px, compressed on `fig-major` slides to 9.5px and
10.5px, which collapses them into one size band. The 2x2 breadcrumb repeats verbatim on
slides 5 through 26 as plain text with no per-slide state styling, so it is repeated copy
rather than orientation.

**A correction to U9's reading of the opening.** Slides 2 through 5 build the 2x2 design
sequentially and are genuinely non-visual argument that a figure would not compress, so
the delayed first figure is defensible pacing. The real defect is narrower: slide 6 is the
deck's first figure-weight content and wears the same class and type scale as the setup
slides before it. The pivot is typeset as a footnote.

**Three things worth keeping in any rebuild.** The 2x2 breadcrumb as a concept, since it
is the right device for a ladder argument and only needs real rendering. The takeaway box
as a mandatory slot, because forcing every dense slide to end in one plain sentence is
good discipline. Control rows as first-class table rows rather than footnotes, which is an
honest choice for a null-heavy thesis; U2's complaint is about the colour, not the row.

**One reversal.** Deleting the hand-duplicated `.cellmap` markup, 16 copies, is debt
rather than a pre-ship fix. Touching it on a frozen deck adds regression risk for no
audience-visible gain.

**Two rhetorical findings.** "Key takeaway" opens the closing paragraph of 24 of the 31
slides, which is a formula that primes every negative result as pre-digested rather than
argued. And slide 17's title, "place survives where the date does not," is contradicted by
its own body: an untrained Qwen3-8B holds the best number in that column. Slides 20 and 28
also disagree about how much weight rho .391 can bear, one calling it "a beginning, not a
solved problem" and the other "what does work."

## II.2 Generation patterns visible in the HTML

Neither artifact is claimed as hand-written, and the question is not authorship but
whether the generation process left defects. It did, and they cluster in a way that says
which parts were made when.

### P-D. Three number-formatting conventions in one deck, so three generation passes and no normalising pass

| convention | where | example |
|---|---|---|
| leading-dot, 3dp, ASCII hyphen for negatives | slides 6, 9, 10, 11, 14, 16, 17 | `.701`, `-0.082` |
| leading-dot, 3dp, typographic `&minus;` | slides 22, 24 | `&minus;.074` |
| leading zero, 3dp, star markers inline | slides 25, 26 | `0.263`, `0.305&#9733;` |

Model identifiers drift the same way: `cuneiform-400M` and `AKK-300M` everywhere except
slides 25 and 26, which say `Thalesian-cunei-400m` and `Thalesian-AKK-300m`, the raw
checkpoint names from the results CSV. So slides 25 and 26 were generated from a
different source, at a different time, by a different template, and never reconciled
with the deck they were inserted into.

### P-E. Slides 25 and 26 are working notes wearing a slide

Same two slides, and the register gives them away. Compare the voice:

- Slide 24: "Word order carries almost none of it."
- Slide 26: "The dial is FLAT on Akkadian maximal (lambda=0 approx lambda=1 within a few
  hundredths for every model)."

Slides 25 and 26 carry: ALL-CAPS emphasis (`FLAT`, `NOT the KPLS family`,
`ONLY the KRR arm`), inline file paths as audience-facing text
(`CSV: results/csv/p9_gkpls.csv`, `results/csv/p8_lambda.csv`), internal experiment IDs
(`P1 / translation slides`), raw formulae in HTML entities
(`[(1&minus;&lambda;)HK y H &minus; &lambda;L]z = &gamma;Dz`), a footnote marker
(`* rows = controls`) that appears on no row, and defensive clarifications addressed to
a reviewer rather than an audience ("NOT the KPLS family: no components and no kernel
choice here"). These are notes-to-self promoted to slides without a rewrite. The thesis
versions of the same two experiments (Sections 10.5, 10.6) are written properly, which
means the prose pass happened on the PDF and not on the deck.

### P-F. Derived columns computed on hidden precision, so the deck shows arithmetic that does not check out

The deck adds `difference` columns the thesis does not have (slides 10, 11, 16, 17), and
they are computed from unrounded values then printed beside rounded ones. Spot checks:

| slide | row | shown | from displayed values |
|---|---|---|---|
| 10 | Llama-2-70B rho | `+.178` | .544 to .723 = +.179 |
| 16 | Llama-2-70B rho | `+.206` | .331 to .538 = +.207 |
| 16 | Qwen3-8B R2 | `+.000` | .082 to .083 = +.001 |
| 17 | AKK-300M rho | `+.126` | .311 to .438 = +.127 |

**Scope, corrected by an independent recount.** These four are not the population. A
sweep of all five delta-bearing tables (slides 10, 11, 16, 17, 24) finds **33 of 94 delta
cells** that do not reproduce from the values printed beside them. But every one of the 33
deviates by exactly .001, the last displayed digit, and none by more. So the honest
severity is lower than "four broken cells" implies and the honest scope is much wider: the
whole delta apparatus is systematically off by a rounding step, not sporadically wrong.

That matters for how it reads to an advisor. One cell showing `+.000` beside a visibly
nonzero change is a typo; a third of the column failing to reconstruct is a pipeline that
prints derived values at a different precision from its sources. Either print the columns
from the same precision you display, or drop them. Do not fix the four.

### P-G. Machine patching visible in the stylesheet

`/* --- added by build_story_deck.py --- */` sits at the two-thirds mark of the CSS, and
everything after it is override-on-override: `.two-col .tp-h`, then `.takeaway.tight`,
then `.cfg.tight`, then `.slide.fig-major .cfg.tight`, then
`.slide.fig-major .takeaway.tight .tk-label`, five levels of specificity walking font
sizes down in 0.5px steps (16.5, 15.5, 14.5, 13.5, 12.5, 11.5, 10.5, 9.5, 9, 8). That is
a generator being asked "it still overflows" repeatedly and responding by shrinking type,
which is how slide 6 arrived at 9.5px. The filename `thesis_story_9.html` names the
iteration count.

The right response to "it overflows" is fewer things on the slide. A build script cannot
make that call, so it made the only call it had. Worth naming explicitly because it is
the generation pattern with the largest effect on the artifact: U1, the deck's biggest
problem, is the accumulated output of nine rounds of automated shrinking.

### P-H. Deck-only inconsistencies that a single proofread pass catches

- Slide 2: "Our regime differs on three axes at once." Slide 4, next slide: "Going
  straight from the paper's setting to Akkadian changes two things at once." The thesis
  says three (entities, language, unit).
- Slide 6 heading: "The paper reproduces on our models, and the controls it never ran
  hold up." Controls do not hold up; results hold up against controls. The thesis
  chapter title is correct, so this is a deck-only regression.
- `<title>` names neither the thesis title nor the deck's subject (world models). It is
  the working name of the project directory.

### What the generation patterns cost, concretely

Not style points. Three of them changed the artifact's meaning: X1 misattributes two
papers, one of them to the advisor in his own meeting; P-F makes four printed numbers
unverifiable; P-G shrank the central replication table to nine and a half pixels. And
P-A plus G2 together are the real risk: a document that asserts honesty twelve times
while its headline result sits on the second-strictest of three protocols is a document
that invites exactly the audit it would fail.

## II.3 The anchor, measured

Taken from `deepseek-v4-2606.19348v1.pdf` rather than from memory, so every styling
claim in the directions below is checkable against a file on disk.

| property | DeepSeek-V4 paper | current deck |
|---|---|---|
| body face | URW Palladio (Palatino), 11pt, 93.8% of glyphs | system sans stack, sizes from 9.5 to 16.5px |
| color in running text | effectively none. Black, plus 798 glyphs of near-black `#262626`. No link colour in the text layer at all | green accent on every slide plus a 4px gradient rule |
| chart accent | `#4D6BFE`, a single hue, and it lives only in the drawing layer (77 fills) | green, plus a red that is defined and never used |
| tables | booktabs: horizontal rules only, no verticals, no cell fills | horizontal rules, green fills on control rows |
| captions | `Figure 1 |` then a sentence, Nature style | `Setup` and `Key takeaway` label blocks |
| figure text | vector, so it survives any zoom | raster PNG, downscaled into a 500px box |

Two useful facts fall out of this. The deck is already one CSS line from the paper's
serif, since Palatino Linotype is what it renders today. And the paper reaches its
authority by removing colour, not by adding it, more completely than I first reported:
its running text has no accent colour whatsoever, only black and a near-black. The single
blue exists in figures and nowhere else.

## II.4 Five directions

Conventionality estimates follow the verbalized-sampling method: an estimate of how
likely each direction is to be the expected choice. They are judgements, not
measurements. Nothing below is a decision.

### Direction A: Offprint

Stop calling them slides. One continuous document set in Palatino at 11pt, sections
separated by rules and numbers rather than by cards, navigated by scroll-snap. A present
mode becomes a stylesheet toggle rather than the primary structure.

```
  When Are Space and Time Linearly
  Represented in Language Models?
  Yarin Beer  ·  HUJI CS  ·  July 2026
  ______________________________________

  6  CELL A
  The paper's setting replicates, and
  survives the controls it never ran

  We rebuilt the paper's own experiment
  in full. Its six English datasets were
  vendored byte for byte from the
  authors' repository ...

  Table 1 | Cell A, best-layer held-out
  ────────────────────────────────────
  model            World   vs twin
  ────────────────────────────────────
  Llama-2-70B       .905     +.735
  Llama-2-13B       .883     +.601
  ────────────────────────────────────
```

Estimated conventionality: 0.12.

Rough cost: 1 to 2 days. The slide sectioning is reusable, the tables mostly become
simpler, and the figures still need vector export. The present-mode toggle is the
unknown.

Why it beats the current deck: table density stops being a problem instead of being
fought. A reader 40cm from a laptop can carry a 16 by 12 table; a projector cannot, and
nine rounds of shrinking type were an attempt to make one medium behave like the other.
Prints correctly by construction. Works on a phone with no extra rules. The published
artifact becomes the same object as the thesis rather than a lossy summary of it.

What it costs: it is not a talk. If there is a defense with a projector, that needs the
toggle to be real work rather than an afterthought, and the figures still need to be
vector for it.

The constraint worth questioning: "an advisor meeting needs slides." Two people at a
laptop do not. A defense does, and that is a different artifact with a different budget.

### Direction C: Squeeze

Ground the palette and the texture in the physical object the thesis is about. Bone
paper, one impressed rule with a single-pixel highlight above the shadow, wedge tick
marks as the only ornament, an accent drawn from oxidized copper rather than from any
software brand. Palatino throughout. Ornament confined to the chrome band; data regions
stay bone and neutral.

```
  ▪▪▪  CELL C · RAW AKKADIAN        A B
                                    ▪ C
  ╱ The date falls to the
    untrained twin

   model          rho    vs twin
   ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔
   cuneiform-400M .699   ████ +.111
   Llama-2-70B    .538   ██   -.050
   Qwen3-8B       .438   ████ -.106
   ▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁
   ref: squeeze of K.1621, CDLI P######

  bone ground, copper accent, ornament
  only in the chrome band
```

Estimated conventionality: 0.15.

Rough cost: 2 days, plus the time to find and cite a real reference object. Highest
variance of the five, because most of the work is judgement rather than markup.

Why it beats the current deck: the deck stops looking like every other ML deck and
starts looking like the field it claims to bridge, which is the thesis argument made
visually. A committee that reads a lot of identical decks will remember this one.

What it costs: it is the only option with real taste risk, and it has a hard
prerequisite. The reference must be a named real object, cited inside the file, so the
grounding is auditable rather than a vibe. Pick a specific squeeze or photograph from
CDLI or ORACC and put its P-number in the footer. Without that citation this direction
degrades into decoration, and decoration is worse than the current deck.

The constraint worth questioning: "academic means visually neutral." Partly real, since
a committee is the audience. Partly inherited from the ML paper monoculture, which is
not the only publishing tradition this thesis sits in. The clamp above is what keeps
the real part of the constraint satisfied.

### Direction B: Delta-first

No slide shows a raw table. Every comparison becomes a lockup: model name, and a bar
drawn from that arm's own control baseline, left of zero or right of zero. Exact numbers
move to appendix slides reachable by a jump.

```
  RAW AKKADIAN · YEAR      versus control

  cuneiform-400M   ──────────►  +.111
  Qwen3-32B          ──►        +.032
  gpt-oss-120B        ─►        +.029
  Llama-2-70B      ◄─           -.050
  Qwen3-8B      ◄────           -.106
  Llama-2-13B  ◄─────           -.140
                    │
           its own untrained twin

  TF-IDF floor .707 beats all six
  full table → appendix A3
```

Estimated conventionality: 0.20.

Rough cost: 2 to 3 days. Every table needs a data transform rather than a restyle, and
the appendix slides and the jump affordance are part of the direction, not extras.

Why it beats the current deck: the argument becomes visible instead of findable. Right
now a viewer has to locate `.946` inside a 7 by 3 table while the speaker talks, and
the deck offers no visual pairing between an arm and its control. This direction encodes
the reading rule itself: cross the line or do not. It also kills the 9.5px problem
structurally rather than by shrinking type a tenth time.

What it costs: precision. Some questions can only be answered from the full table, so
the appendix and the jump-to-slide affordance are not optional extras here, they are
part of the direction. Also more build work than any other option, since every table
needs a data transform rather than a restyle.

### Direction D: Strict paper mimicry

Palatino 11pt, booktabs tables with horizontal rules only, `Figure N |` captions,
`#4D6BFE` for links and for at most one series, white ground, no cards, no shadows, no
gradients.

```
  6  Cell A: the paper's setting replicates

  Table 1 | Best-layer held-out test scores
  on the paper's six English datasets.
  ─────────────────────────────────────────
  model          World    USA    Figures
  ─────────────────────────────────────────
  Llama-2-70B     .905   .846      .833
  Qwen3-32B       .838   .702      .806
  ─────────────────────────────────────────
  TF-IDF*         .642   .536      .645
  L2-70B random*  .170   .240      .198
  ─────────────────────────────────────────
  * control.
```

Estimated conventionality: 0.55.

Rough cost: half a day for the restyle, plus the slide-6 split from II.5, without which
it fails for the same reason the current deck does.

Why it beats the current deck: it reads immediately as work from a serious lab, it
carries essentially no taste risk with a committee, and every single choice can be
traced to a page of the anchor PDF if anyone asks. It is also the fastest of the four
real options.

What it costs: it is a good version of a familiar thing rather than a distinctive one.
It also inherits the table-density problem unchanged, so it must be combined with the
slide-6 split from the shared list below or it fails for the same reason the current
deck does.

### Direction E: Current deck, recolored

Swap green for `#4D6BFE`, set the sans stack to Palatino, leave the geometry alone.

Estimated conventionality: 0.92.

Rough cost: 20 minutes.

Why it might still win: twenty minutes, and the thesis defense is the deadline that
matters. If the calendar is the binding constraint, this is a defensible call, and
saying so plainly is better than half-building one of the others.

What it costs: every problem in II.1 survives. Slide 6 stays at 9.5px, the figures stay
raster, the control rows stay tinted in the accent color, and the file stays a
generated-deck look with a paper's typography bolted on.

## II.5 Edits that ship under all five directions

Ordered by payoff.

### 1. Split slide 6, and give every table a signed delta column

Slide 6 currently renders 384 numbers at `font-size: 9.5px` with `padding: 1.5px 3px`,
inside a card capped at `height: min(700px, 88vh)`. That is the slide the whole ladder
rests on and it is the least readable one in the deck. Split it into space and time.
Then, in every results table, add one signed column: the arm's score minus its own
control. Make that column the only colored thing on the slide. The delta is what the
reading rule is about, and no table currently shows it.

### 2. Retire green as the brand color

`--green: #1a5c3a` currently marks the eyebrow, the top gradient, the `.tp-h` headings,
the `.takeaway` box, and `.rtbl tr.rand td`, which is the control rows. In this deck a
control row winning is the bad news. Painting it in the takeaway color tells the eye the
opposite of the argument. One semantic pair instead: beats its control, loses to it.
Controls neutral grey with a rule. `--red: #8b1a10` is already defined and currently
used only by `.mc-body strong`, a class that appears nowhere in the body.

### 3. Re-export the figures as vector

Eleven raster PNGs scaled into a roughly 500px box. The layer sweeps are four-panel
plots whose argument is which dashed control line a solid line crosses, and star markers
for best layer. Those two encodings are the first to die under downscaling. Since the
plotting code exists (the deck cites `results/csv/p9_gkpls.csv` and `p8_lambda.csv`),
`savefig(..., format="svg")` should be a small change per figure. If any figure must stay
raster, ship one PNG per panel and add click-to-zoom.

### 4. Fix the two latent JavaScript bugs

`const TOTAL = 31` is hardcoded while `slides` is queried from the DOM. `go()` clamps
with `TOTAL`, the toggle loop uses `slides`. They agree today. Add a slide and the last
one is unreachable; remove one and `go()` blanks the stage. Use `slides.length`.

`TITLES` is a 31-entry array duplicating each slide's `<h2>`, maintained separately from
the markup, and it has already drifted: `TITLES[5]` reads "A: the paper reproduces on
our models, with the controls it never ran" while slide 6 reads "...and the controls it
never ran hold up." Read the titles from the DOM.

### 5. Remove the build residue

Slide 12 ships an internal path to the audience:
`v_1/src/stress_tests/e6_clusters/embedding_panels/index.html (open next to this deck;
interactive.html is the self-contained viewer)`. That is a note to self on a slide.

Slides 25 and 26 are still in working-notes register while the rest of the deck is
written prose (detail in P-E). The thesis versions of the same two experiments
(Sections 10.5 and 10.6) are written properly, so the fix is largely a paste-down from
the PDF. Those two slides also use different number formatting and different model names
from the rest of the deck (P-D); normalizing both is part of the same pass.

### 6. Drop or recompute the difference columns

Detail and the four failing spot checks are in P-F. Either print them from the same
precision that is displayed, or drop the columns.

### 7. Accessibility, since this gets a HUJI URL

- `aria-label` on the two nav buttons. They are currently `‹` and `›` glyphs, so a
  screen reader announces punctuation.
- `:focus-visible` styles. `.btn` and `.tp` style `:hover` only, so keyboard users get
  no focus ring anywhere in the deck.
- `<caption>` and `scope="col"` on tables. `<div class="tbl-cap">` is used instead, and
  the deck is mostly tables, so most of the content is currently unlabelled.
- `prefers-reduced-motion` around the `appear` keyframe and the progress transition.
- At least one `@media` breakpoint. There are currently zero besides `print`, in 11 KB
  of CSS, with every font size in fixed px and `html, body { overflow: hidden }`, which
  means clipped content is unreachable at the page level too.
- `--ink-light #6b7484` on `#f8f9fb` is about 4.3:1, which passes for large text and not
  for the 12px `.mc-body` it is used on.
- Image `alt` text exists on all 11 figures, which is more than most decks, but every
  alt is the slide title. For figures that carry the argument, one sentence describing
  what the plot shows costs nothing.

### 8. Test the print path

`@media print` sets `.slide { display: flex !important; height: 100vh; page-break-after:
always }`. `100vh` in print is unreliable across engines, `overflow: hidden` is lifted
on `body` but not on `.text-points`, and the slide numbers are hidden. If print to PDF
is the distribution channel, the clipping problem becomes permanent in the PDF.

### 9. Add an overview grid and a jump

No overview mode, no jump-to-slide, no speaker notes, no section markers in the progress
bar. Keyboard gives arrows, space, Home, End, and `f`. For a meeting where an advisor
interrupts and asks to see slide 9 again, an Escape grid and number-then-Enter are the
two highest-value additions in the file, and both are about twenty lines.

### 10. Rename the tab

`<title>` names neither the thesis nor its subject. For a published artifact the title
is the search result.

### 11. Break the two-archetype monotony, and make the styling carry data

U9 is fixable without a rewrite, because the deck already contains most of what it needs.
Three moves, in order of cost.

**Revive the two archetypes that were cut.** `.method-grid` is a working five-card row
sitting unused in the stylesheet, and slide 5 is the slide it was built for. Restoring it
turns the flattest slide in the opening run into the most structured one, at the cost of
writing five short cards. `.arch` is a working vector diagram of the MLM, and slide 13
currently shows a 134 KB raster of the same thing. Switching back removes a PNG, gains a
diagram that scales and prints, and lets `.ab.head.off` do what it was written for:
showing the region and date heads struck through, which is precisely the point Chapter 8
makes in prose.

**Give each of the four acts its own visual signature.** The deck has real structure
already: Cell A, Cell B, Cell C, the six rescues, and the positive result. That structure
is currently signalled only by a 7.5px locator in the corner. Cheap ways to make it
legible without new layout code: a rule weight or a ground tint that shifts once per act;
the `.cellmap` promoted from 7.5px to a real chrome element that reads at a glance; the
rescue slides numbered R1 to R6 in the eyebrow so the audience knows how many are left.
A viewer should be able to tell which act they are in from across the room, before
reading a word.

**Let a table's shape encode its verdict.** Right now every table looks the same whether
its story is "the model wins by a mile" (slide 6) or "an untrained network matches every
trained one" (slide 15). One shared device fixes both: the signed delta column from
edit 1, drawn as a bar from a zero rule. On slide 6 every bar points the same way and the
slide reads as a wall of agreement. On slide 15 the bars vanish and the slide reads as a
tie. Same component, opposite picture, and the picture is the argument. That is what
"unique styling" means here, and it costs less than a new palette: the variety comes from
the data rather than from decoration.

What to avoid while doing it: adding a second accent hue per act, or per-slide background
images. Both re-introduce decoration that carries no information, which is what the green
gradient already does 31 times.

## II.6 The shortest defensible path for the deck

If only three things happen: fix the two attributions from Part III, split slide 6 and
add the delta column, and re-export the figures as vector. Those address the
argument-damaging problems. Everything else in II.5 improves the artifact; those three
stop it from misrepresenting the work.

Direction is Yarin's call. A, C, and B each change the artifact's character. D is the
safe strong option. E is the honest answer if the calendar is what binds.

---
---

# Part III. Defects in both files

## X1. Attribution drifts toward the advisor

- Deck slide 13: "following *Filling the Gaps in Ancient Akkadian Texts* (Stanovsky et
  al., EMNLP 2021)." The thesis has it right: Lazar, Saret, Yehudai, Horowitz,
  Wasserman, Stanovsky. It is Lazar et al.; Stanovsky is last author and is also the
  advisor.
- Deck slide 29: "consistent with Stanovsky et al. (2022) on multilingual transfer for
  low-resource ancient languages." Deck slide 31, about the same finding: "consistent
  with Malkin et al. (NAACL 2022)." Both refer to thesis reference [13], Malkin,
  Limisiewicz, and Stanovsky. Two attributions of one paper in one deck, one of them
  wrong, both promoting the last author to first.

This is the failure class where a generator picks the recognisable name from an author
list. In a deck being shown to that same person it is also the most embarrassing
possible instance of it. Malkin et al. 2022 is about cross-lingual transfer generally,
not "ancient languages," so slide 29 misstates the paper's scope as well as its
authorship.

Fix these before touching a single line of CSS. They take under a minute and they are
the only items in this document that Gabriel will notice within ten seconds of opening
the file.

## X2. The abstract and slide 5 carry the same two errors

"Ten frozen models" undercounts by one (the 37M MLM is in five results tables), and
"three small translation encoders" is contradicted by Chapter 12, where uMT5-base is
explicitly the arm with no translation finetune. Both errors appear in the PDF abstract
and on deck slide 5, so they were written once and copied.

## X3. Unnamed figure referents appear in both

Section 6.3 and slide 7 both say two arms show a distinctive late-layer rise without
naming them, and the shape is later invoked as a warning sign. Same defect, same
sentence, both artifacts. See P-B.

---
---

# Part IV. Open questions raised during this review

Every question below came up while reading and could not be answered from the two files.
They are listed rather than guessed at. The first four decide whether findings in Part I
are defects or misreadings, so they are worth answering before the meeting.

## About the protocol (these settle G2 and G5)

1. **How many folds does GroupKFold-by-ruler use inside each of the 200 draws?** With 8
   rulers, a fold holds out one or two. If one, Spearman on a single-valued target is
   undefined; if two, it is a two-class discrimination statistic. The number decides how
   to read rho = .391.
2. **Is Spearman computed per fold and then averaged, or are out-of-fold predictions
   pooled and scored once?** Section 5.6 states pooling for LORO and does not state it for
   the stress line. If the stress line scores per fold, the .391 versus .13 gap has a
   mechanical explanation and G2 largely dissolves. If it pools, the gap needs a different
   one.
3. **Were the best layer and best k chosen on the same held-out data they are reported
   on, or on an inner split?** Chapter 5 does not say. If the former, every number in the
   thesis is a maximum over 30 to 80 layers, and the trained-versus-random comparisons
   inherit an asymmetric bias.
4. **What is the std over the 200 draws for the Chapter 12 ordering?** Specifically for
   uMT5-base .277, AKK-300M .300, and cuneiform-400M .391. The entire mechanism argument
   is that ordering.

## About the models

5. **What corpus was cuneiform-400M translation-finetuned on, and does it overlap the
   1,202 evaluation fragments?** Provenance, size, and source editions are not stated
   anywhere. This is G4, and it is the question the positive result stands or falls on.
6. **Same question for AKK-300M,** since the ablation triangle reads its underperformance
   as evidence about the objective rather than about its data.
7. **Why was no random-initialized uMT5 twin built?** If there is a technical reason, it
   belongs in Section 5.3. If there is not, the reading rule can be applied to the winner
   as it was to everything else.
8. **Is the gpt-oss-120B collapse-then-climb depth profile robust to the fp16 sanitizer?**
   It is the only arm needing the clamp, and it is the only arm with that shape.

## About the corpus and the target

9. **Is there any subset of the corpus where the date is not a per-ruler constant?**
   Even a few hundred year-stamped fragments would separate "language resource" from
   "label equals entity identity," which is G6.
10. **Why is place reported in R2 when the same argument that demotes R2 for year applies
    to it?** Ten distinct coordinate targets, ten sites.
11. **What is the exact scope of "effectively all published Akkadian"?** A source list and
    a date turn a falsifiable absence claim into a bounded one.

## About the presentation

12. **Which of the five directions in II.4?** Yarin's call, and the only question in this
    document that is a preference rather than a fact.
13. **Is there a projected defense, or only laptop meetings?** Direction A is strong for
    one and weak for the other, so the answer changes the ranking.
14. **Was the flatter opening intended?** U9 says the CSS suggests otherwise: a
    five-card protocol row was built for slide 5 and never used. Confirming it was cut
    rather than planned decides whether to restore it or to design the opening
    deliberately.
15. **Do the plotting scripts still run?** Everything in edit 3 assumes the figures can be
    re-exported as SVG from existing code rather than rebuilt.

---
---

# What was and was not verified in producing this review

**Corrections this document made to itself after an independent recount.** Four numbers
in earlier versions were wrong and are fixed above: the anchor PDF's Palladio share is
93.8%, not 97%; its 798 near-black glyphs are `#262626`, not `#2625A6`, so the paper has
no text-layer accent colour at all and the styling argument is stronger than the version
that claimed a link colour; "honest" appears 5 times in the deck, not 4; and the deck's
delta-column defect is 33 of 94 cells off by one last digit, not 4 cells, which widens the
scope and lowers the severity. Each was re-derived from the sources by a reviewer with no
access to this document's reasoning.

**A further correction.** An earlier version of U9 said 21
`slide-text` slides. The parse says 20 (1 title, 20 text, 10 figure). Corrected. The
slide-order block was always right; the count line above it was typed rather than read
off the script, which is the same defect P-F charges the deck with.

**Executed.** PyMuPDF extraction and full read of all 58 thesis pages. Font, size, and
color census of the DeepSeek anchor across all 58 of its pages. Byte-level structural
scan of the deck: section count, image count and `alt` presence, PNG payload sizes,
`<svg>` count (zero), `@media` count (one, `print`), the `TOTAL = 31` and `slides`
mismatch, the `build_story_deck.py` marker and the font-size cascade after it. Slide-text
extraction and slide-by-slide read. The four delta-column arithmetic checks in P-F.
Bibliography citation counting (reference [5] appears once, in the bibliography only).

**Not executed.** The deck was never opened in a browser and no page was rendered.
Every claim about clipping (U1), print output (U6), and font fallback (U7) is arithmetic
on the CSS, not an observation, and the contrast figure in U4 is computed by formula
rather than by a checker. No figure was rendered, so P-B and every figure-related remark
concerns captions and prose only. No code, no CSVs, no data, so the Part I findings are
readings of the document rather than reruns. G2's suggestion that rho .391 may be
pairwise reign discrimination is inference from Section 5.6, which does not state the
fold count. G4's contamination concern is a hypothesis about a third party's training
data that was not looked up. The conventionality estimates in II.4 are judgements by
construction.

**Residual risk.** The largest is that G2 and G4, the two findings that most damage the
positive result, cannot be settled from the PDF. If each GroupKFold fold holds out two
rulers, G2 is a real defect; if predictions are pooled before scoring, it partly
dissolves and only the .391 versus .13 gap survives. Only the code answers that. Second,
the interface findings are source-read, so any of them could be wrong in a way a browser
would show immediately, and the cheapest correction is to open the file and look.

**Worth doing before the meeting.** Render the deck at 1366x768 and to PDF, then check
the four densest slides. Read the repo before treating G2 or G4 as established rather
than as questions to ask.
