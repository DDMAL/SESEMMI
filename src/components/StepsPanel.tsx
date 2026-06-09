"use client";

import { Fragment, useEffect, useState, type ReactNode } from "react";
import type { Step, StepStatus } from "@/hooks/useTranslate";

// Warm, present-tense phrases shown (and rotated) while a stage is actively running,
// so the status line feels alive rather than static.
const ACTIVE_PHRASES: Record<string, string[]> = {
  intake: [
    "Getting to know your question",
    "Figuring out what you mean",
    "Reading between the lines",
    "Unpacking your request",
    "Making sense of the wording",
    "Pinpointing what you're after",
    "Sorting out the intent",
    "Mapping out your ask",
    "Catching the details",
    "Listening closely",
  ],
  retrieve: [
    "Digging through the music databases",
    "Gathering the right schema",
    "Finding the relevant pieces",
    "Pulling up the ontology",
    "Tracing the connections",
    "Lining up the entities",
    "Collecting the context",
    "Browsing the catalogues",
    "Matching names to records",
    "Assembling the background",
  ],
  generate: [
    "Composing your SPARQL",
    "Putting the query together",
    "Translating your intent",
    "Shaping the SPARQL",
    "Wiring up the triples",
    "Drafting the query",
    "Crafting the graph patterns",
    "Turning words into SPARQL",
    "Sketching the query",
    "Building the query",
  ],
  validate: [
    "Double-checking the query",
    "Making sure it holds up",
    "Proofreading the SPARQL",
    "Checking the syntax",
    "Looking for typos",
    "Verifying the structure",
    "Testing it against the rules",
    "Tidying up the query",
    "Confirming it parses",
    "Giving it a once-over",
  ],
  execute: [
    "Searching the databases",
    "Fetching your results",
    "Querying the triplestore",
    "Running the search",
    "Combing the records",
    "Gathering the matches",
    "Talking to the triplestore",
    "Pulling the data",
    "Scanning the graphs",
    "Retrieving the rows",
  ],
  judge: [
    "Reviewing the results",
    "Sizing up the answer",
    "Gauging confidence",
    "Weighing the matches",
    "Sanity-checking the output",
    "Judging the quality",
    "Inspecting the rows",
    "Rating the answer",
    "Making sure it fits",
    "Scoring the results",
  ],
};

function Icon({ d, className = "h-4 w-4" }: { d: string; className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path d={d} />
    </svg>
  );
}

// The canonical pipeline stages, in order. Keys match the backend step keys
// emitted over SSE (see llm-service/app/main.py _STEP_LABELS).
const STAGES: { key: string; short: string; friendly: string; icon: ReactNode }[] = [
  {
    key: "intake",
    short: "Route",
    friendly: "Understanding your question",
    // magnifying glass
    icon: <Icon d="M21 21l-4.35-4.35M11 19a8 8 0 100-16 8 8 0 000 16z" />,
  },
  {
    key: "retrieve",
    short: "Context",
    friendly: "Gathering schema",
    // book-open
    icon: (
      <Icon d="M12 6.5A6.5 6.5 0 005.5 4 2 2 0 003.5 6v11a2 2 0 002 2 6.5 6.5 0 016.5 2 6.5 6.5 0 016.5-2 2 2 0 002-2V6a2 2 0 00-2-2A6.5 6.5 0 0012 6.5zm0 0V20" />
    ),
  },
  {
    key: "generate",
    short: "Generate",
    friendly: "Writing the SPARQL query",
    // code-bracket
    icon: <Icon d="M17 7l4 5-4 5M7 7l-4 5 4 5m7-13l-4 16" />,
  },
  {
    key: "validate",
    short: "Validate",
    friendly: "Checking it's valid",
    // shield-check
    icon: <Icon d="M9 12.5l2 2 4-4.5M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z" />,
  },
  {
    key: "execute",
    short: "Run",
    friendly: "Running on the database",
    // play
    icon: (
      <Icon d="M6 4.75c0-.7.76-1.13 1.36-.77l11 7.25a.9.9 0 010 1.54l-11 7.25A.9.9 0 016 19.5V4.75z" />
    ),
  },
  {
    key: "judge",
    short: "Score",
    friendly: "Scoring confidence",
    // sparkles
    icon: (
      <Icon d="M9 4l1.2 3.4L13.5 8.6 10.2 9.8 9 13.2 7.8 9.8 4.5 8.6 7.8 7.4 9 4zm9 9l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7.7-2z" />
    ),
  },
];

type StageState = StepStatus | "upcoming";

interface StepsPanelProps {
  steps: Step[];
  isPending: boolean;
}

function Dot({ state, icon }: { state: StageState; icon: ReactNode }) {
  const base =
    "flex h-9 w-9 items-center justify-center rounded-full transition-all group-hover:scale-110";
  const gradient = "linear-gradient(135deg, #4f46e5, #7c3aed)";

  if (state === "error")
    return (
      <span
        className={`${base} text-white group-hover:shadow-[0_0_0_4px_rgba(239,68,68,0.22)]`}
        style={{ background: "#ef4444" }}
      >
        <span className="text-sm leading-none">✕</span>
      </span>
    );
  if (state === "running")
    return (
      <span
        className={`${base} animate-pulse text-white group-hover:shadow-[0_0_0_4px_rgba(99,102,241,0.32)]`}
        style={{ background: gradient, boxShadow: "0 0 0 4px rgba(99,102,241,0.18)" }}
      >
        {icon}
      </span>
    );
  if (state === "done")
    return (
      <span
        className={`${base} text-white group-hover:shadow-[0_0_0_4px_rgba(99,102,241,0.28)]`}
        style={{ background: gradient }}
      >
        {icon}
      </span>
    );
  // upcoming
  return (
    <span
      className={`${base} text-indigo-300 group-hover:shadow-[0_0_0_4px_rgba(99,102,241,0.15)]`}
      style={{ background: "rgba(99,102,241,0.08)", border: "1px solid rgba(99,102,241,0.22)" }}
    >
      {icon}
    </span>
  );
}

// One connector spans the whole gap between two nodes. Its look reflects the node
// it leads INTO: `running` shows a single shine of colour sweeping forward; `done`
// is a solid filled line reaching the next node; otherwise a faint track.
function Connector({ state }: { state: StageState }) {
  if (state === "running") return <div className="step-connector-shine h-1 flex-1 rounded-full" />;
  return (
    <div
      className="h-1 flex-1 rounded-full"
      style={{
        background: state === "done" ? "rgba(99,102,241,0.6)" : "rgba(99,102,241,0.15)",
      }}
    />
  );
}

// Friendly presentation of the final judge confidence.
const CONFIDENCE: Record<
  string,
  {
    label: string;
    hint: string;
    bars: number;
    fill: string;
    text: string;
    bg: string;
    icon: ReactNode;
  }
> = {
  high: {
    label: "High confidence",
    hint: "Looks accurate.",
    bars: 3,
    fill: "#10b981",
    text: "#047857",
    bg: "rgba(16,185,129,0.10)",
    // check-badge
    icon: <Icon d="M9 12.5l2 2 4-4.5M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z" />,
  },
  medium: {
    label: "Medium confidence",
    hint: "Likely correct — worth a review.",
    bars: 2,
    fill: "#f59e0b",
    text: "#b45309",
    bg: "rgba(245,158,11,0.12)",
    // exclamation-circle
    icon: <Icon d="M12 9v4m0 4h.01M12 21a9 9 0 100-18 9 9 0 000 18z" />,
  },
  low: {
    label: "Low confidence",
    hint: "May be off — review before trusting.",
    bars: 1,
    fill: "#f43f5e",
    text: "#be123c",
    bg: "rgba(244,63,94,0.10)",
    // warning triangle
    icon: (
      <Icon d="M12 9v4m0 4h.01M10.3 3.9L1.8 18a2 2 0 001.7 3h17a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z" />
    ),
  },
};

function ConfidenceCard({ level }: { level: keyof typeof CONFIDENCE }) {
  const c = CONFIDENCE[level];
  return (
    <div className="mt-3">
      <div className="mb-1 text-[10px] font-semibold tracking-widest text-slate-400 uppercase">
        Result
      </div>
      <div
        className="flex items-center gap-3 rounded-xl px-3 py-2.5"
        style={{ background: c.bg, border: `1px solid ${c.fill}33` }}
      >
        <span style={{ color: c.fill }}>{c.icon}</span>
        <div className="min-w-0 flex-1">
          <div className="text-sm font-semibold" style={{ color: c.text }}>
            {c.label}
          </div>
          <div className="text-[11px] text-slate-500">{c.hint}</div>
        </div>
        <div className="flex items-end gap-0.5" aria-hidden="true">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="w-1.5 rounded-sm"
              style={{
                height: `${8 + i * 4}px`,
                background: i < c.bars ? c.fill : "rgba(100,116,139,0.2)",
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

const STATUS_PILL: Record<StageState, { label: string; color: string; bg: string }> = {
  running: { label: "Running", color: "#4f46e5", bg: "rgba(99,102,241,0.12)" },
  done: { label: "Done", color: "#047857", bg: "rgba(16,185,129,0.12)" },
  error: { label: "Error", color: "#be123c", bg: "rgba(244,63,94,0.12)" },
  waiting: { label: "Pending", color: "#64748b", bg: "rgba(100,116,139,0.12)" },
  upcoming: { label: "Pending", color: "#64748b", bg: "rgba(100,116,139,0.12)" },
};

function NodeDetail({
  stage,
  status,
  detail,
  tokens,
  onClose,
}: {
  stage: (typeof STAGES)[number];
  status: StageState;
  detail: string;
  tokens: string;
  onClose: () => void;
}) {
  const pill = STATUS_PILL[status];
  const ran = status !== "upcoming";
  return (
    <div
      className="mt-3 rounded-xl px-3 py-2.5"
      style={{ background: "rgba(99,102,241,0.06)", border: "1px solid rgba(99,102,241,0.15)" }}
    >
      <div className="flex items-center gap-2">
        <span className="text-indigo-500">{stage.icon}</span>
        <span className="text-sm font-semibold text-slate-700">{stage.friendly}</span>
        <span
          className="rounded-full px-1.5 py-0.5 text-[9px] font-semibold tracking-wide uppercase"
          style={{ color: pill.color, background: pill.bg }}
        >
          {pill.label}
        </span>
        <button
          onClick={onClose}
          aria-label="Close detail"
          className="ml-auto cursor-pointer text-slate-400 transition-colors hover:text-slate-600"
        >
          ✕
        </button>
      </div>
      <div className="mt-1.5">
        {!ran ? (
          <p className="text-[11px] text-slate-400">Hasn’t run yet.</p>
        ) : stage.key === "generate" && tokens ? (
          <pre
            className="max-h-40 overflow-y-auto rounded-lg p-2.5 font-mono text-[10px] leading-relaxed break-all whitespace-pre-wrap text-slate-600"
            style={{ background: "rgba(99,102,241,0.06)" }}
          >
            {tokens}
          </pre>
        ) : detail ? (
          <p className="text-xs text-slate-500">{detail}</p>
        ) : (
          <p className="text-[11px] text-slate-400">No additional detail.</p>
        )}
      </div>
    </div>
  );
}

export function StepsPanel({ steps, isPending }: StepsPanelProps) {
  const [expanded, setExpanded] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  // Drives the rotating phrase + animated ellipsis on the live status line.
  const [tick, setTick] = useState(0);
  const running = isPending && steps.some((s) => s.status === "running");
  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => setTick((t) => t + 1), 450);
    return () => clearInterval(id);
  }, [running]);

  if (steps.length === 0) return null;

  // Latest status wins per stage key (repair loop can re-run earlier stages).
  const statusByKey = new Map<string, StepStatus>();
  const detailByKey = new Map<string, string>();
  for (const s of steps) {
    statusByKey.set(s.step, s.status);
    if (s.detail) detailByKey.set(s.step, s.detail);
  }

  const stageStates: StageState[] = STAGES.map((st) => statusByKey.get(st.key) ?? "upcoming");
  const doneCount = stageStates.filter((s) => s === "done").length;
  const runningIndex = stageStates.findIndex((s) => s === "running");
  const errorIndex = stageStates.findIndex((s) => s === "error");
  const allDone = doneCount === STAGES.length;

  const activeIndex =
    errorIndex !== -1
      ? errorIndex
      : runningIndex !== -1
        ? runningIndex
        : Math.max(0, doneCount - 1);
  const activeStage = STAGES[activeIndex];
  const activeDetail = detailByKey.get(activeStage.key) ?? "";
  const isRetry =
    runningIndex !== -1 && runningIndex < doneCount && activeStage.key !== STAGES[doneCount]?.key;

  const counter = allDone
    ? "Done"
    : errorIndex !== -1
      ? "Failed"
      : `Step ${Math.min(runningIndex === -1 ? doneCount + 1 : runningIndex + 1, STAGES.length)} of ${STAGES.length}`;

  const generateTokens = steps.find((s) => s.step === "generate")?.tokens ?? "";
  const generateRunning = statusByKey.get("generate") === "running";

  // Click-to-reveal: the currently selected node's data (null = nothing open).
  const selStage = selected ? (STAGES.find((s) => s.key === selected) ?? null) : null;
  const selTokens = selStage
    ? ([...steps].reverse().find((s) => s.step === selStage.key)?.tokens ?? "")
    : "";

  // Live status line: rotate warm phrases + animated ellipsis while running.
  const activeRunning = stageStates[activeIndex] === "running";
  const phrases = ACTIVE_PHRASES[activeStage.key] ?? [activeStage.friendly];
  const phraseIndex = activeRunning ? Math.floor(tick / 6) % phrases.length : 0;
  const liveText = allDone
    ? "All set!"
    : activeRunning
      ? phrases[phraseIndex]
      : activeStage.friendly;

  // Final confidence arrives as the judge step's detail (e.g. "high").
  const confidenceLevel = (detailByKey.get("judge") ?? "").toLowerCase();
  const hasConfidence = confidenceLevel in CONFIDENCE;
  // Don't repeat the raw "high/medium/low" on the judge line — the card shows it.
  const showActiveDetail = !(activeStage.key === "judge" && hasConfidence) && Boolean(activeDetail);

  return (
    <div
      className="overflow-hidden rounded-xl px-3 py-3"
      style={{ background: "rgba(79,70,229,0.04)", border: "1px solid rgba(99,102,241,0.15)" }}
    >
      {/* Header: status word + counter */}
      <div className="mb-3 flex items-center justify-between">
        <span className="text-[10px] font-semibold tracking-widest text-indigo-400 uppercase">
          {isPending ? "Translating…" : allDone ? "Complete" : counter}
        </span>
        <span className="text-[10px] font-medium text-slate-400">{counter}</span>
      </div>

      {/* Horizontal stepper — single connector per gap, leading INTO each node */}
      <div className="flex items-center">
        {STAGES.map((st, i) => (
          <Fragment key={st.key}>
            {i > 0 && <Connector state={stageStates[i]} />}
            <button
              type="button"
              title={st.friendly}
              onClick={() => setSelected((cur) => (cur === st.key ? null : st.key))}
              aria-label={`Show ${st.friendly} detail`}
              aria-pressed={selected === st.key}
              className={`group shrink-0 cursor-pointer rounded-full transition-all focus:outline-none ${
                selected === st.key ? "ring-2 ring-indigo-400 ring-offset-2" : ""
              }`}
            >
              <Dot state={stageStates[i]} icon={st.icon} />
            </button>
          </Fragment>
        ))}
      </div>
      {/* Labels — same flex rhythm so each sits centred under its node */}
      <div className="mt-1.5 flex items-start">
        {STAGES.map((st, i) => {
          const state = stageStates[i];
          return (
            <Fragment key={st.key}>
              {i > 0 && <div className="flex-1" />}
              <span
                className={`w-9 shrink-0 text-center text-xs font-semibold whitespace-nowrap ${
                  state === "upcoming"
                    ? "text-slate-500"
                    : state === "error"
                      ? "text-red-600"
                      : "text-slate-800"
                }`}
              >
                {st.short}
              </span>
            </Fragment>
          );
        })}
      </div>
      <p className="mt-1 text-right text-[10px] text-slate-400" aria-hidden="true">
        Click a node for details
      </p>

      {/* Click-to-reveal node detail (hidden until a node is clicked) */}
      {selStage && (
        <NodeDetail
          stage={selStage}
          status={statusByKey.get(selStage.key) ?? "upcoming"}
          detail={detailByKey.get(selStage.key) ?? ""}
          tokens={selTokens}
          onClose={() => setSelected(null)}
        />
      )}

      {/* Active stage detail line */}
      <div className="mt-2.5 flex items-baseline gap-2">
        <span
          className={`text-xs font-medium ${errorIndex !== -1 ? "text-red-500" : "text-slate-700"}`}
        >
          {activeRunning ? (
            <span
              key={`${activeStage.key}-${phraseIndex}`}
              className="phrase-enter inline-block"
              aria-label={liveText}
            >
              {liveText.split("").map((ch, i) => (
                <span
                  key={i}
                  aria-hidden="true"
                  className="phrase-letter"
                  style={{ animationDelay: `${i * 0.05}s` }}
                >
                  {ch === " " ? " " : ch}
                </span>
              ))}
            </span>
          ) : (
            <span key={`${activeStage.key}-${phraseIndex}`} className="phrase-enter inline-block">
              {liveText}
            </span>
          )}
          {activeRunning && (
            <span className="ml-0.5 inline-block" aria-hidden="true">
              {[0, 160, 320].map((delay) => (
                <span key={delay} className="phrase-dot" style={{ animationDelay: `${delay}ms` }}>
                  ·
                </span>
              ))}
            </span>
          )}
          {isRetry && (
            <span className="ml-1.5 rounded-full bg-amber-100 px-1.5 py-0.5 text-[9px] font-semibold tracking-wide text-amber-600 uppercase">
              retrying
            </span>
          )}
        </span>
        {showActiveDetail && <span className="text-[11px] text-slate-400">{activeDetail}</span>}
      </div>

      {/* Final confidence — friendly result card */}
      {hasConfidence && <ConfidenceCard level={confidenceLevel as keyof typeof CONFIDENCE} />}

      {/* Collapsible peek at the SPARQL being written */}
      {generateTokens && (
        <div className="mt-2">
          <button
            onClick={() => setExpanded((v) => !v)}
            className="flex cursor-pointer items-center gap-1 text-[11px] font-medium text-indigo-500 transition-colors hover:text-indigo-600"
            aria-expanded={expanded}
          >
            <span className="text-[9px]">{expanded ? "▾" : "▸"}</span>
            {expanded ? "Hide query" : "View query"}
            {generateRunning && !expanded && (
              <span className="animate-pulse text-indigo-300">writing…</span>
            )}
          </button>
          {expanded && (
            <pre
              className="mt-1.5 max-h-40 overflow-y-auto rounded-lg p-2.5 font-mono text-[10px] leading-relaxed break-all whitespace-pre-wrap text-slate-600"
              style={{ background: "rgba(99,102,241,0.06)" }}
            >
              {generateTokens}
              {generateRunning && <span className="animate-pulse text-indigo-400">▋</span>}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
