"use strict";
(() => {
  const data = JSON.parse(document.getElementById("graph-data").textContent);
  const $ = id => document.getElementById(id);
  const allNodes = new Map(data.nodes.map(n => [n.id, n]));
  const allEdges = new Map(data.edges.map(e => [e.id, e]));
  const adjacency = new Map(data.nodes.map(n => [n.id, []]));
  data.edges.forEach(e => {
    adjacency.get(e.from)?.push(e);
    if (e.to !== e.from) adjacency.get(e.to)?.push(e);
  });
  const enabled = new Set(data.nodes.map(n => n.group));
  const nodes = new vis.DataSet();
  const edges = new vis.DataSet();
  let selected = null, focused = null, moving = false;
  const color = n => data.groups[n.group].color;
  const network = new vis.Network($("network"), {nodes, edges}, {
    autoResize: true,
    layout: {randomSeed: 42, improvedLayout: false},
    nodes: {shape: "dot", borderWidth: 2, size: 14,
      font: {color: "#e2e8f0", size: 12, strokeWidth: 3, strokeColor: "#0d1423"},
      chosen: {node: (values) => {values.borderWidth = 4; values.borderColor = "#f8fafc";}}},
    edges: {arrows: {to: {enabled: true, scaleFactor: 0.55}},
      width: 1, color: {color: "#3b4b65", highlight: "#38bdf8", opacity: 0.65},
      smooth: false, font: {color: "#bae6fd", size: 10, strokeWidth: 4, strokeColor: "#0d1423", align: "middle"}},
    interaction: {hover: true, hideEdgesOnDrag: !data.pathMode, multiselect: false,
      keyboard: {enabled: true, bindToWindow: false}, zoomView: true, dragView: true, dragNodes: true},
    physics: {enabled: !data.pathMode, solver: "barnesHut",
      barnesHut: {gravitationalConstant: -6500, centralGravity: 0.2, springLength: 155, springConstant: 0.035, damping: 0.4, avoidOverlap: 0.5},
      stabilization: {enabled: true, iterations: 180, updateInterval: 30}}
  });
  // Exposto apenas no iframe para permitir inspeção e validação da renderização.
  window.graphViewer = {network, nodes, edges};
  function displayName(n) { return `${n.label} · ${data.groups[n.group].label} · ${n.id}`; }
  for (const n of data.nodes) {
    const option = document.createElement("option");
    option.value = displayName(n);
    $("node-list").appendChild(option);
  }
  for (const [group, settings] of Object.entries(data.groups)) {
    const count = data.nodes.filter(n => n.group === group).length;
    if (!count) continue;
    const label = document.createElement("label"); label.className = "filter";
    const check = document.createElement("input"); check.type = "checkbox"; check.checked = true;
    check.setAttribute("aria-label", settings.label);
    check.addEventListener("change", () => {
      if (check.checked) enabled.add(group); else enabled.delete(group);
      render();
    });
    const dot = document.createElement("span"); dot.className = "dot"; dot.style.background = settings.color;
    label.append(check, dot, document.createTextNode(`${settings.label} (${count})`));
    $("filters").appendChild(label);
  }
  function visibleNodes() {
    let pool = data.nodes.filter(n => enabled.has(n.group));
    if (focused) {
      const reachable = new Set([focused]); let frontier = [focused];
      for (let hop = 0; hop < Number($("depth").value); hop++) {
        const next = [];
        frontier.forEach(id => (adjacency.get(id) || []).forEach(e => {
          const neighbor = e.from === id ? e.to : e.from;
          if (!reachable.has(neighbor) && enabled.has(allNodes.get(neighbor).group)) {
            reachable.add(neighbor); next.push(neighbor);
          }
        }));
        frontier = next;
      }
      pool = pool.filter(n => reachable.has(n.id));
    }
    // Mantém os hubs do domínio e distribui a amostra de funcionários de
    // modo determinístico, sem depender da ordem retornada pelo Neo4j.
    if (!data.pathMode) pool.sort((a, b) => {
      if (a.id === focused) return -1;
      if (b.id === focused) return 1;
      return Number(a.group === "Employee") - Number(b.group === "Employee") ||
        (focused ? (adjacency.get(b.id).length - adjacency.get(a.id).length) : 0) ||
        a.label.localeCompare(b.label, "pt-BR", {numeric: true}) || a.id.localeCompare(b.id);
    });
    const limit = data.pathMode ? 0 : Number($("limit").value);
    return {pool: limit ? pool.slice(0, limit) : pool, available: pool.length};
  }
  function nodeStyle(n) {
    const tint = color(n);
    return {background: tint, border: tint, highlight: {background: tint, border: "#fff"}, hover: {background: tint, border: "#e2e8f0"}};
  }
  function render() {
    const {pool, available} = visibleNodes();
    const ids = new Set(pool.map(n => n.id));
    network.stopSimulation(); nodes.clear(); edges.clear();
    nodes.add(pool.map(n => ({...n, color: nodeStyle(n), size: n.group === "Employee" ? 9 : 18,
      ...(data.pathMode ? {x: n.order * 220, y: (n.order % 2) * 80, physics: false} : {})})));
    edges.add(data.edges.filter(e => ids.has(e.from) && ids.has(e.to)).map(e => ({...e,
      label: data.pathMode ? e.relation : "", width: data.pathMode ? 2.5 : 1,
      ...(data.pathMode ? {color: {color: "#38bdf8", opacity: 1}, dashes: e.reversed} : {})})));
    $("empty").hidden = nodes.length > 0;
    $("counts").textContent = `${nodes.length} de ${data.nodes.length} nós · ${edges.length} conexões visíveis`;
    $("status").textContent = available > nodes.length ? `Amostra de ${nodes.length}/${available}. Busque um nó ou amplie o limite.` : (focused ? "Vizinhança selecionada" : "");
    moving = false; $("physics").textContent = "Ativar movimento"; $("physics").setAttribute("aria-pressed", "false");
    if (nodes.length && !data.pathMode) {
      $("loading").hidden = false;
      network.setOptions({physics: {enabled: true}});
      network.stabilize(180);
    } else {
      $("loading").hidden = true;
      network.fit({animation: false});
    }
    if (selected && ids.has(selected)) network.selectNodes([selected]);
    else if (selected) clearSelection();
  }
  network.on("stabilizationIterationsDone", () => {
    network.setOptions({physics: {enabled: false}});
    $("loading").hidden = true;
    if (focused && selected && nodes.get(selected)) {
      network.focus(selected, {scale: 1.15, animation: {duration: 350}});
    } else {
      network.fit({animation: {duration: 350, easingFunction: "easeInOutQuad"}});
    }
  });
  function clearSelection() {
    selected = null;
    $("selection-title").textContent = "Explore o grafo";
    $("selection-detail").textContent = "Clique em um nó para ver suas relações. Arraste para organizar e use a roda do mouse para aproximar.";
    $("selection-meta").textContent = ""; $("neighbors").replaceChildren();
    $("relations-heading").hidden = true; $("explore").hidden = true;
    edges.update(edges.get().map(e => ({id: e.id, label: data.pathMode ? e.relation : "", width: data.pathMode ? 2.5 : 1})));
  }
  function inspect(id) {
    selected = id;
    const node = allNodes.get(id), connected = adjacency.get(id) || [];
    $("selection-title").textContent = node.label;
    $("selection-detail").textContent = data.groups[node.group].label;
    $("selection-meta").textContent = `ID: ${id} · ${connected.length} relações no ${data.pathMode ? "caminho" : "grafo completo"}`;
    $("explore").hidden = data.pathMode;
    $("relations-heading").hidden = !connected.length;
    $("neighbors").replaceChildren();
    connected.slice(0, 40).forEach(edge => {
      const out = edge.from === id, neighbor = allNodes.get(out ? edge.to : edge.from);
      const button = document.createElement("button"); button.className = "neighbor";
      button.textContent = `${out ? "→" : "←"} ${neighbor.label}`;
      const detail = document.createElement("small"); detail.textContent = edge.relation;
      button.appendChild(detail); button.onclick = () => locate(neighbor.id);
      $("neighbors").appendChild(button);
    });
    if (connected.length > 40) {
      const more = document.createElement("p"); more.className = "more";
      more.textContent = `Mostrando 40 de ${connected.length} relações. Use a busca para localizar outros nós.`;
      $("neighbors").appendChild(more);
    }
    edges.update(edges.get().map(e => ({id: e.id,
      label: (data.pathMode || e.from === id || e.to === id) ? e.relation : "",
      width: (e.from === id || e.to === id) ? 2.5 : (data.pathMode ? 2.5 : 1)})));
  }
  function locate(id) {
    if (!nodes.get(id)) {
      enabled.add(allNodes.get(id).group);
      for (const input of $("filters").querySelectorAll("input")) {
        input.checked = enabled.has(Object.keys(data.groups).find(key => data.groups[key].label === input.getAttribute("aria-label")));
      }
      focused = id; render();
    }
    network.selectNodes([id]); inspect(id);
    network.focus(id, {scale: 1.15, animation: {duration: 400}});
  }
  network.on("click", event => {
    if (event.nodes.length) inspect(event.nodes[0]);
    else if (event.edges.length) {
      const edge = allEdges.get(event.edges[0]);
      clearSelection();
      $("selection-title").textContent = edge.relation;
      $("selection-detail").textContent = `${allNodes.get(edge.from).label} → ${allNodes.get(edge.to).label}`;
      $("selection-meta").textContent = data.pathMode && edge.reversed ? "Percorrida no sentido inverso (linha tracejada). A seta mantém a direção original." : "A seta representa a direção original da relação.";
    } else clearSelection();
  });
  $("locate").onclick = () => {
    const value = $("search").value.trim().toLocaleLowerCase("pt-BR");
    if (!value) return;
    const found = data.nodes.find(n => displayName(n).toLocaleLowerCase("pt-BR") === value || n.id.toLowerCase() === value || n.name.toLocaleLowerCase("pt-BR") === value)
      || data.nodes.find(n => n.label.toLocaleLowerCase("pt-BR").includes(value));
    if (found) locate(found.id);
    else $("status").textContent = "Nenhum nó encontrado. Tente outro nome ou número.";
  };
  $("search").addEventListener("keydown", event => {if (event.key === "Enter") $("locate").click();});
  $("explore").onclick = () => {focused = selected; render(); if (selected) inspect(selected);};
  $("reset").onclick = () => {
    focused = null; $("search").value = "";
    data.nodes.forEach(n => enabled.add(n.group));
    $("filters").querySelectorAll("input").forEach(input => {input.checked = true;});
    clearSelection(); render();
  };
  $("limit").onchange = render; $("depth").onchange = () => {if (focused) render();};
  $("fit").onclick = () => network.fit({animation: {duration: 300}});
  $("zoom-in").onclick = () => network.moveTo({scale: Math.min(4, network.getScale() * 1.3), animation: true});
  $("zoom-out").onclick = () => network.moveTo({scale: Math.max(0.03, network.getScale() / 1.3), animation: true});
  $("physics").onclick = () => {
    moving = !moving; network.setOptions({physics: {enabled: moving}});
    $("physics").textContent = moving ? "Pausar movimento" : "Ativar movimento";
    $("physics").setAttribute("aria-pressed", String(moving));
  };
  if (data.pathMode) {
    $("heading").textContent = "Caminho mais curto";
    $("reset").textContent = "Restaurar caminho";
    $("scope-controls").hidden = true;
    $("physics").hidden = true;
    $("hint").textContent = "Setas: direção original · Linha tracejada: percurso inverso · Arraste para organizar";
  }
  render();
})();
