# Используем официальный образ Python
FROM python:3.13-slim

# Устанавливаем git, cmake
RUN apt-get update
RUN apt-get install -y git cmake g++ build-essential

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы
COPY . .

# Делаем start.sh исполняемым
RUN chmod +x start.sh

# Открываем порт Flask
EXPOSE 3030

# Запускаем приложение (без .venv)
CMD ["./start-container.sh"]
