import assert from "node:assert/strict";
import test from "node:test";
import {readLinkedSnapshot, sendSnapshot} from "./worker.mjs";

const hash = async value => Buffer.from(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value))).toString("hex");

test("linked household read is one query and rejects unauthorized scopes", async () => {
  const now = Date.now(), token = "a".repeat(64), expectedHash = await hash(token);
  const generation = await hash("synthetic-generation");
  let queries = 0;
  const row = {write_hash: "synthetic-generation", timezone: "Europe/Berlin",
    live_at: new Date(now).toISOString(), live_json: JSON.stringify({power_w: 1005, home_w: 650, battery_soc: 55}),
    history_at: new Date(now).toISOString(), history_json: JSON.stringify({month_pv_kwh: 100})};
  const env = {DEV_TARGET: JSON.stringify({household: "synthetic-household", generation}),
    SOURCE_DB: {prepare(sql) {
      assert(sql.includes("a.expires>?") && sql.includes("h.id=?") && sql.includes("h.disabled=0"));
      return {bind(tokenHash, at, household) {return {async first() {
        queries++;
        return tokenHash === expectedHash && at === Math.floor(now / 1000) && household === "synthetic-household" ? row : null;
      }}}};
    }}};
  const request = value => new Request("https://example.invalid/v1/pv", {headers: value ? {Authorization: "Bearer " + value} : {}});
  const response = await readLinkedSnapshot(request(token), env, now);
  assert.equal(response.status, 200);
  assert.equal(queries, 1);
  const body = await response.json();
  assert.equal(body.power_w, 1005);
  assert.equal(body.history.month_pv_kwh, 100);
  assert.equal(response.headers.get("Cache-Control"), "no-store");
  assert.equal((await readLinkedSnapshot(request("b".repeat(64)), env, now)).status, 401);
  assert.equal((await readLinkedSnapshot(request(null), env, now)).status, 401);
  const other = {...env, DEV_TARGET: JSON.stringify({household: "foreign", generation})};
  assert.equal((await readLinkedSnapshot(request(token), other, now)).status, 401);
  row.write_hash = "rotated";
  assert.equal((await readLinkedSnapshot(request(token), env, now)).status, 401);
});

test("three changing pushes use one read and one complete object each", async () => {
  const now = Date.now(), generation = await hash("synthetic-generation");
  let reads = 0, sends = 0;
  const writes = [];
  const row = {write_hash: "synthetic-generation", timezone: "Europe/Berlin"};
  const env = {DEV_TARGET: JSON.stringify({device: "amzn1.ask.device.synthetic", household: "synthetic", generation}),
    SOURCE_DB: {prepare(sql) {assert(sql.includes("disabled=0")); return {bind(id) {
      assert.equal(id, "synthetic"); return {async first() {reads++; return row;}};
    }}}}};
  const send = async (url, init) => {
    sends++;
    assert.equal(init.redirect, "manual");
    if (url.includes("/auth/")) return Response.json({access_token: "synthetic"});
    writes.push(JSON.parse(init.body).commands[0].content);
    return Response.json({results: [{deviceId: "amzn1.ask.device.synthetic", type: "SUCCESS"}]});
  };
  for (let i = 0; i < 3; i++) {
    row.live_at = new Date(now + i * 60000).toISOString();
    row.live_json = JSON.stringify({power_w: 1005 + i * 100, home_w: 650 + i * 50, battery_soc: 50 + i});
    assert.equal(await sendSnapshot(env, now + i * 60000, send), "accepted");
  }
  assert.equal(reads, 3); assert.equal(sends, 6); assert.equal(writes.length, 3);
  assert.equal(writes[0].solar, "1,01 kW");
  assert.equal(new Set(writes.map(w => w.sampleTime)).size, 3);
  row.live_at = new Date(now).toISOString();
  row.live_json = JSON.stringify({power_w: null, home_w: 1, battery_soc: 1});
  await assert.rejects(sendSnapshot(env, now, send), /invalid_measurement/);
  assert.equal(writes.length, 3);
});
