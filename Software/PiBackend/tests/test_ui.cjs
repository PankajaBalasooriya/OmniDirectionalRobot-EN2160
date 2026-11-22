// Lightweight DOM/fetch contract checks; no browser or UART required.
const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");
function element() {
  return {disabled: false, hidden: false, checked: false, value: "1", textContent: "",
    listeners: {}, addEventListener(name, fn) { this.listeners[name] = fn; },
    setAttribute() {}};
}
const ids = Object.fromEntries(["mode", "motion-controls", "ack", "ack-label", "send",
  "availability", "state", "uart", "last", "fault", "updated", "telemetry", "selection",
  "move-form", "value", "result", "inspect"].map(id => [id, element()]));
const directions = ["forward", "right", "backward_left"].map(direction => ({
  ...element(), dataset: {direction}, textContent: direction}));
let backend = {backend_id: "instance-1", mode: "simulation", state: "idle", telemetry: {}, last_command: null};
let offline = false;
let failMove = false;
const deferredStatus = [];
const moves = [];
const context = vm.createContext({document: {getElementById: id => ids[id],
  querySelectorAll: () => directions}, window: {setTimeout() {}},
  AbortSignal, Date, console, fetch: async (url, options) => {
    if (offline) throw new Error("offline");
    if (url === "/api/status") {
      if (deferredStatus.length) return deferredStatus.shift();
      return {ok: true, json: async () => backend};
    }
    if (failMove) throw new Error("lost response");
    assert.equal(options.headers["X-Backend-ID"], backend.backend_id);
    assert.equal(options.headers["X-Expected-Mode"], backend.mode);
    moves.push(JSON.parse(options.body));
    return {ok: true, json: async () => ({simulated: backend.mode === "simulation", packet_hex: "0401"})};
  }});
vm.runInContext(fs.readFileSync("pi_backend/static/control.js", "utf8"), context);
const tick = () => new Promise(resolve => setImmediate(resolve));
const submit = () => ids["move-form"].listeners.submit({preventDefault() {}});
(async () => {
  await tick();
  assert.equal(ids.send.disabled, false);
  directions[1].listeners.click();
  assert.equal(moves.length, 0, "selection must not send motion");
  await submit();
  assert.deepEqual(moves, [{direction: "right", value: 1}]);
  assert.match(ids.result.textContent, /Simulated/);
  backend = {...backend, mode: "uart", hardware_enabled: false};
  await vm.runInContext("refresh()", context);
  assert.equal(ids.send.disabled, true);
  await submit();
  assert.equal(moves.length, 1);
  backend.hardware_enabled = true;
  ids.ack.checked = true;
  await vm.runInContext("refresh()", context);
  assert.equal(ids.send.disabled, false);
  directions[2].listeners.click();
  assert.equal(ids.send.disabled, true, "known bad direction must be blocked live");
  directions[0].listeners.click();
  backend.state = "awaiting_completion";
  await vm.runInContext("refresh()", context);
  assert.equal(ids.send.disabled, true);
  offline = true;
  await vm.runInContext("refresh()", context);
  assert.equal(ids.send.disabled, true);
  assert.equal(ids.ack.checked, false);
  offline = false;
  backend = {...backend, mode: "simulation", state: "idle"};
  await vm.runInContext("refresh()", context);
  failMove = true;
  await submit();
  assert.equal(ids.send.disabled, true, "uncertain submission must latch even when idle");
  await vm.runInContext("refresh()", context);
  assert.equal(ids.send.disabled, true);
  assert.equal(ids.inspect.hidden, false);
  ids.inspect.listeners.click();
  assert.equal(ids.send.disabled, false);

  let resolveOld;
  deferredStatus.push(new Promise(resolve => { resolveOld = resolve; }));
  const oldRefresh = vm.runInContext("refresh()", context);
  backend = {...backend, state: "fault"};
  await vm.runInContext("refresh()", context);
  resolveOld({ok: true, json: async () => ({...backend, state: "idle"})});
  await oldRefresh;
  assert.equal(ids.state.textContent, "fault", "old response must not overwrite newer status");
  assert.equal(ids.send.disabled, true);
  console.log("UI contract checks passed");
})().catch(error => { console.error(error); process.exitCode = 1; });
