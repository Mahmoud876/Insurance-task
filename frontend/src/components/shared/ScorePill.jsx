function ScorePill({ score }) {
  const numericScore = Number(score) || 0;
  const tone = numericScore >= 85 ? "border-emerald-200 bg-emerald-50 text-emerald-700" : numericScore >= 60 ? "border-amber-200 bg-amber-50 text-amber-700" : "border-red-200 bg-red-50 text-red-700";
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold ${tone}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" /> {numericScore}%
    </span>
  );
}

export { ScorePill };
