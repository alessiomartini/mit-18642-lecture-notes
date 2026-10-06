/* Study page: math, sticky YouTube player synced with paragraphs, local notes/solutions. No framework. */
(function () {
  "use strict";
  const CH = window.STUDY.chapter;
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
  const esc = (t) => t.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  const fmt = (s) => { s = Math.floor(s); const h = Math.floor(s / 3600), m = Math.floor(s / 60) % 60, x = s % 60;
    return (h ? h + ":" + String(m).padStart(2, "0") : m) + ":" + String(x).padStart(2, "0"); };
  const say = (t) => { $("#msg").textContent = t || ""; };

  /* ---------- math ---------- */
  const KATEX = {
    delimiters: [{ left: "\\[", right: "\\]", display: true }, { left: "\\(", right: "\\)", display: false }],
    throwOnError: false,
    macros: { "\\Prob": "\\mathbb{P}", "\\E": "\\mathbb{E}", "\\Q": "\\mathbb{Q}", "\\R": "\\mathbb{R}", "\\N": "\\mathbb{N}",
      "\\Var": "\\operatorname{Var}", "\\Cov": "\\operatorname{Cov}", "\\Corr": "\\operatorname{Corr}",
      "\\tr": "\\operatorname{tr}", "\\rank": "\\operatorname{rank}", "\\diag": "\\operatorname{diag}",
      "\\T": "^{\\mathsf T}", "\\dd": "\\,\\mathrm{d}", "\\ind": "\\mathbf{1}", "\\eqd": "\\stackrel{d}{=}",
      "\\bm": "\\boldsymbol{#1}" },
  };
  const math = (el) => { if (window.renderMathInElement) renderMathInElement(el || document.body, KATEX); };
  window.addEventListener("load", () => math());
  if (document.readyState !== "loading") math();

  /* ---------- video ---------- */
  const anchors = {};          // video id -> [{t, unit}] sorted by t
  const lectures = [];         // [{key, vid}]
  $$("a.ts[data-v]").forEach((a) => {
    const v = a.dataset.v, t = +a.dataset.t, unit = a.closest(".u");
    (anchors[v] = anchors[v] || []).push({ t, unit, a });
    if (!lectures.some((l) => l.vid === v)) lectures.push({ key: a.dataset.k, vid: v });
  });
  Object.values(anchors).forEach((l) => l.sort((x, y) => x.t - y.t));
  const sel = $("#lecture");
  lectures.forEach((l) => { const [y, n] = l.key.split("@"); const o = document.createElement("option");
    o.value = l.vid; o.textContent = `20${y} lecture ${n}`; sel.appendChild(o); });
  let player = null, ready = false, pending = null, curUnit = null, curA = null;

  window.onYouTubeIframeAPIReady = function () {
    if (!lectures.length) return;
    player = new YT.Player("player", {
      videoId: lectures[0].vid, host: "https://www.youtube.com",
      playerVars: { rel: 0, playsinline: 1, origin: location.origin },
      events: { onReady: () => { ready = true; if (pending) { load(pending.v, pending.t); pending = null; } },
                onError: () => say("Video unavailable (offline?)") },
    });
  };
  if (window.YT && YT.Player) window.onYouTubeIframeAPIReady();

  function curVid() { try { return player.getVideoData().video_id; } catch (e) { return null; } }
  function load(v, t) {
    if (!ready) { pending = { v, t }; return; }
    sel.value = v;
    if (curVid() === v) player.seekTo(t, true); else player.loadVideoById(v, t);
    player.playVideo();
  }
  sel.addEventListener("change", () => { if (ready) player.cueVideoById(sel.value, 0); });
  document.addEventListener("click", (e) => {
    const a = e.target.closest("a.ts[data-v]");
    if (!a) return;
    e.preventDefault(); load(a.dataset.v, +a.dataset.t);
  });

  function tick() {
    if (!ready || !player.getCurrentTime) return;
    const v = curVid(), t = player.getCurrentTime();
    $("#clock").textContent = fmt(t);
    if (v && sel.value !== v && anchors[v]) sel.value = v;
    const list = anchors[v]; if (!list) return;
    let best = null;
    for (const x of list) { if (x.t <= t + 0.7) best = x; else break; }   // last timestamp already reached
    const unit = best && best.unit;
    if (best && best.a !== curA) { if (curA) curA.classList.remove("active"); curA = best.a; curA.classList.add("active"); }
    if (unit !== curUnit) {
      if (curUnit) curUnit.classList.remove("now");
      curUnit = unit;
      if (unit) { unit.classList.add("now");
        if ($("#follow").checked) unit.scrollIntoView({ block: "center", behavior: "smooth" }); }
    }
  }
  setInterval(tick, 400);

  /* ---------- notes ---------- */
  function md(text) {
    const m = [];
    let t = text.replace(/\$\$([\s\S]+?)\$\$|\$([^$\n]+?)\$/g, (s, a, b) => { m.push([a != null, a != null ? a : b]); return "@@M" + (m.length - 1) + "@@"; });
    let h = window.marked ? marked.parse(t, { breaks: true }) : "<p>" + esc(t).replace(/\n/g, "<br>") + "</p>";
    return h.replace(/@@M(\d+)@@/g, (s, i) => { const [d, x] = m[i]; return d ? "\\[" + esc(x) + "\\]" : "\\(" + esc(x) + "\\)"; });
  }
  const api = async (method, url, body) => {
    const r = await fetch(url, { method, headers: body ? { "Content-Type": "application/json" } : {}, body: body ? JSON.stringify(body) : undefined });
    if (!r.ok) throw new Error((await r.text()) || r.status);
    return r.json();
  };
  const unitEl = (id) => document.getElementById(id);

  function card(n) {
    const d = document.createElement("div");
    d.className = "sc mine" + (n.kind === "solution" ? " sol" : ""); d.dataset.id = n.id;
    const tag = n.imported_at ? '<span class="tag t-imported">IMPORTED</span>' : '<span class="tag t-new">NEW</span>';
    const vt = n.video_time != null && n.video_id
      ? ` &middot; <a class="ts" href="https://youtu.be/${n.video_id}?t=${Math.floor(n.video_time)}" data-v="${n.video_id}" data-t="${Math.floor(n.video_time)}">&#9654; ${fmt(n.video_time)}</a>` : "";
    d.innerHTML = `${tag}<b>${n.kind}</b>${md(n.text)}<div class="meta">${esc((n.created_at || "").slice(0, 16).replace("T", " "))}${vt}
      ${n.imported_at ? "" : ' &middot; <button class="del">delete</button>'}</div>`;
    const del = $(".del", d);
    if (del) del.onclick = async () => { if (!confirm("Delete this note?")) return;
      try { await api("DELETE", "/api/notes/" + n.id); d.remove(); } catch (e) { alert(e.message); } };
    return d;
  }
  function place(n) {
    const u = unitEl(n.paragraph_id);
    if (!u) { const o = $("#orphans") || (() => { const x = document.createElement("div"); x.id = "orphans"; x.className = "side";
      x.innerHTML = "<h3>Notes whose paragraph is no longer in the text</h3>"; $("#page").appendChild(x); return x; })(); o.appendChild(card(n)); return; }
    const c = card(n);
    if (n.kind === "solution") (u.querySelector(".mysol") || u).appendChild(c);
    else (u.closest(".row").querySelector(".side")).appendChild(c);
    math(c); u.classList.add("has-notes");
  }

  function openEditor(u, kinds) {
    if (u._ed && u._ed.isConnected) { u._ed.remove(); return; }
    const e = document.createElement("div");
    e.className = "editor" + (kinds[0] === "solution" ? " sol" : "");
    e.innerHTML = `<textarea placeholder="${kinds[0] === "solution" ? "My solution (Markdown, $math$)" : "Note or question (Markdown, $math$)"}"></textarea>
      <div class="preview"></div>
      <div class="bar2">${kinds.length > 1 ? '<select class="kind">' + kinds.map((k) => `<option>${k}</option>`).join("") + "</select>" : ""}
      <label><input type="checkbox" class="attach"> attach video time <span class="vt"></span></label>
      <button class="save">Save</button><button class="cancel">Cancel</button><span class="err"></span></div>`;
    u._ed = e;
    if (kinds[0] === "solution") $(".mysol", u).appendChild(e); else u.after(e);
    const ta = $("textarea", e), pv = $(".preview", e);
    const t0 = ready && player.getCurrentTime ? player.getCurrentTime() : 0;
    if (t0 > 0.5) { $(".attach", e).checked = true; $(".vt", e).textContent = fmt(t0); }
    let timer; ta.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(() => { pv.innerHTML = ta.value.trim() ? md(ta.value) : ""; math(pv); }, 150); });
    $(".cancel", e).onclick = () => e.remove();
    $(".save", e).onclick = async () => {
      if (!ta.value.trim()) return;
      const body = { chapter: CH, paragraph_id: u.id || u.dataset.ex, kind: ($(".kind", e) || { value: kinds[0] }).value,
        text: ta.value, created_at: new Date().toISOString() };
      if ($(".attach", e).checked && ready) { body.video_time = Math.floor(player.getCurrentTime()); body.video_id = curVid(); }
      try { const n = await api("POST", "/api/notes", body); e.remove(); place(n); }
      catch (x) { $(".err", e).textContent = "Not saved: " + x.message; }
    };
    ta.focus();
  }
  document.addEventListener("click", (ev) => {
    const b = ev.target.closest("button.add");
    if (b) openEditor(b.closest(".u"), ["note", "question"]);
    const s = ev.target.closest("button.solbtn");
    if (s) openEditor(document.getElementById(s.dataset.ex), ["solution"]);
  });
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" && (ev.ctrlKey || ev.metaKey) && ev.target.matches(".editor textarea")) $(".save", ev.target.closest(".editor")).click();
  });

  api("GET", "/api/notes?chapter=" + CH).then((rows) => rows.forEach(place)).catch(() => say("Notes server not running (python study/server.py)"));
})();
