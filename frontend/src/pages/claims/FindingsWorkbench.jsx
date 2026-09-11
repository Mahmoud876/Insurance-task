import { useMemo, useState } from "react";

const ruleHelp = {
  RADIOGRAPH_REQUIRED: ["Documentation", "A radiograph is required for this procedure.", "Payer clinical attachment policy"],
  NARRATIVE_REQUIRED: ["Documentation", "A clinical narrative is required for this procedure.", "Payer clinical attachment policy"],
  PRE_AUTHORISATION_REQUIRED: ["Documentation", "This procedure requires an authorisation number before submission.", "Plan pre-authorisation policy"],
  LINE_FEES_DO_NOT_SUM_TO_TOTAL: ["Financial", "The claim total must equal the sum of its line fees.", "Claim billing integrity standard"],
  NON_POSITIVE_FEE: ["Financial", "A submitted procedure must have a positive fee.", "Claim billing integrity standard"],
  FEE_EXCEEDS_ALLOWED_AMOUNT: ["Financial", "The fee is above the plan's allowed amount.", "Plan fee schedule"],
  LIKELY_DUPLICATE_CLAIM: ["Duplicate", "A matching patient, service date and procedure set was found.", "Duplicate-claim prevention policy"],
  UNSUPPORTED_ATTACHMENT_TYPE: ["Attachments", "Only approved document and image formats can be transmitted.", "Electronic attachment specification"],
  ATTACHMENT_SIZE_LIMIT: ["Attachments", "Attachments must be no larger than 10 MB.", "Electronic attachment specification"],
};

const severityRank = { ERROR: 0, WARNING: 1, INFO: 2 };

function money(value) {
  return `$${Number(value || 0).toFixed(2)}`;
}

export function makeFindings(values) {
  const findings = [];
  const lines = values.lines || [];
  const lineTotal = lines.reduce((sum, line) => sum + (Number(line.charge_amount) || 0), 0);
  const total = Number(values.total_amount) || 0;
  const requiresDocumentation = (code) => /^D7|^D8/.test(code || "");
  const needsAuth = (code) => /^D8/.test(code || "");

  if (lines.some((line) => requiresDocumentation(line.procedure_code)) && !values.narrative?.trim()) {
    findings.push({ code: "NARRATIVE_REQUIRED", message: "A clinical narrative is required for this procedure.", value: "No narrative", path: "narrative", severity: "ERROR", fix: { narrative: "Clinical necessity documented." } });
  }
  if (lines.some((line) => requiresDocumentation(line.procedure_code)) && !(values.attachments || []).some((item) => /pdf|image\/(jpeg|png)/.test(item.type || ""))) {
    findings.push({ code: "RADIOGRAPH_REQUIRED", message: "A radiograph attachment is required for this procedure.", value: "No radiograph", path: "attachments", severity: "ERROR" });
  }
  if (lines.some((line) => needsAuth(line.procedure_code)) && !values.authorization_number?.trim()) {
    findings.push({ code: "PRE_AUTHORISATION_REQUIRED", message: "Pre-authorisation is required but no number was provided.", value: "Blank", path: "authorization_number", severity: "ERROR" });
  }
  (values.attachments || []).forEach((item, index) => {
    if (item.type && !["application/pdf", "image/jpeg", "image/png"].includes(item.type)) findings.push({ code: "UNSUPPORTED_ATTACHMENT_TYPE", message: "This attachment type is not supported.", value: item.type, path: `attachments.${index}`, severity: "ERROR" });
    if (item.size > 10 * 1024 * 1024) findings.push({ code: "ATTACHMENT_SIZE_LIMIT", message: "This attachment exceeds the 10 MB limit.", value: `${(item.size / 1024 / 1024).toFixed(1)} MB`, path: `attachments.${index}`, severity: "ERROR" });
  });
  if (Math.abs(lineTotal - total) > 0.001) findings.push({ code: "LINE_FEES_DO_NOT_SUM_TO_TOTAL", message: "Line fees do not sum to the claim total.", value: `${money(lineTotal)} vs ${money(total)}`, path: "total_amount", severity: "ERROR", fix: { total_amount: lineTotal.toFixed(2) } });
  lines.forEach((line, index) => {
    if (Number(line.charge_amount) <= 0) findings.push({ code: "NON_POSITIVE_FEE", message: "Claim line fee must be greater than zero.", value: money(line.charge_amount), path: `lines.${index}.charge_amount`, severity: "ERROR", fix: { [`lines.${index}.charge_amount`]: "1.00" } });
    if (line.allowed_amount && Number(line.charge_amount) > Number(line.allowed_amount)) findings.push({ code: "FEE_EXCEEDS_ALLOWED_AMOUNT", message: "Line fee exceeds the allowed amount.", value: `${money(line.charge_amount)} / allowed ${money(line.allowed_amount)}`, path: `lines.${index}.charge_amount`, severity: "WARNING", fix: { [`lines.${index}.charge_amount`]: String(line.allowed_amount) } });
  });
  return findings;
}

export default function FindingsWorkbench({ values, onGoTo, onFix, dispositions, onDisposition }) {
  const [why, setWhy] = useState(null);
  const [override, setOverride] = useState(null);
  const [reason, setReason] = useState("");
  const findings = useMemo(() => makeFindings(values), [values]);
  const active = findings.filter((finding) => !dispositions[finding.code]);
  const score = Math.max(0, 100 - active.reduce((sum, item) => sum + (item.severity === "ERROR" ? 18 : 7), 0));
  const grouped = active.sort((a, b) => severityRank[a.severity] - severityRank[b.severity]).reduce((groups, finding) => {
    const category = ruleHelp[finding.code]?.[0] || "Other";
    const key = `${finding.severity}|${category}`;
    groups[key] = [...(groups[key] || []), finding];
    return groups;
  }, {});

  return <aside className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
    <div className="flex items-start justify-between gap-3">
      <div><h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Findings</h2><p className="mt-1 text-xs text-slate-500">Grouped by severity and category</p></div>
      <div title="Readiness starts at 100 and is reduced for unresolved errors and warnings." className="cursor-help rounded-lg bg-slate-100 px-3 py-2 text-right"><div className="text-xs text-slate-500">Readiness ⓘ</div><div className="text-xl font-bold text-slate-900">{score}%</div></div>
    </div>
    <div className="mt-4 space-y-4">
      {Object.entries(grouped).map(([key, items]) => <section key={key}><h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">{key.replace("|", " · ")}</h3><div className="space-y-2">{items.map((finding) => <article key={`${finding.code}-${finding.path}`} className={`rounded-lg border p-3 ${finding.severity === "ERROR" ? "border-red-200 bg-red-50/40" : "border-amber-200 bg-amber-50/40"}`}><div className="flex justify-between gap-2"><p className="text-sm font-medium text-slate-800">{finding.message}</p><span className="text-xs font-bold text-slate-500">{finding.severity}</span></div><p className="mt-1 text-xs text-slate-600">Offending value: <span className="font-medium">{finding.value}</span></p><p className="mt-1 text-xs text-slate-500">Fix hint: {finding.fix ? "A safe correction is available." : "Add the required information, then recheck."}</p><div className="mt-3 flex flex-wrap gap-2"><button onClick={() => onGoTo(finding.path)} type="button" className="text-xs font-medium text-slate-700 underline">Go to field</button>{finding.fix && <button onClick={() => { onFix(finding.fix); onDisposition(finding, "fixed", "Applied suggested fix"); }} type="button" className="text-xs font-medium text-emerald-700 underline">Apply fix</button>}<button onClick={() => { setOverride(finding); setReason(""); }} type="button" className="text-xs font-medium text-amber-700 underline">Override</button><button onClick={() => setWhy(finding)} type="button" className="text-xs font-medium text-slate-700 underline">Why?</button></div></article>)}</div></section>)}
      {!active.length && <p className="rounded-md bg-emerald-50 p-3 text-sm text-emerald-800">All findings are resolved. This claim is ready to submit.</p>}
    </div>
    {why && <div role="dialog" className="mt-4 rounded-lg border border-slate-300 bg-white p-3 text-sm shadow-lg"><p className="font-semibold">{why.code}</p><p className="mt-1 text-slate-600">{ruleHelp[why.code]?.[1]}</p><p className="mt-2 text-xs text-slate-500">Citation: {ruleHelp[why.code]?.[2]}</p><button type="button" onClick={() => setWhy(null)} className="mt-3 text-sm underline">Close</button></div>}
    {override && <div role="dialog" aria-label="Override finding" className="mt-4 rounded-lg border border-amber-300 bg-amber-50 p-3"><label className="block text-sm font-semibold text-slate-800">Reason for override <span className="text-red-600">*</span></label><textarea value={reason} onChange={(event) => setReason(event.target.value)} className="mt-2 w-full rounded border p-2 text-sm" placeholder="Document the clinical or operational reason" /><div className="mt-2 flex gap-2"><button type="button" disabled={!reason.trim()} onClick={() => { onDisposition(override, "overridden", reason.trim()); setOverride(null); }} className="rounded bg-slate-900 px-3 py-2 text-xs font-semibold text-white disabled:opacity-40">Confirm override</button><button type="button" onClick={() => setOverride(null)} className="text-xs underline">Cancel</button></div></div>}
  </aside>;
}
