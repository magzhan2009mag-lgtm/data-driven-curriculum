export default function Loading() {
  return (
    <div role="status" aria-label="Загрузка данных" className="space-y-8 motion-safe:animate-pulse">
      <div className="h-10 max-w-xl rounded-sm bg-muted" />
      <div className="h-5 max-w-prose rounded-sm bg-muted" />
      <div className="h-96 rounded-sm bg-muted" />
    </div>
  );
}
