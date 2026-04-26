const samples = {
  urban: {
    schema: "laz-tile-index/v1",
    header: {
      bbox: [637000, 4789000, 638200, 4790200],
      point_count: 1850000,
      grid_shape: [8, 8],
      source_filename: "urban-block.indexed.las",
      source_sha1: "3f8b6db4b27a9b13e5267af4e917c7f879a1c4aa",
      cell_size: [150, 150],
    },
    cells: {},
  },
  corridor: {
    schema: "laz-tile-index/v1",
    header: {
      bbox: [411500, 5761000, 415500, 5762600],
      point_count: 3260000,
      grid_shape: [12, 5],
      source_filename: "rail-corridor.indexed.las",
      source_sha1: "76c77f64dce7833a3956a3a9e2262a1bf70f72f5",
      cell_size: [333.333333, 320],
    },
    cells: {},
  },
};

function seedCells(index) {
  const [nx, ny] = index.header.grid_shape;
  let start = 0;
  for (let i = 0; i < nx; i += 1) {
    for (let j = 0; j < ny; j += 1) {
      const density = 0.72 + Math.sin((i + 1) * 1.7) * 0.18 + Math.cos((j + 2) * 1.15) * 0.14;
      const count = Math.max(2500, Math.round((index.header.point_count / (nx * ny)) * density));
      index.cells[`${i},${j}`] = [start, count];
      start += count;
    }
  }
  return index;
}

seedCells(samples.urban);
seedCells(samples.corridor);

let activeIndex = structuredClone(samples.urban);
let activeCells = [];

const el = {
  status: document.querySelector("#status"),
  sampleSelect: document.querySelector("#sampleSelect"),
  sampleButton: document.querySelector("#sampleButton"),
  sidecarInput: document.querySelector("#sidecarInput"),
  dropZone: document.querySelector("#dropZone"),
  fileName: document.querySelector("#fileName"),
  minx: document.querySelector("#minx"),
  miny: document.querySelector("#miny"),
  maxx: document.querySelector("#maxx"),
  maxy: document.querySelector("#maxy"),
  queryButton: document.querySelector("#queryButton"),
  commandBox: document.querySelector("#commandBox"),
  sourceValue: document.querySelector("#sourceValue"),
  pointsValue: document.querySelector("#pointsValue"),
  gridValue: document.querySelector("#gridValue"),
  cellsValue: document.querySelector("#cellsValue"),
  bboxMeta: document.querySelector("#bboxMeta"),
  gridCanvas: document.querySelector("#gridCanvas"),
  resultStack: document.querySelector("#resultStack"),
  healthList: document.querySelector("#healthList"),
  cellList: document.querySelector("#cellList"),
};

function formatNumber(value) {
  return new Intl.NumberFormat("en").format(Math.round(value));
}

function bboxFromInputs() {
  return [
    Number(el.minx.value),
    Number(el.miny.value),
    Number(el.maxx.value),
    Number(el.maxy.value),
  ];
}

function setStatus(text, state = "") {
  el.status.textContent = text;
  if (state) {
    el.status.dataset.state = state;
  } else {
    delete el.status.dataset.state;
  }
}

function normalizeIndex(blob) {
  if (!blob || blob.schema !== "laz-tile-index/v1" || !blob.header || !blob.cells) {
    throw new Error("Unsupported sidecar JSON.");
  }
  const header = blob.header;
  const required = ["bbox", "point_count", "grid_shape", "source_filename", "cell_size"];
  for (const key of required) {
    if (!(key in header)) {
      throw new Error(`Sidecar header is missing ${key}.`);
    }
  }
  return blob;
}

function loadIndex(index, label) {
  activeIndex = structuredClone(index);
  const [minx, miny, maxx, maxy] = activeIndex.header.bbox;
  const width = maxx - minx;
  const height = maxy - miny;
  // Center the default bbox in the data extent (0.30 - 0.70 on both axes
  // -> midpoint at 0.50, occupying the middle 40% of the canvas).
  el.minx.value = Math.round(minx + width * 0.30);
  el.miny.value = Math.round(miny + height * 0.30);
  el.maxx.value = Math.round(minx + width * 0.70);
  el.maxy.value = Math.round(miny + height * 0.70);
  el.fileName.textContent = label;
  previewQuery();
}

function intersectingCells(bbox, index) {
  const [minx, miny, maxx, maxy] = bbox;
  const [hMinx, hMiny, hMaxx, hMaxy] = index.header.bbox;
  if (maxx < hMinx || minx > hMaxx || maxy < hMiny || miny > hMaxy) {
    return [];
  }
  const [nx, ny] = index.header.grid_shape;
  const [cw, ch] = index.header.cell_size;
  const i0 = Math.max(0, Math.floor((minx - hMinx) / cw));
  const i1 = Math.min(nx - 1, Math.floor((maxx - hMinx) / cw));
  const j0 = Math.max(0, Math.floor((miny - hMiny) / ch));
  const j1 = Math.min(ny - 1, Math.floor((maxy - hMiny) / ch));
  const cells = [];
  for (let i = i0; i <= i1; i += 1) {
    for (let j = j0; j <= j1; j += 1) {
      const range = index.cells[`${i},${j}`];
      if (range) {
        cells.push({ i, j, start: Number(range[0]), count: Number(range[1]) });
      }
    }
  }
  return cells;
}

function previewQuery() {
  const bbox = bboxFromInputs();
  if (bbox.some((value) => Number.isNaN(value)) || bbox[0] >= bbox[2] || bbox[1] >= bbox[3]) {
    setStatus("Invalid bbox", "error");
    return;
  }
  activeCells = intersectingCells(bbox, activeIndex);
  const scanned = activeCells.reduce((sum, cell) => sum + cell.count, 0);
  const [nx, ny] = activeIndex.header.grid_shape;

  el.sourceValue.textContent = activeIndex.header.source_filename;
  el.pointsValue.textContent = formatNumber(activeIndex.header.point_count);
  el.gridValue.textContent = `${nx} x ${ny}`;
  el.cellsValue.textContent = `${activeCells.length}`;
  el.bboxMeta.textContent = `${bbox.map((value) => Math.round(value)).join(", ")}`;
  el.commandBox.textContent = [
    `laz-tile-index build ${activeIndex.header.source_filename.replace(".indexed.las", ".las")}`,
    `laz-tile-index query ${activeIndex.header.source_filename}.lzti.json ${bbox.map((value) => Math.round(value)).join(" ")}`,
  ].join("\n");

  renderResult(scanned);
  renderHealth(scanned);
  renderCells();
  drawGrid();
  setStatus("Preview ready");
}

function renderResult(scanned) {
  const ratio = activeIndex.header.point_count ? scanned / activeIndex.header.point_count : 0;
  el.resultStack.innerHTML = "";
  [
    ["Candidate points", formatNumber(scanned)],
    ["Share of cloud", `${(ratio * 100).toFixed(2)}%`],
    ["Ranges to read", activeCells.length.toString()],
    ["Sidecar cells", Object.keys(activeIndex.cells).length.toString()],
  ].forEach(([label, value]) => {
    const row = document.createElement("span");
    row.innerHTML = `<b>${label}</b>${value}`;
    el.resultStack.append(row);
  });
}

function renderHealth(scanned) {
  const [nx, ny] = activeIndex.header.grid_shape;
  const expected = nx * ny;
  const actual = Object.keys(activeIndex.cells).length;
  const ratio = activeIndex.header.point_count ? scanned / activeIndex.header.point_count : 0;
  const signals = [
    activeIndex.schema === "laz-tile-index/v1" ? "Schema matches laz-tile-index/v1." : "Schema does not match the current reader.",
    actual === expected ? "All grid cells are represented in the sidecar." : `${actual} of ${expected} grid cells have ranges.`,
    ratio < 0.35 ? "The bbox is selective enough for a focused read." : "The bbox covers a broad area; expect larger point reads.",
    activeIndex.header.source_sha1 ? "Source fingerprint is present for stale-sidecar checks." : "Source fingerprint is missing.",
  ];
  el.healthList.innerHTML = "";
  signals.forEach((signal) => {
    const item = document.createElement("li");
    item.textContent = signal;
    el.healthList.append(item);
  });
}

function renderCells() {
  el.cellList.innerHTML = "";
  if (!activeCells.length) {
    const item = document.createElement("span");
    item.className = "cell-pill";
    item.textContent = "No intersecting cells";
    el.cellList.append(item);
    return;
  }
  activeCells.slice(0, 80).forEach((cell) => {
    const item = document.createElement("span");
    item.className = "cell-pill";
    item.textContent = `${cell.i},${cell.j} | ${formatNumber(cell.count)}`;
    el.cellList.append(item);
  });
}

function drawGrid() {
  const canvas = el.gridCanvas;
  const ctx = canvas.getContext("2d");
  const { width, height } = canvas;
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#edf5f1";
  ctx.fillRect(0, 0, width, height);

  const padding = 34;
  const plotW = width - padding * 2;
  const plotH = height - padding * 2;
  const [nx, ny] = activeIndex.header.grid_shape;
  const cellW = plotW / nx;
  const cellH = plotH / ny;
  const hit = new Set(activeCells.map((cell) => `${cell.i},${cell.j}`));

  ctx.strokeStyle = "#c6d6cf";
  ctx.lineWidth = 1;
  for (let i = 0; i < nx; i += 1) {
    for (let j = 0; j < ny; j += 1) {
      const x = padding + i * cellW;
      const y = padding + (ny - 1 - j) * cellH;
      ctx.fillStyle = hit.has(`${i},${j}`) ? "rgba(255, 200, 87, 0.58)" : "#ffffff";
      ctx.fillRect(x, y, cellW - 1, cellH - 1);
      ctx.strokeRect(x, y, cellW, cellH);
    }
  }

  const maxCount = Math.max(...Object.values(activeIndex.cells).map((range) => Number(range[1])));
  Object.entries(activeIndex.cells).forEach(([key, range]) => {
    const [i, j] = key.split(",").map(Number);
    const count = Number(range[1]);
    const x = padding + i * cellW + cellW / 2;
    const y = padding + (ny - 1 - j) * cellH + cellH / 2;
    const radius = Math.max(2, Math.min(9, (count / maxCount) * 8));
    ctx.beginPath();
    ctx.fillStyle = hit.has(key) ? "#0f4c39" : "#0f6f7a";
    ctx.globalAlpha = hit.has(key) ? 0.9 : 0.42;
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();
  });
  ctx.globalAlpha = 1;

  const bbox = bboxFromInputs();
  const [minx, miny, maxx, maxy] = activeIndex.header.bbox;
  const bx = padding + ((bbox[0] - minx) / (maxx - minx)) * plotW;
  const by = padding + ((maxy - bbox[3]) / (maxy - miny)) * plotH;
  const bw = ((bbox[2] - bbox[0]) / (maxx - minx)) * plotW;
  const bh = ((bbox[3] - bbox[1]) / (maxy - miny)) * plotH;
  ctx.strokeStyle = "#9f2f36";
  ctx.lineWidth = 4;
  ctx.strokeRect(bx, by, bw, bh);
  ctx.fillStyle = "rgba(159, 47, 54, 0.08)";
  ctx.fillRect(bx, by, bw, bh);

  ctx.fillStyle = "#56635d";
  ctx.font = "12px Arial, sans-serif";
  ctx.fillText(`${Math.round(minx)}, ${Math.round(miny)}`, padding, height - 10);
  ctx.fillText(`${Math.round(maxx)}, ${Math.round(maxy)}`, width - padding - 120, 20);
}

function readSidecar(file) {
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const parsed = normalizeIndex(JSON.parse(String(reader.result)));
      loadIndex(parsed, file.name);
      setStatus("Sidecar loaded");
    } catch (error) {
      setStatus("Load failed", "error");
      el.fileName.textContent = error.message;
    }
  };
  reader.readAsText(file);
}

el.sampleButton.addEventListener("click", () => {
  const sample = samples[el.sampleSelect.value];
  loadIndex(sample, "Using sample sidecar");
});

el.queryButton.addEventListener("click", previewQuery);
["minx", "miny", "maxx", "maxy"].forEach((id) => {
  el[id].addEventListener("input", previewQuery);
});

el.sidecarInput.addEventListener("change", (event) => {
  const file = event.target.files?.[0];
  if (file) {
    readSidecar(file);
  }
});

["dragenter", "dragover"].forEach((name) => {
  el.dropZone.addEventListener(name, (event) => {
    event.preventDefault();
    el.dropZone.classList.add("drag-active");
  });
});

["dragleave", "drop"].forEach((name) => {
  el.dropZone.addEventListener(name, (event) => {
    event.preventDefault();
    el.dropZone.classList.remove("drag-active");
  });
});

el.dropZone.addEventListener("drop", (event) => {
  const file = event.dataTransfer.files?.[0];
  if (file) {
    readSidecar(file);
  }
});

window.addEventListener("resize", drawGrid);
loadIndex(activeIndex, "Using sample sidecar");
