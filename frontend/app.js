(function () {
  "use strict";

  var API_URL = "__CREDA_API_URL__";
  var POLL_MS = 1500;
  var POLL_MAX_MS = 120000;
  var STAGES = ["Intake", "Evidence", "Verdict", "Judgment", "Follow-up"];

  var session = { caseId: null, token: null };
  var pollTimer = null;
  var elapsedTimer = null;
  var pollStartedAt = 0;
  var lastData = null;
  var pendingAttachments = [];
  var parsedLinks = [];
  var MAX_ATTACHMENTS = 3;
  var lastLiveExhibitCount = 0;
  var lastStreamBody = "";
  var lastActiveStage = -1;
  var lastView = "intake";
  var pendingFollowupQuestion = "";
  var followupPollMode = false;
  var optimisticTurns = [];
  var conversationPending = false;
  var followupBaseline = null;
  var caseHadAttachment = false;

  var CredaStageMachine = {
    current: null,
    scenes: {
      intake: { id: "scene-intake", label: "Opening your case file…" },
      evidence: { id: "scene-evidence", label: "Pulling scam signals…" },
      ocr: { id: "scene-ocr", label: "Reading your screenshot…" },
      official_checks: { id: "scene-evidence", label: "Checking official careers listing…" },
      qwen_weigh: { id: "scene-qwen", label: "Qwen weighing evidence…" },
      stamp: { id: "scene-stamp", label: "Stamping your ruling…" }
    },
    sceneIds: ["scene-intake", "scene-evidence", "scene-ocr", "scene-qwen", "scene-stamp"],
    forceScene: function (key, data) {
      var meta = this.scenes[key];
      if (!meta) return;
      if (this.current === key) return;
      this.current = key;
      this.sceneIds.forEach(function (id) {
        var el = document.getElementById(id);
        if (el) el.classList.toggle("is-off", id !== meta.id);
      });
      var title = $("wait-title");
      var sub = $("wait-subtitle");
      if (title) title.textContent = meta.label;
      if (sub) sub.textContent = pipelineWaitCopy(data || {}) || meta.label;
      updatePrestreamRail(key);
      if (!CredaMotion.ok() || CredaMotion.reduced) return;
      if (meta.id) {
        var active = document.getElementById(meta.id);
        if (active) gsap.fromTo(active, { opacity: 0.35, y: 8 }, { opacity: 1, y: 0, duration: 0.42, ease: "power2.out" });
      }
      if (key === "intake") {
        gsap.fromTo("#stage-sheet", { y: 12, opacity: 0 }, { y: 0, opacity: 1, duration: 0.4, ease: "power2.out" });
        gsap.fromTo("#stage-folder-tab", { scale: 1 }, { scale: 1.08, duration: 0.25, yoyo: true, repeat: 1, transformOrigin: "50% 100%" });
      }
      if (key === "evidence" || key === "official_checks") {
        gsap.fromTo("#scene-evidence circle", { scale: 0.9 }, { scale: 1, duration: 0.35, ease: "back.out(2)", transformOrigin: "50% 50%" });
      }
      if (key === "ocr") {
        gsap.fromTo(".scan-line", { y1: 28, y2: 28 }, { y1: 72, y2: 72, duration: 1.2, repeat: 2, ease: "sine.inOut" });
      }
      if (key === "qwen_weigh") {
        gsap.fromTo("#scene-qwen circle", { scale: 0.88, opacity: 0.5 }, { scale: 1, opacity: 1, duration: 0.55, ease: "back.out(1.8)", transformOrigin: "50% 50%" });
      }
      if (key === "stamp") {
        gsap.fromTo("#stage-stamp-press", { scale: 0.92, y: -4 }, {
          scale: 1.02, y: 0, duration: 0.2, ease: "power2.out",
          onComplete: function () {
            gsap.to("#stage-stamp-press", { scale: 1, rotation: 1.5, duration: 0.2, ease: "power1.inOut" });
          }
        });
      }
    },
    reset: function () {
      this.current = null;
    }
  };

  var WaitStoryboard = {
    MIN_MS: 700,
    running: false,
    sequence: [],
    stepIndex: 0,
    stepTimer: null,
    readyData: null,
    dwellComplete: false,
    lastPollData: null,
    start: function () {
      this.running = true;
      this.readyData = null;
      this.dwellComplete = false;
      this.lastPollData = null;
      this.sequence = ["intake", "evidence"];
      if (caseHadAttachment) this.sequence.push("ocr");
      this.sequence.push("official_checks", "qwen_weigh", "stamp");
      this.stepIndex = 0;
      this._playStep();
    },
    _playStep: function () {
      if (!this.running) return;
      var key = this.sequence[this.stepIndex];
      CredaStageMachine.forceScene(key, this.lastPollData || {});
      var self = this;
      clearTimeout(this.stepTimer);
      this.stepTimer = setTimeout(function () {
        if (!self.running) return;
        if (self.stepIndex < self.sequence.length - 1) {
          self.stepIndex += 1;
          self._playStep();
        } else {
          self.dwellComplete = true;
          self._tryFinish();
        }
      }, this.MIN_MS);
    },
    onPoll: function (data) {
      this.lastPollData = data;
    },
    markReady: function (data) {
      this.readyData = data;
      this._tryFinish();
    },
    _tryFinish: function () {
      if (!this.running || !this.readyData || !this.dwellComplete) return;
      this.running = false;
      clearTimeout(this.stepTimer);
      var data = this.readyData;
      this.readyData = null;
      stopPolling();
      followupPollMode = false;
      conversationPending = false;
      optimisticTurns = [];
      showView("result");
      renderResult(data);
    },
    isRunning: function () { return this.running; },
    reset: function () {
      this.running = false;
      this.readyData = null;
      this.dwellComplete = false;
      clearTimeout(this.stepTimer);
    }
  };

  var CredaShieldArt = {
    init: function () {
      CredaShieldArt.setFlowStep(0);
    },
    setFlowStep: function (step) {
      var items = document.querySelectorAll("#intake-steps li");
      if (!items.length) return;
      items.forEach(function (li, i) {
        li.classList.toggle("is-active", i === step);
      });
    }
  };

  var CredaMotion = {
    ok: function () { return typeof gsap !== "undefined"; },
    reduced: window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    signalTween: null,
    hintTimer: null,
    hintIndex: 0,
    HINTS: [
      "Paste the full email — who sent it, subject line, and every link.",
      "Paste a Telegram DM word for word, or open CredaShield on Telegram.",
      "Or write: “A friend forwarded me this Amazon offer on Telegram…”",
      "Only have a photo? Tap + or drop a screenshot of the message.",
      "Creda reads text and images — sender, employer, and links are inferred."
    ],
    init: function () {
      var host = document.getElementById("hint-cycle");
      if (host && !host.textContent) host.textContent = this.HINTS[0];
      if (!this.ok()) return;
      var self = this;
      gsap.matchMedia().add("(prefers-reduced-motion: reduce)", function () {
        self.reduced = true;
        if (self.signalTween) self.signalTween.pause();
        if (self.hintTimer) clearInterval(self.hintTimer);
      });
      this.pageLoad();
      this.startHintCycle();
      this.startSignalRack();
    },
    pageLoad: function () {
      if (!this.ok() || this.reduced) return;
      var ease = "cubic-bezier(.22,1,.36,1)";
      gsap.from(".topbar", { y: 12, autoAlpha: 0, duration: 0.4, ease: ease });
      gsap.from(".intake-motif", { scale: 0.92, autoAlpha: 0, duration: 0.35, delay: 0.05, ease: ease });
      gsap.from(".intake-kicker", { y: 8, autoAlpha: 0, duration: 0.35, delay: 0.08, ease: ease });
      gsap.from("#hero-title", { y: 14, autoAlpha: 0, duration: 0.4, delay: 0.1, ease: ease });
      gsap.from(".intake-lede", { y: 10, autoAlpha: 0, duration: 0.38, delay: 0.14, ease: ease });
      gsap.from(".composer-card", { y: 20, autoAlpha: 0, duration: 0.45, delay: 0.18, ease: ease });
      gsap.from(".telegram-row", { y: 8, autoAlpha: 0, duration: 0.35, delay: 0.28, ease: ease });
      gsap.from(".intake-explain", { y: 6, autoAlpha: 0, duration: 0.32, delay: 0.34, ease: ease });
    },
    startHintCycle: function () {
      var host = document.getElementById("hint-cycle");
      if (!host) return;
      var hints = this.HINTS;
      var show = function (text, animate) {
        if (!animate || !CredaMotion.ok() || CredaMotion.reduced) {
          host.textContent = text;
          return;
        }
        gsap.fromTo(host, { y: 5, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 0.35, ease: "power2.out" });
        host.textContent = text;
      };
      show(hints[0], false);
      if (this.reduced || hints.length < 2) return;
      var self = this;
      this.hintTimer = setInterval(function () {
        self.hintIndex = (self.hintIndex + 1) % hints.length;
        if (CredaMotion.ok() && !CredaMotion.reduced) {
          gsap.to(host, {
            autoAlpha: 0, y: -4, duration: 0.22, onComplete: function () {
              host.textContent = hints[self.hintIndex];
              gsap.to(host, { autoAlpha: 1, y: 0, duration: 0.32, ease: "power2.out" });
            }
          });
        } else {
          host.textContent = hints[self.hintIndex];
        }
      }, 4200);
    },
    setHint: function (text) {
      var host = document.getElementById("hint-cycle");
      if (!host) return;
      if (this.hintTimer) clearInterval(this.hintTimer);
      if (this.ok() && !this.reduced) {
        gsap.fromTo(host, { y: 4, autoAlpha: 0.4 }, { y: 0, autoAlpha: 1, duration: 0.3 });
      }
      host.textContent = text;
    },
    startSignalRack: function () {
      if (!this.ok() || this.reduced) return;
      var bars = document.querySelectorAll(".signal-rack i");
      if (!bars.length) return;
      this.signalTween = gsap.to(bars, {
        scaleY: 1.35, opacity: 1, duration: 0.45, stagger: { each: 0.06, from: "random" },
        repeat: -1, yoyo: true, ease: "sine.inOut", transformOrigin: "50% 100%"
      });
    },
    enterView: function (name) {
      if (!this.ok() || this.reduced || name === lastView) return;
      lastView = name;
      var el = name === "wait" ? "#view-wait" : name === "result" ? "#view-result" : "#view-intake";
      gsap.fromTo(el, { autoAlpha: 0, y: 12 }, { autoAlpha: 1, y: 0, duration: 0.45, ease: "power3.out" });
      if (name === "wait") {
        gsap.from(".prestream-rail .prestream-step", {
          y: 8, autoAlpha: 0, duration: 0.35, stagger: 0.06, ease: "power2.out", delay: 0.08
        });
        gsap.from(".stage-canvas", { scale: 0.98, autoAlpha: 0, duration: 0.5, ease: "back.out(1.4)" });
      }
    },
    pulseStage: function (idx) {
      if (!this.ok() || this.reduced) return;
      var stages = document.querySelectorAll(".stage-rail .stage");
      if (!stages[idx]) return;
      gsap.fromTo(stages[idx], { scale: 0.92 }, { scale: 1, duration: 0.35, ease: "back.out(2)" });
    },
    streamPulse: function () {
      if (!this.ok() || this.reduced) return;
      gsap.fromTo("#stream-body", { boxShadow: "inset 0 0 0 rgba(21,94,239,0)" }, {
        boxShadow: "inset 0 0 24px rgba(21,94,239,0.12)", duration: 0.25, yoyo: true, repeat: 1
      });
    },
    slipIn: function (nodes) {
      if (!this.ok() || this.reduced || !nodes || !nodes.length) return;
      gsap.from(nodes, {
        x: -16, autoAlpha: 0, duration: 0.42, stagger: 0.08, ease: "power3.out"
      });
    },
    resultReveal: function () {
      if (!this.ok() || this.reduced) return;
      var stamp = document.querySelector(".ruling-stamp-press");
      if (stamp) stamp.classList.add("is-pressed");
      var tl = gsap.timeline({ defaults: { ease: "power3.out" } });
      tl.from(".board-stamp", { y: 16, autoAlpha: 0, duration: 0.45 })
        .from(stamp, { scale: 2.2, rotation: -18, autoAlpha: 0, duration: 0.55, ease: "back.out(2.2)" }, "-=0.2")
        .from("#board-headline", { y: 10, autoAlpha: 0, duration: 0.35 }, "-=0.15")
        .from("#tactics-host .tactic-line", {
          y: 10, autoAlpha: 0, duration: 0.28, stagger: { each: 0.06, from: "start" }, ease: "power2.out"
        }, "-=0.12")
        .from("#exhibits-host .flip-card, #exhibits-host .exhibit-card", {
          y: 14, autoAlpha: 0, duration: 0.3, stagger: { each: 0.07, from: "start" }, ease: "power2.out"
        }, "-=0.1")
        .from("#orders-host .board-action", { x: -10, autoAlpha: 0, duration: 0.32, stagger: 0.06 }, "-=0.15");
      var urgent = document.querySelector(".board-action.urgent");
      if (urgent) {
        gsap.to(urgent, { scale: 1.02, duration: 0.2, yoyo: true, repeat: 1, ease: "power1.inOut", delay: 0.6 });
      }
    }
  };

  function formatStreamBranches(text) {
    if (!text) return "";
    var chunks = text.split(/\n+/).map(function (s) { return s.trim(); }).filter(Boolean);
    if (chunks.length <= 1) {
      chunks = text.match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [text];
      chunks = chunks.map(function (s) { return s.trim(); }).filter(Boolean);
    }
    if (!chunks.length) return "";
    return '<div class="agent-branch">' + chunks.map(function (line, i) {
      var active = i === chunks.length - 1 ? " active" : "";
      var shimmer = i === chunks.length - 1 ? " stream-line-shimmer" : "";
      return '<div class="branch-node"><span class="branch-dot' + active + '"></span><div class="branch-content' + shimmer + '">' + esc(line) + "</div></div>";
    }).join("") + "</div>";
  }

  function wireFlipCards(root) {
    (root || document).querySelectorAll(".flip-card").forEach(function (card) {
      if (card.dataset.wired) return;
      card.dataset.wired = "1";
      card.addEventListener("click", function (e) {
        if (e.target.closest("a")) return;
        card.classList.toggle("is-flipped");
      });
      card.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); card.classList.toggle("is-flipped"); }
      });
    });
  }

  function confBarHtml(conf) {
    if (conf == null || conf === "") return "";
    var n = typeof conf === "number" ? conf : parseFloat(String(conf).replace("%", ""));
    if (isNaN(n)) return '<span class="micro-metric">CONF ' + esc(String(conf)) + "</span>";
    var pct = n <= 1 ? Math.round(n * 100) : Math.round(n);
    pct = Math.max(0, Math.min(100, pct));
    return (
      '<div class="conf-bar" title="Confidence ' + pct + '%">' +
        '<span class="micro-metric">CONF ' + pct + "%</span>" +
        '<div class="conf-bar-track"><div class="conf-bar-fill" style="width:' + pct + '%"></div></div>' +
      "</div>"
    );
  }

  function esc(value) {
    if (value == null) return "";
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function $(id) { return document.getElementById(id); }

  var errorCountdowns = {};

  function toAppError(err) {
    if (!err) return { code: "UNKNOWN" };
    if (err.code && !err.status) return { code: err.code, message: err.message, ctx: err.ctx };
    if (!navigator.onLine) return { code: "OFFLINE" };
    var status = err.status;
    var msg = err.message || "";
    if (status === 401) return { code: "SESSION_EXPIRED" };
    if (status === 403) return { code: "FORBIDDEN" };
    if (status === 404) return { code: "NOT_FOUND" };
    if (status === 413) return { code: "FILE_TOO_LARGE", message: msg };
    if (status === 409) return { code: "CONFLICT" };
    if (status === 400 || status === 422) return { code: "VALIDATION", message: msg };
    if (status === 429) {
      var sec = 10;
      return { code: "RATE_LIMITED", ctx: { seconds: sec } };
    }
    if (status === 502 || status === 504) return { code: "TIMEOUT" };
    if (status === 503) return { code: "MAINTENANCE" };
    if (status >= 500) return { code: "SERVER_ERROR" };
    if (/could not reach/i.test(msg)) return { code: "OFFLINE" };
    if (/could not upload|storage bucket|cors/i.test(msg)) return { code: "UPLOAD_BLOCKED", message: msg };
    if (/paste the recruiter|add a message|attach a screenshot/i.test(msg)) return { code: "VALIDATION", message: msg };
    if (/jpeg|png|webp|pdf|unsupported/i.test(msg)) return { code: "UNSUPPORTED_FILE", message: msg };
    if (/too large|too big|8 mb/i.test(msg)) return { code: "FILE_TOO_LARGE", message: msg };
    if (/type a follow-up|type a question/i.test(msg)) return { code: "VALIDATION", message: msg };
    if (/no active case/i.test(msg)) return { code: "NOT_FOUND", message: msg };
    if (/paste the scam/i.test(msg)) return { code: "VALIDATION", message: msg };
    if (/timed out waiting/i.test(msg)) return { code: "POLL_TIMEOUT" };
    return { code: "UNKNOWN", message: msg };
  }

  function errorCopy(spec) {
    var seconds = (spec.ctx && spec.ctx.seconds) || 10;
    var msg = spec.message || "";
    var table = {
      OFFLINE: {
        title: "You're offline",
        body: "Your message stays in the box.",
        primary: { action: "retry", label: "Try again" }
      },
      TIMEOUT: {
        title: "Creda is slow right now",
        body: "The check may still finish on its own.",
        primary: { action: "retry_poll", label: "Try again" },
        secondary: { action: "back_intake", label: "Go back" }
      },
      POLL_TIMEOUT: {
        title: "No final ruling yet",
        body: "Partial exhibits are shown if Creda found any.",
        primary: { action: "dismiss", label: "Got it" },
        secondary: { action: "back_intake", label: "Check another" }
      },
      VALIDATION: {
        title: "Can't send yet",
        body: msg || "Add the recruiter message or attach a screenshot.",
        primary: { action: "focus_field", label: "Fix it" }
      },
      SESSION_EXPIRED: {
        title: "This case expired",
        body: "Start a new check. Your pasted text is still here.",
        primary: { action: "clear_session", label: "Start new check" }
      },
      FORBIDDEN: {
        title: "Can't open this case",
        body: "You may not have access to it.",
        primary: { action: "back_intake", label: "Check another offer" }
      },
      NOT_FOUND: {
        title: "Case not found",
        body: "It may have been cleared.",
        primary: { action: "back_intake", label: "Start new check" }
      },
      CONFLICT: {
        title: "Case changed while you waited",
        body: "Reload to see the latest version.",
        primary: { action: "reload", label: "Reload" }
      },
      FILE_TOO_LARGE: {
        title: "File too large",
        body: msg || "Max 8 MB per file.",
        primary: { action: "focus_field", label: "Choose another file" }
      },
      UNSUPPORTED_FILE: {
        title: "Unsupported file type",
        body: msg || "Use JPG, PNG, WebP, or PDF.",
        primary: { action: "focus_field", label: "Choose another file" }
      },
      UPLOAD_BLOCKED: {
        title: "Upload blocked",
        body: msg || "Paste the email text instead, or try again in a moment.",
        primary: { action: "focus_field", label: "Paste text instead" },
        secondary: { action: "retry", label: "Try upload again" }
      },
      RATE_LIMITED: {
        title: "Too many requests",
        body: "Wait " + seconds + "s, then try again.",
        primary: { action: "retry_countdown", label: "Try again in " + seconds + "s", seconds: seconds }
      },
      MAINTENANCE: {
        title: "Creda is down briefly",
        body: "Try again in a few minutes.",
        primary: { action: "retry", label: "Try again" }
      },
      SERVER_ERROR: {
        title: "Couldn't reach Creda",
        body: "Your message is still here.",
        primary: { action: "retry", label: "Try again" },
        secondary: { action: "copy_details", label: "Copy details" },
        details: true
      },
      UNKNOWN: {
        title: "Something went wrong",
        body: msg || "Your message is still here.",
        primary: { action: "retry", label: "Try again" },
        secondary: { action: "copy_details", label: "Copy details" },
        details: true
      }
    };
    return table[spec.code] || table.UNKNOWN;
  }

  function errorIconSvg() {
    return '<svg class="error-card__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>';
  }

  function buildErrorCardHtml(spec, copy, detailsText) {
    var html = '<div class="error-card"><div class="error-card__head">' + errorIconSvg() +
      '<p class="error-card__title">' + esc(copy.title) + "</p></div>";
    if (copy.body) html += '<p class="error-card__body">' + esc(copy.body) + "</p>";
    html += '<div class="error-card__actions">';
    if (copy.primary) {
      html += '<button type="button" class="error-card__btn primary" data-error-action="' + esc(copy.primary.action) + '"';
      if (copy.primary.seconds) html += ' data-countdown="' + esc(String(copy.primary.seconds)) + '" disabled';
      html += ">" + esc(copy.primary.label) + "</button>";
    }
    if (copy.secondary) {
      html += '<button type="button" class="error-card__btn" data-error-action="' + esc(copy.secondary.action) + '">' +
        esc(copy.secondary.label) + "</button>";
    }
    html += "</div>";
    if (copy.details && detailsText) {
      html += '<details class="error-card__details"><summary>Technical details</summary><pre style="margin:.35rem 0 0;white-space:pre-wrap;font-family:var(--mono);font-size:.68rem">' +
        esc(detailsText) + "</pre></details>";
    }
    html += "</div>";
    return html;
  }

  function runErrorAction(action, ctx, hostId) {
    if (action === "dismiss") {
      if (hostId === "stream-body") {
        $("stream-body").innerHTML = '<span class="shimmer">Waiting for Creda…</span>';
        return;
      }
      showError(hostId, "");
      return;
    }
    if (action === "retry" && ctx.onRetry) { showError(hostId, ""); ctx.onRetry(); return; }
    if (action === "retry_poll") {
      showError(hostId, "");
      pollOnce().catch(function (e) { renderStreamError(e, ctx); });
      return;
    }
    if (action === "retry_countdown") return;
    if (action === "clear_session") {
      stopPolling();
      session.caseId = null;
      session.token = null;
      pendingFollowupQuestion = "";
      saveSession();
      showError(hostId, "");
      showView("intake");
      return;
    }
    if (action === "back_intake") { showError(hostId, ""); resetToIntake(); return; }
    if (action === "reload") { location.reload(); return; }
    if (action === "focus_field" && ctx.focusId) { showError(hostId, ""); var f = $(ctx.focusId); if (f) f.focus(); return; }
    if (action === "copy_details" && ctx.lastErr) {
      var text = (ctx.lastErr.message || "") + (ctx.lastErr.status ? " (" + ctx.lastErr.status + ")" : "");
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text);
      return;
    }
  }

  function wireErrorCard(el, spec, ctx) {
    el.querySelectorAll("[data-error-action]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        runErrorAction(btn.getAttribute("data-error-action"), ctx, el.id);
      });
    });
    var countdownBtn = el.querySelector("[data-countdown]");
    if (countdownBtn) {
      var sec = parseInt(countdownBtn.getAttribute("data-countdown"), 10) || 10;
      var key = el.id;
      if (errorCountdowns[key]) clearInterval(errorCountdowns[key]);
      errorCountdowns[key] = setInterval(function () {
        sec -= 1;
        if (sec <= 0) {
          clearInterval(errorCountdowns[key]);
          countdownBtn.disabled = false;
          countdownBtn.textContent = "Try again";
          return;
        }
        countdownBtn.textContent = "Try again in " + sec + "s";
      }, 1000);
    }
    var primary = el.querySelector(".error-card__btn");
    if (primary && !primary.disabled) primary.focus();
  }

  function showError(id, input, ctx) {
    var el = $(id);
    if (!el) return;
    ctx = ctx || {};
    if (!input) {
      el.classList.add("hidden");
      el.innerHTML = "";
      if (errorCountdowns[id]) { clearInterval(errorCountdowns[id]); delete errorCountdowns[id]; }
      return;
    }
    var spec = typeof input === "string" ? toAppError({ message: input }) : toAppError(input);
    ctx.lastErr = typeof input === "object" ? input : { message: input };
    var copy = errorCopy(spec);
    var details = ctx.lastErr.status ? ("Status " + ctx.lastErr.status + ". " + (ctx.lastErr.message || "")) : (ctx.lastErr.message || "");
    el.innerHTML = buildErrorCardHtml(spec, copy, details);
    el.classList.remove("hidden");
    wireErrorCard(el, spec, Object.assign({ focusId: ctx.focusId }, ctx));
  }

  function renderStreamError(err, ctx) {
    ctx = Object.assign({
      onRetry: function () {
        $("stream-body").innerHTML = '<span class="shimmer">Reconnecting…</span>';
        pollOnce().catch(function (e) { renderStreamError(e, ctx); });
      },
      lastErr: err
    }, ctx || {});
    var spec = toAppError(err);
    var copy = errorCopy(spec);
    var details = err && err.status ? ("Status " + err.status + ". " + (err.message || "")) : (err && err.message) || "";
    $("stream-body").innerHTML =
      '<div class="stream-error" role="alert">' + buildErrorCardHtml(spec, copy, details) + "</div>";
    wireErrorCard($("stream-body"), spec, ctx);
  }

  function normalize(v) { return String(v || "").toLowerCase(); }

  function verdictTone(v) {
    v = normalize(v);
    if (v === "high_risk") return "risk";
    if (v === "no_conflict_found") return "safe";
    return "warn";
  }

  function verdictPlain(v) {
    v = normalize(v);
    if (v === "high_risk") return "High risk";
    if (v === "no_conflict_found") return "No conflict found";
    if (v === "unverified") return "Unverified";
    if (v === "pending") return "Review in progress";
    return "Result";
  }

  function stampLabel(v) {
    v = normalize(v);
    if (v === "high_risk") return "HIGH RISK";
    if (v === "no_conflict_found") return "NO CONFLICT";
    if (v === "unverified") return "NOT ENOUGH PROOF";
    if (v === "pending") return "PENDING";
    return "REVIEW";
  }

  function rulingStampPressHtml(label, tone) {
    tone = tone || "neutral";
    var lines = label.split(" ");
    var tspan = lines.length > 1
      ? '<tspan x="84" y="46">' + esc(lines[0]) + '</tspan><tspan x="84" y="62">' + esc(lines.slice(1).join(" ")) + "</tspan>"
      : '<tspan x="84" y="54">' + esc(label) + "</tspan>";
    return (
      '<div class="ruling-stamp-press" aria-hidden="true">' +
        '<svg viewBox="0 0 168 112" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="' + esc(label) + ' stamp">' +
          '<rect class="stamp-frame stamp-frame-' + esc(tone) + '" x="8" y="12" width="152" height="88" rx="8" fill="none" stroke-width="3" opacity=".55"/>' +
          '<rect class="stamp-fill stamp-fill-' + esc(tone) + '" x="14" y="18" width="140" height="76" rx="6"/>' +
          '<text class="stamp-text stamp-text-' + esc(tone) + '" text-anchor="middle" font-family="JetBrains Mono, ui-monospace, monospace" font-size="13" font-weight="700" letter-spacing=".12em">' + tspan + "</text>" +
        "</svg>" +
      "</div>"
    );
  }

  function stampBoardHtml(data) {
    var v = normalize(data.verdict);
    var tone = verdictTone(v);
    var stampWord = stampLabel(v);
    return '<div class="board-stamp ruling-stamp-wrap ' + esc(tone) + '">' + rulingStampPressHtml(stampWord, tone) + "</div>";
  }

  function updatePrestreamRail(sceneKey) {
    var sceneToStep = { intake: "file", evidence: "signals", ocr: "signals", official_checks: "check", qwen_weigh: "qwen", stamp: "qwen" };
    var order = ["file", "signals", "check", "qwen"];
    var activeStep = sceneToStep[sceneKey] || "file";
    var activeIdx = order.indexOf(activeStep);
    var rail = $("prestream-rail");
    if (!rail) return;
    rail.querySelectorAll(".prestream-step").forEach(function (el) {
      var step = el.getAttribute("data-step");
      var idx = order.indexOf(step);
      el.classList.toggle("is-done", idx >= 0 && idx < activeIdx);
      el.classList.toggle("is-active", idx === activeIdx);
      el.classList.toggle("is-pending", idx > activeIdx);
    });
    if (activeIdx !== lastActiveStage) {
      lastActiveStage = activeIdx;
      if (CredaMotion.ok() && !CredaMotion.reduced) {
        var stepEl = rail.querySelector('.prestream-step[data-step="' + activeStep + '"]');
        if (stepEl) gsap.fromTo(stepEl, { scale: 0.92 }, { scale: 1, duration: 0.35, ease: "back.out(2)" });
      }
    }
  }

  function followupReplyComplete(data) {
    if (!conversationPending) return true;
    var agent = normalize(data.agentStatus);
    if (agent === "running" || agent === "streaming") return false;
    if (data.agentReply || data.followupReply) return true;
    var turns = data.conversationTurns || [];
    var lastUser = -1;
    for (var i = turns.length - 1; i >= 0; i--) {
      if (normalize(turns[i].role) === "user") { lastUser = i; break; }
    }
    if (lastUser >= 0) {
      for (var j = lastUser + 1; j < turns.length; j++) {
        var role = normalize(turns[j].role);
        if (role !== "user" && (turns[j].text || "").trim()) return true;
      }
    }
    if (followupBaseline && (agent === "ready" || normalize(data.status) === "completed")) {
      if ((data.headline || "") !== (followupBaseline.headline || "")) return true;
      var explain = data.explanation || data.agentReasoning || "";
      if (explain && explain !== (followupBaseline.explanation || "")) return true;
      if ((data.evidence || []).length !== followupBaseline.evidenceLen) return true;
      if (turns.length > followupBaseline.turnCount) return true;
    }
    return false;
  }

  function ensureFollowupAssistantTurn(data) {
    var turns = (data.conversationTurns || []).slice();
    var lastUser = -1;
    for (var i = turns.length - 1; i >= 0; i--) {
      if (normalize(turns[i].role) === "user") { lastUser = i; break; }
    }
    if (lastUser < 0) return turns;
    for (var j = lastUser + 1; j < turns.length; j++) {
      if (normalize(turns[j].role) !== "user" && (turns[j].text || "").trim()) return turns;
    }
    var reply = (data.agentReply || data.followupReply || data.headline || data.explanation || data.agentReasoning || "").trim();
    if (reply) turns.push({ role: "assistant", text: reply });
    return turns;
  }

  function outcomeTone(outcome) {
    var o = normalize(outcome);
    if (o === "conflict" || o === "high_risk" || o === "fail" || o === "risk") return "risk";
    if (o === "confirmed" || o === "pass" || o === "safe") return "safe";
    return "warn";
  }

  function outcomeStamp(outcome) {
    var o = normalize(outcome);
    if (o === "conflict" || o === "high_risk" || o === "fail" || o === "risk") return "RISK";
    if (o === "confirmed" || o === "pass" || o === "safe") return "SAFE";
    if (o === "unverified" || o === "inconclusive" || o === "warn") return "WARN";
    return String(outcome || "CHECK").toUpperCase().slice(0, 8);
  }

  function consequenceFor(v, headline) {
    v = normalize(v);
    if (headline) return headline;
    if (v === "high_risk") return "Do not pay or share documents until this is cleared through official channels.";
    if (v === "no_conflict_found") return "Nothing in the evidence conflicted with official sources — that is not proof the offer is authentic.";
    if (v === "unverified") return "Creda could not gather enough official exhibits. Treat this as unresolved.";
    return "Review the exhibits before you reply.";
  }

  function saveSession() {
    if (session.caseId && session.token) {
      try { sessionStorage.setItem("creda_case", JSON.stringify({ caseId: session.caseId, token: session.token })); }
      catch (e) {}
    } else {
      try { sessionStorage.removeItem("creda_case"); } catch (e) {}
    }
  }

  function bootstrapSessionFromUrl() {
    try {
      var params = new URLSearchParams(window.location.search);
      var caseId = params.get("case");
      var token = params.get("token");
      if (!caseId || !token) return;
      session.caseId = caseId;
      session.token = token;
      saveSession();
      if (window.history && window.history.replaceState) {
        params.delete("case");
        params.delete("token");
        var qs = params.toString();
        window.history.replaceState({}, "", window.location.pathname + (qs ? "?" + qs : ""));
      }
    } catch (e) {}
  }

  function restoreSession() {
    try {
      var saved = sessionStorage.getItem("creda_case");
      if (!saved) return;
      var parsed = JSON.parse(saved);
      if (parsed.caseId && parsed.token) {
        session.caseId = parsed.caseId;
        session.token = parsed.token;
      }
    } catch (e) {}
  }

  function showView(name) {
    var views = { intake: $("view-intake"), wait: $("view-wait"), result: $("view-result") };
    Object.keys(views).forEach(function (key) {
      var on = name === key;
      views[key].classList.toggle("hidden", !on);
      views[key].setAttribute("aria-hidden", on ? "false" : "true");
    });
    document.body.classList.remove("view-bleed");
    document.body.classList.toggle("view-wide", name === "wait" || name === "result");
    if (name === "intake") CredaShieldArt.setFlowStep(0);
    else if (name === "wait") CredaShieldArt.setFlowStep(1);
    else if (name === "result") CredaShieldArt.setFlowStep(2);
    CredaMotion.enterView(name);
  }

  function formatElapsed(ms) {
    var sec = Math.floor(ms / 1000);
    return Math.floor(sec / 60) + ":" + String(sec % 60).padStart(2, "0");
  }

  function startElapsed() {
    pollStartedAt = Date.now();
    if (elapsedTimer) clearInterval(elapsedTimer);
    elapsedTimer = setInterval(function () {
      $("elapsed-timer").textContent = formatElapsed(Date.now() - pollStartedAt);
    }, 250);
  }

  function stopElapsed() {
    if (elapsedTimer) { clearInterval(elapsedTimer); elapsedTimer = null; }
  }

  async function apiFetch(path, options) {
    var opts = options || {};
    var headers = Object.assign({}, opts.headers || {});
    var url = API_URL.replace(/\/$/, "") + path;
    var resp;
    try {
      resp = await fetch(url, Object.assign({}, opts, { headers: headers }));
    } catch (e) {
      var netErr = new Error("Could not reach the Creda API. Check your connection and try again.");
      netErr.cause = e;
      throw netErr;
    }
    var data = null;
    try { data = await resp.json(); } catch (e) { data = null; }
    if (!resp.ok) {
      var msg = (data && (data.nextAction || data.message || data.error)) || ("Request failed (" + resp.status + ")");
      var err = new Error(msg);
      err.status = resp.status;
      err.data = data;
      throw err;
    }
    return data;
  }

  async function checkHealth() {
    try {
      var data = await apiFetch("/health");
      if ($("health-dot")) $("health-dot").className = "dot ok";
      if ($("health-label")) $("health-label").textContent = "Ready";
      var dot = $("footer-health-dot");
      if (dot) dot.className = "footer-health-dot ok";
      return data;
    } catch (e) {
      $("health-dot").className = "dot err";
      $("health-label").textContent = "API unreachable";
      var dot = $("footer-health-dot");
      if (dot) dot.className = "footer-health-dot err";
      return null;
    }
  }

  function caseToken(data) {
    return (data && (data.accessToken || data.token)) || session.token;
  }

  function allowedFile(file) {
    var type = file.type || "";
    return type === "image/jpeg" || type === "image/png" || type === "image/webp" || type === "application/pdf";
  }

  function addAttachmentFiles(fileList) {
    if (!fileList || !fileList.length) return;
    for (var i = 0; i < fileList.length; i++) {
      if (pendingAttachments.length >= MAX_ATTACHMENTS) break;
      var file = fileList[i];
      if (!allowedFile(file)) {
        showError("intake-error", "Use JPG, PNG, WebP, or PDF.", { focusId: "offer-text", onRetry: function () { $("file-input").click(); } });
        continue;
      }
      if (file.size > 8 * 1024 * 1024) {
        showError("intake-error", file.name + " is too large. Max 8 MB.", { focusId: "offer-text", onRetry: function () { $("file-input").click(); } });
        continue;
      }
      var preview = file.type.indexOf("image/") === 0 ? URL.createObjectURL(file) : null;
      pendingAttachments.push({ id: "att_" + Date.now() + "_" + i, file: file, preview: preview });
    }
    showError("intake-error", "");
    renderAttachmentChips();
  }

  function removeAttachment(id) {
    pendingAttachments = pendingAttachments.filter(function (item) {
      if (item.id === id && item.preview) URL.revokeObjectURL(item.preview);
      return item.id !== id;
    });
    renderAttachmentChips();
  }

  function renderAttachmentChips() {
    var row = $("attachment-row");
    if (!row) return;
    if (!pendingAttachments.length) {
      row.innerHTML = "";
      row.classList.add("hidden");
      syncSendButton();
      return;
    }
    row.classList.remove("hidden");
    row.innerHTML = pendingAttachments.map(function (item) {
      var thumb = item.preview
        ? '<img src="' + item.preview + '" alt="" />'
        : "PDF";
      return '<span class="attach-chip" data-id="' + esc(item.id) + '">' +
        '<span class="attach-thumb">' + thumb + "</span>" +
        '<span class="attach-name">' + esc(item.file.name) + "</span>" +
        '<button type="button" class="attach-remove" data-remove="' + esc(item.id) + '" aria-label="Remove ' + esc(item.file.name) + '">×</button>' +
        "</span>";
    }).join("");
    row.querySelectorAll("[data-remove]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        removeAttachment(btn.getAttribute("data-remove"));
      });
    });
    syncSendButton();
  }

  function syncSendButton() {
    var btn = $("btn-check");
    if (!btn) return;
    var textLen = ($("offer-text").value || "").trim().length;
    var hasFiles = pendingAttachments.length > 0;
    var hasLinks = parsedLinks.length > 0;
    var ready = textLen >= 12 || hasFiles || hasLinks;
    btn.classList.toggle("is-active", ready);
    btn.disabled = !ready;
  }

  function autoResizeComposer() {
    var ta = $("offer-text");
    if (!ta) return;
    ta.style.height = "0";
    var next = Math.min(ta.scrollHeight, 280);
    ta.style.height = next + "px";
    ta.style.overflowY = ta.scrollHeight > 280 ? "auto" : "hidden";
    syncSendButton();
  }

  function syncParsedLinksFromText() {
    parsedLinks = extractUrls(($("offer-text").value || "")).slice(0, 5);
    renderParsedLinks();
    syncSendButton();
  }

  function renderParsedLinks() {
    var host = $("parsed-links");
    if (!host) return;
    if (!parsedLinks.length) {
      host.innerHTML = "";
      host.classList.add("hidden");
      return;
    }
    host.classList.remove("hidden");
    host.innerHTML = parsedLinks.map(function (url, idx) {
      var short = url.replace(/^https?:\/\//i, "");
      if (short.length > 42) short = short.slice(0, 39) + "…";
      return '<span class="link-chip">' +
        '<span class="link-chip-url" title="' + esc(url) + '">' + esc(short) + "</span>" +
        '<button type="button" class="link-chip-remove" data-link-idx="' + idx + '" aria-label="Remove link">×</button>' +
        "</span>";
    }).join("");
    host.querySelectorAll("[data-link-idx]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        removeParsedLink(parseInt(btn.getAttribute("data-link-idx"), 10));
      });
    });
  }

  function removeParsedLink(idx) {
    var url = parsedLinks[idx];
    if (!url) return;
    var ta = $("offer-text");
    ta.value = (ta.value || "").replace(url, "").replace(/\s{2,}/g, " ").trim();
    syncParsedLinksFromText();
    autoResizeComposer();
  }

  function clearComposer() {
    $("offer-text").value = "";
    parsedLinks = [];
    renderParsedLinks();
    pendingAttachments.forEach(function (item) {
      if (item.preview) URL.revokeObjectURL(item.preview);
    });
    pendingAttachments = [];
    renderAttachmentChips();
    $("file-input").value = "";
    showError("intake-error", "");
    autoResizeComposer();
  }

  async function uploadPendingAttachments() {
    var uploaded = [];
    for (var i = 0; i < pendingAttachments.length; i++) {
      var item = pendingAttachments[i];
      var file = item.file;
      var meta = await apiFetch("/upload-url", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contentType: file.type || "image/png",
          fileName: file.name || "attachment"
        })
      });
      var uploadUrl = meta.uploadUrl || meta.url;
      var key = meta.key || meta.objectKey || meta.fileKey || null;
      if (!uploadUrl || !key) throw new Error("Upload URL missing from API.");
      var put;
      try {
        put = await fetch(uploadUrl, {
          method: "PUT",
          headers: { "Content-Type": file.type || "image/png" },
          body: file
        });
      } catch (uploadErr) {
        var uploadMsg = (uploadErr && uploadErr.message) || "upload failed";
        if (/failed to fetch|networkerror/i.test(uploadMsg)) {
          throw new Error("Could not upload " + file.name + ". The storage bucket may be blocking browser uploads (CORS). Try pasting the text instead.");
        }
        throw uploadErr;
      }
      if (!put.ok) throw new Error("Upload failed for " + file.name + " (" + put.status + ").");
      uploaded.push({
        name: file.name,
        contentType: file.type || "image/jpeg",
        s3Key: key,
        sizeBytes: file.size || 0
      });
    }
    return uploaded;
  }

  function buildPayload(uploadedAttachments) {
    var offerText = $("offer-text").value.trim();
    if (!offerText && (!uploadedAttachments || !uploadedAttachments.length)) {
      throw new Error("Add a message or attach a screenshot.");
    }
    if (offerText && offerText.length < 12 && (!uploadedAttachments || !uploadedAttachments.length)) {
      throw new Error("Paste the complete email or message, including sender and any links.");
    }
    var payload = {
      offerText: offerText || "[Multimodal intake]",
      locale: "en-IN",
      sourceChannel: "web"
    };
    if (uploadedAttachments && uploadedAttachments.length) {
      payload.attachments = uploadedAttachments;
      if (uploadedAttachments[0] && uploadedAttachments[0].s3Key) {
        payload.screenshotKey = uploadedAttachments[0].s3Key;
      }
    }
    var links = parsedLinks.concat(collectLinkInputs()).concat(extractUrls(offerText));
    links = links.filter(function (u, i) { return links.indexOf(u) === i; }).slice(0, 5);
    if (links.length) payload.links = links;
    return payload;
  }

  function tacticVectorSvg(key, title) {
    var hay = (key + " " + (title || "")).toLowerCase();
    if (/fee|deposit|payment|upi|paytm/.test(hay)) {
      return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><rect x="3" y="6" width="18" height="14" rx="2"/><path d="M7 10h4M7 14h2"/><line x1="16" y1="8" x2="20" y2="12"/><line x1="20" y1="8" x2="16" y2="12"/></svg>';
    }
    if (/telegram|whatsapp|signal|dm|channel/.test(hay)) {
      return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>';
    }
    if (/form|enroll|google/.test(hay)) {
      return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/></svg>';
    }
    if (/domain|mailbox|email|gmail|sender/.test(hay)) {
      return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><rect x="3" y="5" width="8" height="6" rx="1"/><rect x="13" y="13" width="8" height="6" rx="1"/><path d="M11 8h2M11 16h2"/></svg>';
    }
    if (/vacancy|careers|link|url/.test(hay)) {
      return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/><line x1="8" y1="16" x2="10" y2="14" stroke-dasharray="2 2"/></svg>';
    }
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><path d="M12 9v4"/><path d="M12 17h.01"/><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/></svg>';
  }

  function wireInputChannels() {
    document.querySelectorAll(".channel-chip").forEach(function (chip) {
      chip.addEventListener("click", function () {
        document.querySelectorAll(".channel-chip").forEach(function (c) { c.classList.remove("is-active"); });
        chip.classList.add("is-active");
        var hint = chip.getAttribute("data-hint") || "";
        var channel = chip.getAttribute("data-channel") || "";
        if (hint) CredaMotion.setHint(hint);
        $("offer-text").focus();
        if (channel === "attach") $("file-input").click();
        if (channel === "telegram") {
          window.open("https://t.me/CredashieldBot", "_blank", "noopener,noreferrer");
        }
      });
    });
  }

  function wireDropTarget(el, overlayId) {
    if (!el) return;
    ["dragenter", "dragover"].forEach(function (evt) {
      el.addEventListener(evt, function (e) {
        e.preventDefault();
        el.classList.add("is-dragging");
        if (overlayId && $(overlayId)) $(overlayId).classList.remove("hidden");
      });
    });
    el.addEventListener("dragleave", function (e) {
      if (!el.contains(e.relatedTarget)) {
        el.classList.remove("is-dragging");
        if (overlayId && $(overlayId)) $(overlayId).classList.add("hidden");
      }
    });
    el.addEventListener("drop", function (e) {
      e.preventDefault();
      el.classList.remove("is-dragging");
      if (overlayId && $(overlayId)) $(overlayId).classList.add("hidden");
      addAttachmentFiles(e.dataTransfer && e.dataTransfer.files);
    });
  }

  function wireComposer() {
    var shell = $("composer-shell");
    var input = $("file-input");
    var ta = $("offer-text");
    ta.addEventListener("input", function () {
      syncParsedLinksFromText();
      autoResizeComposer();
    });
    ta.addEventListener("paste", function () {
      setTimeout(function () {
        syncParsedLinksFromText();
        autoResizeComposer();
      }, 0);
    });
    ta.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submitCase();
    });
    shell.addEventListener("click", function (e) {
      if (e.target === shell || e.target.classList.contains("composer-toolbar")) ta.focus();
    });
    autoResizeComposer();
    syncParsedLinksFromText();
    $("btn-attach").addEventListener("click", function () { input.click(); });
    input.addEventListener("change", function () {
      addAttachmentFiles(input.files);
      input.value = "";
    });
    wireDropTarget(shell, "drop-overlay");
  }

  function stopPolling() {
    if (pollTimer) { clearTimeout(pollTimer); pollTimer = null; }
    stopElapsed();
  }

  function isWaiting(data) {
    var status = normalize(data.status);
    var verdict = normalize(data.verdict);
    var agent = normalize(data.agentStatus);
    if (status === "queued" || status === "running") return true;
    if (status === "completed" && (verdict === "pending" || !verdict)) return true;
    if (agent === "running" || agent === "streaming" || agent === "pending" || agent === "queued") return true;
    return false;
  }

  function isReady(data) {
    var status = normalize(data.status);
    var verdict = normalize(data.verdict);
    var agent = normalize(data.agentStatus);
    if (status === "failed" || status === "could_not_complete") return true;
    if (status === "completed" && agent === "ready" && verdict && verdict !== "pending") return true;
    if (agent === "ready" && verdict && verdict !== "pending") return true;
    if (status === "needs_evidence" && agent === "ready") return true;
    return false;
  }

  function stageState(data) {
    var status = normalize(data.status);
    var verdict = normalize(data.verdict);
    var agent = normalize(data.agentStatus);
    var states = { Intake: "pending", Evidence: "pending", Verdict: "pending", Judgment: "pending", "Follow-up": "pending" };
    var scene = CredaStageMachine.current || "intake";
    if (scene === "intake") states.Intake = "active";
    else states.Intake = "done";
    if (scene === "evidence" || scene === "ocr") states.Evidence = "active";
    else if (states.Intake === "done") states.Evidence = "done";
    if (scene === "stream") {
      states.Evidence = "done";
      states.Verdict = "active";
    } else if (states.Evidence === "done" && verdict && verdict !== "pending") {
      states.Verdict = "done";
    }
    if (scene === "stamp") {
      states.Evidence = "done";
      states.Verdict = "done";
      states.Judgment = "active";
    }
    if (agent === "ready" && verdict && verdict !== "pending") {
      states.Evidence = "done";
      states.Verdict = "done";
      states.Judgment = "done";
      states["Follow-up"] = (data.conversationTurns && data.conversationTurns.length) ? "done" : "active";
    }
    if (status === "could_not_complete") states.Judgment = "fail";
    return states;
  }

  function renderStageRail(data) {
    if (WaitStoryboard.isRunning()) return;
    var map = stageState(data || {});
    var activeIdx = -1;
    STAGES.forEach(function (name, i) {
      if ((map[name] || "") === "active") activeIdx = i;
    });
    $("stage-rail").innerHTML = STAGES.map(function (name) {
      return '<div class="stage ' + esc(map[name] || "pending") + '">' + esc(name) + "</div>";
    }).join("");
    if (activeIdx >= 0 && activeIdx !== lastActiveStage) {
      lastActiveStage = activeIdx;
      CredaMotion.pulseStage(activeIdx);
    }
  }

  function extractStream(data) {
    var stream = data.agentStreamText || "";
    if (!stream && data.agentReasoning) return data.agentReasoning;
    if (!stream) return "";
    try {
      var parsed = JSON.parse(stream);
      if (parsed.reasoning) return parsed.reasoning;
      if (parsed.explanation) return parsed.explanation;
      if (parsed.headline) return parsed.headline;
    } catch (e) {}
    var m = stream.match(/"reasoning"\s*:\s*"((?:\\.|[^"\\])*)/);
    if (m) return m[1].replace(/\\n/g, "\n").replace(/\\"/g, '"');
    return stream.slice(0, 800) + (stream.length > 800 ? "…" : "");
  }

  function pipelineWaitCopy(data) {
    var log = data.pipelineLog || [];
    var last = log.length ? String(log[log.length - 1]) : "";
    var agent = normalize(data.agentStatus);
    var verdict = normalize(data.verdict);
    var evidence = data.evidence || [];
    if (agent === "ready" && verdict && verdict !== "pending") return "Ruling ready — opening your result…";
    if (last) return last;
    if (data.agentProgress) return String(data.agentProgress);
    if (evidence.length) return "Found " + evidence.length + " evidence signal(s) — Creda is writing your ruling…";
    return "Preparing the case file…";
  }

  function renderWaitPipeline(data) {
    var host = $("wait-pipeline");
    if (!host) return;
    var log = data.pipelineLog || [];
    if (!log.length) {
      host.innerHTML = "";
      return;
    }
    var tail = log.slice(-4);
    host.innerHTML = tail.map(function (line, i) {
      var cls = i === tail.length - 1 ? "is-latest" : "is-done";
      return '<li class="' + cls + '">' + esc(String(line)) + "</li>";
    }).join("");
  }

  function sceneFromPipeline(data) {
    var blob = (data.pipelineLog || []).join(" ").toLowerCase();
    if (/writing|explanation|ruling|judge|computed/.test(blob)) return "stamp";
    if (/ocr|screenshot|extracted text|uploaded image/.test(blob)) return "ocr";
    if (/official|careers|ats|vacancy/.test(blob)) return "official_checks";
    if (/ats|vacancy|employer|tactic|official|evidence|compared/.test(blob)) return "evidence";
    return null;
  }

  function updateWaitTelemetry(data) {
    var status = normalize(data.status) || "queued";
    var agent = normalize(data.agentStatus) || "pending";
    var tlStatus = $("tl-status");
    var tlAgent = $("tl-agent");
    if (tlStatus) tlStatus.textContent = status.toUpperCase();
    if (tlAgent) tlAgent.textContent = agent.toUpperCase();
    var sub = $("wait-subtitle");
    if (sub) sub.textContent = pipelineWaitCopy(data);
  }

  function renderStickyUrgent(data) {
    var host = $("sticky-urgent");
    if (!host) return;
    if (normalize(data.verdict) !== "high_risk") {
      host.classList.add("hidden");
      host.innerHTML = "";
      return;
    }
    var blocks = synthesizeBlocks(data);
    var actions = [];
    blocks.forEach(function (b) {
      if (b.type === "safe_actions" && b.props && b.props.items) actions = actions.concat(b.props.items);
    });
    var urgent = actions.find(function (a) {
      var tone = normalize(a.tone || a.urgency || "");
      return tone === "urgent" || /do not pay|don't pay|never pay/i.test(String(a.label || a.title || ""));
    }) || actions[0];
    if (!urgent) {
      host.classList.add("hidden");
      host.innerHTML = "";
      return;
    }
    host.classList.remove("hidden");
    host.innerHTML = "<strong>" + esc(urgent.label || urgent.title || "Do not pay") + "</strong><span>" +
      esc(urgent.detail || urgent.description || "Stop and verify on the employer official careers site before sending money.") + "</span>";
  }

  function renderLiveExhibits(data) {
    var host = $("live-exhibits");
    var items = data.evidence || [];
    if (!items.length) {
      host.innerHTML = '<div class="empty"><svg width="120" height="80" viewBox="0 0 120 80" fill="none" aria-hidden="true"><rect x="20" y="18" width="80" height="50" rx="8" stroke="#c5d0da" stroke-width="2"/><path d="M40 38h40M40 48h24" stroke="#c5d0da" stroke-width="2" stroke-linecap="round"/><circle cx="92" cy="22" r="10" fill="#eef2f6" stroke="#c5d0da" stroke-width="2"/></svg><div>Exhibits will slip in as checks finish.</div></div>';
      return;
    }
    var prev = lastLiveExhibitCount;
    host.innerHTML = items.slice(0, 8).map(function (ev) {
      return '<div class="slip"><div class="meta">' +
        '<span class="pill ' + esc(normalize(ev.outcome)) + '">' + esc(outcomeStamp(ev.outcome)) + "</span>" +
        (ev.tier != null ? '<span class="pill t' + esc(ev.tier) + '">T' + esc(ev.tier) + "</span>" : "") +
        (ev.sourceUrl ? '<span class="pill source">SOURCE</span>' : "") +
        '<span class="pill match">' + esc(String(ev.check || "CHECK").replace(/_/g, " ").toUpperCase()) + "</span>" +
        "</div><div>" + esc(ev.excerpt || ev.summary || ev.text || "") + "</div></div>";
    }).join("");
    lastLiveExhibitCount = Math.min(items.length, 8);
    if (items.length > prev) {
      var slips = host.querySelectorAll(".slip");
      CredaMotion.slipIn(Array.prototype.slice.call(slips, prev));
    }
  }

  function pickOfficialUrl(data) {
    var items = data.evidence || [];
    var i;
    for (i = 0; i < items.length; i++) {
      if (items[i].sourceUrl) return items[i].sourceUrl;
    }
    var claims = data.claims || [];
    for (i = 0; i < claims.length; i++) {
      if (claims[i].url) return claims[i].url;
    }
    return "https://careers.example.com";
  }

  function renderOfficialChecks(data) {
    var urlEl = $("browser-url");
    var statusEl = $("official-status");
    var listEl = $("official-checklist");
    if (!urlEl || !listEl) return;
    var url = pickOfficialUrl(data);
    urlEl.textContent = url.replace(/^https?:\/\//i, "");
    if (statusEl) statusEl.textContent = pipelineWaitCopy(data);
    var labels = ["Employer careers domain", "Vacancy index", "Fee policy cross-check"];
    var active = Math.min(labels.length, Math.max(1, (data.evidence || []).length));
    listEl.innerHTML = labels.map(function (label, idx) {
      return '<li class="' + (idx < active ? "is-active" : "") + '">' + esc(label) + "</li>";
    }).join("");
  }

  function renderWait(data) {
    if (WaitStoryboard.isRunning()) {
      WaitStoryboard.onPoll(data);
    } else {
      var liveScene = sceneFromPipeline(data);
      if (liveScene && liveScene !== "stamp") CredaStageMachine.forceScene(liveScene, data);
      else updatePrestreamRail(CredaStageMachine.current || "intake");
    }
    var statusEl = $("official-status");
    if (statusEl) statusEl.textContent = pipelineWaitCopy(data);
    renderLiveExhibits(data);
  }

  function humanizeEvidence(ev) {
    var check = ev.check || "";
    var excerpt = ev.excerpt || ev.summary || "";
    if (check === "free_mailbox") return excerpt || "Sender used a free mailbox (not a company domain).";
    if (check === "fee_policy") return excerpt || "Official policy says no recruitment fees — compare with any payment ask.";
    if (check === "payment_demand") return excerpt || "The message asks for money before you start.";
    if (check === "domain_match" && normalize(ev.outcome) === "conflict") return excerpt || "Sender domain does not match the employer’s official site.";
    if (check === "vacancy_match" && normalize(ev.outcome) === "confirmed") return excerpt || "Role appears on an official careers page.";
    return excerpt || String(ev.outcome || "");
  }

  function theySaid(ev, data) {
    var claims = data.claims || [];
    var hit = claims.find(function (c) { return c.check === ev.check || c.type === ev.check; });
    if (hit) return hit.text || hit.claim || hit.value || "";
    if (ev.claimText) return ev.claimText;
    if (ev.check === "payment_demand") return "Asks for payment / fee before joining.";
    if (ev.check === "free_mailbox") return "Uses a free email address.";
    if (ev.check === "lookalike_domain" || ev.check === "official_domain") return "Sender claims to represent the employer brand.";
    if (ev.check === "fee_policy") return "Message implies a fee is required to proceed.";
    return String(ev.check || "Claim").replace(/_/g, " ");
  }

  function evidenceHighlightItems(data) {
    return (data.evidence || []).map(function (ev) {
      return {
        check: ev.check,
        outcome: ev.outcome,
        tier: ev.tier,
        text: humanizeEvidence(ev),
        claimText: theySaid(ev, data),
        sourceUrl: ev.sourceUrl
      };
    });
  }

  function synthesizeBlocks(data) {
    var pres = data.agentPresentation || {};
    if (pres.blocks && pres.blocks.length) {
      var blocks = pres.blocks.slice();
      var fullEvidence = evidenceHighlightItems(data);
      if (fullEvidence.length) {
        var replaced = false;
        blocks = blocks.map(function (b) {
          if (b.type !== "evidence_highlights") return b;
          var items = ((b.props || b.data || {}).items || []);
          if (items.length >= fullEvidence.length) return b;
          replaced = true;
          return { type: "evidence_highlights", props: { items: fullEvidence } };
        });
        if (!replaced && !blocks.some(function (b) { return b.type === "evidence_highlights"; })) {
          blocks.push({ type: "evidence_highlights", props: { items: fullEvidence } });
        }
      }
      return blocks;
    }

    var blocks = [];
    blocks.push({
      type: "verdict_banner",
      props: {
        title: verdictPlain(data.verdict),
        subtitle: consequenceFor(data.verdict, data.headline)
      }
    });

    var explain = data.explanation || data.agentReasoning || (pres.explanation && pres.explanation.text) || "";
    if (explain) blocks.push({ type: "explanation", props: { text: explain } });

    var researchItems = [];
    if (Array.isArray(data.checks)) {
      researchItems = data.checks.map(function (c) {
        return (c.label || c.id || "check") + ": " + (c.summary || c.state || "");
      });
    }
    if (researchItems.length) blocks.push({ type: "research_status", props: { label: "What Creda checked", items: researchItems } });

    var fullEvidence = evidenceHighlightItems(data);
    if (fullEvidence.length) {
      blocks.push({ type: "evidence_highlights", props: { items: fullEvidence } });
    }

    var tactics = [];
    (data.tactics || data.matchedTactics || []).forEach(function (t) {
      tactics.push(typeof t === "string" ? { title: t, guidance: "" } : t);
    });
    (data.evidence || []).forEach(function (ev) {
      if (ev.check === "payment_demand" && normalize(ev.outcome) === "confirmed") {
        tactics.push({ title: "Upfront fee", guidance: "Real employers do not ask you to pay to get the job." });
      }
      if (ev.check === "free_mailbox" && (normalize(ev.outcome) === "conflict" || normalize(ev.outcome) === "confirmed")) {
        tactics.push({ title: "Free mailbox", guidance: "Prefer recruiters on the company domain." });
      }
    });
    if (tactics.length) blocks.push({ type: "tactic_highlights", props: { items: tactics } });

    var unc = data.unresolved || data.uncertainty || [];
    if (unc.length) blocks.push({ type: "uncertainty", props: { items: unc } });

    var actions = data.nextActions || data.safeActions || [];
    if (actions.length) blocks.push({ type: "safe_actions", props: { items: actions } });

    var askItems = chipTaxonomy(data).ask;
    if (askItems.length) blocks.push({ type: "follow_up_questions", props: { items: askItems } });

    var turns = data.conversationTurns || [];
    if (turns.length) blocks.push({ type: "conversation", props: { turns: turns } });

    return blocks;
  }

  var BLOCK_RENDERERS = {
    verdict_banner: function (block, data) {
      var props = block.props || block.data || {};
      var v = normalize(props.verdict || data.verdict);
      var tone = verdictTone(v);
      var title = props.title || verdictPlain(v);
      var subtitle = props.subtitle || consequenceFor(v, data.headline);
      var conf = props.confidence != null ? props.confidence : (data.confidence != null ? data.confidence : null);
      var confHtml = confBarHtml(conf);
      var exhibitItems = evidenceHighlightItems(data);
      var exhibitCount = exhibitItems.length;
      var stampWord = stampLabel(v);
      return (
        '<div class="ruling judgment-shell liquid-glass ' + esc(tone) + '">' +
          '<div class="stamp-row">' +
            rulingStampPressHtml(stampWord, tone) +
            '<div class="stamp-meta">' +
              (exhibitCount ? '<span class="micro-metric">EXHIBITS ' + esc(exhibitCount) + "</span>" : "") +
              '<span class="micro-metric verdict-chip">' + esc(stampWord) + "</span>" +
            "</div>" +
          "</div>" +
          confHtml +
          "<h2>" + esc(title) + "</h2>" +
          '<p class="consequence">' + esc(subtitle) + "</p>" +
        "</div>"
      );
    },
    explanation: function (block, data) {
      var props = block.props || block.data || {};
      var text = props.text || data.agentReasoning || data.explanation || "";
      if (!text) return "";
      return (
        '<details class="glass-shell liquid-glass">' +
          "<summary><span>Why Creda ruled this way</span><span aria-hidden=\"true\">▾</span></summary>" +
          '<div class="body">' + esc(text) + "</div>" +
        "</details>"
      );
    },
    research_status: function (block) {
      var props = block.props || block.data || {};
      var items = props.items || [];
      if (!items.length) return "";
      return (
        '<details class="glass-shell liquid-glass">' +
          "<summary><span>" + esc(props.label || "What Creda checked") + "</span><span aria-hidden=\"true\">▾</span></summary>" +
          '<div class="body"><ul style="margin:.35rem 0 0;padding-left:1.1rem">' + items.map(function (it) {
            var t = typeof it === "string" ? it : (it.label || it.text || "");
            return "<li>" + esc(t) + "</li>";
          }).join("") + "</ul></div></details>"
      );
    },
    evidence_highlights: function (block, data) {
      var props = block.props || block.data || {};
      var items = props.items || [];
      if (!items.length) return "";
      return items.map(function (item, idx) {
        var claim = item.claimText || item.claim || theySaid(item, data);
        var checked = (item.text || item.excerpt || humanizeEvidence(item) || "").trim();
        if (!checked && item.sourceUrl) checked = "Matched against an official employer source.";
        if (!checked && item.check) checked = "Check: " + String(item.check).replace(/_/g, " ") + " — " + outcomeStamp(item.outcome) + ".";
        var hasBack = checked.length > 0;
        var tone = outcomeTone(item.outcome);
        var pin = "E" + (idx + 1);
        var flipClass = hasBack ? " flip-card" : " exhibit-card";
        return (
          '<div class="' + flipClass + ' tone-' + esc(tone) + '"' + (hasBack ? ' tabindex="0" aria-label="Exhibit ' + esc(pin) + ' — tap to flip"' : "") + ">" +
            '<div class="flip-inner">' +
              '<div class="flip-front">' +
                '<div class="exhibit-head">' +
                  '<div class="exhibit-claim">' + esc(claim) + "</div>" +
                  '<span class="exhibit-pin">' + esc(pin) + "</span>" +
                "</div>" +
                '<div class="exhibit-meta">' +
                  '<span class="pill ' + esc(normalize(item.outcome)) + '">' + esc(outcomeStamp(item.outcome)) + "</span>" +
                  (item.tier != null ? '<span class="pill t' + esc(item.tier) + '">T' + esc(item.tier) + "</span>" : "") +
                  (item.sourceUrl ? '<span class="pill source">SOURCE</span>' : "") +
                  '<span class="pill match">' + esc(String(item.check || "MATCH").replace(/_/g, " ").toUpperCase()) + "</span>" +
                "</div>" +
                (hasBack ? '<span class="flip-hint">Why we trust this</span>' : "") +
              "</div>" +
              (hasBack ? (
              '<div class="flip-back">' +
                '<div class="pk">Why we trust this</div>' +
                "<div>" + esc(checked) + "</div>" +
                (item.sourceUrl ? '<div style="margin-top:.35rem"><a href="' + esc(item.sourceUrl) + '" target="_blank" rel="noopener noreferrer">Open source</a></div>' : "") +
              "</div>"
              ) : "") +
            "</div>" +
          "</div>"
        );
      }).join("");
    },
    tactic_highlights: function (block) {
      var props = block.props || block.data || {};
      var items = props.items || [];
      if (!items.length) return "";
      return items.map(function (item, i) {
        var title = item.title || item.display_name || item.type || "Pattern";
        var guide = item.guidance || item.user_guidance || item.detail || "";
        var key = (item.tactic_id || item.tacticId || title || "").toLowerCase();
        return (
          '<div class="tactic-tile" data-tactic-idx="' + i + '">' +
            tacticVectorSvg(key, title) +
            "<strong>" + esc(String(title).replace(/_/g, " ")) + "</strong>" +
            (guide ? "<span>" + esc(guide) + "</span>" : "") +
          "</div>"
        );
      }).join("");
    },
    uncertainty: function (block, data) {
      var props = block.props || block.data || {};
      var items = props.items || data.unresolved || [];
      if (!items.length) {
        if (normalize(data.verdict) === "unverified") {
          return '<div class="unc-item">Official exhibits were incomplete — do not treat silence as clearance.</div>';
        }
        return '<div class="unc-item" style="color:var(--muted)">No open questions flagged.</div>';
      }
      return items.map(function (item) {
        var text = typeof item === "string" ? item : (item.text || item.message || "");
        return '<div class="unc-item">' + esc(text) + "</div>";
      }).join("");
    },
    safe_actions: function (block) {
      var props = block.props || block.data || {};
      var items = props.items || [];
      if (!items.length) return "";
      return items.map(function (item) {
        var tone = normalize(item.tone || item.urgency || "");
        var label = item.label || item.title || item.action || "Next step";
        var detail = item.detail || item.description || "";
        return '<div class="order ' + (tone === "urgent" || tone === "high_risk" ? "urgent" : "") + '"><strong>' + esc(label) + "</strong><span>" + esc(detail) + "</span></div>";
      }).join("");
    },
    follow_up_questions: function (block, data) {
      var props = block.props || block.data || {};
      var items = props.items || props.questions || data.agentFollowups || [];
      items = items.slice(0, 3);
      if (!items.length) return "";
      return items.map(function (q) {
        var text = typeof q === "string" ? q : (q.text || q.question || "");
        return '<button type="button" class="chip" data-followup="' + esc(text) + '">' + esc(text) + "</button>";
      }).join("");
    },
    conversation: function (block, data) {
      var props = block.props || block.data || {};
      var turns = props.turns || data.conversationTurns || optimisticTurns || [];
      return renderConversationHtml(turns, conversationPending);
    }
  };

  function chipTaxonomy(data) {
    var need = [];
    var ask = [];
    (data.unresolved || []).forEach(function (u) {
      var t = typeof u === "string" ? u : (u.text || u.message || "");
      if (t) need.push(t);
    });
    (data.needsMoreInfo || []).forEach(function (u) {
      var t = typeof u === "string" ? u : (u.text || u.message || "");
      if (t && need.indexOf(t) < 0) need.push(t);
    });
    (data.agentFollowups || data.followUpQuestions || []).forEach(function (q) {
      var t = typeof q === "string" ? q : (q.text || q.question || "");
      if (t) ask.push(t);
    });
    return { need: need.slice(0, 3), ask: ask.slice(0, 3) };
  }

  function needChipPrefill(text) {
    var t = String(text || "").trim();
    if (/url|link|site|domain/i.test(t)) return "Here's the official link: ";
    if (/employer|company/i.test(t)) return "The employer is: ";
    return "I can share: " + t;
  }

  function renderConversationHtml(turns, pending) {
    if (!turns || !turns.length) {
      if (pending) {
        return '<div class="conv-thread"><div class="conv-bubble assistant pending"><div class="conv-role">Creda</div>Thinking…</div></div>';
      }
      return "";
    }
    var html = '<div class="conv-thread">' + turns.map(function (t) {
      var role = normalize(t.role) || "user";
      var label = role === "user" ? "You" : "Creda";
      return '<div class="conv-bubble ' + esc(role) + '"><div class="conv-role">' + esc(label) + "</div>" + esc((t.text || "").slice(0, 1200)) + "</div>";
    }).join("");
    if (pending) {
      html += '<div class="conv-bubble assistant pending"><div class="conv-role">Creda</div>Thinking…</div>';
    }
    return html + "</div>";
  }

  function renderChipRows(data) {
    var tax = chipTaxonomy(data);
    var needHost = $("need-chips-host");
    var askHost = $("ask-chips-host");
    var needSection = $("need-section");
    var askSection = $("ask-section");
    if (needHost) {
      needHost.innerHTML = tax.need.map(function (text) {
        return '<button type="button" class="chip need" data-need="' + esc(text) + '">' + esc(text) + "</button>";
      }).join("");
      needHost.querySelectorAll("[data-need]").forEach(function (btn) {
        btn.addEventListener("click", function () {
          var val = needChipPrefill(btn.getAttribute("data-need") || "");
          $("followup-input").value = val;
          $("followup-input").focus();
        });
      });
    }
    if (askHost) {
      askHost.innerHTML = tax.ask.map(function (text) {
        return '<button type="button" class="chip ask" data-ask="' + esc(text) + '">' + esc(text) + "</button>";
      }).join("");
      askHost.querySelectorAll("[data-ask]").forEach(function (btn) {
        btn.addEventListener("click", function () {
          sendFollowup(btn.getAttribute("data-ask") || "");
        });
      });
    }
    if (needSection) needSection.classList.toggle("hidden", !tax.need.length);
    if (askSection) askSection.classList.toggle("hidden", !tax.ask.length);
  }

  function extractUrls(text) {
    var found = [];
    var re = /https?:\/\/[^\s"'<>)\]]+/gi;
    var match;
    while ((match = re.exec(text || ""))) {
      var url = match[0].replace(/[.,);]+$/, "");
      if (found.indexOf(url) < 0) found.push(url);
    }
    return found;
  }

  function collectLinkInputs() {
    var links = [];
    ["link-input-1", "link-input-2"].forEach(function (id) {
      var val = (($(id) && $(id).value) || "").trim();
      if (val && links.indexOf(val) < 0) links.push(val);
    });
    return links;
  }

  function toggleLinksPanel(open) {
    var panel = $("links-panel");
    if (!panel) return;
    panel.classList.toggle("hidden", !open);
    if (open) {
      var first = $("link-input-1");
      if (first && !first.value) first.focus();
    }
  }

  function blocksByType(blocks) {
    var map = {};
    blocks.forEach(function (b) {
      if (!map[b.type]) map[b.type] = [];
      map[b.type].push(b);
    });
    return map;
  }

  function renderEvidenceDock(data) {
    var host = $("evidence-dock");
    var items = data.evidence || [];
    var summary = $("evidence-dock-summary");
    if (!items.length) {
      if (summary) summary.textContent = "Raw evidence";
      host.innerHTML = '<div class="empty">No raw evidence rows on this case.</div>';
      return;
    }
    if (summary) summary.textContent = "Raw evidence (" + items.length + " checks)";
    host.innerHTML = items.map(function (ev, idx) {
      return '<details ' + (idx === 0 ? "open" : "") + ">" +
        "<summary><span>" + esc(String(ev.check || "evidence").replace(/_/g, " ")) +
        '</span><span class="pill ' + esc(normalize(ev.outcome)) + '">' + esc(outcomeStamp(ev.outcome)) + "</span></summary>" +
        '<div class="dock-body">' + esc(humanizeEvidence(ev)) +
        (ev.sourceUrl ? '<div style="margin-top:.35rem"><a href="' + esc(ev.sourceUrl) + '" target="_blank" rel="noopener noreferrer">Open source</a></div>' : "") +
        "</div></details>";
    }).join("");
  }

  function defaultDetailForAction(label) {
    if (/do not pay|don't pay|never pay/i.test(label)) return "Stop replying until you verify on the employer official careers site.";
    if (/verify|official/i.test(label)) return "Open the employer careers page directly instead of using links from the message.";
    return "Take this step before sending money or personal documents.";
  }

  function defaultActionsForVerdict(verdict) {
    var v = normalize(verdict);
    if (v === "high_risk") {
      return [{ label: "Do not pay or send documents", detail: "Stop replying until you verify on the employer official careers site.", tone: "urgent" }];
    }
    if (v === "no_conflict_found") {
      return [{ label: "Still verify the sender", detail: "No conflict found does not prove the offer is authentic.", tone: "primary" }];
    }
    if (v === "unverified") {
      return [{ label: "Treat as unresolved", detail: "Creda could not gather enough official exhibits.", tone: "warn" }];
    }
    return [{ label: "Review exhibits before you reply", detail: "Share only what is needed through official channels.", tone: "neutral" }];
  }

  function normalizeActions(raw, verdict) {
    var actions = (raw || []).map(function (a) {
      if (typeof a === "string") return { label: a.slice(0, 80), detail: defaultDetailForAction(a), tone: "primary" };
      var label = a.label || a.title || a.action || "Next step";
      return {
        label: label,
        detail: a.detail || a.description || defaultDetailForAction(label),
        tone: a.tone || a.urgency || "neutral"
      };
    }).filter(function (a) { return a.label; });
    if (!actions.length) actions = defaultActionsForVerdict(verdict);
    return actions.slice(0, 5);
  }

  function dedupeExhibits(items, max) {
    var seen = {};
    var out = [];
    (items || []).forEach(function (item) {
      var text = (item.text || item.excerpt || humanizeEvidence(item) || "").trim();
      var key = String(item.check || "evidence") + "|" + text.slice(0, 96);
      if (seen[key]) return;
      seen[key] = true;
      out.push(item);
    });
    return out.slice(0, max || 6);
  }

  function collectTacticItems(blocks) {
    var items = [];
    (blocks || []).forEach(function (b) {
      if (b.type !== "tactic_highlights") return;
      var props = b.props || b.data || {};
      items = items.concat(props.items || []);
    });
    return items;
  }

  function mergeFollowupSnapshot(data) {
    if (!followupPollMode || !followupBaseline) return data;
    var agent = normalize(data.agentStatus);
    var verdict = normalize(data.verdict);
    if (!conversationPending) return data;
    if (!(agent === "running" || agent === "streaming" || verdict === "pending")) return data;
    var merged = Object.assign({}, data);
    merged.verdict = followupBaseline.verdict || merged.verdict;
    merged.headline = followupBaseline.headline || merged.headline;
    merged.nextActions = (followupBaseline.nextActions && followupBaseline.nextActions.length)
      ? followupBaseline.nextActions
      : merged.nextActions;
    if (followupBaseline.explanation) {
      merged.agentReasoning = followupBaseline.explanation;
      merged.explanation = followupBaseline.explanation;
    }
    if (followupBaseline.presentation) merged.agentPresentation = followupBaseline.presentation;
    if (followupBaseline.evidence && followupBaseline.evidence.length) merged.evidence = followupBaseline.evidence;
    if (followupBaseline.tactics && followupBaseline.tactics.length) merged.tactics = followupBaseline.tactics;
    merged.conversationTurns = data.conversationTurns || merged.conversationTurns;
    return merged;
  }

  function renderResult(data, opts) {
    opts = opts || {};
    data = mergeFollowupSnapshot(data);
    data.nextActions = normalizeActions(data.nextActions || data.safeActions, data.verdict);
    lastData = data;
    document.body.setAttribute("data-verdict", normalize(data.verdict) || "");

    $("ruling-host").innerHTML = stampBoardHtml(data);
    var headline = (data.headline || consequenceFor(data.verdict, null) || "").trim();
    $("board-headline").textContent = headline;

    var blocks = synthesizeBlocks(data);
    var by = blocksByType(blocks);
    var tacticItems = collectTacticItems(blocks);
    if (!tacticItems.length && data.tactics && data.tactics.length) tacticItems = data.tactics;
    tacticItems = tacticItems.slice(0, 5);
    $("tactics-host").innerHTML = tacticItems.map(function (item) {
      var title = item.title || item.display_name || item.type || "Pattern";
      var guide = item.guidance || item.user_guidance || item.detail || "";
      var line = guide ? String(title).replace(/_/g, " ") + " — " + guide : String(title).replace(/_/g, " ");
      if (line.length > 140) line = line.slice(0, 137) + "…";
      return '<div class="tactic-line">' + esc(line) + "</div>";
    }).join("");

    var exhibitItems = dedupeExhibits(evidenceHighlightItems(data), 6);
    $("exhibits-host").innerHTML = exhibitItems.length
      ? BLOCK_RENDERERS.evidence_highlights({ props: { items: exhibitItems } }, data)
      : "";

    $("orders-host").innerHTML = data.nextActions.map(function (a) {
      var urgent = a.tone === "urgent" || a.tone === "high_risk" ? " urgent" : "";
      return '<div class="board-action' + urgent + '"><strong>' + esc(a.label) + "</strong><span>" + esc(a.detail) + "</span></div>";
    }).join("");

    var turns = (data.conversationTurns && data.conversationTurns.length)
      ? ensureFollowupAssistantTurn(data)
      : optimisticTurns;
    $("conversation-host").innerHTML = renderConversationHtml(turns, conversationPending);

    var judgmentHost = $("judgment-host");
    var researchHost = $("research-host");
    if (judgmentHost) judgmentHost.innerHTML = "";
    if (researchHost) researchHost.innerHTML = "";

    wireFlipCards($("exhibits-host"));
    renderStickyUrgent(data);
    if (!opts.skipReveal) requestAnimationFrame(function () { CredaMotion.resultReveal(); });
  }

  async function pollOnce() {
    if (!session.caseId || !session.token) return;
    var data = await apiFetch("/cases/" + encodeURIComponent(session.caseId), {
      headers: { "X-Case-Token": session.token }
    });
    lastData = data;
    if (followupPollMode) {
      showView("result");
      if (followupReplyComplete(data)) {
        stopPolling();
        conversationPending = false;
        optimisticTurns = [];
        followupPollMode = false;
        renderResult(data);
        return;
      }
      renderResult(data, { skipReveal: true });
      if (Date.now() - pollStartedAt > POLL_MAX_MS) {
        stopPolling();
        conversationPending = false;
        followupPollMode = false;
        showError("followup-error", { code: "POLL_TIMEOUT", message: "Timed out waiting for Creda's reply." });
        renderResult(data, { skipReveal: true });
        return;
      }
      pollTimer = setTimeout(function () { pollOnce().catch(function () {}); }, POLL_MS);
      return;
    }
    if (isReady(data)) {
      if (WaitStoryboard.isRunning()) {
        WaitStoryboard.markReady(data);
        renderWait(data);
        pollTimer = setTimeout(function () { pollOnce().catch(function () {}); }, POLL_MS);
        return;
      }
      stopPolling();
      showView("result");
      renderResult(data);
      return;
    }
    if (Date.now() - pollStartedAt > POLL_MAX_MS) {
      stopPolling();
      followupPollMode = false;
      conversationPending = false;
      showView("result");
      if (data && (data.evidence || data.verdict)) renderResult(data);
      showError("result-error", { code: "POLL_TIMEOUT", message: "Timed out waiting for a final ruling." });
      return;
    }
    showView("wait");
    renderWait(data);
    pollTimer = setTimeout(function () {
      pollOnce().catch(function (e) {
        if (followupPollMode) {
          showError("followup-error", e, { onRetry: function () { pollOnce().catch(function () {}); } });
        } else {
          showView("wait");
          renderStreamError(e, { onRetry: function () { pollOnce().catch(function (err) { renderStreamError(err); }); } });
        }
        pollTimer = setTimeout(function () { pollOnce().catch(function () {}); }, POLL_MS * 2);
      });
    }, POLL_MS);
  }

  function startPolling(opts) {
    opts = opts || {};
    stopPolling();
    if (!opts.followup) {
      startElapsed();
      CredaStageMachine.reset();
      WaitStoryboard.reset();
      WaitStoryboard.start();
      showView("wait");
      $("live-exhibits").innerHTML = "";
      lastLiveExhibitCount = 0;
      lastStreamBody = "";
      lastActiveStage = -1;
      var statusEl = $("official-status");
      if (statusEl) statusEl.textContent = "Case accepted — preparing your file…";
      updatePrestreamRail("intake");
    }
    pollOnce().catch(function (e) {
      stopPolling();
      if (opts.followup) {
        conversationPending = false;
        showError("followup-error", e, { focusId: "followup-input", onRetry: function () { startPolling({ followup: true }); } });
        return;
      }
      showView("intake");
      showError("intake-error", e, { focusId: "offer-text", onRetry: submitCase });
    });
  }

  async function resumeSession() {
    if (!session.caseId || !session.token) return;
    try {
      var data = await apiFetch("/cases/" + encodeURIComponent(session.caseId), {
        headers: { "X-Case-Token": session.token }
      });
      lastData = data;
      if (isReady(data)) {
        showView("result");
        renderResult(data);
        return;
      }
      startPolling();
    } catch (e) {
      session.caseId = null;
      session.token = null;
      saveSession();
      showView("intake");
      showError("intake-error", e, { focusId: "offer-text", onRetry: submitCase });
    }
  }

  async function submitCase() {
    showError("intake-error", "");
    $("btn-check").disabled = true;
    try {
      var uploaded = await uploadPendingAttachments();
      caseHadAttachment = uploaded.length > 0 || pendingAttachments.length > 0;
      var payload = buildPayload(uploaded);
      var data = await apiFetch("/cases", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      session.caseId = data.caseId;
      session.token = caseToken(data);
      if (!session.caseId || !session.token) throw new Error("Create case response missing caseId/token.");
      saveSession();
      startPolling();
    } catch (e) {
      showError("intake-error", e, { focusId: "offer-text", onRetry: submitCase });
    } finally {
      $("btn-check").disabled = false;
    }
  }

  async function sendFollowup(presetText) {
    showError("followup-error", "");
    var q = (presetText || $("followup-input").value || "").trim();
    if (!q) { showError("followup-error", "Type a question first.", { focusId: "followup-input" }); return; }
    if (!session.caseId || !session.token) { showError("followup-error", "No active case.", { onRetry: resetToIntake }); return; }
    $("btn-followup").disabled = true;
    optimisticTurns = (lastData && lastData.conversationTurns) ? lastData.conversationTurns.slice() : [];
    optimisticTurns.push({ role: "user", text: q });
    followupBaseline = {
      verdict: (lastData && lastData.verdict) || "",
      headline: (lastData && lastData.headline) || "",
      explanation: (lastData && (lastData.explanation || lastData.agentReasoning)) || "",
      nextActions: normalizeActions((lastData && lastData.nextActions) || [], lastData && lastData.verdict),
      presentation: (lastData && lastData.agentPresentation) || null,
      evidence: (lastData && lastData.evidence) ? lastData.evidence.slice() : [],
      tactics: lastData ? collectTacticItems(synthesizeBlocks(lastData)) : [],
      evidenceLen: (lastData && lastData.evidence && lastData.evidence.length) || 0,
      turnCount: (lastData && lastData.conversationTurns && lastData.conversationTurns.length) || 0
    };
    conversationPending = true;
    followupPollMode = true;
    $("conversation-host").innerHTML = renderConversationHtml(optimisticTurns, true);
    showView("result");
    try {
      var question = pendingFollowupQuestion && pendingFollowupQuestion !== q ? pendingFollowupQuestion : "";
      await apiFetch("/cases/" + encodeURIComponent(session.caseId) + "/followup", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Case-Token": session.token
        },
        body: JSON.stringify({
          answerText: q,
          text: q,
          userMessage: q,
          question: question
        })
      });
      pendingFollowupQuestion = "";
      $("followup-input").value = "";
      pollStartedAt = Date.now();
      startPolling({ followup: true });
    } catch (e) {
      conversationPending = false;
      followupPollMode = false;
      optimisticTurns = [];
      showError("followup-error", e, { focusId: "followup-input", onRetry: function () { sendFollowup(q); } });
    } finally {
      $("btn-followup").disabled = false;
    }
  }

  function toggleReportPanel(open) {
    var sheet = $("report-sheet");
    if (sheet) sheet.classList.toggle("hidden", !open);
    showError("report-error", "");
    if (open) {
      var prefill = ($("offer-text").value || "").trim();
      if (!prefill && lastData) prefill = (lastData.offerText || lastData.headline || "").trim();
      if (!prefill && lastData) {
        prefill = [lastData.headline, lastData.verdict, (lastData.links || []).join("\n")].filter(Boolean).join("\n\n");
      }
      if (prefill && !($("report-text").value || "").trim()) $("report-text").value = prefill;
      $("report-text").focus();
    }
  }

  async function submitReport() {
    var text = ($("report-text").value || "").trim();
    if (!text) {
      showError("report-error", "Paste the scam message or describe what Creda missed.", { focusId: "report-text" });
      return;
    }
    $("btn-report-send").disabled = true;
    showError("report-error", "");
    try {
      var body = {
        reportText: text,
        notes: "Creda UI report. User believes a scam was missed.",
        contactConsent: false
      };
      if (session.caseId) body.linkedCaseId = session.caseId;
      if (lastData && lastData.verdict) body.linkedVerdict = lastData.verdict;
      await apiFetch("/reports/scam", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      toggleReportPanel(false);
      $("report-text").value = "";
      $("btn-report").textContent = "Report sent";
      setTimeout(function () { $("btn-report").textContent = "Report a missed scam"; }, 2500);
    } catch (e) {
      showError("report-error", e, { focusId: "report-text", onRetry: submitReport });
    } finally {
      $("btn-report-send").disabled = false;
    }
  }

  function resetToIntake() {
    stopPolling();
    session.caseId = null;
    session.token = null;
    pendingFollowupQuestion = "";
    followupPollMode = false;
    conversationPending = false;
    followupBaseline = null;
    optimisticTurns = [];
    caseHadAttachment = false;
    CredaStageMachine.reset();
    WaitStoryboard.reset();
    lastActiveStage = -1;
    toggleReportPanel(false);
    clearComposer();
    saveSession();
    document.body.removeAttribute("data-verdict");
    showError("intake-error", "");
    showError("result-error", "");
    showView("intake");
  }

  function wire() {
    CredaMotion.init();
    CredaShieldArt.init();
    $("btn-check").addEventListener("click", submitCase);
    wireComposer();
    $("btn-clear").addEventListener("click", clearComposer);
    $("btn-cancel-wait").addEventListener("click", resetToIntake);
    $("btn-new").addEventListener("click", resetToIntake);
    $("btn-followup").addEventListener("click", function () { sendFollowup(); });
    $("followup-input").addEventListener("keydown", function (e) {
      if (e.key === "Enter") sendFollowup();
    });
    document.querySelectorAll(".demo-chip[data-demo]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var ta = $("offer-text");
        if (ta) {
          ta.value = btn.getAttribute("data-demo") || "";
          syncParsedLinksFromText();
          autoResizeComposer();
          ta.focus();
        }
      });
    });
    $("btn-report").addEventListener("click", function () { toggleReportPanel(true); });
    $("btn-report-cancel").addEventListener("click", function () { toggleReportPanel(false); });
    $("btn-report-send").addEventListener("click", submitReport);
    bootstrapSessionFromUrl();
    restoreSession();
    checkHealth().then(function () {
      if (session.caseId && session.token) resumeSession();
    });
  }

  wire();

})();
