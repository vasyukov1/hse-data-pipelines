export function KpiCard({ title, value }) {
  return (
    <article className="kpi-card">
      <p className="kpi-title">{title}</p>
      <strong className="kpi-value">{value}</strong>
    </article>
  );
}
