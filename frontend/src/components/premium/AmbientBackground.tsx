export function AmbientBackground() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 bg-[var(--canvas)] transition-colors duration-300" />
  );
}
