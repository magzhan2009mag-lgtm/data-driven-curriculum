"use client";

import { Button } from "@/components/ui/button";

export default function ErrorPage({ retry }: { error: unknown; retry: () => void }) {
  return (
    <div className="max-w-prose border-y py-8">
      <h1 className="text-2xl font-semibold">Не удалось получить данные</h1>
      <p className="mt-2 text-muted-foreground">
        Похоже, сервер аналитики не запущен или ещё запускается. Запустите проект через start.bat и попробуйте снова.
      </p>
      <Button className="mt-4" onClick={() => retry()}>
        Попробовать снова
      </Button>
    </div>
  );
}
