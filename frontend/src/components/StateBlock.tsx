type StateBlockProps = {
  label: string;
};

export function LoadingBlock({ label }: StateBlockProps) {
  return (
    <div className="rounded-md border border-slate-200 bg-white p-5 text-sm text-slate-500">
      Loading {label}...
    </div>
  );
}

export function ErrorBlock({ label }: StateBlockProps) {
  return (
    <div className="rounded-md border border-red-200 bg-red-50 p-5 text-sm text-red-700">
      Could not load {label}.
    </div>
  );
}
