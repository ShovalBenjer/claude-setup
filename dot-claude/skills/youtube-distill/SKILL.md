---
name: youtube-distill
description: Analyse a YouTube video by driving Claude in Chrome to Gemini, which reads the video directly from its URL, then interrogate that reading over up to five differentiated follow-up turns and distil it into a fixed contract with a summary and search-ready takeaways. Triggers on "analyse this video", "what does this talk say", "distil this youtube", "summarise this video", a YouTube URL pasted or attached with or without a question, or /youtube-distill. Records what is quoted versus what is a model's reading, and which claims stayed inferred.
---

# YouTube distill

Turn a video into a small, checkable artifact instead of a summary nobody re-reads.

The mechanism is a browser round trip: Claude in Chrome opens Gemini, hands it the
YouTube URL with a fixed question, and reads the answer back. Gemini is used because it
reads the video itself from the URL rather than a scraped transcript, which is a
capability the local session does not have.

## What Gemini can and cannot do here, measured before relying on it

- It accepts a YouTube URL directly and reasons over the video.
- **It cannot produce a verbatim transcript.** It summarises and answers; it does not
  return the words in order. So nothing it returns may be presented as a quotation.
- Public videos only. Private and unlisted fail.
- One video URL per request, and a daily cap around eight hours of video.
- Timestamps use `MM:SS`, and it will honour them if you ask about a specific moment.

The consequence that shapes this whole skill: **the output is a model's reading of a
video, not the video.** A timestamp Gemini returns is a POINTER TO GO CHECK, never
evidence on its own. Anything load-bearing gets opened at that timestamp by a human or
by a second pass before it is repeated as fact.

## Step 1: name the research phase before writing the question

The question changes completely depending on why you are watching. Three phases, each
needing a different mind, from Neel Nanda's research process
(https://www.lesswrong.com/posts/hjMy4ZxS5ogA9cTYK/how-i-think-about-my-research-process-explore-understand):

- **Explore.** You do not yet know the right question. The goal is to learn the shape of
  the problem space without trying to confirm anything. Ask for the map, the vocabulary,
  and the disagreements. Noticing which anomaly is interesting rather than boring is the
  whole skill here.
- **Understand.** You have a hypothesis. The goal is a question that would distinguish it
  from its nearest rival. Ask what the speaker's claim predicts that a competing claim
  does not. Treat every result as false until shown otherwise, and treat an exciting
  result as more likely false, not less.
- **Distill.** You already understand it and need to hand it on. Ask what the shortest
  defensible version is and what to leave out. Distillation is a judgement about what to
  deprioritise, not a compression of everything.

The phases are not a pipeline. Finding a mess during Distill sends you back to Explore,
and that is the normal case rather than a failure.

**Research taste** is the acquired sense of which questions are worth asking at all. It
is trained on small, unambitious attempts, not on one large one. If you cannot say what a
video would change about a decision you are making, that is the signal to skip it.

## Step 2: choose the question by expected information gain, not by coverage

Do not ask for a summary. A summary maximises coverage, and coverage is the wrong
objective: it returns what you already know alongside what you do not, at equal length.

Pick the question whose ANSWER YOU CANNOT PREDICT. Formally this is expected information
gain, the drop in entropy from prior to posterior once the answer is known
(https://arxiv.org/abs/2406.17453). Practically, the test is one sentence:

> Write down what you expect the answer to be. If you can, the question is worth little.
> Ask the one where you cannot.

Two corollaries worth keeping. A highly informative question is useless if the source
cannot answer it, so weight by answerability as well as by information. And a question
that can only be answered "yes" carries no information at all, whatever it feels like.

## Step 3: run it

Load the browser tools in ONE ToolSearch call, then:

1. `tabs_context_mcp` with `createIfEmpty: true`. If several browsers are connected you
   MUST ask which one before acting.
2. Navigate to `https://gemini.google.com/app`.
3. Paste the contract below with the URL substituted, then read the answer with
   `get_page_text` rather than screenshots. Text is cheaper and exact.
4. If the answer is truncated or the page is still streaming, re-read rather than
   guessing. Never fill a gap from your own knowledge of the topic: that is the failure
   this skill exists to prevent, because a plausible sentence you wrote is
   indistinguishable in the artifact from something the video said.

## The contract sent to Gemini

Keep it minimal and fixed. A stable contract makes two videos comparable; a bespoke
prompt per video makes every artifact a one-off.

```
Watch this video and answer ONLY the following. Do not summarise.

URL: <youtube url>

1. THESIS. The single claim the video is arguing for, in one sentence. If it argues
   for nothing, say so.
2. MECHANISM. How the thing actually works, in at most five sentences. Concrete over
   abstract. If a mechanism is asserted but never explained, say which.
3. EVIDENCE. What is offered as support, and of what kind: measurement, demo,
   anecdote, appeal to authority, or none. Give MM:SS for each.
4. LOAD-BEARING TIMESTAMPS. At most five MM:SS pointers where a claim I would repeat
   is actually made, so I can verify them myself.
5. DISAGREEMENT. Anything the speaker presents as settled that is actually contested,
   and anything they explicitly disagree with.
6. VOCABULARY. The exact terms, tool names, paper titles and people named, spelled as
   said. This is for search, so precision beats readability.
7. WHAT IS NOT HERE. What a viewer would wrongly assume was covered.
8. CONFIDENCE. For each of 1 to 3, say whether you are reading it from the video or
   inferring it.
9. SUMMARY. Only now, and last: six sentences of plain summary for someone who will
   never watch it.

If you cannot access the video, say exactly that. Do not answer from the title.
```

Item 8 is the one people delete first and it is the one that matters. Without it the
artifact cannot distinguish what the video said from what the model filled in.

Item 9 sits last on purpose and the order is the whole point. Step 2 argues against
summaries because coverage returns what you already know at the same length as what you
do not, and that argument still holds. What it rules out is summary as THE question, not
summary as a field. Asked after items 1 to 8 it costs one paragraph and gives you
something to paste to a person who was not going to watch the video anyway. Asked first
it becomes the frame everything else is squeezed into, which is the failure. If you ever
find yourself moving item 9 up the list, that is the signal to reread step 2.

## Step 3b: the follow-up turns, at most five, usually fewer

One round trip gets you the model's first reading. That reading is where it is most
confident and least checked, so the follow-ups are the part that earns the session.

**Every follow-up must ask something the previous answer did not already settle.** This
is not a style note. Step 5 below states that re-asking the same question of the same
model produces agreement rather than confirmation, so an undifferentiated loop makes the
artifact look five times better verified while adding nothing. A loop with a count and no
exit predicate spends five turns on every video regardless.

The previous answer tells you what to ask next. Draw each follow-up from one of these,
in this priority order:

1. **An item 8 inference.** Anything the model marked as inferred rather than read is the
   highest-value target, because it is exactly where the artifact is currently claiming
   more than the video supports. Ask for the moment in the video that grounds it, or for
   an explicit statement that no such moment exists.
2. **An item 7 gap** that matters for your decision. Not every gap does. A gap you were
   never going to act on is not worth a turn.
3. **A contested point from item 5**, asked as what the speaker would say to the strongest
   objection. This surfaces whether the video engages the objection or ignores it.
4. **A load-bearing number or name from item 3 or 6**, asked back in a form that would
   expose a hallucination: what units, what baseline, whose paper, what year.

**Stop when the next follow-up would come from none of those four, or at five, whichever
is first.** Two turns settling a real inference beats five turns of polite elaboration,
and a video whose first answer had no item 8 inferences and no gaps you care about is
finished at one turn. Record the turn count in the artifact so a thin run is visible as
thin rather than passing for a thorough one.

Two failure modes to watch, both of which look like progress:

- The model agreeing with your follow-up because you phrased it as a leading question.
  Ask "what does the video say about X" rather than "doesn't the video say X".
- The model answering a follow-up from general knowledge once the video is several turns
  back in the conversation. If an answer stops citing MM:SS, that is the tell. Ask it
  directly whether it is still reading the video, and mark the answer accordingly.

## Step 4: the artifact

Write one file. It is short on purpose.

```markdown
# <title> (<channel>, <duration>)
Source: <url>          Read by: Gemini via browser, <date>
Phase: explore | understand | distill
Turns: <n> of 5, stopped because <exhausted the four sources | hit the ceiling>
Question asked, and why its answer was unpredictable: <one line>

THESIS
MECHANISM
EVIDENCE          (kind + MM:SS)
CHECK THESE       (<= 5 timestamps, unverified until opened)
DISAGREEMENT
SEARCH TERMS      (exact spellings, for finding this again and for the next query)
NOT COVERED
STILL INFERRED    Item 8 inferences the follow-ups did not manage to ground. Empty is a
                  result; so is a long list, and the long list is the honest one more often.
SUMMARY           Six sentences, from contract item 9.
DECISION          What this changes. If nothing, say "nothing" and keep the file anyway.
```

`SEARCH TERMS` is the row that earns the artifact's keep. Six months later nobody rereads
a summary, but the exact spelling of a tool or a paper is what makes the thing findable.

`DECISION` saying "nothing" is a real and useful outcome. A file that always finds a
decision is a file that invents them.

## Step 5: verify before it becomes a claim

Anything that will be repeated as fact gets one of these before it leaves the artifact:

- Open the timestamp and confirm it.
- Or search for the primary source. A video citing a paper is not the paper. If the
  video names a benchmark, the benchmark's own page settles the number.
- Or mark it `unverified` in the artifact and keep it marked.

For a claim that would change a decision, do a second pass with a DIFFERENT question
rather than re-asking the same one. Re-asking the same question of the same model
produces agreement, not confirmation.

## Boundaries

- **The trigger is advisory, not enforced.** Measured 2026-08-01: the description above is
  matched by the model at the start of a turn, and `~/.claude/settings.json` has two
  UserPromptSubmit hooks, neither of which looks at URLs. So a pasted YouTube link invokes
  this skill only if the model decides the turn is about the video, and a link pasted as
  background to some other request will correctly not trigger it. Nothing in this file can
  change that. Deterministic firing would need a UserPromptSubmit hook that matches a
  YouTube URL and injects the instruction, which is a harness change with its own gate,
  not a skill edit. Until then, `/youtube-distill` is the reliable way to force it.
- Never present Gemini's words as the speaker's words. It cannot transcribe.
- Do not send private repository content, credentials or personal data into the browser
  prompt. The URL and the fixed contract are all that goes.
- One video per run. The daily cap is real and a batch will fail partway with no clear
  error.
- If the video is unavailable, record that and stop. Do not answer from the title, the
  channel, or prior knowledge of the topic.
