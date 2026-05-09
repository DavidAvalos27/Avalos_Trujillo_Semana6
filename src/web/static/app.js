const boardEl = document.querySelector("#board");
const noticeEl = document.querySelector("#notice");
const facePill = document.querySelector("#facePill");
const turnPill = document.querySelector("#turnPill");
const faceMessage = document.querySelector("#faceMessage");
const newGameButton = document.querySelector("#newGame");
const cameraGate = document.querySelector("#cameraGate");

const metricMode = document.querySelector("#metricMode");
const metricNodes = document.querySelector("#metricNodes");
const metricTime = document.querySelector("#metricTime");
const metricScore = document.querySelector("#metricScore");

let state = null;
let starter = "humano";
let difficulty = "imposible";

function createBoard() {
  boardEl.innerHTML = "";
  for (let index = 0; index < 9; index += 1) {
    const cell = document.createElement("button");
    cell.className = "cell";
    cell.type = "button";
    cell.dataset.index = String(index);
    cell.setAttribute("aria-label", `Casilla ${index + 1}`);
    cell.addEventListener("click", () => play(index));
    boardEl.appendChild(cell);
  }
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    noticeEl.textContent = data.notice || "No se pudo completar la accion.";
  }
  return data;
}

async function loadState() {
  state = await requestJson("/api/state");
  render();
}

async function newGame() {
  state = await requestJson("/api/new-game", {
    method: "POST",
    body: JSON.stringify({ starter, difficulty }),
  });
  render();
}

async function play(index) {
  if (!state || state.game_over || state.current_player !== "O") {
    return;
  }
  state = await requestJson("/api/move", {
    method: "POST",
    body: JSON.stringify({ index }),
  });
  render();
}

async function updateCameraGate() {
  state = await requestJson("/api/settings", {
    method: "POST",
    body: JSON.stringify({ camera_gate: cameraGate.checked }),
  });
  render();
}

async function pollFace() {
  const data = await requestJson("/api/face");
  if (state) {
    state.face_present = data.face_present;
    state.face_message = data.message;
    state.camera_gate = data.camera_gate;
    renderStatus();
    renderCells();
  }
}

function setActiveButtons(groupSelector, value, dataName) {
  document.querySelectorAll(`${groupSelector} button`).forEach((button) => {
    button.classList.toggle("active", button.dataset[dataName] === value);
  });
}

function render() {
  if (!state) {
    return;
  }
  renderCells();
  renderStatus();
  renderMetrics();
}

function renderCells() {
  const win = new Set(state?.winning_line || []);
  document.querySelectorAll(".cell").forEach((cell) => {
    const index = Number(cell.dataset.index);
    const value = state.board[index];
    const playable = state.current_player === "O" && !state.game_over && value === "" && (state.face_present || !state.camera_gate);

    cell.innerHTML = value ? `<span class="mark ${value === "X" ? "x" : "o"}">${value}</span>` : "";
    cell.classList.toggle("disabled", !playable);
    cell.classList.toggle("last", state.last_move === index);
    cell.classList.toggle("win", win.has(index));
    cell.disabled = !playable;
  });
}

function renderStatus() {
  const faceReady = Boolean(state.face_present) || !state.camera_gate;
  facePill.textContent = faceReady ? "Rostro detectado" : "Esperando rostro";
  facePill.classList.toggle("ready", faceReady);
  facePill.classList.toggle("waiting", !faceReady);

  if (state.game_over) {
    turnPill.textContent = "Partida finalizada";
  } else {
    turnPill.textContent = state.current_player === "X" ? "Turno IA" : "Turno humano";
  }

  faceMessage.textContent = state.face_message || "Camara activa.";
  noticeEl.textContent = state.message;
}

function renderMetrics() {
  const metrics = state.metrics || {};
  metricMode.textContent = capitalize(metrics.mode || difficulty);
  metricNodes.textContent = String(metrics.nodes ?? 0);
  metricTime.textContent = `${metrics.elapsed_ms ?? 0} ms`;
  metricScore.textContent = String(metrics.score ?? 0);
}

function capitalize(value) {
  return `${value}`.charAt(0).toUpperCase() + `${value}`.slice(1);
}

document.querySelectorAll("#difficulty button").forEach((button) => {
  button.addEventListener("click", () => {
    difficulty = button.dataset.difficulty;
    setActiveButtons("#difficulty", difficulty, "difficulty");
    newGame();
  });
});

document.querySelectorAll("#starter button").forEach((button) => {
  button.addEventListener("click", () => {
    starter = button.dataset.starter;
    setActiveButtons("#starter", starter, "starter");
    newGame();
  });
});

newGameButton.addEventListener("click", newGame);
cameraGate.addEventListener("change", updateCameraGate);

createBoard();
loadState();
setInterval(loadState, 900);
setInterval(pollFace, 450);
