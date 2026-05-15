window.APP_CONFIG = {
  envName: "dev",
  dataSource: "s3a://warehouse/dev/orders-daily/",
  refreshSeconds: 300,
  kpis: [
    { title: "Выручка за день", value: "721 ₽" },
    { title: "Заказов", value: "6" },
    { title: "Топ товар", value: "cake" }
  ]
};
