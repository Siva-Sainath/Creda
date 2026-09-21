import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.160.1/build/three.module.js";

const REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const STAGE_U = [0.14, 0.38, 0.58, 0.92];
const LIVE_U = {
  intake: 0.14,
  evidence: 0.38,
  official_checks: 0.58,
  qwen_weigh: 0.74,
  stamp: 0.92,
};
const LIVE_STAGE = {
  intake: 0,
  evidence: 1,
  official_checks: 2,
  qwen_weigh: 2,
  stamp: 3,
};

function lerp(a, b, t) {
  return a + (b - a) * t;
}

// #region agent log
function dbgLog(hypothesisId, location, message, data) {
  fetch("http://127.0.0.1:7669/ingest/4ad1f601-7980-4b32-bbec-c86691d43e55", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Debug-Session-Id": "2641c1" },
    body: JSON.stringify({
      sessionId: "2641c1",
      runId: "pre-fix",
      hypothesisId,
      location,
      message,
      data,
      timestamp: Date.now(),
    }),
  }).catch(function () {});
}
// #endregion

function texCard(title, lines, head) {
  const c = document.createElement("canvas");
  c.width = 256;
  c.height = 320;
  const ctx = c.getContext("2d");
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, 256, 320);
  ctx.fillStyle = head;
  ctx.fillRect(0, 0, 256, 44);
  ctx.fillStyle = "#ffffff";
  ctx.font = "700 22px 'Plus Jakarta Sans', system-ui, sans-serif";
  ctx.fillText(title, 16, 30);
  ctx.fillStyle = "#0f2433";
  ctx.font = "500 18px 'Plus Jakarta Sans', system-ui, sans-serif";
  (lines || []).forEach(function (line, i) {
    ctx.fillRect(16, 72 + i * 36, Math.min(220, 80 + line.length * 8), 10);
  });
  ctx.fillStyle = "#5f6d7a";
  ctx.font = "600 14px 'JetBrains Mono', monospace";
  (lines || []).forEach(function (line, i) {
    ctx.fillText(line, 16, 68 + i * 36);
  });
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  const mat = new THREE.MeshStandardMaterial({ map: tex, roughness: 0.46, metalness: 0 });
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(1.05, 1.32, 0.05), mat);
  return mesh;
}

function chip(label, color) {
  const c = document.createElement("canvas");
  c.width = 256;
  c.height = 64;
  const ctx = c.getContext("2d");
  ctx.fillStyle = color;
  ctx.fillRect(0, 0, 256, 64);
  ctx.fillStyle = "#ffffff";
  ctx.font = "700 28px 'JetBrains Mono', monospace";
  ctx.textAlign = "center";
  ctx.fillText(label, 128, 42);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  const mesh = new THREE.Mesh(
    new THREE.BoxGeometry(0.92, 0.24, 0.04),
    new THREE.MeshStandardMaterial({ map: tex, roughness: 0.4 })
  );
  return mesh;
}

function siteBlock() {
  const g = new THREE.Group();
  const frame = new THREE.Mesh(
    new THREE.BoxGeometry(1.15, 1.05, 0.08),
    new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.42 })
  );
  const bar = new THREE.Mesh(
    new THREE.BoxGeometry(1.15, 0.18, 0.09),
    new THREE.MeshStandardMaterial({ color: 0x155eef, roughness: 0.35 })
  );
  bar.position.y = 0.435;
  const lock = new THREE.Mesh(
    new THREE.TorusGeometry(0.07, 0.018, 8, 16),
    new THREE.MeshStandardMaterial({ color: 0xc8f06c, roughness: 0.3 })
  );
  lock.position.set(-0.38, 0.435, 0.06);
  const page = new THREE.Mesh(
    new THREE.BoxGeometry(0.86, 0.58, 0.03),
    new THREE.MeshStandardMaterial({ color: 0xeff4ff, roughness: 0.5 })
  );
  page.position.y = -0.08;
  g.add(frame, bar, lock, page);
  return g;
}

function stampPress() {
  const g = new THREE.Group();
  const handle = new THREE.Mesh(
    new THREE.CylinderGeometry(0.08, 0.08, 0.55, 12),
    new THREE.MeshStandardMaterial({ color: 0x3d5a45, roughness: 0.4 })
  );
  handle.position.y = 0.62;
  const head = new THREE.Mesh(
    new THREE.BoxGeometry(0.85, 0.22, 0.85),
    new THREE.MeshStandardMaterial({ color: 0xb42318, roughness: 0.38 })
  );
  head.position.y = 0.28;
  const pad = new THREE.Mesh(
    new THREE.BoxGeometry(0.92, 0.06, 0.92),
    new THREE.MeshStandardMaterial({ color: 0x7a271a, roughness: 0.55 })
  );
  pad.position.y = 0.14;
  const paper = new THREE.Mesh(
    new THREE.BoxGeometry(1.05, 0.03, 1.2),
    new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.5 })
  );
  paper.position.y = 0;
  g.add(handle, head, pad, paper);
  g.userData.head = head;
  g.userData.handle = handle;
  g.userData.pad = pad;
  return g;
}

function stationMark() {
  const ring = new THREE.Mesh(
    new THREE.RingGeometry(0.72, 0.78, 40),
    new THREE.MeshBasicMaterial({ color: 0x155eef, transparent: true, opacity: 0.18, side: THREE.DoubleSide })
  );
  ring.rotation.x = -Math.PI / 2;
  ring.position.y = -0.02;
  return ring;
}

function labelAnchor(x, y, z) {
  const obj = new THREE.Object3D();
  obj.position.set(x, y, z);
  return obj;
}

function project(camera, obj, canvas) {
  const v = obj.getWorldPosition(new THREE.Vector3());
  v.project(camera);
  return {
    x: (v.x * 0.5 + 0.5) * canvas.clientWidth,
    y: (-v.y * 0.5 + 0.5) * canvas.clientHeight,
  };
}

function start() {
  const host = document.getElementById("iso-host");
  const canvas = document.getElementById("iso-canvas");
  if (!host || !canvas || REDUCED) {
    window.CredaPass = { mount: function () {}, setStage: function () {}, setMode: function () {}, sync: function () {} };
    return;
  }

  const scene = new THREE.Scene();
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: false,
      powerPreference: "default",
      preserveDrawingBuffer: false,
    });
  } catch (err) {
    window.CredaPass = { mount: function () {}, setStage: function () {}, setMode: function () {}, sync: function () {} };
    return;
  }
  renderer.setClearColor(0xf3f1ec, 1);
  renderer.setPixelRatio(dpr);
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  let contextLost = false;
  canvas.addEventListener("webglcontextlost", function (e) {
    e.preventDefault();
    contextLost = true;
  });
  canvas.addEventListener("webglcontextrestored", function () {
    contextLost = false;
    lastResizeW = -1;
    lastResizeH = -1;
    resize(true);
  });

  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 50);
  camera.position.set(8.4, 6.6, 8.4);
  camera.lookAt(0.2, 0.55, 0);

  scene.add(new THREE.HemisphereLight(0xf7f4ee, 0xb7c4ce, 1.05));
  const key = new THREE.DirectionalLight(0xffffff, 1.12);
  key.position.set(5, 9, 3);
  scene.add(key);

  const root = new THREE.Group();
  scene.add(root);

  const offer = texCard("OFFER", ["sender", "fee ask", "link"], "#0f2433");
  offer.position.set(-3.05, 0.7, 0);
  offer.rotation.y = 0.18;
  offer.userData.baseY = 0.7;

  const signals = new THREE.Group();
  const fee = chip("FEE", "#b42318");
  const domain = chip("DOMAIN", "#155eef");
  const mail = chip("MAIL", "#9a6700");
  fee.position.set(0, 0.42, 0.12);
  domain.position.set(0.08, 0, 0);
  mail.position.set(-0.06, -0.42, -0.1);
  signals.add(fee, domain, mail);
  signals.position.set(-0.85, 0.7, 0.15);
  signals.userData.baseY = 0.7;

  const careers = siteBlock();
  careers.position.set(1.35, 0.62, 0);
  careers.userData.baseY = 0.62;

  const stamp = stampPress();
  stamp.position.set(3.25, 0.08, 0.1);
  stamp.userData.baseY = 0.08;

  const marks = [-3.05, -0.85, 1.35, 3.25].map(function (x) {
    const m = stationMark();
    m.position.x = x;
    root.add(m);
    return m;
  });

  root.add(offer, signals, careers, stamp);

  const path = new THREE.CatmullRomCurve3([
    new THREE.Vector3(-3.9, 0.72, 0.4),
    new THREE.Vector3(-3.05, 0.72, 0.55),
    new THREE.Vector3(-0.85, 0.95, 0.55),
    new THREE.Vector3(1.35, 0.95, 0.45),
    new THREE.Vector3(3.25, 0.55, 0.35),
  ]);
  const rail = new THREE.Mesh(
    new THREE.TubeGeometry(path, 48, 0.026, 8, false),
    new THREE.MeshBasicMaterial({ color: 0x155eef, transparent: true, opacity: 0.42 })
  );
  root.add(rail);

  const packet = texCard("MSG", ["paste"], "#155eef");
  packet.scale.setScalar(0.5);
  root.add(packet);

  const stations = [offer, signals, careers, stamp];
  const stationScale = [1, 1, 1, 1];
  const markOp = [0.18, 0.18, 0.18, 0.18];
  const anchors = {
    offer: labelAnchor(-3.05, 1.55, 0),
    signals: labelAnchor(-0.85, 1.55, 0.15),
    careers: labelAnchor(1.35, 1.45, 0),
    ruling: labelAnchor(3.25, 1.45, 0.1),
  };
  Object.values(anchors).forEach(function (a) {
    root.add(a);
  });
  const hud = {};
  host.querySelectorAll("[data-hud]").forEach(function (el) {
    hud[el.getAttribute("data-hud")] = el;
  });

  let liveMode = false;
  let liveKey = "intake";
  let rendering = false;
  let packetU = 0.12;
  let lastStage = -1;
  const metersNow = [0.22, 0.16, 0.16];
  const cycle = 7.2;
  const _fitV = new THREE.Vector3();
  const _fitBox = new THREE.Box3();
  const restMin = new THREE.Vector3();
  const restMax = new THREE.Vector3();
  let lastResizeW = -1;
  let lastResizeH = -1;
  let resizeQueued = false;
  let resizeObserver = null;
  let cameraFitted = false;
  let mountParentId = "";
  let resizeCalls = 0;
  let fitCalls = 0;
  let setSizeCalls = 0;
  let tickFrames = 0;
  let tickSkips = 0;
  let lastDbgAt = 0;

  function captureRestBox() {
    stations.forEach(function (s) {
      s.position.y = s.userData.baseY;
      s.scale.setScalar(1);
    });
    packet.scale.setScalar(0.5);
    root.updateMatrixWorld(true);
    camera.updateMatrixWorld();
    _fitBox.makeEmpty();
    stations.forEach(function (s) { _fitBox.expandByObject(s); });
    marks.forEach(function (m) { _fitBox.expandByObject(m); });
    _fitBox.expandByObject(rail);
    _fitBox.min.y -= 0.25;
    _fitBox.max.y += 1.25;
    restMin.copy(_fitBox.min);
    restMax.copy(_fitBox.max);
  }

  function placeHud() {
    if (!liveMode) return;
    const cw = canvas.clientWidth || host.clientWidth;
    const ch = canvas.clientHeight || host.clientHeight;
    const inset = 22;
    Object.keys(anchors).forEach(function (k) {
      const el = hud[k];
      if (!el) return;
      const p = project(camera, anchors[k], canvas);
      const x = Math.min(cw - inset, Math.max(inset, p.x));
      const y = Math.min(ch - inset, Math.max(inset, p.y));
      el.style.transform = "translate(" + x.toFixed(0) + "px," + y.toFixed(0) + "px) translate(-50%,-50%)";
    });
    host.classList.add("is-hud-ready");
  }

  function fitCamera(aspect) {
    camera.updateMatrixWorld();
    const inv = camera.matrixWorldInverse;
    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;
    for (let ix = 0; ix < 2; ix++) {
      for (let iy = 0; iy < 2; iy++) {
        for (let iz = 0; iz < 2; iz++) {
          _fitV.set(ix ? restMax.x : restMin.x, iy ? restMax.y : restMin.y, iz ? restMax.z : restMin.z);
          _fitV.applyMatrix4(inv);
          if (_fitV.x < minX) minX = _fitV.x;
          if (_fitV.x > maxX) maxX = _fitV.x;
          if (_fitV.y < minY) minY = _fitV.y;
          if (_fitV.y > maxY) maxY = _fitV.y;
        }
      }
    }
    const pad = 1.22;
    let halfW = ((maxX - minX) / 2) * pad;
    let halfH = ((maxY - minY) / 2) * pad;
    if (!isFinite(halfW) || halfW < 0.4) halfW = 3.6;
    if (!isFinite(halfH) || halfH < 0.3) halfH = 2.1;
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    if (halfW / halfH > aspect) halfH = halfW / aspect;
    else halfW = halfH * aspect;
    camera.left = cx - halfW;
    camera.right = cx + halfW;
    camera.top = cy + halfH;
    camera.bottom = cy - halfH;
    camera.updateProjectionMatrix();
    cameraFitted = true;
  }

  function resize(force) {
    if (!rendering) return;
    const w = Math.round(host.clientWidth || 0);
    const h = Math.round(host.clientHeight || 0);
    if (w < 48 || h < 48) return;
    if (!force && Math.abs(w - lastResizeW) < 8 && Math.abs(h - lastResizeH) < 8) return;
    resizeCalls += 1;
    const dpr = renderer.getPixelRatio();
    const bufW = renderer.domElement.width;
    const bufH = renderer.domElement.height;
    const needSize = Math.round(w * dpr) !== bufW || Math.round(h * dpr) !== bufH;
    const needFit = !cameraFitted || force;
    // #region agent log
    if (resizeCalls <= 8 || resizeCalls % 20 === 0) {
      dbgLog("H1", "iso-loop.js:resize", "resize tick", {
        force: !!force,
        w,
        h,
        needSize,
        needFit,
        cameraFitted,
        resizeCalls,
        fitCalls,
        setSizeCalls,
        parentId: host.parentElement ? host.parentElement.id : null,
      });
    }
    // #endregion
    lastResizeW = w;
    lastResizeH = h;
    if (needSize) {
      setSizeCalls += 1;
      renderer.setSize(w, h, false);
    }
    if (needFit) {
      fitCalls += 1;
      fitCamera(w / h);
    } else if (needSize) {
      fitCamera(w / h);
    }
    placeHud();
  }

  function requestResize() {
    if (!rendering || resizeQueued) return;
    resizeQueued = true;
    requestAnimationFrame(function () {
      resizeQueued = false;
      resize(false);
    });
  }

  function setRendering(on, forceResize) {
    rendering = !!on;
    if (rendering) {
      if (!resizeObserver) {
        resizeObserver = new ResizeObserver(function () {
          // #region agent log
          dbgLog("H1", "iso-loop.js:ResizeObserver", "observer fired", {
            w: Math.round(host.clientWidth || 0),
            h: Math.round(host.clientHeight || 0),
          });
          // #endregion
          requestResize();
        });
        resizeObserver.observe(host);
      }
      if (forceResize) {
        requestAnimationFrame(function () { resize(true); });
      } else {
        requestResize();
      }
      return;
    }
    if (resizeObserver) {
      resizeObserver.disconnect();
      resizeObserver = null;
    }
  }

  captureRestBox();

  function tick(now) {
    requestAnimationFrame(tick);
    tickFrames += 1;
    if (!rendering || document.hidden || contextLost) {
      tickSkips += 1;
      return;
    }
    const r = host.getBoundingClientRect();
    if (r.width < 40 || r.height < 40) {
      tickSkips += 1;
      // #region agent log
      if (now - lastDbgAt > 2000) {
        lastDbgAt = now;
        dbgLog("H4", "iso-loop.js:tick", "tick skip small rect", {
          w: Math.round(r.width),
          h: Math.round(r.height),
          tickFrames,
          tickSkips,
          resizeCalls,
          fitCalls,
          setSizeCalls,
        });
      }
      // #endregion
      return;
    }
    // #region agent log
    if (now - lastDbgAt > 2000) {
      lastDbgAt = now;
      dbgLog("H5", "iso-loop.js:tick", "tick render heartbeat", {
        liveMode,
        stage: lastStage,
        tickFrames,
        tickSkips,
        resizeCalls,
        fitCalls,
        setSizeCalls,
        parentId: host.parentElement ? host.parentElement.id : null,
      });
    }
    // #endregion

    let stage;
    let targetU;
    if (liveMode) {
      stage = LIVE_STAGE[liveKey] == null ? 0 : LIVE_STAGE[liveKey];
      targetU = LIVE_U[liveKey] == null ? STAGE_U[stage] : LIVE_U[liveKey];
      packetU = lerp(packetU, targetU, 0.045);
    } else {
      const t = (now / 1000) % cycle;
      targetU = t / cycle;
      packetU = lerp(packetU, targetU, 0.12);
      stage = packetU < 0.24 ? 0 : packetU < 0.5 ? 1 : packetU < 0.76 ? 2 : 3;
    }

    const pt = path.getPointAt(Math.min(0.999, Math.max(0.001, packetU)));
    packet.position.copy(pt);
    packet.rotation.y = 0.25 + Math.sin(now / 1400) * 0.08;
    packet.scale.setScalar(0.5);
    packet.visible = packetU < 0.97;

    stations.forEach(function (s, i) {
      const on = i === stage;
      const wantY = s.userData.baseY + (on ? 0.04 : 0);
      const wantS = on ? 1.04 : 1;
      s.position.y = lerp(s.position.y, wantY, 0.06);
      stationScale[i] = lerp(stationScale[i], wantS, 0.06);
      s.scale.setScalar(stationScale[i]);
      if (marks[i] && marks[i].material) {
        markOp[i] = lerp(markOp[i], on ? 0.42 : 0.12, 0.08);
        marks[i].material.opacity = markOp[i];
      }
    });

    const pressAmt = stage === 3 ? 0.5 + 0.5 * Math.sin(now / 420) : 0;
    const press = liveMode && liveKey !== "stamp" ? 0 : pressAmt * (stage === 3 ? 1 : 0);
    stamp.userData.head.position.y = lerp(stamp.userData.head.position.y, 0.28 - press * 0.16, 0.12);
    stamp.userData.handle.position.y = lerp(stamp.userData.handle.position.y, 0.62 - press * 0.16, 0.12);
    stamp.userData.pad.position.y = lerp(stamp.userData.pad.position.y, 0.14 - press * 0.16, 0.12);

    const sigOn = stage === 1;
    fee.rotation.z = lerp(fee.rotation.z, sigOn ? Math.sin(now / 280) * 0.08 : 0, 0.12);
    domain.rotation.z = lerp(domain.rotation.z, sigOn ? Math.sin(now / 240 + 1) * 0.08 : 0, 0.12);
    mail.rotation.z = lerp(mail.rotation.z, sigOn ? Math.sin(now / 300 + 2) * 0.08 : 0, 0.12);

    if (stage !== lastStage) {
      lastStage = stage;
      ["offer", "signals", "careers", "ruling"].forEach(function (k, i) {
        if (hud[k]) hud[k].classList.toggle("is-on", i === stage);
      });
      host.setAttribute("data-stage", String(stage));
    }
    applyMeters(stage, false);
    renderer.render(scene, camera);
  }

  function applyMeters(stage, instant) {
    const t = [
      stage >= 0 ? 0.88 : 0.16,
      stage >= 1 ? (stage >= 2 ? 0.84 : 0.52) : 0.16,
      stage >= 3 ? 0.96 : stage >= 2 ? 0.28 : 0.16,
    ];
    metersNow.forEach(function (v, i) {
      metersNow[i] = instant ? t[i] : lerp(v, t[i], 0.085);
    });
    document.querySelectorAll("[data-meter]").forEach(function (el) {
      var i = Number(el.getAttribute("data-meter"));
      if (i >= 0 && i < metersNow.length) el.style.transform = "scaleX(" + metersNow[i].toFixed(3) + ")";
    });
  }

  requestAnimationFrame(tick);

  window.CredaPass = {
    mount: function (el, mode) {
      const isLive = mode === "live";
      const nextParentId = el ? el.id || "anon" : "";
      const parentChanged = !!(el && host.parentNode !== el);
      const modeChanged = liveMode !== isLive;
      // #region agent log
      dbgLog("H3", "iso-loop.js:mount", "mount called", {
        mode,
        parentChanged,
        modeChanged,
        nextParentId,
        prevParentId: mountParentId,
      });
      // #endregion
      if (parentChanged && el) el.appendChild(host);
      liveMode = isLive;
      if (!isLive) liveKey = "intake";
      host.classList.add("iso-live");
      host.classList.toggle("iso-live-hud", isLive);
      host.classList.remove("is-hud-ready");
      renderer.setClearColor(isLive ? 0xf3f1ec : 0xffffff, 1);
      if (parentChanged || modeChanged || !mountParentId) {
        cameraFitted = false;
        lastResizeW = -1;
        lastResizeH = -1;
      }
      mountParentId = nextParentId;
      setRendering(true, parentChanged || modeChanged || !cameraFitted);
    },
    sync: function () {
      if (rendering) requestResize();
    },
    setMode: function (mode) {
      liveMode = mode === "live";
      if (!liveMode) liveKey = "intake";
      host.classList.toggle("iso-live-hud", liveMode);
    },
    setStage: function (key) {
      if (!key || LIVE_STAGE[key] == null) return;
      liveMode = true;
      liveKey = key;
    },
  };

  window.CredaPass.mount(document.getElementById("iso-home"), "idle");
}

start();
