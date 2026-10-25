# Задача: обновление архитектуры локального LLM-переводчика

Разработай Python-приложение для перевода технической документации с использованием LangChain и OpenAI-совместимого API.

Основные требования предыдущего ТЗ сохраняются: поддержка TXT, Markdown и DOCX, сегментация, сохранение структуры, глоссарий, CLI, обработка ошибок и тестирование.

Внеси следующие изменения в архитектуру и функциональность.

## 1. Технологический стек

Используй:

- Python 3.12+
- uv
- langchain-core
- langchain-openai
- openai
- Pydantic и pydantic-settings
- Typer
- httpx
- python-docx
- markdown-it-py
- pytest

Не используй Ollama SDK. Взаимодействие с моделями должно осуществляться через OpenAI-совместимый API.

LangChain используй для создания prompt templates, построения цепочек перевода и вызова LLM.

## 2. Конфигурация API

Все параметры подключения должны задаваться через YAML-конфигурацию и переменные окружения.

Пример `configs/default.yaml`:

```yaml
llm:
  provider: openai_compatible
  base_url: "http://localhost:1234/v1"
  model: "local-model"
  temperature: 0.0
  max_tokens: 2048
  timeout: 120
  max_retries: 2

translation:
  source_language: "en"
  target_language: "ru"
  chunk_size: 1500
  context_window: 8192
  glossary_path: "glossaries/en_ru.yaml"

logging:
  level: INFO
```

API-ключ получай из переменной окружения `LLM_API_KEY`.

Если локальный сервер требует формального значения ключа, допускай использование `local`, но не отправляй секреты в логи.

Не используй облачный endpoint по умолчанию.

## 3. LangChain Translator

Реализуй класс `LangChainTranslator`.

Для взаимодействия с моделью используй `ChatOpenAI`:

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model=config.model,
    base_url=config.base_url,
    api_key=config.api_key,
    temperature=config.temperature,
    timeout=config.timeout,
    max_retries=config.max_retries,
    use_responses_api=False,
)
```

Используй:

- `ChatPromptTemplate` для создания промптов.
- `SystemMessage` и `HumanMessage` для передачи инструкций и текста.
- LCEL (LangChain Expression Language) для построения цепочки перевода.
- Pydantic для валидации структурированного результата, когда возможности сервера позволяют это сделать.

Для серверов, которые не поддерживают structured output, реализуй fallback на обычный текстовый ответ с последующей проверкой результата.

Предусмотри передачу контекста предыдущих сегментов и глоссария.

## 4. Функция тестирования API

Реализуй отдельный модуль `src/tech_translator/llm/api_health.py`.

Он должен обеспечивать проверку работоспособности OpenAI-совместимого API.

### Проверки

**1. Подключение к API**

Проверить доступность API-сервера и корректность сетевого соединения.

**2. Доступность модели**

Попробовать получить список моделей через `/v1/models`, если сервер поддерживает этот endpoint.

Проверить присутствие выбранной модели.

Если получение списка моделей не поддерживается, не считать это автоматической ошибкой — перейти к тесту генерации.

**3. Тестовая генерация**

Отправить через LangChain запрос:

```text
Translate the following text into Russian.
Return only the translation.

The server is running successfully.
```

Проверить:

- Отсутствие ошибок API.
- Успешное получение ответа.
- Наличие непустого текстового содержимого.
- Время выполнения запроса.

**4. Диагностика**

Корректно обрабатывать:

- ConnectionError
- Timeout
- HTTP 401/403
- HTTP 404
- HTTP 429
- HTTP 500/502/503
- Ошибки отсутствующей модели
- Пустой ответ
- Некорректный формат ответа

Не выводить API-ключ или конфиденциальные HTTP-заголовки.

### Результат проверки

Возвращай структурированный объект `APIHealthResult` с полями:

```python
class APIHealthResult(BaseModel):
    connected: bool
    model_available: bool | None
    generation_success: bool
    response_time_ms: float | None
    test_response: str | None
    error: str | None
```

Значение `model_available=None` означает, что проверить список моделей не удалось или эта возможность не поддерживается.

Успешной общей проверкой считать успешную тестовую генерацию через выбранную модель.

## 5. CLI для проверки API

Добавь команду:

```bash
uv run tech-translator test-api
```

Поддержи параметры:

```bash
uv run tech-translator test-api \
  --config configs/default.yaml \
  --model local-model
```

Команда должна отображать понятный диагностический отчет:

```text
LLM API Connection Test
-----------------------------
Endpoint: http://localhost:1234/v1
Model: local-model

Connection:          OK
Model availability:  OK
Generation:          OK
Response time:       850 ms

Test response:
Сервер успешно работает.

Result: SUCCESS
```

При неудачной проверке выводи причину ошибки и заверши выполнение с ненулевым exit code.

Добавь опцию `--json` для машиночитаемого результата.

## 6. Автоматические тесты

Напиши тесты для модуля диагностики API.

Используй mock-объекты для имитации:

- Успешного соединения.
- Недоступного сервера.
- Неверного API-ключа.
- Отсутствующей модели.
- Превышения таймаута.
- Пустого ответа.
- Сервера, не поддерживающего `/models`.
- Успешной генерации без возможности получить список моделей.

Тесты не должны требовать реального LLM-сервера.

Дополнительно реализуй интеграционный тест, который запускается отдельно при наличии локального API.

## 7. Архитектура

Организуй код следующим образом:

```text
src/tech_translator/
├── cli.py
├── config.py
├── llm/
│   ├── client.py
│   ├── translator.py
│   ├── prompts.py
│   └── api_health.py
├── core/
│   ├── pipeline.py
│   ├── segmenter.py
│   └── glossary.py
├── parsers/
├── exporters/
└── utils/
```

Модуль `client.py` отвечает за создание и настройку `ChatOpenAI`.

Модуль `translator.py` отвечает исключительно за выполнение переводов.

Модуль `api_health.py` отвечает за проверку API.

Все компоненты должны использовать единую конфигурацию подключения.

## 8. Порядок реализации

Работай последовательно.

1. Настрой зависимости, конфигурацию и подключение к OpenAI-совместимому API.
2. Реализуй `LangChainTranslator` с тестовым переводом короткого текста.
3. Реализуй модуль проверки API и команду `test-api`.
4. Добавь unit-тесты подключения и генерации.
5. Только после этого переходи к парсерам документов, сегментации и экспорту.

Не создавай веб-интерфейс и не добавляй ненужные зависимости.

Приоритет — простой, расширяемый и тестируемый код.

После реализации покажи команды запуска и результаты тестов.
