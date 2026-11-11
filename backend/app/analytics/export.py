"""План часов в CSV для Excel: разделитель «;» и UTF-8 с BOM, чтобы русский Excel открыл файл сразу."""

import csv
import io
from urllib.parse import quote

NOT_ENOUGH = "мало данных"


def hours_csv(recommendations: dict) -> str:
    """Строка на тему в порядке программы: часы по плану, общий план и план каждого учебника."""
    items = sorted(recommendations["items"], key=lambda item: item["topic_id"])
    textbooks = [row["textbook"] for row in items[0]["by_textbook"]] if items else []
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    writer.writerow(["Тема", "Часов по плану", "Рекомендовано всем классам", *textbooks, "Причина"])
    for item in items:
        by_textbook = {row["textbook"]: row["hours_recommended"] for row in item["by_textbook"]}
        hours = [NOT_ENOUGH if by_textbook[name] is None else by_textbook[name] for name in textbooks]
        writer.writerow([item["topic"], item["hours_current"], item["hours_recommended"], *hours, item["reason"]])
    return "\ufeff" + buffer.getvalue()


def csv_filename(school_id: int | None) -> str:
    return "часы-по-темам.csv" if school_id is None else f"часы-по-темам-школа-{school_id}.csv"


def content_disposition(filename: str) -> str:
    """Имя файла по-русски (RFC 5987) и латиницей для старых программ."""
    fallback = filename.replace("часы-по-темам", "hours").replace("школа", "school")
    return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(filename)}"
