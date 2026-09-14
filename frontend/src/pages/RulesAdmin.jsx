import { useMemo, useState } from "react";
import { EmptyState } from "@/components/shared";

const rules = [
  ["RADIOGRAPH_REQUIRED", "Documentation", "ERROR", "Add a radiograph attachment", 128],
  ["NARRATIVE_REQUIRED", "Documentation", "ERROR", "Add a clinical narrative", 96],
  ["PRE_AUTHORISATION_REQUIRED", "Documentation", "ERROR", "Enter an authorisation number", 73],
  ["UNSUPPORTED_ATTACHMENT_TYPE", "Attachments", "ERROR", "Replace with PDF, JPEG, or PNG", 31],
  ["ATTACHMENT_SIZE_LIMIT", "Attachments", "ERROR", "Compress or replace attachment", 19],
  ["LINE_FEES_DO_NOT_SUM_TO_TOTAL", "Financial", "ERROR", "Set total to line-fee sum", 62],
  ["NON_POSITIVE_FEE", "Financial", "ERROR", "Enter a positive fee", 14],
  ["FEE_EXCEEDS_ALLOWED_AMOUNT", "Financial", "WARNING", "Use allowed amount", 84],
  ["LIKELY_DUPLICATE_CLAIM", "Duplicate", "WARNING", "Review matching claim", 22],
].map(([code, category, severity, fixture, hits]) => ({ code, category, severity, fixture, hits }));

export default function RulesAdmin() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [severity, setSeverity] = useState("");
  const [selected, setSelected] = useState(rules[0]);
  const [enabled, setEnabled] = useState(true);
  const [simulation, setSimulation] = useState(null);

  const filtered = useMemo(() =>
    rules.filter((rule) =>
      (!query || rule.code.toLowerCase().includes(query.toLowerCase())) &&
      (!category || rule.category === category) &&
      (!severity || rule.severity === severity)
    ), [query, category, severity]
  );

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-widest text-slate-500">Administration</p>
        <h1 className="mt-1 text-3xl font-bold text-slate-950">Rules catalogue</h1>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
        <section className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
          <div className="grid gap-3 border-b border-slate-200 p-4 bg-slate-50/50 md:grid-cols-3">
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search rule code..."
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <select
              value={category}
              onChange={(event) => setCategory(event.target.value)}
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">All categories</option>
              {[...new Set(rules.map((rule) => rule.category))].map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
            <select
              value={severity}
              onChange={(event) => setSeverity(event.target.value)}
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">All severities</option>
              <option value="ERROR">ERROR</option>
              <option value="WARNING">WARNING</option>
            </select>
          </div>

          <div className="divide-y divide-slate-100">
            {filtered.length > 0 ? (
              filtered.map((rule) => (
                <button
                  key={rule.code}
                  type="button"
                  onClick={() => { setSelected(rule); setEnabled(true); }}
                  className={`flex w-full items-center justify-between px-4 py-3 text-left transition-colors hover:bg-slate-50 ${selected.code === rule.code ? "bg-indigo-50/50 ring-1 ring-inset ring-indigo-100" : ""}`}
                >
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-sm font-semibold text-slate-900">{rule.code}</span>
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-500">{rule.category}</span>
                  </div>
                  <span className={`text-xs font-bold ${rule.severity === "ERROR" ? "text-red-600" : "text-amber-600"}`}>{rule.severity}</span>
                </button>
              ))
            ) : (
              <div className="p-12">
                <EmptyState title="No rules match filters" description="Try adjusting your search query or selecting a different category." />
              </div>
            )}
          </div>
        </section>

        <aside className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm h-fit sticky top-6">
          <div className="flex items-center justify-between mb-4">
            <p className="font-mono text-lg font-bold text-slate-900">{selected.code}</p>
            <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${selected.severity === "ERROR" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"}`}>
              {selected.severity}
            </span>
          </div>

          <p className="text-sm text-slate-600 leading-relaxed">
            Definition: validates claim data against the organisation's configured <span className="font-semibold text-slate-900">{selected.category.toLowerCase()}</span> policy.
          </p>

          <div className="mt-6 rounded-xl bg-slate-50 p-4 border border-slate-100">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Test Fixture</p>
            <p className="text-sm font-mono text-slate-700">{selected.fixture}</p>
          </div>

          <div className="mt-6 flex items-center justify-between">
            <p className="text-sm text-slate-600">
              <strong className="text-slate-900">{selected.hits}</strong> hits in last 90 days
            </p>
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700 cursor-pointer">
              <input
                type="checkbox"
                checked={enabled}
                onChange={(event) => setEnabled(event.target.checked)}
                className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
              />
              Enabled
            </label>
          </div>

          <div className="mt-8 pt-6 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setSimulation({ checked: 24, matched: Math.max(1, Math.round(selected.hits / 9)), runAt: new Date().toLocaleTimeString() })}
              className="w-full rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 active:scale-95"
            >
              Run simulation
            </button>

            {simulation && (
              <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900 animate-in fade-in slide-in-from-top-2 duration-300">
                <div className="flex items-center gap-2 font-bold mb-1">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m22 2-7 20-4-//-9-20Z"/><path d="M2 2l20-2"/></svg>
                  Simulation complete
                </div>
                <p className="text-emerald-800 leading-relaxed">
                  Checked <span className="font-bold">{simulation.checked}</span> representative claims; <span className="font-bold">{simulation.matched}</span> would receive this finding.
                </p>
                <p className="mt-2 text-[10px] text-emerald-600/70 uppercase font-medium">Run at {simulation.runAt}</p>
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
