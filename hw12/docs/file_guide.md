# Пояснение по файлам с кодом

## 1. Утилита генерации workflow

### [main.go](hse-data-pipelines/hw12/cmd/workflowgen/main.go)

Что делает:

- читает YAML с параметрами среды;
- читает шаблон `CronWorkflow`;
- подставляет значения;
- записывает готовый YAML в `argo/workflows/generated/...`.

Что менять:

- если нужно добавить новый параметр в workflow, его надо:
  - добавить в структуру `workflowConfig`;
  - добавить в файл значений;
  - использовать в шаблоне `orders-daily-workflow.tpl.yaml`.

На что смотреть в первую очередь:

- `type workflowConfig` — список доступных параметров;
- `readConfig` — загрузка и проверка значений;
- `renderTemplate` — подстановка параметров в шаблон.

## 2. Spark-задача

### [job.py](hse-data-pipelines/hw12/apps/spark/orders_daily/src/job.py)

Что делает:

- создаёт `SparkSession`;
- читает CSV;
- считает агрегаты по дате и товару;
- пишет итог в JSON.

Что менять:

- входной путь: переменная окружения `INPUT_PATH`;
- выходной путь: переменная окружения `OUTPUT_PATH`;
- бизнес-логику агрегации: блок `result = (...)`.

Если нужно добавить новые вычисления:

- новые колонки добавляются через `withColumn`;
- новые метрики добавляются в `.agg(...)`;
- новый разрез добавляется в `.groupBy(...)`.

### [orders.csv](hse-data-pipelines/hw12/apps/spark/orders_daily/data/orders.csv)

Что делает:

- даёт небольшой учебный набор данных для локальной демонстрации и для сборки образа.

Что менять:

- можно подложить другой CSV с той же схемой.

### [Dockerfile](hse-data-pipelines/hw12/apps/spark/orders_daily/Dockerfile)

Что делает:

- берёт готовый образ Spark;
- копирует внутрь код и тестовые данные;
- готовит образ для запуска через Spark Operator.

Что менять:

- если нужен другой базовый образ Spark, менять строку `FROM`;
- если добавятся зависимости или дополнительные файлы, дописывать `COPY` и `RUN`.

## 3. Витрина на React

### [package.json](hse-data-pipelines/hw12/apps/showcase/sales_dashboard/package.json)

Что делает:

- описывает зависимости и команды сборки `vite`.

Что менять:

- новые зависимости подключаются здесь.

### [App.jsx](hse-data-pipelines/hw12/apps/showcase/sales_dashboard/src/App.jsx)

Что делает:

- отображает главную страницу витрины;
- читает параметры из `window.APP_CONFIG`.

Что менять:

- текст заголовков, подписи и порядок карточек меняются здесь.

### [KpiCard.jsx](hse-data-pipelines/hw12/apps/showcase/sales_dashboard/src/components/KpiCard.jsx)

Что делает:

- отдельная карточка показателя.

Что менять:

- если нужна другая разметка карточки, менять этот файл.

### [styles.css](hse-data-pipelines/hw12/apps/showcase/sales_dashboard/src/styles.css)

Что делает:

- задаёт внешний вид витрины.

Что менять:

- цвета, отступы, типографику и сетку.

### [env-config.js](hse-data-pipelines/hw12/apps/showcase/sales_dashboard/public/env-config.js)

Что делает:

- задаёт локальные значения по умолчанию.

Что менять:

- если хочется показать локальный запуск без Kubernetes.

### [Dockerfile](hse-data-pipelines/hw12/apps/showcase/sales_dashboard/Dockerfile)

Что делает:

- собирает React-приложение;
- затем кладёт статические файлы в `nginx`.

Что менять:

- если понадобится другой веб-сервер или другая сборка.

### [default.conf](hse-data-pipelines/hw12/apps/showcase/sales_dashboard/nginx/default.conf)

Что делает:

- настраивает `nginx` для одностраничного приложения.

Что менять:

- если нужно добавить сжатие, заголовки или другой порт.

## 4. Универсальные шаблоны Argo

### [report-template.yaml](hse-data-pipelines/hw12/argo/templates/common/report-template.yaml)

Что делает:

- формирует текстовый итог по запуску Spark-задачи.

Что менять:

- если нужно расширить отчёт, добавлять новые параметры и строки в Python-блоке.

### [spark-submit-template.yaml](hse-data-pipelines/hw12/argo/templates/spark/spark-submit-template.yaml)

Что делает:

- создаёт `SparkApplication`.

Что менять:

- ресурсы драйвера и исполнителей;
- параметры `sparkConf`;
- образ Spark;
- политику перезапуска.

### [spark-wait-template.yaml](hse-data-pipelines/hw12/argo/templates/spark/spark-wait-template.yaml)

Что делает:

- опрашивает Kubernetes API и ждёт состояние `COMPLETED` или `FAILED`.

Что менять:

- время ожидания;
- число попыток;
- логику обработки таймаута.

## 5. Шаблон и значения workflow

### [orders-daily-workflow.tpl.yaml](hse-data-pipelines/hw12/argo/workflows/templates/orders-daily-workflow.tpl.yaml)

Что делает:

- описывает общий вид `CronWorkflow`;
- связывает универсальные шаблоны Argo в один DAG.

Что менять:

- расписание, если оно должно управляться шаблоном;
- состав шагов;
- связи между задачами.

### [orders-daily-dev.values.yaml](hse-data-pipelines/hw12/argo/workflows/templates/orders-daily-dev.values.yaml)
### [orders-daily-prod.values.yaml](hse-data-pipelines/hw12/argo/workflows/templates/orders-daily-prod.values.yaml)

Что делают:

- задают значения для разных сред.

Что менять:

- имя workflow;
- расписание;
- путь к данным;
- число исполнителей;
- тег образа.

## 6. Внешние Helm-чарты

### [Chart.yaml](hse-data-pipelines/hw12/deploy/helm/argo-workflows/Chart.yaml)
### [values.yaml](hse-data-pipelines/hw12/deploy/helm/argo-workflows/values.yaml)

Что делают:

- фиксируют версию внешнего чарта Argo Workflows и его настройки.

То же самое устроено для:

- [minio](hse-data-pipelines/hw12/deploy/helm/minio)
- [postgresql](hse-data-pipelines/hw12/deploy/helm/postgresql)
- [spark-operator](hse-data-pipelines/hw12/deploy/helm/spark-operator)

Что менять:

- версию внешнего чарта в `Chart.yaml`;
- параметры установки в `values.yaml`.

## 7. Kustomize для витрины

### [deployment.yaml](hse-data-pipelines/hw12/deploy/kustomize/showcase/base/deployment.yaml)

Что делает:

- описывает развёртывание витрины.

Что менять:

- имя образа;
- порты;
- дополнительные переменные, тома или probes.

### [service.yaml](hse-data-pipelines/hw12/deploy/kustomize/showcase/base/service.yaml)

Что делает:

- открывает HTTP-доступ к витрине внутри кластера.

### [configmap.yaml](hse-data-pipelines/hw12/deploy/kustomize/showcase/base/configmap.yaml)

Что делает:

- задаёт runtime-конфигурацию витрины.

### Оверлеи `dev` и `prod`

Файлы:

- [dev/kustomization.yaml](hse-data-pipelines/hw12/deploy/kustomize/showcase/overlays/dev/kustomization.yaml)
- [dev/patch-deployment.yaml](hse-data-pipelines/hw12/deploy/kustomize/showcase/overlays/dev/patch-deployment.yaml)
- [dev/patch-configmap.yaml](hse-data-pipelines/hw12/deploy/kustomize/showcase/overlays/dev/patch-configmap.yaml)
- [prod/kustomization.yaml](hse-data-pipelines/hw12/deploy/kustomize/showcase/overlays/prod/kustomization.yaml)
- [prod/patch-deployment.yaml](hse-data-pipelines/hw12/deploy/kustomize/showcase/overlays/prod/patch-deployment.yaml)
- [prod/patch-configmap.yaml](hse-data-pipelines/hw12/deploy/kustomize/showcase/overlays/prod/patch-configmap.yaml)

Что меняют:

- теги образов;
- число реплик;
- путь к данным;
- значения показателей по умолчанию.

## 8. Служебные Kubernetes-файлы

### [00-namespaces.yaml](hse-data-pipelines/hw12/deploy/core/00-namespaces.yaml)

Что делает:

- создаёт пространства имён `argo`, `data-jobs`, `showcase`.

### [01-spark-rbac.yaml](hse-data-pipelines/hw12/deploy/core/01-spark-rbac.yaml)

Что делает:

- создаёт сервисный аккаунт `spark-driver` и нужные права для Spark-драйвера.

## 9. Скрипты

### [bootstrap-tools.sh](hse-data-pipelines/hw12/scripts/bootstrap-tools.sh)

Что делает:

- скачивает `helm` в локальный каталог `hw12/bin`.

### [generate-workflows.sh](hse-data-pipelines/hw12/scripts/generate-workflows.sh)

Что делает:

- генерирует `dev` и `prod` workflow одним вызовом.

### [render-helm.sh](hse-data-pipelines/hw12/scripts/render-helm.sh)

Что делает:

- подтягивает зависимости Helm;
- рендерит манифесты в `rendered/helm`.

### [deploy-platform.sh](hse-data-pipelines/hw12/scripts/deploy-platform.sh)

Что делает:

- ставит платформенные компоненты через Helm;
- затем применяет Kustomize-оверлей витрины.

### [verify.sh](hse-data-pipelines/hw12/scripts/verify.sh)

Что делает:

- прогоняет базовую локальную проверку проекта.

## 10. GitLab CI

### [.gitlab-ci.yml](hse-data-pipelines/hw12/.gitlab-ci.yml)

Что делает:

- задаёт стадии:
  - проверка,
  - сборка,
  - генерация workflow,
  - развёртывание.

Что менять:

- адреса реестра;
- правила запуска по веткам;
- команды развёртывания;
- имена окружений.
