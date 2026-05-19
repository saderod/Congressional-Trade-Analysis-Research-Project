export function MethodologyNotes() {
  return (
    <section className="rounded-md border border-slate-200 bg-white p-6">
      <h2 className="text-lg font-semibold text-slate-950">How This Was Tested</h2>
      <div className="mt-4 grid gap-4 text-sm leading-6 text-slate-600 md:grid-cols-3">
        <p>The project only studies congressional stock trades that were publicly reported starting in January 2025.</p>
        <p>For each trade, it looks for news that was already public before the trade report came out, then judges whether that news sounded positive, negative, or neutral.</p>
        <p>It checks how the stock did about one month later and compares it with the S&amp;P 500 ETF, which represents the broad stock market.</p>
      </div>
    </section>
  );
}
