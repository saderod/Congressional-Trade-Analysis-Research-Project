export function MethodologyNotes() {
  return (
    <section className="rounded-md border border-slate-200 bg-white p-6">
      <h2 className="text-lg font-semibold text-slate-950">Methodology</h2>
      <div className="mt-4 grid gap-4 text-sm leading-6 text-slate-600 md:grid-cols-3">
        <p>Universe is congressional trades disclosed from January 2025 onward, with prices aligned to the next market signal date.</p>
        <p>Headlines are retrieved only before disclosure, then scored by a weighted NB, FinBERT, and capped Ollama ensemble.</p>
        <p>Returns are forward 21 trading days versus SPY, with a separate NLP-filtered strategy for headline-supported trades.</p>
      </div>
    </section>
  );
}
