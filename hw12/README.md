# Домашнее задание 12

Реализация смешанной платформы данных в Kubernetes:

- сторонние системы ставятся через Helm;
- свои витрины ставятся через Kustomize;
- Spark-задача запускается через Argo Workflows и Spark Operator;
- GitLab CI собирает образы, генерирует YAML и применяет манифесты.

## Выбранный стек

### Где собирать образы

Сборку я выбрал в `GitLab CI`.

Причины:

- он естественно привязан к `git push`, review и веткам;
- легко разнести стадии на проверку, сборку, генерацию YAML и развёртывание;
- удобно складывать промежуточные артефакты в артефакты пайплайна;
- для сборки контейнеров можно использовать `kaniko`, без отдельного Docker-демона.

### Где хранить артефакты

- Docker-образы: `GitLab Container Registry`.
- Сгенерированные `Workflow`-файлы: артефакты GitLab CI и каталог `argo/workflows/generated/` в репозитории.
- Helm-зависимости и собранные манифесты: локально в `charts/` и `rendered/helm/`, в CI как временные артефакты.
- Данные Spark-задачи: `MinIO`.
- Служебные метаданные и витрины при необходимости: `PostgreSQL`.

## Структура

```text
hw12/
├── .gitlab-ci.yml
├── README.md
├── go.mod
├── cmd/
│   └── workflowgen/
├── apps/
│   ├── spark/
│   │   └── orders_daily/
│   └── showcase/
│       └── sales_dashboard/
├── argo/
│   ├── templates/
│   │   ├── common/
│   │   └── spark/
│   └── workflows/
│       ├── templates/
│       └── generated/
├── deploy/
│   ├── core/
│   ├── helm/
│   └── kustomize/
├── docs/
│   ├── report.md
│   └── speech_text.md
└── scripts/
```

## Что и где лежит

- Внешние Helm-чарты: `deploy/helm/argo-workflows`, `deploy/helm/minio`, `deploy/helm/postgresql`, `deploy/helm/spark-operator`.
- Внутренняя витрина и её Kubernetes-манифесты: `apps/showcase/sales_dashboard` и `deploy/kustomize/showcase`.
- Оверлеи сред: `deploy/kustomize/showcase/overlays/dev` и `deploy/kustomize/showcase/overlays/prod`.
- Универсальные шаблоны Argo: `argo/templates/common` и `argo/templates/spark`.
- Исходники Spark-задачи: `apps/spark/orders_daily`.
- Шаблон и готовые `Workflow`-файлы: `argo/workflows/templates` и `argo/workflows/generated`.

## Путь от git push до запуска в кластере

1. Разработчик делает `git push`.
2. GitLab CI запускает стадию проверки:
   - `go test ./...`
   - `python3 -m py_compile`
   - генерация `Workflow` через утилиту `workflowgen`
   - рендер `Kustomize`
3. На стадии сборки `kaniko` собирает:
   - Spark-образ `orders-daily`
   - образ витрины `sales-dashboard`
4. Образы публикуются в `GitLab Container Registry`.
5. На стадии `workflow` GitLab CI подставляет свежий тег Spark-образа в файл параметров и генерирует итоговый `CronWorkflow` YAML.
6. На стадии развёртывания:
   - применяются `deploy/core/*.yaml`;
   - через `helm upgrade --install` ставятся Argo Workflows, Spark Operator, MinIO и PostgreSQL;
   - через `kubectl apply` загружаются `WorkflowTemplate`;
   - через `kubectl apply -f argo/workflows/generated/dev/orders-daily.yaml` создаётся `CronWorkflow`;
   - через `kubectl apply -k deploy/kustomize/showcase/overlays/dev` выкатывается витрина.
7. После появления объекта `Workflow` или `CronWorkflow` контроллер Argo сам подхватывает его из API Kubernetes и запускает DAG.

## Почему схема удобная

- Шаблоны Argo переиспользуются: в конкретный `Workflow` подставляются только имя, расписание, образ и пути.
- Версии отделены друг от друга:
  - код живёт в `apps/`,
  - параметры среды живут в `values.yaml` и `overlays/`,
  - итоговый YAML живёт отдельно в `generated/`.
- Откат упрощается:
  - для сторонней платформы есть `helm rollback`;
  - для своих витрин можно вернуть прошлый коммит с `Kustomize`-патчами;
  - для Spark-задачи достаточно вернуть старый тег образа и заново сгенерировать `Workflow`.

## Как запустить локально

Ниже минимальный путь, который можно выполнить уже сейчас.

### 1. Прогнать проверки

```bash
cd /Users/alexvasyukov/Documents/GitHub/hse-data-pipelines/hw12
chmod +x scripts/*.sh
./scripts/verify.sh
```

### 2. Посмотреть сгенерированный workflow

```bash
sed -n '1,220p' /Users/alexvasyukov/Documents/GitHub/hse-data-pipelines/hw12/argo/workflows/generated/dev/orders-daily.yaml
```

### 3. Подготовить манифесты платформы

```bash
./scripts/render-helm.sh
ls /Users/alexvasyukov/Documents/GitHub/hse-data-pipelines/hw12/rendered/helm
```

### 4. Развернуть в кластере

Если уже есть доступный Kubernetes-кластер и настроен `kubectl`:

```bash
kubectl apply -f /Users/alexvasyukov/Documents/GitHub/hse-data-pipelines/hw12/deploy/core/00-namespaces.yaml
kubectl apply -f /Users/alexvasyukov/Documents/GitHub/hse-data-pipelines/hw12/deploy/core/01-spark-rbac.yaml
./scripts/deploy-platform.sh dev
kubectl apply -n argo -f /Users/alexvasyukov/Documents/GitHub/hse-data-pipelines/hw12/argo/templates/common/report-template.yaml
kubectl apply -n argo -f /Users/alexvasyukov/Documents/GitHub/hse-data-pipelines/hw12/argo/templates/spark/spark-submit-template.yaml
kubectl apply -n argo -f /Users/alexvasyukov/Documents/GitHub/hse-data-pipelines/hw12/argo/templates/spark/spark-wait-template.yaml
kubectl apply -f /Users/alexvasyukov/Documents/GitHub/hse-data-pipelines/hw12/argo/workflows/generated/dev/orders-daily.yaml
```
