# CourseWork Data Quality Pipeline

## О проекте
`CourseWork Data Quality Pipeline` — это проект по теме Argo Workflows. Его цель — показать, как из переиспользуемых `WorkflowTemplate` собрать понятный data pipeline для автоматической проверки структуры студенческой проектной работы.

На вход пайплайн получает URL архива с проектом. Дальше он скачивает архив, распаковывает содержимое, проверяет наличие обязательных файлов и директорий, а затем формирует итоговый markdown-отчёт.

## Что делает пайплайн
1. Скачивает архив проекта по URL.
2. Распаковывает `.zip`, `.tar.gz` или `.tgz`.
3. Проверяет структуру проекта по списку обязательных путей.
4. Формирует финальный отчёт для преподавателя или студента.

## Почему шаблоны универсальные и переиспользуемые
- Каждый шаблон принимает параметры через `inputs.parameters`, поэтому его можно использовать не только для одной конкретной курсовой, но и для любых похожих проверок.
- Передача данных между шагами сделана через `outputs.artifacts` и `outputs.parameters`, а не через жёстко прошитые пути между файлами проекта.
- Основной `Workflow` связывает шаблоны через `templateRef`, поэтому отдельные блоки легко переиспользовать в других пайплайнах.

## Состав WorkflowTemplate
- `01-download-artifact-template.yaml` — универсальный шаблон скачивания файла по URL и возврата его как artifact.
- `02-unpack-archive-template.yaml` — шаблон распаковки архива в директорию проекта.
- `03-project-check-template.yaml` — шаблон проверки структуры проекта и формирования промежуточного текстового отчёта.
- `04-report-template.yaml` — шаблон сборки финального markdown-отчёта.

## Входные параметры основного Workflow
- `project-url` — URL архива с проектом.
- `archive-filename` — имя архива внутри контейнера, например `coursework.zip`.
- `project-name` — название проекта.
- `student-name` — имя студента или автора.
- `required-paths` — обязательные пути через запятую, например `README.md,go.mod,cmd`.

## Схема пайплайна
```text
download-project
        |
        v
unpack-project
        |
        v
check-project
        |
        v
generate-report
```

## Структура проекта
```text
hw11/
├── demo/
│   └── coursework-demo-server.yaml
├── scripts/
│   ├── bootstrap-local-demo.sh
│   ├── run-demo-success.sh
│   ├── run-demo-failure.sh
│   └── destroy-local-demo.sh
├── templates/
│   ├── 01-download-artifact-template.yaml
│   ├── 02-unpack-archive-template.yaml
│   ├── 03-project-check-template.yaml
│   └── 04-report-template.yaml
├── workflows/
│   └── coursework-check-workflow.yaml
├── speach_text.md
└── README.md
```

## Базовые команды запуска
```bash
kubectl apply -n argo -f hw11/templates/
argo submit -n argo hw11/workflows/coursework-check-workflow.yaml
```

## Пример запуска через Argo
```bash
argo submit -n argo hw11/workflows/coursework-check-workflow.yaml \
  -p project-url=https://example.com/coursework.zip \
  -p archive-filename=coursework.zip \
  -p project-name=AntiPlagiarism \
  -p student-name="Alexander Vasyukov" \
  -p required-paths="README.md,go.mod,cmd"
```

Так как workflow использует `generateName: coursework-check-`, каждый запуск создаёт новый объект с уникальным именем. Это удобно для демонстрации нескольких сценариев подряд.

## Воспроизводимый локальный demo-стенд
Проект можно показать полностью локально. Для этого добавлен demo-контур на `kind`:

- поднимается кластер `kind`;
- устанавливается `Argo Workflows` из официального `quick-start-minimal.yaml`;
- вместе с Argo поднимается встроенный `MinIO`, поэтому `outputs.artifacts` реально сохраняются;
- разворачивается `coursework-demo-server`, который внутри кластера отдаёт тестовые архивы:
  - `coursework-ok.zip`
  - `coursework-ok.tgz`
  - `coursework-broken.zip`
  - `coursework-broken.tgz`

### Что нужно локально
- `docker`
- `kubectl`
- `curl`

Скрипты сами докачают `kind` и `argo` в каталог `hw11/bin`, если этих утилит нет в системе или не хочется ставить их глобально.

### Поднять стенд
```bash
./hw11/scripts/bootstrap-local-demo.sh
```

Примечание: первый запуск может занять несколько минут, потому что Docker скачивает `kindest/node` и образы Argo Workflows.
Если интернет медленный, можно увеличить ожидание:

```bash
ARGO_WAIT_TIMEOUT=900s DEMO_WAIT_TIMEOUT=600s ./hw11/scripts/bootstrap-local-demo.sh
```

### Показать успешный прогон
```bash
./hw11/scripts/run-demo-success.sh
```

Этот сценарий использует архив:

```text
http://coursework-demo-server.argo.svc.cluster.local:8000/coursework-ok.zip
```

Ожидаемый результат:
- `check-status = OK`
- в логах шага `generate-report` выводится итоговый markdown-отчёт
- workflow завершается в статусе `Succeeded`

### Показать прогон с ошибкой
```bash
./hw11/scripts/run-demo-failure.sh
```

Этот сценарий использует архив:

```text
http://coursework-demo-server.argo.svc.cluster.local:8000/coursework-broken.tgz
```

Ожидаемый результат:
- `check-status = FAILED`
- `missing-paths = cmd`
- workflow всё равно завершается успешно, потому что отчёт должен собраться даже при ошибке проверки структуры

### Удалить локальный стенд
```bash
./hw11/scripts/destroy-local-demo.sh
```

## Просмотр статуса и логов
```bash
argo list -n argo
argo get -n argo <workflow-name>
argo logs -n argo <workflow-name>
```

## Ожидаемый результат
- скачанный архив проекта как artifact после `download-project`;
- распакованная директория проекта как artifact после `unpack-project`;
- текстовый отчёт проверки структуры как artifact после `check-project`;
- финальный markdown-отчёт как artifact после `generate-report`.

## Что находится в каждом файле
- `hw11/demo/coursework-demo-server.yaml` — deployment и service с локальной раздачей тестовых архивов внутри кластера.
- `hw11/scripts/bootstrap-local-demo.sh` — полный bootstrap локального стенда `kind + Argo + demo-server`.
- `hw11/scripts/run-demo-success.sh` — воспроизводимый успешный прогон.
- `hw11/scripts/run-demo-failure.sh` — воспроизводимый прогон с отсутствующим `cmd`.
- `hw11/scripts/destroy-local-demo.sh` — удаление локального demo-кластера.
- `hw11/templates/01-download-artifact-template.yaml` — скачивание файла по URL.
- `hw11/templates/02-unpack-archive-template.yaml` — распаковка архива в каталог проекта.
- `hw11/templates/03-project-check-template.yaml` — структурная проверка проекта и генерация промежуточного отчёта.
- `hw11/templates/04-report-template.yaml` — сборка финального markdown-отчёта.
- `hw11/workflows/coursework-check-workflow.yaml` — основной DAG, который вызывает шаблоны через `templateRef`.
- `hw11/README.md` — инструкция по запуску, проверке и демонстрации проекта.
- `hw11/speach_text.md` — готовый текст для устной защиты примерно на 5 минут.
