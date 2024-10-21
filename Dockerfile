# Используем официальный образ Python в качестве базового
FROM python:3.12

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальную часть кода
COPY . .

# Запускаем приложение
CMD ["python", "import discord.py"]
