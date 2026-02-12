import json
import os

FILE = "ads_database.json"

def save_ads(data):
    """Сохраняет список объявлений в файл."""
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_ads():
    """Загружает объявления. Всегда возвращает список []."""
    if not os.path.exists(FILE):
        return []
    try:
        with open(FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            data = json.loads(content)
            # Если в файле вдруг не список, приводим к списку
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"Ошибка при загрузке файла: {e}")
        return []