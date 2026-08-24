"use client";

import { useEffect, useMemo, useState } from "react";

type Screen = "dashboard" | "quest" | "talents" | "codex" | "research" | "review" | "admin";
type Tree = "oracle" | "architect" | "warden" | "discovery";
type Quest = { id: Tree; time: string; title: string; subtitle: string; duration: string; accent: string; xp: number };
type SavedState = { xp: Record<Tree, number>; completed: string[]; streak: number; recovery: boolean; lastAnswer?: string };

const quests: Quest[] = [
  { id: "oracle", time: "08:00", title: "Oracle Quest", subtitle: "Calibration under uncertainty", duration: "12 min", accent: "violet", xp: 4 },
  { id: "architect", time: "12:00", title: "Crafting Quest", subtitle: "Hash maps in tool registries", duration: "10 min", accent: "copper", xp: 0 },
  { id: "warden", time: "17:00", title: "Azure Dungeon", subtitle: "Managed Identity boundaries", duration: "14 min", accent: "blue", xp: 0 },
  { id: "discovery", time: "22:00", title: "Lore Quest", subtitle: "Evidence before novelty", duration: "12 min", accent: "gold", xp: 0 },
];

const concepts = [
  { title: "Poisson Distribution", he: "התפלגות פואסון", tree: "Probability", score: 14, due: true, meaning: "Models event counts in a fixed interval when events occur independently at a stable average rate." },
  { title: "Calibration", he: "כיול", tree: "Probability", score: 11, due: false, meaning: "Aligns predicted probabilities with observed frequencies." },
  { title: "Brier Score", he: "מדד ברייר", tree: "Probability", score: 8, due: true, meaning: "Measures the squared error of probabilistic predictions." },
  { title: "Hash Map", he: "טבלת גיבוב", tree: "Architecture", score: 10, due: false, meaning: "Maps keys to values for near-constant-time lookup." },
  { title: "Managed Identity", he: "זהות מנוהלת", tree: "Cloud", score: 7, due: true, meaning: "Lets Azure resources authenticate without embedded credentials." },
  { title: "Walk-forward Validation", he: "אימות מתקדם בזמן", tree: "Probability", score: 5, due: false, meaning: "Tests time-dependent models without leaking future information." },
];

const nav: { id: Screen; label: string; mark: string }[] = [
  { id: "dashboard", label: "Sanctum", mark: "SC" }, { id: "talents", label: "Talent Trees", mark: "TT" },
  { id: "codex", label: "Codex", mark: "CX" }, { id: "research", label: "Research", mark: "RA" },
  { id: "review", label: "Weekly Review", mark: "WR" }, { id: "admin", label: "Curriculum", mark: "CR" },
];

const initialState: SavedState = { xp: { oracle: 4, architect: 0, warden: 0, discovery: 0 }, completed: [], streak: 1, recovery: true };

function Ring({ value, label, color }: { value: number; label: string; color: string }) {
  return <div className="ring-wrap"><div className="ring" style={{ "--p": `${value * 10}%`, "--ring": color } as React.CSSProperties}><span>{value}</span><small>/ 10</small></div><p>{label}</p></div>;
}

function ProgressBar({ value, tone = "gold" }: { value: number; tone?: string }) {
  return <div className="progress"><span className={tone} style={{ width: `${Math.min(value * 10, 100)}%` }} /></div>;
}

export default function LivingCodex({ userKey, displayName }: { userKey: string; displayName: string }) {
  const [screen, setScreen] = useState<Screen>("dashboard");
  const [state, setState] = useState<SavedState>(initialState);
  const [activeQuest, setActiveQuest] = useState<Quest>(quests[0]);
  const [answer, setAnswer] = useState("");
  const [confidence, setConfidence] = useState(70);
  const [reasoning, setReasoning] = useState("");
  const [attempts, setAttempts] = useState(0);
  const [feedback, setFeedback] = useState<"idle" | "retry" | "correct" | "revealed">("idle");
  const [query, setQuery] = useState("");
  const [graph, setGraph] = useState(false);
  const [selectedConcept, setSelectedConcept] = useState(concepts[0]);
  const [mobileNav, setMobileNav] = useState(false);
  const storageKey = `living-codex:${userKey}`;

  useEffect(() => {
    const raw = localStorage.getItem(storageKey);
    if (raw) setState(JSON.parse(raw));
    fetch("/api/state").then(r => r.ok ? r.json() : null).then(data => data?.state && setState(data.state)).catch(() => null);
  }, [storageKey]);

  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify(state));
    const timer = setTimeout(() => fetch("/api/state", { method: "PUT", headers: { "content-type": "application/json" }, body: JSON.stringify({ state }) }).catch(() => null), 500);
    return () => clearTimeout(timer);
  }, [state, storageKey]);

  const filtered = useMemo(() => concepts.filter(c => `${c.title} ${c.he} ${c.tree}`.toLowerCase().includes(query.toLowerCase())), [query]);

  function openQuest(q: Quest) {
    setActiveQuest(q); setAnswer(""); setReasoning(""); setAttempts(0); setFeedback("idle"); setScreen("quest"); setMobileNav(false);
  }

  function submitAnswer() {
    if (!answer || feedback === "correct" || feedback === "revealed") return;
    const nextAttempt = attempts + 1; setAttempts(nextAttempt);
    if (answer === "A") {
      const earned = nextAttempt === 1 ? 2 : 1;
      setFeedback("correct");
      setState(s => ({ ...s, xp: { ...s.xp, [activeQuest.id]: s.xp[activeQuest.id] + earned }, completed: [...new Set([...s.completed, activeQuest.id])], recovery: false, lastAnswer: new Date().toISOString() }));
    } else if (nextAttempt >= 2) setFeedback("revealed");
    else setFeedback("retry");
  }

  return <div className="app-shell">
    <aside className={mobileNav ? "sidebar open" : "sidebar"}>
      <button className="mobile-close" onClick={() => setMobileNav(false)} aria-label="Close navigation">Close</button>
      <div className="brand"><div className="sigil">LC</div><div><strong>The Living Codex</strong><span>Systems Artificer</span></div></div>
      <nav aria-label="Primary navigation">{nav.map(item => <button key={item.id} className={screen === item.id ? "active" : ""} onClick={() => { setScreen(item.id); setMobileNav(false); }}><span>{item.mark}</span>{item.label}</button>)}</nav>
      <div className="sidebar-foot"><div className="rank-mark">II</div><div><span>Current rank</span><strong>Apprentice</strong><small>6 knowledge to Scholar</small></div></div>
    </aside>

    <main>
      <header className="topbar">
        <button className="menu" onClick={() => setMobileNav(true)} aria-label="Open navigation">Menu</button>
        <div><span className="eyebrow">Jerusalem · The twelfth of July</span><h1>{screen === "dashboard" ? `Welcome back, ${displayName}` : nav.find(n => n.id === screen)?.label ?? activeQuest.title}</h1></div>
        <div className="top-status"><div><span>Journey</span><strong>{state.streak} day</strong></div><div className="avatar">SB</div></div>
      </header>

      {screen === "dashboard" && <div className="page dashboard-page">
        <section className="hero-panel">
          <div className="hero-copy"><span className="chapter">Chapter I · Foundations</span><h2>Continue the work.<br /><em>Keep the knowledge alive.</em></h2><p>Four focused practices. No debt to yesterday. The Codex grows whenever you return.</p><div className="hero-actions"><button className="primary" onClick={() => openQuest(quests.find(q => !state.completed.includes(q.id)) ?? quests[0])}>Continue Journey</button><span>Next session · {quests.find(q => !state.completed.includes(q.id))?.duration ?? "Review"}</span></div></div>
          <div className="artificer-seal" aria-label="Systems Artificer milestone seal"><div className="orbit one" /><div className="orbit two" /><div className="core">SA</div><span>First session milestone</span></div>
        </section>

        <section className="status-strip"><div><span className="status-dot" />Recovery path active</div><p>Complete any available quest to restore your rhythm. No knowledge penalty.</p><button onClick={() => openQuest(quests[0])}>Begin recovery</button></section>

        <div className="section-head"><div><span className="eyebrow">Daily practice</span><h2>Available Quests</h2></div><span>Asia/Jerusalem</span></div>
        <section className="quest-grid">{quests.map(q => <button className={`quest-card ${q.accent}`} key={q.id} onClick={() => openQuest(q)}><div className="quest-time"><span>{q.time}</span><i>{state.completed.includes(q.id) ? "Completed" : "Available"}</i></div><div className="quest-glyph">{q.id === "oracle" ? "PO" : q.id === "architect" ? "AA" : q.id === "warden" ? "CW" : "DL"}</div><h3>{q.title}</h3><p>{q.subtitle}</p><footer><span>{q.duration}</span><strong>Enter</strong></footer></button>)}</section>

        <section className="dashboard-lower">
          <div className="panel mastery-panel"><div className="panel-title"><div><span className="eyebrow">Mastery</span><h3>Three Disciplines</h3></div><button onClick={() => setScreen("talents")}>View trees</button></div><div className="rings"><Ring value={state.xp.oracle} label="Probability Oracle" color="#8770a7" /><Ring value={state.xp.architect} label="Agent Architect" color="#a86d4f" /><Ring value={state.xp.warden} label="Cloud Warden" color="#527aa4" /></div></div>
          <div className="panel focus-panel"><span className="eyebrow">Fragile knowledge</span><h3>Weakest mastery node</h3><div className="focus-row"><div className="mini-sigil">BV</div><div><strong>Brier Score</strong><span>Apply · 1 of 4</span></div><b>Repair</b></div><p>Your recognition is sound. Next, practice comparing two calibrated MatchIQ forecasts.</p><button onClick={() => openQuest(quests[0])}>Start a focused recall</button></div>
        </section>

        <section className="recent"><div className="section-head"><div><span className="eyebrow">Persistent memory</span><h2>Recent Codex Discoveries</h2></div><button onClick={() => setScreen("codex")}>Open full Codex</button></div><div className="discovery-grid">{concepts.slice(0, 3).map(c => <button key={c.title} onClick={() => { setSelectedConcept(c); setScreen("codex"); }}><span>{c.tree}</span><h3>{c.title}</h3><p>{c.he}</p><ProgressBar value={Math.ceil(c.score / 2)} tone={c.tree === "Cloud" ? "blue" : "violet"} /></button>)}</div></section>
      </div>}

      {screen === "quest" && <div className="page quest-page">
        <button className="back" onClick={() => setScreen("dashboard")}>Back to Sanctum</button>
        <div className="quest-layout"><section className="quest-main panel"><div className="quest-heading"><span className="chapter">{activeQuest.time} · {activeQuest.duration}</span><h2>{activeQuest.title}</h2><p>{activeQuest.subtitle}</p><div className="stepper"><span className="done" /><span className="current" /><span /><span /><span /></div></div>
          <div className="warmup"><span>Warm-up · Recognize</span><h3>A football league has a mean of 2.8 goals per match and variance of 2.9. Which statement is most accurate?</h3><div className="answers">{[
            ["A", "The data is reasonably consistent with a Poisson model"], ["B", "The data is strongly overdispersed"], ["C", "The data is strongly underdispersed"], ["D", "Switch immediately to Negative Binomial"]
          ].map(([key, text]) => <button key={key} className={answer === key ? "selected" : ""} onClick={() => setAnswer(key)} disabled={feedback === "correct" || feedback === "revealed"}><b>{key}</b><span>{text}</span></button>)}</div>
          <label className="confidence"><span>Confidence <strong>{confidence}%</strong></span><input type="range" min="0" max="100" value={confidence} onChange={e => setConfidence(Number(e.target.value))} /></label>
          <label className="reason"><span>Optional reasoning</span><textarea value={reasoning} onChange={e => setReasoning(e.target.value)} placeholder="Why does your answer make sense?" /></label>
          {feedback !== "idle" && <div className={`feedback ${feedback}`}><strong>{feedback === "correct" ? "Sound reasoning" : feedback === "retry" ? "Reconsider the relationship" : "Answer revealed"}</strong><p>{feedback === "retry" ? "Compare the mean and variance directly. You have one more attempt." : "A is correct. When mean and variance are close, the observed counts are reasonably consistent with the Poisson assumption."}</p>{feedback !== "retry" && <small>Overdispersion — פיזור־יתר · variance exceeds what the model expects.</small>}</div>}
          <div className="submit-row"><span>Attempt {Math.min(attempts + 1, 2)} of 2</span><button className="primary" onClick={submitAnswer} disabled={!answer || feedback === "correct" || feedback === "revealed"}>Submit answer</button></div></div>
        </section><aside className="quest-aside"><div className="panel"><span className="eyebrow">Session map</span><ol><li className="active">Spaced recall</li><li>Easy challenge</li><li>Medium challenge</li><li>Interview level</li><li>Project connection</li></ol></div><div className="panel project-link"><span className="eyebrow">MatchIQ connection</span><h3>Goals are counts</h3><p>This assumption decides whether the probability engine can use a simple Poisson baseline or needs a richer variance model.</p></div></aside></div>
      </div>}

      {screen === "talents" && <div className="page"><div className="intro"><span className="eyebrow">Meaningful progression</span><h2>Talent Trees</h2><p>One substantial node unlocks every ten knowledge. Mastery requires evidence across recognition, explanation, application, connection, and challenge.</p></div><div className="tree-grid">{[
        ["Probability Oracle", "violet", ["Measure uncertainty", "Model event counts", "Calibrate belief", "Challenge assumptions"]], ["Agent Architect", "copper", ["Reason in code", "Design reliable interfaces", "Evaluate agents", "Orchestrate systems"]], ["Cloud Warden", "blue", ["Secure identity", "Observe production", "Design for failure", "Govern platforms"]]
      ].map(([title, tone, nodes]) => <section className={`talent-tree ${tone}`} key={title as string}><header><div className="tree-mark">{(title as string).split(" ").map(x => x[0]).join("")}</div><h3>{title as string}</h3></header>{(nodes as string[]).map((node, i) => <button className={i === 0 ? "unlocked" : i === 1 ? "available" : "locked"} key={node}><span>{i + 1}</span><div><strong>{node}</strong><small>{i === 0 ? "Unlocked · evidence recorded" : i === 1 ? "Available at 10 knowledge" : "Prerequisite required"}</small></div></button>)}</section>)}</div></div>}

      {screen === "codex" && <div className="page"><div className="intro split"><div><span className="eyebrow">Knowledge that compounds</span><h2>The Codex</h2><p>Concepts reveal their relationships as you demonstrate mastery.</p></div><button className="secondary" onClick={() => setGraph(!graph)}>{graph ? "List view" : "Graph view"}</button></div><div className="codex-tools"><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search concepts, translations, or disciplines" aria-label="Search Codex" /><button>Due for review</button><button>Project: MatchIQ</button></div>{graph ? <div className="concept-graph panel"><div className="graph-edge e1" /><div className="graph-edge e2" /><div className="graph-edge e3" />{concepts.slice(0, 5).map((c, i) => <button key={c.title} className={`graph-node n${i + 1}`} onClick={() => setSelectedConcept(c)}><span>{c.tree}</span><strong>{c.title}</strong></button>)}</div> : <div className="codex-layout"><div className="concept-list">{filtered.map(c => <button className={selectedConcept.title === c.title ? "active" : ""} key={c.title} onClick={() => setSelectedConcept(c)}><div><span>{c.tree}</span><h3>{c.title}</h3><p>{c.he}</p></div><b>{c.score}/20</b></button>)}</div><article className="concept-detail panel"><span className="eyebrow">{selectedConcept.tree} · concept entry</span><h2>{selectedConcept.title}</h2><h3 lang="he">{selectedConcept.he}</h3><p className="lead">{selectedConcept.meaning}</p><div className="definition"><strong>Why it exists</strong><p>To give engineers a precise tool for reasoning about uncertainty, system behavior, and the gap between expectation and evidence.</p></div><h4>Mastery dimensions</h4>{["Recognize", "Explain", "Apply", "Connect", "Challenge"].map((d, i) => <div className="dimension" key={d}><span>{d}</span><ProgressBar value={Math.max(1, 4 - i)} /><b>{Math.max(1, 4 - i)} / 4</b></div>)}<div className="connections"><strong>Revealed connections</strong><span>MatchIQ</span><span>Calibration</span><span>Model assumptions</span></div></article></div>}</div>}

      {screen === "research" && <div className="page"><div className="intro"><span className="eyebrow">Discovery requires evidence</span><h2>Research Archive</h2><p>Sample entries are deliberately marked. Publication status must be verified from primary sources before a Lore Quest treats a paper as current.</p></div><div className="paper-list">{[
        ["Evaluating Agentic Systems Under Tool Failure", "DEMO ENTRY", "Evaluation", "Promising mechanism; evidence not yet verified"], ["Calibration in Sequential Decision Systems", "DEMO ENTRY", "Probability", "Useful framing; venue intentionally unspecified"], ["Identity Boundaries for Enterprise AI Agents", "DEMO ENTRY", "Cloud", "Strong practical connection; sample content only"]
      ].map((p, i) => <article className="paper panel" key={p[0]}><div className="paper-index">0{i + 1}</div><div><span>{p[1]} · 2026</span><h3>{p[0]}</h3><p>{p[3]}</p><footer><b>{p[2]}</b><button>Open notes</button></footer></div></article>)}</div></div>}

      {screen === "review" && <div className="page"><div className="intro"><span className="eyebrow">Week 28 · July 6–12</span><h2>Weekly Review</h2><p>A calm accounting of what strengthened and what needs another pass.</p></div><div className="review-grid"><div className="panel review-hero"><span className="chapter">The week in evidence</span><strong>12</strong><p>questions attempted across three focused sessions</p><div className="review-stats"><div><b>75%</b><span>first try</span></div><div><b>81%</b><span>confidence</span></div><div><b>+9</b><span>knowledge</span></div></div></div><div className="panel"><span className="eyebrow">Strongest connection</span><h3>Poisson → MatchIQ</h3><p>You explained when the simple count model is defensible and when variance signals a richer model.</p><ProgressBar value={8} tone="violet" /></div><div className="panel"><span className="eyebrow">Sunday repair</span><h3>Confidence calibration</h3><p>Compare confidence with observed correctness across five closed questions.</p><button className="secondary" onClick={() => openQuest(quests[0])}>Prepare repair quest</button></div></div></div>}

      {screen === "admin" && <div className="page"><div className="intro"><span className="eyebrow">Curriculum controls</span><h2>Shape the Academy</h2><p>Deterministic seeded content is active. AI generation is not connected and no claim is made otherwise.</p></div><div className="admin-grid">{[
        ["Quest templates", "4 active", "Warm-up, three challenges, project connection, takeaway and recap"], ["Talent nodes", "12 seeded", "Substantial unlocks across the three disciplines"], ["Translation glossary", "24 terms", "English, concise Hebrew, and plain-language meaning"], ["Paper sources", "Verification required", "Primary sources and publication status rules"], ["XP thresholds", "10 per node", "First attempt 2, second attempt 1, explanation bonus 1"], ["Project contexts", "11 linked", "MatchIQ, MCP, Azure AI, RAG, SQLTok and agent evaluation"]
      ].map(card => <button className="admin-card" key={card[0]}><span>{card[1]}</span><h3>{card[0]}</h3><p>{card[2]}</p><b>Configure</b></button>)}</div><div className="panel engine-note"><div className="engine-light" /><div><span className="eyebrow">Generation architecture</span><h3>Provider adapter ready for a later integration</h3><p>Any generated question must pass single-answer, explanation consistency, translation, duplication, and source-status validation before reaching a quest.</p></div></div></div>}
    </main>
  </div>;
}
