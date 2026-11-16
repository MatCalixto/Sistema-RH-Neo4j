// Testa os controles JavaScript em um DOM mínimo, sem navegador ou rede.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const {DataSet} = require('../src/assets/vis-network.min.js');

class Element {
  constructor(tag = 'div') { this.tag = tag; this.children = []; this.attrs = {}; this.events = {}; this.style = {}; this.value = ''; }
  append(...items) { this.children.push(...items); }
  appendChild(item) { this.children.push(item); return item; }
  replaceChildren(...items) { this.children = items; }
  setAttribute(name, value) { this.attrs[name] = value; }
  getAttribute(name) { return this.attrs[name]; }
  addEventListener(name, callback) { this.events[name] = callback; }
  querySelectorAll(tag) { return this.children.flatMap(c => c instanceof Element ? [...(c.tag === tag ? [c] : []), ...c.querySelectorAll(tag)] : []); }
  click() { this.onclick?.(); }
}

class Network {
  constructor(container, data) { this.data = data; this.events = {}; this.scale = 1; }
  on(name, callback) { this.events[name] = callback; }
  setOptions(options) { this.options = options; }
  stopSimulation() {}
  stabilize() {}
  fit() { this.fitted = true; }
  selectNodes(ids) { this.selection = ids; }
  focus(id, options) { this.focused = id; this.scale = options.scale; }
  getScale() { return this.scale; }
  moveTo(options) { this.scale = options.scale; }
}

function viewer(payload) {
  const elements = new Map();
  const element = id => {
    if (!elements.has(id)) elements.set(id, new Element());
    return elements.get(id);
  };
  element('graph-data').textContent = JSON.stringify(payload);
  element('depth').value = '1'; element('limit').value = '150';
  const window = {};
  const context = {document: {getElementById: element, createElement: tag => new Element(tag), createTextNode: text => text},
    vis: {DataSet, Network}, window, console};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../src/assets/graph.js'), 'utf8'), context);
  return {...window.graphViewer, element};
}

function graphFixture() {
  const groups = {Department: {label: 'Departamentos', color: '#38bdf8'}, Employee: {label: 'Funcionários', color: '#94a3b8'}};
  const nodes = [{id: '4:db:0', label: 'Área', name: 'Área', group: 'Department', order: 0}];
  const edges = [];
  for (let i = 1; i <= 175; i++) {
    nodes.push({id: `4:db:${i}`, label: `Funcionário ${i}`, name: String(i), group: 'Employee', order: i});
    edges.push({id: `e${i}`, from: `4:db:${i}`, to: '4:db:0', relation: 'WORKS_IN'});
  }
  return {nodes, edges, groups, pathMode: false};
}

test('amostra preserva endpoints e busca localiza nós fora do limite', () => {
  const {nodes, edges, network, element} = viewer(graphFixture());
  assert.equal(nodes.length, 150);
  assert.equal(edges.length, 149);
  for (const edge of edges.get()) {assert.ok(nodes.get(edge.from)); assert.ok(nodes.get(edge.to));}
  assert.equal(nodes.get('4:db:175'), null);
  element('search').value = '175'; element('locate').click();
  assert.equal(nodes.length, 2);
  assert.ok(nodes.get('4:db:175'));
  assert.equal(network.focused, '4:db:175');
  assert.equal(element('selection-title').textContent, 'Funcionário 175');
  assert.equal(edges.get()[0].label, 'WORKS_IN');
  network.events.stabilizationIterationsDone();
  assert.equal(network.focused, '4:db:175');
  element('reset').click();
  assert.equal(nodes.length, 150);
});

test('filtros, limite, zoom e movimento atualizam o grafo', () => {
  const {nodes, edges, network, element} = viewer(graphFixture());
  const checks = element('filters').querySelectorAll('input');
  const employees = checks.find(c => c.getAttribute('aria-label') === 'Funcionários');
  employees.checked = false; employees.events.change();
  assert.equal(nodes.length, 1); assert.equal(edges.length, 0);
  employees.checked = true; employees.events.change();
  element('limit').value = '0'; element('limit').onchange();
  assert.equal(nodes.length, 176);
  element('zoom-in').click(); assert.ok(network.scale > 1);
  element('zoom-out').click(); assert.equal(network.scale, 1);
  element('physics').click(); assert.equal(network.options.physics.enabled, true);
  element('physics').click(); assert.equal(network.options.physics.enabled, false);
});

test('caminho mantém arestas e marca percurso inverso sem física', () => {
  const payload = graphFixture();
  payload.nodes = payload.nodes.slice(0, 3);
  payload.edges = payload.edges.slice(0, 2);
  payload.edges[1].reversed = true;
  payload.pathMode = true;
  const {nodes, edges, network, element} = viewer(payload);
  assert.equal(nodes.length, 3); assert.equal(edges.length, 2);
  assert.ok(nodes.get().every(node => node.physics === false));
  assert.equal(edges.get('e2').dashes, true);
  assert.equal(edges.get('e2').from, '4:db:2');
  assert.equal(element('physics').hidden, true);
  network.events.click({nodes: [], edges: ['e2']});
  assert.equal(element('selection-title').textContent, 'WORKS_IN');
  assert.match(element('selection-meta').textContent, /inverso/);
});
