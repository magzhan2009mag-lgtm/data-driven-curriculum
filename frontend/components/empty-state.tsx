export function EmptyState() {
  return (
    <div className="max-w-prose border-y py-8">
      <h1 className="text-2xl font-semibold">Результатов тестов пока нет</h1>
      <p className="mt-2 text-muted-foreground">
        Здесь появится анализ тем, когда в базе будут результаты. Для демонстрации создайте данные: в папке backend
        выполните <code className="font-mono text-sm">python -m scripts.seed --reset</code>.
      </p>
    </div>
  );
}
