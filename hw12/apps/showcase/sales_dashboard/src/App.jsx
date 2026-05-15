import { KpiCard } from "./components/KpiCard";

const defaultConfig = {
  envName: "dev",
  dataSource: "s3a://warehouse/dev/orders-daily/",
  refreshSeconds: 300,
  kpis: [
    { title: "Выручка за день", value: "721 ₽" },
    { title: "Заказов", value: "6" },
    { title: "Топ товар", value: "cake" },
  ],
};

export default function App() {
  const runtimeConfig = window.APP_CONFIG || defaultConfig;

  return (
    <main className="page">
      <section className="hero">
        <div>
          <p className="eyebrow">Домашнее задание 12</p>
          <h1>Витрина итогов ежедневной обработки заказов</h1>
          <p className="lead">
            React-приложение получает путь к данным и параметры обновления из
            Kubernetes ConfigMap. Для разных сред меняются только значения в
            Kustomize-оверлеях.
          </p>
        </div>
        <div className="meta">
          <span>Среда: {runtimeConfig.envName}</span>
          <span>Источник: {runtimeConfig.dataSource}</span>
          <span>Обновление: раз в {runtimeConfig.refreshSeconds} сек.</span>
        </div>
      </section>

      <section className="kpi-grid">
        {runtimeConfig.kpis.map((item) => (
          <KpiCard key={item.title} title={item.title} value={item.value} />
        ))}
      </section>
    </main>
  );
}
