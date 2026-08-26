function ScorePill({ score }) {
  return (
    <span className="inline-flex items-center rounded-full border px-2.5 py-1 text-sm font-medium">
      {score}
    </span>
  );
}

export { ScorePill };