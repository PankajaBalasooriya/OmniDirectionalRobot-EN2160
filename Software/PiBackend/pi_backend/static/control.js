"use strict";
const get = (id) => document.getElementById(id);
const buttons = [...document.querySelectorAll("[data-direction]")];
let selected = "forward";
let status = null;
let sending = false;
let online = false;
let refreshSequence = 0;
let uncertainDelivery = false;

function availability() {
  if (!online || !status) return "Backend unavailable. Motion controls disabled.";
  if (uncertainDelivery) return "Delivery uncertain. Inspect the robot, then acknowledge below before another move.";
  if (sending) return "Submitting one move…";
  if (status.state !== "idle") return `Backend is ${status.state}. No new move allowed.`;
  if (status.mode === "uart") {
    if (!status.hardware_enabled) return "Hardware motion is disabled on the backend.";
    if (selected === "backward_left") return "Backward-left is blocked due to a known firmware direction defect.";
    if (!get("ack").checked) return "Confirm hardware safety checks before sending a move.";
  }
  return "";
}

function renderControls() {
  get("motion-controls").disabled = !online || sending || !status || status.state !== "idle";
  for (const button of buttons) {
    button.disabled = status?.mode === "uart" && button.dataset.direction === "backward_left";
    button.setAttribute("aria-pressed", String(button.dataset.direction === selected));
  }
  get("inspect").hidden = !uncertainDelivery;
  const reason = availability();
  get("send").disabled = Boolean(reason);
  get("availability").textContent = reason || (status.mode === "simulation"
    ? "Simulation only: no UART commands will be sent."
    : "One discrete move; no software stop is available.");
}

async function request(url, options = {}) {
  const response = await fetch(url, {...options, signal: AbortSignal.timeout(5000), cache: "no-store"});
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || `HTTP ${response.status}`);
  return body;
}

async function refresh() {
  const sequence = ++refreshSequence;
  try {
    const next = await request("/api/status");
    if (sequence !== refreshSequence) return;
    if (status && status.backend_id !== next.backend_id) get("ack").checked = false;
    status = next;
    online = true;
    get("mode").textContent = status.mode === "simulation" ? "SIMULATION · no hardware" : "LIVE UART · hardware";
    get("ack-label").hidden = status.mode !== "uart";
    get("state").textContent = status.state;
    get("uart").textContent = status.mode === "uart" ? `${status.port} · ${status.baudrate} baud` : "Not opened";
    get("last").textContent = status.last_command
      ? `${status.last_command.direction} / ${status.last_command.value} (bytes ${status.last_command.packet_hex})` : "None";
    get("fault").textContent = status.error || "None reported";
    get("updated").textContent = new Date().toLocaleTimeString();
    get("telemetry").textContent = Object.keys(status.telemetry).length
      ? JSON.stringify(status.telemetry, null, 2) : "No telemetry yet.";
  } catch (error) {
    if (sequence !== refreshSequence) return;
    online = false;
    get("ack").checked = false;
    get("mode").textContent = "OFFLINE · status unknown";
    get("state").textContent = "Unknown — backend unreachable";
    get("fault").textContent = error.message;
  }
  renderControls();
}

for (const button of buttons) {
  button.addEventListener("click", () => {
    selected = button.dataset.direction;
    get("selection").textContent = `Selected: ${button.textContent.trim().replace(/\s+/g, " ")}`;
    renderControls();
  });
}
get("ack").addEventListener("change", renderControls);
get("inspect").addEventListener("click", () => {
  uncertainDelivery = false;
  get("ack").checked = false;
  get("result").textContent = "Operator acknowledged robot inspection. No move has been retried.";
  renderControls();
});
get("move-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (availability()) return;
  const value = Number(get("value").value);
  if (!Number.isInteger(value) || value < 1 || value > 255) {
    get("result").textContent = "Enter an integer from 1 to 255.";
    return;
  }
  sending = true;
  renderControls();
  try {
    const result = await request("/api/move", {method: "POST",
      headers: {"Content-Type": "application/json", "X-Backend-ID": status.backend_id,
        "X-Expected-Mode": status.mode}, body: JSON.stringify({direction: selected, value})});
    get("result").textContent = result.simulated
      ? `Simulated acceptance · bytes ${result.packet_hex}. No physical move occurred.`
      : `Accepted for UART transmission · bytes ${result.packet_hex}. This is not completion confirmation.`;
  } catch (error) {
    uncertainDelivery = true;
    get("result").textContent = `Move request failed: ${error.message}. Delivery may be uncertain; do not automatically retry. Check robot status.`;
  } finally {
    await refresh();
    sending = false;
    renderControls();
  }
});

async function poll() {
  await refresh();
  window.setTimeout(poll, 1000);
}
poll();
