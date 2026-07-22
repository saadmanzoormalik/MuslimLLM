export function ReasoningSummary({ items }: { items: string[] }) {
  if (!items.length) return null;
  return (
    <div className="mt-2 border-t pt-2">
      <p className="mb-1 text-[11px] font-medium uppercase text-muted-foreground">Process summary</p>
      <ul className="grid gap-1 text-xs leading-5 text-muted-foreground">
        {items.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
      </ul>
    </div>
  );
}
