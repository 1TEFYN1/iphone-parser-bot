# 1. Используем официальный образ Python
FROM python:3.10-slim

# 2. Настройка окружения, чтобы логи выводились сразу
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Установка системных библиотек, необходимых для работы Chrome
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    libnss3 \
    libgconf-2-4 \
    libxss1 \
    libasound2 \
    libatk1.0-0 \
    libc6 \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    lsb-release \
    xdg-utils \
    libgbm1 \
    --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 4. Установка Google Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# 5. Установка рабочей директории внутри контейнера
WORKDIR /app

# 6. Установка зависимостей Python
# Сначала копируем только requirements.txt, чтобы Docker кэшировал слои
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 7. Копируем весь остальной код проекта
COPY . .

# 8. Запуск бота
CMD ["python", "test_bot.py"]