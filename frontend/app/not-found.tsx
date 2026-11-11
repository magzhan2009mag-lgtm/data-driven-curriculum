import Link from "next/link";

export default function NotFound() {
  return (
    <div className="max-w-prose border-y py-8">
      <h1 className="text-2xl font-semibold">Такой страницы нет</h1>
      <p className="mt-2 text-muted-foreground">Возможно, такой темы или школы нет, или в адресе ошибка.</p>
      <Link href="/" className="mt-4 inline-block text-primary underline underline-offset-4">
        Перейти к сложным темам
      </Link>
    </div>
  );
}
