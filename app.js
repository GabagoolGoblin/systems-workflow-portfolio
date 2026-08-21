"use strict";

(() => {
  const data = window.PORTFOLIO_DATA;
  const grid = document.querySelector("#project-grid");
  const note = document.querySelector("#evidence-note");
  const buttons = [...document.querySelectorAll("[data-filter]")];

  if (!data || !Array.isArray(data.projects) || !grid || !note) {
    document.body.dataset.renderState = "error";
    return;
  }

  const text = (tag, className, value) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    node.textContent = value;
    return node;
  };

  const projectCard = (project, index) => {
    const article = document.createElement("article");
    article.className = `project-card ${index < 3 ? "featured" : ""}`.trim();
    article.dataset.category = project.category;
    article.dataset.projectId = project.id;

    if (project.hero) {
      const image = document.createElement("img");
      image.src = project.hero;
      image.alt = `${project.title} synthetic interface preview`;
      image.loading = "eager";
      image.width = 1440;
      image.height = 960;
      article.append(image);
    }

    const body = document.createElement("div");
    body.className = "card-body";
    const meta = text("p", "card-meta", `${project.category} · ${project.runtime}`);
    const title = text("h3", "", project.title);
    const problem = text("p", "problem", project.problem);
    const evidence = text("p", "evidence", project.evidence);
    const counts = text(
      "p",
      "counts",
      `${project.unit_tests} deterministic tests${project.browser_checks ? ` · ${project.browser_checks} browser checks` : ""}`,
    );
    const boundary = text("p", "non-claim", project.non_claim);

    const actions = document.createElement("div");
    actions.className = "card-actions";
    const open = document.createElement("a");
    open.href = project.route;
    open.textContent = project.route.endsWith(".html") ? "Open demo" : "Review project";
    const readme = document.createElement("a");
    readme.href = project.readme;
    readme.textContent = "README";
    actions.append(open, readme);

    body.append(meta, title, problem, evidence, counts, boundary, actions);
    article.append(body);
    return article;
  };

  const render = (filter) => {
    const projects = filter === "all"
      ? data.projects
      : data.projects.filter((project) => project.category === filter);
    grid.replaceChildren(...projects.map(projectCard));
    note.textContent = `${projects.length} project${projects.length === 1 ? "" : "s"} shown. ${data.evidence_note}`;
    buttons.forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.filter === filter)));
    document.body.dataset.renderState = "ready";
  };

  buttons.forEach((button) => button.addEventListener("click", () => render(button.dataset.filter)));
  render("all");
})();
