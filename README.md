# Финансист - Ассистент для анализа финансовых данных

Решение кейса AIDOCPROCESSING на хакатоне InnoGlobalHack 2024.

## Фичи

- Парсинг финансовых отчетов в формате pdf с сайта Disclosure
- Распознавание сканов документов и таблиц на них
- Веб-интерфейс для доступа к LLM
- Retrieval Augmented Generation для поиска релевантных документов и ответов на вопросы
- Отображение данных из таблиц в виде графиков под ответом LLM

## Запуск

Проект запускается на Ubuntu 22.04 с amd64 архитектурой, также требует видеокарту Nvidia с поддержкой CUDA.

1. Установите [Docker и Docker Compose](https://docs.docker.com/engine/install/ubuntu/).
2. Установите [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html).
3. Склонируйте репозиторий и перейдите в папку проекта.
4. Если требуется особая настройка Open WebUI, отредактируйте `open-webui-data/config.json`.
5. Запустите проект командой `docker compose up --build`.
6. Перейдите на `http://localhost:3000` в браузере.
7. Создайте пользователя, который будет иметь права администратора.
8. Загрузите настройки для Open WebUI:
   - [Функции](http://localhost:3000/workspace/functions) импортируйте из `open-webui-data/functions.json`
   - Добавьте базу знаний на странице [Базы знаний](http://localhost:3000/workspace/knowledge)
   - [Настройки моделей](http://localhost:3000/workspace/models) импортируйте из `open-webui-data/models.json`
9. Сделайте запрос к модели: http://localhost:3000/

## Структура репозитория

- `webui` - форк Open WebUI с нашими изменениями
- `open-webui-data` - настройки для Open WebUI и хранилище данных
- `functions` - функции-фильтры для моделей
- `parse` - парсеры для Disclosure

## Команда

one-zero-eight, Университет Иннополис
- Руслан Бельков
- Артём Булгаков
- Антон Кудрявцев
- Софья Ткаченко
