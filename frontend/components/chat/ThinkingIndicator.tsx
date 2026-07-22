export function ThinkingIndicator() {
  return (
    <span className="inline-flex items-center gap-1" aria-label="Working">
      {[0, 1, 2].map((index) => (
        <span
          key={index}
          className="h-1 w-1 animate-pulse rounded-full bg-current motion-reduce:animate-none"
          style={{ animationDelay: `${index * 160}ms` }}
        />
      ))}
    </span>
  );
}
