/* Presentation-neutral SQLite snapshot binding for the existing Dashboard theme. */
(function () {
  const data = window.ASAAN_QANOON_DATA;
  if (!data) return;
  const metrics = data.metrics || {};
  const values = [metrics.questions || 0, metrics.cases || 0, metrics.documents || 0, metrics.users || 0];
  document.querySelectorAll(".metric-value").forEach(function (node, index) {
    if (index < values.length) node.textContent = values[index];
  });
  const path = window.location.pathname.toLowerCase();
  if (path.endsWith("/users.html")) {
    const tbody = document.querySelector("table tbody");
    if (tbody && Array.isArray(data.users)) {
      tbody.innerHTML = data.users.map(function (user) {
        const created = (user.created_at || "").slice(0, 10);
        return "<tr><td><div class=\"d-flex align-items-center gap-2\"><div><p class=\"fw-semibold mb-0\">"
          + escapeHtml(user.name) + "</p><p class=\"text-muted small mb-0\">" + escapeHtml(user.email || "") +
          "</p></div></div></td><td>" + escapeHtml(user.role) +
          "</td><td>Asaan Qanoon AI</td><td><span class=\"badge text-bg-success\">Active</span></td><td>" +
          escapeHtml(created) + "</td><td class=\"text-end\"><a class=\"btn btn-light btn-sm\" href=\"user-details.html\">View</a></td></tr>";
      }).join("");
    }
  }
  document.documentElement.dataset.databaseUpdated = data.generated_at || "";
  function escapeHtml(value) {
    const temp = document.createElement("div");
    temp.textContent = String(value || "");
    return temp.innerHTML;
  }
}())