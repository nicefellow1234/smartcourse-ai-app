const state = {
  sessionId: null,
  latestResults: null,
  historyMap: new Map(),
};

document.addEventListener("DOMContentLoaded", () => {
  setupRecommendationPage(state);
  setupDashboard(state);
});

function setupRecommendationPage(appState) {
  const form = document.getElementById("recommendation-form");
  if (!form) {
    return;
  }

  const preferenceField = document.getElementById("preference");
  const modelField = document.getElementById("model");
  const resultsSection = document.getElementById("results-section");
  const resultsSummary = document.getElementById("results-summary");
  const recommendationsContainer = document.getElementById("recommendations");
  const placeholder = document.getElementById("placeholder");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const preference = preferenceField.value.trim();
    if (!preference) {
      preferenceField.focus();
      return;
    }

    const payload = {
      preference,
      model: modelField.value,
    };

    resultsSection.classList.remove("d-none");
    placeholder.classList.add("d-none");
    setAlert(resultsSummary, "info", "Fetching recommendations...");
    recommendationsContainer.innerHTML = "";

    try {
      const response = await fetch("/api/recommend", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Failed to fetch recommendations");
      }

      renderRecommendations(data, recommendationsContainer, resultsSummary, appState);
    } catch (error) {
      setAlert(resultsSummary, "danger", error.message);
    }
  });

  recommendationsContainer.addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-course]");
    if (!button) {
      return;
    }
    if (!appState.sessionId) {
      setAlert(resultsSummary, "warning", "Please run a recommendation query first.");
      return;
    }

    try {
      const courseData = JSON.parse(decodeURIComponent(button.dataset.course));
      await saveRecommendation(appState.sessionId, courseData);
      setAlert(resultsSummary, "success", `Saved “${courseData.course_title}” to dashboard.`);
    } catch (error) {
      setAlert(resultsSummary, "danger", error.message);
    }
  });
}

function setupDashboard(appState) {
  const dashboardRoot = document.getElementById("dashboard-root");
  if (!dashboardRoot) {
    return;
  }

  const refreshButton = document.getElementById("refresh-history");
  const clearButton = document.getElementById("clear-history");
  const historyList = document.getElementById("history-list");

  if (!historyList) {
    return;
  }

  historyList.addEventListener("click", (event) => {
    const button = event.target.closest("[data-session-id]");
    if (!button) {
      return;
    }
    const session = appState.historyMap.get(button.dataset.sessionId);
    if (!session) {
      return;
    }
    historyList.querySelectorAll(".active").forEach((node) => node.classList.remove("active"));
    button.classList.add("active");
    appState.sessionId = session.id;
    appState.latestResults = {
      tfidf: session.tfidf_results || [],
      neural: session.neural_results || [],
    };
    renderComparisonPanel(session);
  });

  refreshButton?.addEventListener("click", () => loadDashboard(appState));
  clearButton?.addEventListener("click", async () => {
    const confirmed = window.confirm("Clear all search history and saved recommendations?");
    if (!confirmed) {
      return;
    }
    await clearHistory(appState);
  });
  loadDashboard(appState);
}

async function saveRecommendation(sessionId, course) {
  const response = await fetch("/api/save", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({session_id: sessionId, course}),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Unable to save recommendation");
  }
  return data;
}

async function loadDashboard(appState) {
  try {
    const response = await fetch("/api/history");
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Failed to load dashboard");
    }
    renderHistoryList(data.history || [], appState);
    renderSavedList(data.saved || []);
    if ((data.history || []).length > 0) {
      const firstSession = data.history[0];
      const historyList = document.getElementById("history-list");
      const firstButton = historyList.querySelector("[data-session-id]");
      if (firstSession && firstButton) {
        firstButton.classList.add("active");
        appState.sessionId = firstSession.id;
        appState.latestResults = {
          tfidf: firstSession.tfidf_results || [],
          neural: firstSession.neural_results || [],
        };
        renderComparisonPanel(firstSession);
      }
    } else {
      renderComparisonPanel(null);
    }
  } catch (error) {
    console.error(error);
  }
}

async function clearHistory(appState) {
  try {
    const response = await fetch("/api/history", {method: "DELETE"});
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || "Failed to clear history");
    }
    appState.sessionId = null;
    appState.latestResults = null;
    appState.historyMap = new Map();
    renderHistoryList([], appState);
    renderSavedList([]);
    renderComparisonPanel(null);
    window.alert("Search history cleared.");
  } catch (error) {
    console.error(error);
    window.alert(`Unable to clear history: ${error.message}`);
  }
}

function renderRecommendations(data, container, summaryNode, appState) {
  appState.sessionId = data.session_id;
  appState.latestResults = data.results;

  const {preference, model, results = {}} = data;
  setAlert(summaryNode, "info", `Showing ${model} recommendations for “${preference}”`);

  const entries = [];
  if (model === "hybrid") {
    entries.push({label: "TF-IDF", list: results.tfidf || []});
    entries.push({label: "Neural", list: results.neural || []});
  } else {
    entries.push({label: model.toUpperCase(), list: results.items || []});
  }

  container.innerHTML = entries.map((entry) => renderResultColumn(entry.label, entry.list, {includeSave: true})).join("");
}

function renderHistoryList(history, appState) {
  const container = document.getElementById("history-list");
  if (!container) {
    return;
  }
  container.innerHTML = "";
  appState.historyMap = new Map();

  if (history.length === 0) {
    container.innerHTML = '<div class="list-group-item text-muted">No searches yet.</div>';
    return;
  }

  history.forEach((session) => {
    appState.historyMap.set(String(session.id), session);
    const created = session.created_at ? new Date(session.created_at) : null;
    const createdLabel = created && !Number.isNaN(created.getTime()) ? created.toLocaleString() : "Unknown time";
    const button = document.createElement("button");
    button.type = "button";
    button.className = "list-group-item list-group-item-action";
    button.dataset.sessionId = session.id;
    button.innerHTML = `
      <div class="d-flex justify-content-between align-items-center">
        <div>
          <div class="fw-semibold">${escapeHtml(session.query_text)}</div>
          <div class="small text-muted">${escapeHtml(createdLabel)}</div>
        </div>
        <span class="badge text-bg-primary rounded-pill">${(session.saved_recommendations || []).length} saved</span>
      </div>
    `;
    container.appendChild(button);
  });
}

function renderSavedList(saved) {
  const container = document.getElementById("saved-list");
  if (!container) {
    return;
  }
  container.innerHTML = "";
  if (saved.length === 0) {
    container.innerHTML = '<div class="list-group-item text-muted">No saved recommendations yet.</div>';
    return;
  }

  saved.forEach((record) => {
    const modelLabel = (record.model_type || "unknown").toUpperCase();
    const savedAt = record.saved_at ? new Date(record.saved_at) : null;
    const savedLabel = savedAt && !Number.isNaN(savedAt.getTime()) ? savedAt.toLocaleString() : "Unknown time";
    const item = document.createElement("div");
    item.className = "list-group-item";
    item.innerHTML = `
      <div class="d-flex justify-content-between align-items-start">
        <div>
          <div class="fw-semibold">${escapeHtml(record.course_title)}</div>
          <div class="small text-muted">${escapeHtml(record.department || "General")} • ${escapeHtml(modelLabel)}</div>
          <div class="small text-muted">${escapeHtml(savedLabel)}</div>
        </div>
        <span class="badge text-bg-success">${Math.round((record.relevance_score || 0) * 100)}%</span>
      </div>
    `;
    container.appendChild(item);
  });
}

function renderComparisonPanel(session) {
  const panel = document.getElementById("comparison-panel");
  if (!panel) {
    return;
  }
  if (!session) {
    panel.innerHTML = '<div class="col-12 text-muted">Run a recommendation to compare models.</div>';
    return;
  }

  const tfidfColumn = renderResultColumn("TF-IDF", session.tfidf_results || [], {includeSave: false});
  const neuralColumn = renderResultColumn("Neural", session.neural_results || [], {includeSave: false});
  panel.innerHTML = tfidfColumn + neuralColumn;
}

function renderResultColumn(label, items, options = {}) {
  const includeSave = options.includeSave ?? false;
  if (!items || items.length === 0) {
    return `<div class="col-12"><div class="alert alert-warning mb-0">No results for ${escapeHtml(label)} model.</div></div>`;
  }

  const cards = items
    .map((item) => {
      const score = Math.round((item.score || 0) * 100);
      const encodedCourse = encodeURIComponent(JSON.stringify(item));
      return `
        <div class="col-12">
          <div class="card border-0 shadow-sm h-100">
            <div class="card-body d-flex flex-column">
              <div class="d-flex justify-content-between">
                <div>
                  <h6 class="fw-bold mb-1">${escapeHtml(item.course_title || "Untitled Course")}</h6>
                  <p class="text-muted small mb-2">${escapeHtml(item.department || "General")} • ${escapeHtml(item.university || "Unknown University")}</p>
                </div>
                <div class="text-end">
                  <div class="progress mb-1">
                    <div class="progress-bar bg-success" role="progressbar" style="width: ${score}%" aria-valuemin="0" aria-valuemax="100"></div>
                  </div>
                  <span class="badge text-bg-success">${score}%</span>
                </div>
              </div>
              <p class="flex-grow-1">${escapeHtml(item.description || "No description available.")}</p>
              ${
                includeSave
                  ? `<button class="btn btn-outline-primary btn-sm mt-2 align-self-start" data-model="${escapeHtml(item.model_type || label)}" data-course="${encodedCourse}">Save</button>`
                  : ""
              }
            </div>
          </div>
        </div>
      `;
    })
    .join("");

  return `
    <div class="col-md-6">
      <h3 class="h6 text-uppercase text-muted mb-3">${escapeHtml(label)}</h3>
      <div class="row gy-3">${cards}</div>
    </div>
  `;
}

function setAlert(node, status, message) {
  if (!node) {
    return;
  }
  node.classList.remove("alert-info", "alert-danger", "alert-success", "alert-warning");
  node.classList.add(`alert-${status}`);
  node.textContent = message;
}

function escapeHtml(value) {
  if (value === undefined || value === null) {
    return "";
  }
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
