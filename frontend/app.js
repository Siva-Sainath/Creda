(function () {
  "use strict";

  var API_URL = "https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com";
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
  var followupGraceStartedAt = 0;
  var FOLLOWUP_GRACE_MS = 8000;
  var readySince = 0;
  var reportMode = "scam";

  var CredaStageMachine = {
    current: null,
    scenes: {
      intake: { id: "scene-intake", label: "Opening your case file…" },
      evidence: { id: "scene-evidence", label: "Pulling scam signals…" },
      official_checks: { id: "scene-careers", label: "Checking official careers listing…" },
      qwen_weigh: { id: "scene-qwen", label: "Weighing the evidence…" },
      stamp: { id: "scene-stamp", label: "Stamping your ruling…" }
    },
    sceneIds: ["scene-intake", "scene-evidence", "scene-careers", "scene-qwen", "scene-stamp"],
    subtitles: {
      intake: "Reading the message for sender, links, and claims…",
      evidence: "Comparing against known scam tactics…",
      official_checks: "Cross-checking the careers link with official listings…",
      qwen_weigh: "Weighing every signal before ruling…",
      stamp: "Finalizing the ruling…"
    },
    infraCopy: {
      intake: "Reading sender, links, and claims…",
      evidence: "Matching known scam patterns…",
      official_checks: "Checking the careers domain…",
      qwen_weigh: "Weighing signals…",
      stamp: "Stamping the ruling…"
    },
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
      var infra = $("wait-infra");
      if (title) CredaMotion.setHeadlineWords(title, meta.label);
      if (sub) {
        var copy = pipelineWaitCopy(data || {});
        if (!copy || copy === meta.label || (/preparing/i.test(copy) && key !== "intake")) {
          copy = this.subtitles[key] || "Please wait — this can take under a minute.";
        }
        sub.textContent = copy;
      }
      if (infra) infra.textContent = this.infraCopy[key] || this.subtitles[key] || "";
      updatePrestreamRail(key);
      if (window.CredaPass && typeof CredaPass.setStage === "function") CredaPass.setStage(key);
      CredaMotion.startStageLoop(key);
      if (!CredaMotion.ok() || CredaMotion.reduced) return;
      if (meta.id) {
        var active = document.getElementById(meta.id);
        if (active) gsap.fromTo(active, { opacity: 0.35, y: 8 }, { opacity: 1, y: 0, duration: 0.42, ease: "power2.out" });
      }
      if (key === "intake") {
        gsap.fromTo("#stage-sheet", { y: 12, opacity: 0 }, { y: 0, opacity: 1, duration: 0.4, ease: "power2.out" });
        gsap.fromTo("#stage-folder-tab", { scale: 1 }, { scale: 1.08, duration: 0.25, yoyo: true, repeat: 1, transformOrigin: "50% 100%" });
      }
      if (key === "evidence") {
        gsap.fromTo("#evidence-pulse", { scale: 0.9, opacity: 0.5 }, { scale: 1, opacity: 1, duration: 0.35, ease: "back.out(2)", transformOrigin: "50% 50%" });
      }
      if (key === "official_checks") {
        gsap.fromTo("#scene-careers", { opacity: 0.4, y: 6 }, { opacity: 1, y: 0, duration: 0.4, ease: "power2.out" });
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
      CredaMotion.stopStageLoop();
    }
  };

  var WaitStoryboard = {
    MIN_MS: 1400,
    running: false,
    sequence: [],
    stepIndex: 0,
    stepTimer: null,
    readyData: null,
    dwellComplete: false,
    lastPollData: null,
    stampShownAt: 0,
    start: function () {
      this.running = true;
      this.readyData = null;
      this.dwellComplete = false;
      this.lastPollData = null;
      this.stampShownAt = 0;
      this.sequence = ["intake", "evidence", "official_checks", "qwen_weigh", "stamp"];
      this.stepIndex = 0;
      this._playStep();
    },
    _playStep: function () {
      if (!this.running) return;
      var key = this.sequence[this.stepIndex];
      if (key === "stamp" && !this.readyData) {
        CredaStageMachine.forceScene("qwen_weigh", this.lastPollData || {});
        var selfWait = this;
        this.stepTimer = setTimeout(function () { selfWait._playStep(); }, 400);
        return;
      }
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
      // Wall-clock driven on purpose: this fires from the outer poll loop
      // (every ~2-3s, reliable) rather than depending on the inner 400ms
      // setTimeout retry chain, which can silently stop rescheduling (e.g.
      // background-tab timer throttling) and leave the wait screen stuck
      // forever even though the backend is ready.
      this.readyData = data;
      var stampIdx = this.sequence.indexOf("stamp");
      if (stampIdx >= 0 && this.running) {
        if (CredaStageMachine.current !== "stamp") {
          this.stepIndex = stampIdx;
          clearTimeout(this.stepTimer);
          CredaStageMachine.forceScene("stamp", data);
          this.stampShownAt = Date.now();
        }
        if (this.stampShownAt && Date.now() - this.stampShownAt >= this.MIN_MS) {
          this.dwellComplete = true;
        }
      }
      this._tryFinish();
    },
    _tryFinish: function () {
      if (!this.running || !this.readyData || !this.dwellComplete) return;
      this.running = false;
      clearTimeout(this.stepTimer);
      var data = this.readyData;
      this.readyData = null;
      CredaMotion.stopStageLoop();
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
      this.stampShownAt = 0;
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
    stageLoopTween: null,
    pipelineTl: null,
    emptyTl: null,
    hintTimer: null,
    hintIndex: 0,
    useCaseTimer: null,
    useCaseIndex: 0,
    intakeTimer: null,
    intakeIndex: 0,
    INTAKE_TIPS: [
      { title: "Paste the offer", lede: "Creda reads the message against known employers before you reply." },
      { title: "Don't send KYC first", lede: "Aadhaar, PAN, and OTPs never belong in a recruiter's opening chat." },
      { title: "Trust the sender, not the logo", lede: "Handle, domain, and any fee ask matter more than letterhead." },
      { title: "Then reply", lede: "A typical pass takes about a minute." }
    ],
    USE_CASES: [
      {
        kicker: "WhatsApp hire",
        title: "Is this recruiter real?",
        lede: "Paste the chat before you send Aadhaar, an OTP, or a joining fee.",
        emptyHtml: "Is this <span class=\"mark\">recruiter</span> real?",
        emptyLede: "Creda checks the employer name, the fee ask, and the careers domain before you reply.",
        prompt: "Hi, congratulations you are selected for Amazon warehouse night shift. Pay ₹1,499 for uniform then we share joining letter. Send Aadhaar now."
      },
      {
        kicker: "LinkedIn DM",
        title: "HR in your inbox",
        lede: "A hiring manager you never applied to wants you on a private Google Meet.",
        emptyHtml: "HR in your <span class=\"mark\">inbox</span>",
        emptyLede: "Lookalike titles and rushed interviews are a common kit. Creda flags the pattern, not the vibe.",
        prompt: "Hello I am Priya from Wipro Talent. You are shortlisted. Join this Meet in 10 minutes and keep your PAN card ready for KYC: meet.google.com/xyz-fake"
      },
      {
        kicker: "Lookalike careers page",
        title: "Does that URL check out?",
        lede: "Paste the offer that links to a careers site that is almost the real one.",
        emptyHtml: "Does that <span class=\"mark\">URL</span> check out?",
        emptyLede: "One extra letter in the domain is enough. Creda weighs known employer hosts, not the logo in the email.",
        prompt: "Please complete onboarding on our portal https://careers-infosys.co.in/join and pay ₹2,000 refundable security for laptop dispatch."
      },
      {
        kicker: "Internship stipend",
        title: "Unpaid until you pay",
        lede: "Training fees dressed up as internships still count as an offer Creda can rule on.",
        emptyHtml: "Unpaid until you <span class=\"mark\">pay</span>",
        emptyLede: "Upfront course fees and “stipend after week 2” are a registered scam pattern, not a company policy.",
        prompt: "Selected for remote internship. Stipend ₹25,000 after training. First pay ₹3,999 for LMS access. UPI: intern-hr@okaxis"
      },
      {
        kicker: "Work-from-home kit",
        title: "Task-based income",
        lede: "Copy-paste jobs that ask you to recharge a wallet first belong in this box too.",
        emptyHtml: "Task-based <span class=\"mark\">income</span>",
        emptyLede: "Creda is not only for Fortune-500 lookalikes. Daily-task and data-entry kits use the same fee-and-OTP play.",
        prompt: "Earn ₹1,200/day typing captions. To activate your ID send the OTP we just texted and load ₹500 in the partner wallet."
      },
      {
        kicker: "Email offer letter",
        title: "PDF in the thread",
        lede: "Forward the email body. Creda reads the text — not the letterhead.",
        emptyHtml: "PDF in the <span class=\"mark\">thread</span>",
        emptyLede: "Official-looking PDFs still have to match a known employer. If the sender domain is off, say so in the paste.",
        prompt: "From: hr@tcs-careers.net Subject: Offer of Employment. Attach your cancelled cheque and Aadhaar to confirm payroll. Joining bonus after you complete Form-16 upload on the link."
      }
    ],
    applyUseCase: function (scene) {
      if (!scene) return;
      var title = $("empty-title");
      var lede = $("empty-lede");
      if (title) title.innerHTML = scene.emptyHtml;
      if (lede) lede.textContent = scene.emptyLede;
    },
    applyIntakeTip: function (tip) {
      if (!tip) return;
      var hero = $("hero-title");
      var lede = $("hero-lede");
      if (hero) hero.textContent = tip.title;
      if (lede) lede.textContent = tip.lede;
    },
    crossfade: function (el, write) {
      if (!el) { write(); return; }
      if (!this.ok() || this.reduced) { write(); return; }
      gsap.to(el, {
        y: -6, opacity: 0, duration: 0.26, ease: "power2.in",
        onComplete: function () {
          write();
          gsap.fromTo(el, { y: 10, opacity: 0 }, { y: 0, opacity: 1, duration: 0.48, ease: "power3.out" });
        }
      });
    },
    useCasePaused: function () {
      if (document.body.classList.contains("has-case")) return true;
      var empty = $("casefile-empty");
      if (empty && empty.classList.contains("hidden")) return true;
      return false;
    },
    startUseCaseCycle: function () {
      var self = this;
      var scenes = this.USE_CASES;
      var tips = this.INTAKE_TIPS;
      if (!scenes.length) return;
      this.applyUseCase(scenes[0]);
      this.applyIntakeTip(tips[0]);
      if (this.useCaseTimer) clearInterval(this.useCaseTimer);
      if (this.intakeTimer) clearInterval(this.intakeTimer);
      if (this.reduced) return;
      this.useCaseTimer = setInterval(function () {
        if (self.useCasePaused()) return;
        self.useCaseIndex = (self.useCaseIndex + 1) % scenes.length;
        self.crossfade($("empty-copy"), function () { self.applyUseCase(scenes[self.useCaseIndex]); });
      }, 5600);
      this.intakeTimer = setInterval(function () {
        if (document.body.classList.contains("has-case")) return;
        self.intakeIndex = (self.intakeIndex + 1) % tips.length;
        self.crossfade($("intake-copy"), function () { self.applyIntakeTip(tips[self.intakeIndex]); });
      }, 6800);
    },
    stopUseCaseCycle: function () {
      if (this.useCaseTimer) { clearInterval(this.useCaseTimer); this.useCaseTimer = null; }
      if (this.intakeTimer) { clearInterval(this.intakeTimer); this.intakeTimer = null; }
    },
    init: function () {
      if (!this.ok()) return;
      var self = this;
      if (typeof MotionPathPlugin !== "undefined") gsap.registerPlugin(MotionPathPlugin);
      if (typeof Flip !== "undefined") gsap.registerPlugin(Flip);
      gsap.matchMedia().add("(prefers-reduced-motion: reduce)", function () {
        self.reduced = true;
      });
      this.pageLoad();
    },
    pageLoad: function () {
      if (!this.ok() || this.reduced) {
        this.startPipelineLoop();
        this.startUseCaseCycle();
        return;
      }
      var ease = "cubic-bezier(.22,1,.36,1)";
      var targets = [".topbar", ".pane-intake > *", ".casefile-stage"];
      targets.forEach(function (sel) {
        gsap.fromTo(sel, { y: 12 }, {
          y: 0, duration: 0.4, stagger: 0.05, ease: ease,
          onComplete: function () { gsap.set(sel, { clearProps: "transform" }); }
        });
      });
      this.startPipelineLoop();
      this.startEmptyScene();
      this.startUseCaseCycle();
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
      gsap.fromTo(el, { autoAlpha: 0, y: 12 }, {
        autoAlpha: 1, y: 0, duration: 0.45, ease: "power3.out",
        onComplete: function () { gsap.set(el, { clearProps: "opacity,visibility,transform,autoAlpha" }); }
      });
      if (name === "wait") {
        gsap.fromTo(".prestream-rail .prestream-step",
          { y: 8, autoAlpha: 0 },
          { y: 0, autoAlpha: 1, duration: 0.35, stagger: 0.06, ease: "power2.out", delay: 0.08,
            onComplete: function () { gsap.set(".prestream-rail .prestream-step", { clearProps: "opacity,transform,autoAlpha" }); }
          });
        gsap.fromTo(".wait-iso-slot",
          { autoAlpha: 0 },
          { autoAlpha: 1, duration: 0.4, ease: "power2.out",
            onComplete: function () { gsap.set(".wait-iso-slot", { clearProps: "opacity,visibility,autoAlpha" }); }
          });
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
      gsap.fromTo(nodes,
        { x: -16, autoAlpha: 0 },
        { x: 0, autoAlpha: 1, duration: 0.42, stagger: 0.08, ease: "power3.out",
          onComplete: function () { gsap.set(nodes, { clearProps: "opacity,transform,autoAlpha" }); }
        });
    },
    setHeadlineWords: function (el, text) {
      if (!el) return;
      var value = String(text || "").trim();
      if (!value) { el.textContent = ""; return; }
      var words = value.split(/\s+/);
      if (!this.ok() || this.reduced || words.length > 12) {
        el.textContent = value;
        return;
      }
      el.innerHTML = words.map(function (w) {
        return '<span class="word">' + esc(w) + "</span>";
      }).join(" ");
      gsap.fromTo(el.querySelectorAll(".word"), { y: 10, autoAlpha: 0 }, {
        y: 0, autoAlpha: 1, duration: 0.35, stagger: 0.02, ease: "power3.out",
        onComplete: function () { gsap.set(el.querySelectorAll(".word"), { clearProps: "opacity,transform,autoAlpha" }); }
      });
    },
    // Baseten-style pipeline loop: icons draw on, then a packet travels the wire
    // to the next node. pathLength="1" lets one dash value drive every path.
    startPipelineLoop: function () {
      this.stopPipelineLoop();
      var host = document.getElementById("how-it-works");
      var hl = document.getElementById("how-highlight");
      if (!host) return;
      var steps = host.querySelectorAll(".how-step");
      if (!steps.length) return;
      var activate = function (i, animate) {
        for (var j = 0; j < steps.length; j++) steps[j].classList.toggle("is-active", j === i);
        if (!hl || !steps[i]) return;
        if (animate && typeof Flip !== "undefined") {
          Flip.fit(hl, steps[i], { duration: 0.55, ease: "power3.inOut" });
        } else if (typeof Flip !== "undefined") {
          Flip.fit(hl, steps[i], { duration: 0 });
        }
      };
      activate(0, false);
      if (!this.ok() || this.reduced) return;
      var tl = gsap.timeline({ repeat: -1 });
      steps.forEach(function (step, i) {
        tl.call(function () { activate(i, true); });
        tl.to({}, { duration: i === steps.length - 1 ? 1.45 : 1.15 });
      });
      this.pipelineTl = tl;
    },
    stopPipelineLoop: function () {
      if (this.pipelineTl) { this.pipelineTl.kill(); this.pipelineTl = null; }
    },
    startEmptyScene: function () {
      this.stopEmptyScene();
      if (!this.ok() || this.reduced) return;
      if (document.getElementById("iso-host") && document.getElementById("iso-host").classList.contains("iso-live")) return;
      var meters = document.querySelectorAll("#empty-infer [data-meter]");
      if (!meters.length) return;
      gsap.set(meters, { scaleX: 0.16, transformOrigin: "0% 50%" });
      var hop = gsap.timeline({ repeat: -1, repeatDelay: 0.2 });
      hop.to(meters[0], { scaleX: 0.9, duration: 1.4, ease: "power2.inOut" }, 0.15);
      hop.to(meters[1], { scaleX: 0.76, duration: 1.5, ease: "power2.inOut" }, 1.55);
      hop.to(meters[2], { scaleX: 0.97, duration: 1.3, ease: "power2.inOut" }, 3.2);
      hop.to(meters, { scaleX: 0.18, duration: 0.5, ease: "power2.in" }, 5.15);
      this.emptyTl = hop;
    },
    stopEmptyScene: function () {
      if (this.emptyTl) { this.emptyTl.kill(); this.emptyTl = null; }
      if (this.ok()) gsap.killTweensOf("#empty-infer [data-meter]");
    },
    startStageLoop: function (key) {
      this.stopStageLoop();
      if (!this.ok() || this.reduced) return;
      var meta = CredaStageMachine.scenes[key];
      if (!meta) return;
      var scene = document.getElementById(meta.id);
      if (!scene) return;
      var target = scene.querySelector("g, circle, rect, path, line") || scene;
      if (key === "evidence") {
        this.stageLoopTween = gsap.to("#evidence-pulse circle:first-child", {
          scale: 1.12, opacity: 0.55, duration: 1.1, repeat: -1, yoyo: true, ease: "sine.inOut", transformOrigin: "50% 50%"
        });
        return;
      }
      if (key === "qwen_weigh") {
        this.stageLoopTween = gsap.to("#scene-qwen", {
          rotation: 2.5, duration: 1.4, repeat: -1, yoyo: true, ease: "sine.inOut", transformOrigin: "50% 50%"
        });
        return;
      }
      if (key === "stamp") {
        this.stageLoopTween = gsap.to("#stage-stamp-press", {
          y: 2, duration: 0.8, repeat: -1, yoyo: true, ease: "sine.inOut"
        });
        return;
      }
      this.stageLoopTween = gsap.to(target, {
        y: -4, duration: 1.2, repeat: -1, yoyo: true, ease: "sine.inOut"
      });
    },
    stopStageLoop: function () {
      if (this.stageLoopTween) {
        this.stageLoopTween.kill();
        this.stageLoopTween = null;
      }
      if (!this.ok()) return;
      ["#scene-intake", "#scene-evidence", "#scene-careers", "#scene-qwen", "#stage-stamp-press", "#evidence-pulse circle:first-child"].forEach(function (sel) {
        try { gsap.set(sel, { clearProps: "transform,opacity" }); } catch (e) {}
      });
    },
    revealTargets: function () {
      return [
        ".board-stamp", ".board-stamp-host", ".ruling-stamp-press",
      "#board-headline", "#board-meta", "#board-consequence",
      "#orders-host .action-badge", "#tactics-host .tactic-tile",
      "#exhibits-host .extra-checks", "#judgment-host .why-collapsed",
      ".report-hero", "#report-stats", "#conversation-host .conv-bubble",
      ".timeline-item", ".ticket", ".evidence-card"
      ];
    },
    forceRevealVisible: function () {
      var sel = this.revealTargets().join(", ");
      var nodes = document.querySelectorAll(sel);
      for (var i = 0; i < nodes.length; i++) {
        nodes[i].style.opacity = "1";
        nodes[i].style.visibility = "visible";
      }
      if (!this.ok()) return;
      try {
        if (this._revealTl) { this._revealTl.kill(); this._revealTl = null; }
        gsap.killTweensOf(sel);
        gsap.set(sel, { autoAlpha: 1, opacity: 1, visibility: "visible", clearProps: "opacity,visibility,transform,autoAlpha" });
        if (typeof gsap.utils !== "undefined" && gsap.utils.toArray) {
          gsap.utils.toArray(sel).forEach(function (el) {
            try { gsap.set(el, { clearProps: "all" }); } catch (e1) {}
            el.style.opacity = "1";
            el.style.visibility = "visible";
          });
        }
      } catch (e) {}
    },
    resultReveal: function () {
      var stamp = document.querySelector(".ruling-stamp-press");
      if (stamp) stamp.classList.add("is-pressed");
      this.forceRevealVisible();
      bindTiltCards();
      if (!this.ok() || this.reduced) {
        this.forceRevealVisible();
        animateConfBar(true);
        return;
      }
      var targets = this.revealTargets();
      var sel = targets.join(", ");
      var self = this;
      try { gsap.set(sel, { autoAlpha: 1, opacity: 1, visibility: "visible" }); } catch (e0) {}
      var timelineLine = document.querySelector(".timeline-line");
      if (timelineLine) gsap.set(timelineLine, { scaleY: 0, transformOrigin: "top center" });
      var tl = gsap.timeline({
        defaults: { ease: "power3.out" },
        onComplete: function () {
          self.forceRevealVisible();
          try { gsap.set(sel, { autoAlpha: 1, opacity: 1, clearProps: "opacity,visibility,transform,autoAlpha" }); } catch (e2) {}
        }
      });
      this._revealTl = tl;
      tl.fromTo(".report-hero", { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.18 })
        .fromTo(".board-stamp", { y: 10, scale: 0.9, rotation: -6 }, { y: 0, scale: 1, rotation: 0, autoAlpha: 1, duration: 0.4, ease: "back.out(1.7)" }, "-=0.1")
        .fromTo(stamp || ".ruling-stamp-press", { scale: 1.08, rotation: -4 }, { scale: 1, rotation: 0, autoAlpha: 1, duration: 0.36, ease: "back.out(1.6)" }, "<")
        .fromTo("#board-headline", { y: 10 }, { y: 0, autoAlpha: 1, duration: 0.3 }, "-=0.2")
        .fromTo("#board-meta:not(.is-empty)", { y: 6 }, { y: 0, autoAlpha: 1, duration: 0.22 }, "-=0.18")
        .fromTo("#board-consequence", { y: 6 }, { y: 0, autoAlpha: 1, duration: 0.24 }, "-=0.16")
        .call(function () { animateConfBar(false); }, null, "-=0.1")
        .to(timelineLine, { scaleY: 1, duration: 0.55, ease: "power2.inOut" }, "-=0.05")
        .fromTo(".timeline-dot", { scale: 0, autoAlpha: 0 }, { scale: 1, autoAlpha: 1, duration: 0.32, stagger: 0.14, ease: "back.out(2.4)" }, "-=0.45")
        .fromTo(".timeline-copy", { x: -10, autoAlpha: 0 }, { x: 0, autoAlpha: 1, duration: 0.3, stagger: 0.14 }, "<0.05")
        .fromTo(".ticket", { y: 16, autoAlpha: 0, rotation: -1.5 }, {
          y: 0, autoAlpha: 1, rotation: 0, duration: 0.34, stagger: 0.06, ease: "back.out(1.5)"
        }, "-=0.25")
        .fromTo(".evidence-card", { x: 14, autoAlpha: 0 }, {
          x: 0, autoAlpha: 1, duration: 0.28, stagger: 0.05
        }, "-=0.4")
        .fromTo("#conversation-host .conv-bubble, .followup-composer .chip", { y: 8, autoAlpha: 0 }, {
          y: 0, autoAlpha: 1, duration: 0.24, stagger: 0.04
        }, "-=0.15");
      var urgent = document.querySelector(".action-badge.urgent");
      if (urgent) {
        gsap.to(urgent, { scale: 1.03, duration: 0.18, yoyo: true, repeat: 1, ease: "power1.inOut", delay: 0.45 });
      }
    }
  };

  function animateConfBar(instant) {
    var fill = document.querySelector(".conf-bar-fill");
    if (!fill) return;
    var target = fill.style.width || "0%";
    if (instant || !CredaMotion.ok() || CredaMotion.reduced) {
      fill.style.width = target;
      return;
    }
    gsap.fromTo(fill, { width: "0%" }, { width: target, duration: 0.9, ease: "power3.out", delay: 0.15 });
  }

  var TILT_MAX = 6;
  function bindTiltCards() {
    if (!CredaMotion.ok() || CredaMotion.reduced) return;
    if (!window.matchMedia("(hover: hover) and (pointer: fine)").matches) return;
    var cards = document.querySelectorAll(".ticket, .evidence-card");
    cards.forEach(function (card) {
      if (card._tiltBound) return;
      card._tiltBound = true;
      var qx = gsap.quickTo(card, "rotateX", { duration: 0.35, ease: "power3.out" });
      var qy = gsap.quickTo(card, "rotateY", { duration: 0.35, ease: "power3.out" });
      var qs = gsap.quickTo(card, "y", { duration: 0.35, ease: "power3.out" });
      card.style.transformPerspective = "600px";
      card.addEventListener("mousemove", function (e) {
        var r = card.getBoundingClientRect();
        var px = (e.clientX - r.left) / r.width - 0.5;
        var py = (e.clientY - r.top) / r.height - 0.5;
        qx(-py * TILT_MAX);
        qy(px * TILT_MAX);
        qs(-2);
      });
      card.addEventListener("mouseleave", function () {
        qx(0); qy(0); qs(0);
      });
    });
  }

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

  function formatReportHtml(text) {
    var raw = String(text || "").trim();
    if (!raw) return "";
    var blocks = raw.split(/\n{2,}/).map(function (b) { return b.trim(); }).filter(Boolean);
    if (blocks.length === 1 && raw.length > 160 && raw.indexOf("\n") < 0) {
      blocks = raw.replace(/([.!?])\s+(?=[A-Z])/g, "$1\n\n").split(/\n{2,}/).filter(Boolean);
    }
    return '<div class="report-prose">' + blocks.map(function (block) {
      var lines = block.split(/\n/).map(function (l) { return l.trim(); }).filter(Boolean);
      var list = lines.length > 1 && lines.every(function (l) { return /^[-•*]\s+/.test(l); });
      if (list) {
        return "<ul>" + lines.map(function (l) {
          return "<li>" + linkifyEsc(l.replace(/^[-•*]\s+/, "")) + "</li>";
        }).join("") + "</ul>";
      }
      return "<p>" + linkifyEsc(lines.join(" ")) + "</p>";
    }).join("") + "</div>";
  }

  function splitFindings(text) {
    var raw = String(text || "").trim();
    if (!raw) return [];
    var blocks = raw.split(/\n{2,}/).map(function (b) { return b.trim(); }).filter(Boolean);
    if (blocks.length === 1) {
      blocks = raw.replace(/([.!?])\s+(?=[A-Z])/g, "$1\n\n").split(/\n{2,}/).map(function (b) { return b.trim(); }).filter(Boolean);
    }
    if (blocks.length === 1 && raw.length > 90) {
      var bits = raw.match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [raw];
      blocks = bits.map(function (s) { return s.trim(); }).filter(Boolean);
    }
    return blocks.slice(0, 3);
  }

  function findingsHtml(text) {
    var parts = splitFindings(text);
    if (!parts.length) return "";
    return (
      '<div class="report-timeline">' +
        '<div class="timeline-line" aria-hidden="true"></div>' +
        parts.map(function (p, i) {
          return (
            '<div class="timeline-item">' +
              '<span class="timeline-dot">' + (i + 1) + "</span>" +
              '<div class="timeline-copy">' + linkifyEsc(p) + "</div>" +
            "</div>"
          );
        }).join("") +
      "</div>"
    );
  }

  var ACTION_ICONS = [
    { test: /\bpay|\bfee|\botp|\bid\b|aadhaar|kyc|share.*(id|otp|bank)/i,
      svg: '<path d="M12 3 4 6.5V11c0 5 3.4 8.4 8 9.7 4.6-1.3 8-4.7 8-9.7V6.5L12 3Z" stroke-linejoin="round"/><path d="M9.2 12.1 11.2 14l3.6-4.2" stroke-linecap="round" stroke-linejoin="round"/>' },
    { test: /verify|official|careers|domain|jobs page|website|url|link/i,
      svg: '<circle cx="11" cy="11" r="6.4" opacity=".14" fill="currentColor" stroke-width="1.6"/><path d="M8.4 11.2 10.3 13l3.6-4.2" stroke-linecap="round" stroke-linejoin="round"/><path d="m16.2 16.2 4 4" stroke-linecap="round"/>' },
    { test: /report|flag|forward|scam desk|block/i,
      svg: '<path d="M6 21V4h11l-2 3.5L17 11H6" stroke-linejoin="round"/>' },
    { test: /mailbox|email|domain|sender/i,
      svg: '<rect x="3.5" y="6" width="17" height="12" rx="2"/><path d="m4.5 7.5 7.5 6 7.5-6" stroke-linecap="round" stroke-linejoin="round"/>' }
  ];
  function actionIconSvg(label) {
    var found = ACTION_ICONS.find(function (a) { return a.test.test(label || ""); });
    var body = found ? found.svg : '<path d="M5 12h13M12 5l7 7-7 7" stroke-linecap="round" stroke-linejoin="round"/>';
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">' + body + "</svg>";
  }

  function linkifyEsc(text) {
    var escaped = esc(text);
    return escaped.replace(/https?:\/\/[^\s<&]+/g, function (url) {
      var clean = url.replace(/[.,);]+$/, "");
      return '<a href="' + clean + '" target="_blank" rel="noopener noreferrer">' + clean + "</a>";
    });
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
        var statusEl = $("official-status");
        if (statusEl) statusEl.textContent = "Reconnecting…";
        pollOnce().catch(function (e) { renderStreamError(e, ctx); });
      },
      lastErr: err
    }, ctx || {});
    showError("result-error", err, ctx);
    var statusEl = $("official-status");
    if (statusEl) statusEl.textContent = (err && err.message) ? err.message : "Connection issue — retrying…";
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
      ? '<tspan x="84" y="50">' + esc(lines[0]) + '</tspan><tspan x="84" y="72">' + esc(lines.slice(1).join(" ")) + "</tspan>"
      : '<tspan x="84" y="62">' + esc(label) + "</tspan>";
    return (
      '<div class="ruling-stamp-press is-pressed" aria-hidden="true">' +
        '<svg viewBox="0 0 168 112" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="' + esc(label) + ' stamp">' +
          '<rect class="stamp-frame stamp-frame-' + esc(tone) + '" x="6" y="10" width="156" height="92" rx="10" fill="none" stroke-width="5"/>' +
          '<rect class="stamp-fill stamp-fill-' + esc(tone) + '" x="14" y="18" width="140" height="76" rx="6"/>' +
          '<text class="stamp-text stamp-text-' + esc(tone) + '" text-anchor="middle" font-family="JetBrains Mono, ui-monospace, monospace" font-size="15" font-weight="800" letter-spacing=".08em">' + tspan + "</text>" +
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

  var INTERIM_REPLY_RE = /writing the explanation|writing your ruling|cred\s*a is writing|cred a is writing/i;

  function isInterimText(text) {
    return INTERIM_REPLY_RE.test(String(text || ""));
  }

  function extractFollowupAnswer(data) {
    if (!data) return "";
    var candidates = [
      data.agentReply,
      data.followupReply,
      data.agentAnswer,
      data.answerText
    ];
    var turns = data.conversationTurns || [];
    var lastUser = -1;
    for (var i = turns.length - 1; i >= 0; i--) {
      if (normalize(turns[i].role) === "user") { lastUser = i; break; }
    }
    if (lastUser >= 0) {
      for (var j = lastUser + 1; j < turns.length; j++) {
        if (normalize(turns[j].role) === "user") continue;
        candidates.push(turns[j].text);
      }
    }
    for (var k = 0; k < candidates.length; k++) {
      var t = String(candidates[k] || "").trim();
      if (t && !isInterimText(t)) return t;
    }
    // Live backend regenerates agentReasoning/explanation in place on follow-up —
    // it never appends a discrete assistant turn or agentReply field. Treat a
    // changed, non-interim reasoning string as the real answer.
    var reasoning = String(data.agentReasoning || data.explanation || "").trim();
    if (reasoning && !isInterimText(reasoning)) {
      var baselineReasoning = String((followupBaseline && followupBaseline.explanation) || "").trim();
      if (reasoning !== baselineReasoning) return reasoning;
    }
    return "";
  }

  function followupReplyComplete(data) {
    if (!conversationPending) return true;
    var agent = normalize(data.agentStatus);
    if (agent === "running" || agent === "streaming") {
      followupGraceStartedAt = 0;
      return false;
    }
    var answer = extractFollowupAnswer(data);
    if (answer) {
      followupGraceStartedAt = 0;
      return true;
    }
    if (!followupGraceStartedAt) followupGraceStartedAt = Date.now();
    if (Date.now() - followupGraceStartedAt < FOLLOWUP_GRACE_MS) return false;
    followupGraceStartedAt = 0;
    return true;
  }

  function ensureFollowupAssistantTurn(data, fallbackText) {
    var turns = (data.conversationTurns || []).slice();
    var lastUser = -1;
    for (var i = turns.length - 1; i >= 0; i--) {
      if (normalize(turns[i].role) === "user") { lastUser = i; break; }
    }
    if (lastUser < 0) return turns;
    for (var j = lastUser + 1; j < turns.length; j++) {
      var existing = (turns[j].text || "").trim();
      if (normalize(turns[j].role) !== "user" && existing && !isInterimText(existing)) return turns;
    }
    // Strip any interim assistant placeholders after the last user turn
    turns = turns.filter(function (t, idx) {
      if (idx <= lastUser) return true;
      if (normalize(t.role) === "user") return true;
      return !isInterimText(t.text);
    });
    var reply = extractFollowupAnswer(data) || String(fallbackText || "").trim();
    if (reply && !isInterimText(reply)) turns.push({ role: "assistant", text: reply });
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
    if (v === "high_risk") return "Do not pay or share ID until you verify on the official careers site.";
    if (v === "no_conflict_found") return "No conflict found — still verify the sender before you reply.";
    if (v === "unverified") return "Not enough official proof — treat this as unresolved.";
    return "Review the stamps and tiles before you reply.";
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
      if (!caseId || !token) return false;
      session.caseId = caseId;
      session.token = token;
      saveSession();
      if (window.history && window.history.replaceState) {
        params.delete("case");
        params.delete("token");
        var qs = params.toString();
        window.history.replaceState({}, "", window.location.pathname + (qs ? "?" + qs : ""));
      }
      return true;
    } catch (e) { return false; }
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
    // Two-pane workspace: intake stays visible on the left; wait/result swap on the right.
    var intake = $("view-intake");
    var wait = $("view-wait");
    var result = $("view-result");
    var empty = $("casefile-empty");
    if (intake) {
      intake.classList.remove("hidden");
      intake.setAttribute("aria-hidden", "false");
    }
    if (wait) {
      wait.classList.toggle("hidden", name !== "wait");
      wait.setAttribute("aria-hidden", name === "wait" ? "false" : "true");
    }
    if (result) {
      result.classList.toggle("hidden", name !== "result");
      result.setAttribute("aria-hidden", name === "result" ? "false" : "true");
    }
    if (empty) {
      var showEmpty = name === "intake";
      empty.classList.toggle("hidden", !showEmpty);
      empty.setAttribute("aria-hidden", showEmpty ? "false" : "true");
    }
    document.body.classList.remove("view-bleed");
    document.body.classList.toggle("view-wide", name === "wait" || name === "result");
    document.body.classList.toggle("has-case", name === "wait" || name === "result");
    if (name === "intake") CredaShieldArt.setFlowStep(0);
    else if (name === "wait") CredaShieldArt.setFlowStep(1);
    else if (name === "result") CredaShieldArt.setFlowStep(2);
    // Keep Clear/Check/demos locked while case is running; unlock on result/intake
    if (name === "wait") setIntakeBusy(true);
    else if (!conversationPending) setIntakeBusy(false);
    var follow = $("btn-followup");
    var fu = $("followup-input");
    var report = $("btn-report");
    if (follow) {
      var followReady = name === "result" && !conversationPending;
      follow.disabled = !followReady;
      follow.textContent = conversationPending ? "Waiting…" : "Send";
    }
    if (fu) fu.disabled = name !== "result" || conversationPending;
    if (report) report.disabled = name === "wait";
    var eta = $("wait-eta");
    if (eta) eta.textContent = followupPollMode ? "Usually up to ~100s on follow-ups" : "Usually 45–90s";
    document.body.classList.toggle("ui-waiting", name === "wait" || conversationPending);
    document.body.classList.toggle("ui-ready", name === "result" && !conversationPending);
    if (window.CredaPass && typeof CredaPass.mount === "function") {
      if (name === "wait") CredaPass.mount($("wait-iso-slot"), "live");
      else CredaPass.mount($("iso-home"), "idle");
    }
    if (name !== "wait") CredaMotion.stopStageLoop();
    // The pipeline strip only lives in the intake lane; don't burn frames when it's hidden.
    if (name === "intake") {
      CredaMotion.startPipelineLoop();
      CredaMotion.startEmptyScene();
    } else {
      CredaMotion.stopPipelineLoop();
      CredaMotion.stopEmptyScene();
    }
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
    if (session.token && /^\/cases\/[^/?]+$/.test(path.split("?")[0]) && (!opts.method || opts.method === "GET")) {
      if (!headers["X-Case-Token"] && !headers["x-case-token"]) headers["X-Case-Token"] = session.token;
    }
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
      if ($("health-dot")) $("health-dot").className = "dot err";
      if ($("health-label")) $("health-label").textContent = "API unreachable";
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


  function setIntakeBusy(busy) {
    ["btn-check", "btn-clear"].forEach(function (id) {
      var el = $(id);
      if (el) el.disabled = !!busy;
    });
    var ta = $("offer-text");
    if (ta) ta.readOnly = !!busy;
    var health = $("health-label");
    var pill = $("health-pill");
    if (health) {
      if (busy) {
        health.textContent = "CHECKING";
        if (pill) pill.setAttribute("data-state", "checking");
      } else if ((health.textContent || "").toUpperCase() === "CHECKING") {
        health.textContent = "Ready";
        if (pill) pill.setAttribute("data-state", "ready");
      }
    }
    if (!busy) syncSendButton();
  }

  function syncSendButton() {
    var btn = $("btn-check");
    if (!btn) return;
    var textLen = ($("offer-text").value || "").trim().length;
    var ready = textLen >= 12;
    btn.classList.toggle("is-active", ready);
    btn.disabled = !ready;
    var clearBtn = $("btn-clear");
    if (clearBtn) clearBtn.disabled = !textLen;
  }

  function autoResizeComposer() {
    var ta = $("offer-text");
    if (!ta) return;
    // Desktop: CSS flexes the textarea to fill the lane, so JS must not set a height.
    if (window.matchMedia("(min-width: 1024px)").matches) {
      ta.style.height = "";
      ta.style.overflowY = ta.scrollHeight > ta.clientHeight ? "auto" : "hidden";
      syncSendButton();
      return;
    }
    var maxPx = Math.max(220, Math.floor(window.innerHeight * 0.6));
    ta.style.height = "0";
    var next = Math.min(ta.scrollHeight, maxPx);
    ta.style.height = next + "px";
    ta.style.overflowY = ta.scrollHeight > maxPx ? "auto" : "hidden";
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

  function buildPayload() {
    var offerText = $("offer-text").value.trim();
    if (!offerText || offerText.length < 12) {
      throw new Error("Paste the complete email or message, including sender and any links.");
    }
    var payload = {
      offerText: offerText,
      locale: "en-IN",
      sourceChannel: "web"
    };
    var links = parsedLinks.concat(collectLinkInputs()).concat(extractUrls(offerText));
    links = links.filter(function (u, i) { return links.indexOf(u) === i; }).slice(0, 5);
    if (links.length) payload.links = links;
    return payload;
  }

  function tacticVectorSvg(key, title) {
    // Lucide/Heroicons-style inline SVGs (MIT): wallet, message-circle, link, building, shield-alert, globe
    var hay = (key + " " + (title || "")).toLowerCase();
    var atr = 'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"';
    if (/fee|deposit|payment|upi|paytm|wallet|money|bank|kit|phonepe/.test(hay)) {
      return '<svg ' + atr + '><path d="M19 7V6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-1"/><path d="M3 10h18"/><path d="M17 14h.01"/><rect x="15" y="12" width="6" height="6" rx="1"/></svg>';
    }
    if (/telegram|whatsapp|signal|dm|channel|chat|message/.test(hay)) {
      return '<svg ' + atr + '><path d="M7.9 20A9 9 0 1 0 4 16.1L2 22z"/></svg>';
    }
    if (/vacancy|careers|link|url|http|redirect/.test(hay)) {
      return '<svg ' + atr + '><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>';
    }
    if (/employer|company|org|building|ats|official|brand/.test(hay)) {
      return '<svg ' + atr + '><path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"/><path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2"/><path d="M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2"/><path d="M10 6h4"/><path d="M10 10h4"/><path d="M10 14h4"/><path d="M10 18h4"/></svg>';
    }
    if (/risk|alert|scam|threat|shield|warn|phishing/.test(hay)) {
      return '<svg ' + atr + '><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg>';
    }
    if (/domain|mailbox|email|gmail|sender|web|site|globe|dns|whois/.test(hay)) {
      return '<svg ' + atr + '><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>';
    }
    if (/form|enroll|google|doc/.test(hay)) {
      return '<svg ' + atr + '><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><path d="M8 13h8"/><path d="M8 17h6"/></svg>';
    }
    return '<svg ' + atr + '><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg>';
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
    window.addEventListener("resize", autoResizeComposer);
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

  function humanizePipelineLine(line) {
    var s = String(line || "");
    var lower = s.toLowerCase();
    if (/^(file|signals|check|qwen)\b/i.test(s.trim())) {
      s = s.replace(/^(file|signals|check|qwen)\b[:\s-]*/i, "");
      lower = s.toLowerCase();
    }
    if (/file|intake|queued|opening/.test(lower)) return "Opening your case file…";
    if (/ocr|screenshot|image|pdf/.test(lower)) return "Reading your screenshot…";
    if (/signal|tactic|evidence|compared/.test(lower)) return "Pulling scam signals…";
    if (/official|careers|ats|vacancy|employer/.test(lower)) return "Checking official careers listing…";
    if (/qwen|weigh|judge|stream|inference/.test(lower)) return "Weighing evidence…";
    if (/writing|explanation|ruling|stamp|computed/.test(lower)) return "Stamping your ruling…";
    return s || "Preparing the case file…";
  }

  function pipelineWaitCopy(data) {
    var log = data.pipelineLog || [];
    var last = log.length ? String(log[log.length - 1]) : "";
    var agent = normalize(data.agentStatus);
    var verdict = normalize(data.verdict);
    var evidence = data.evidence || [];
    var scene = CredaStageMachine.current;
    if (agent === "ready" && verdict && verdict !== "pending") return "Ruling ready — opening your result…";
    if (scene && CredaStageMachine.scenes[scene]) {
      var sceneLabel = CredaStageMachine.scenes[scene].label;
      if (WaitStoryboard.isRunning() && !WaitStoryboard.dwellComplete && scene === "stamp") {
        return CredaStageMachine.scenes.qwen_weigh.label;
      }
      if (last) return humanizePipelineLine(last) || sceneLabel;
      if (evidence.length && scene !== "stamp") return "Found " + evidence.length + " signal(s) — still checking…";
      return sceneLabel;
    }
    if (last) return humanizePipelineLine(last);
    if (data.agentProgress) return humanizePipelineLine(data.agentProgress);
    if (evidence.length) return "Found " + evidence.length + " signal(s) — still checking…";
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
    var agent = normalize(data.agentStatus);
    if (/writing|explanation|ruling|judge|computed/.test(blob)) {
      if (agent === "ready" || agent === "streaming") return "stamp";
      return "qwen_weigh";
    }
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

  function renderStickyUrgent() {
    var host = $("sticky-urgent");
    if (host) { host.classList.add("hidden"); host.innerHTML = ""; }
  }

  function renderLiveExhibits(data) {
    var host = $("live-exhibits");
    if (!host) return;
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
  }

  function humanizeEvidence(ev) {
    var check = ev.check || "";
    var excerpt = ev.excerpt || ev.summary || "";
    if (check === "free_mailbox") return excerpt || "Sender used a free mailbox (not a company domain).";
    if (check === "fee_policy") return excerpt || "Official policy says no recruitment fees — compare with any payment ask.";
    if (check === "payment_demand") return excerpt || "The message asks for money before you start.";
    if (check === "domain_match" && normalize(ev.outcome) === "conflict") return excerpt || "Sender domain does not match the employer’s official site.";
    if (check === "vacancy_match" && normalize(ev.outcome) === "confirmed") return excerpt || "Role appears on an official careers page.";
    var cleaned = String(excerpt || "").replace(/\s*Discovery context only[^.]*\.?/gi, "").trim();
    return cleaned || String(ev.outcome || "").replace(/_/g, " ");
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

    var actions = extractRawActions(data);
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
          "<summary><span>Why Creda ruled this way</span><span aria-hidden=\"true\"></span></summary>" +
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
          "<summary><span>" + esc(props.label || "What Creda checked") + "</span><span aria-hidden=\"true\"></span></summary>" +
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
      return items.slice(0, 6).map(function (item, idx) {
        var smoking = clipWords(item.text || item.excerpt || humanizeEvidence(item) || theySaid(item, data) || "", 22);
        if (!smoking && item.check) smoking = clipWords(String(item.check).replace(/_/g, " "), 12);
        var tone = outcomeTone(item.outcome);
        var pin = "E" + (idx + 1);
        return (
          '<div class="exhibit-slip tone-' + esc(tone) + '" aria-label="Exhibit ' + esc(pin) + '">' +
            '<span class="exhibit-pin">' + esc(pin) + "</span>" +
            '<span class="pill ' + esc(normalize(item.outcome)) + '">' + esc(outcomeStamp(item.outcome)) + "</span>" +
            '<span class="exhibit-smoking">' + esc(smoking) + "</span>" +
            (item.sourceUrl
              ? '<a class="source-chip" href="' + esc(item.sourceUrl) + '" target="_blank" rel="noopener noreferrer">src</a>'
              : '<span class="source-chip source-chip-muted">—</span>') +
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
        return '<div class="conv-thread"><div class="conv-bubble assistant pending"><div class="conv-role">Checking</div>Reading the case file…</div></div>';
      }
      return "";
    }
    var html = '<div class="conv-thread">' + turns.map(function (t) {
      var role = normalize(t.role) || "user";
      var label = role === "user" ? "You" : "Answer";
      var body = role === "user"
        ? "<p>" + esc((t.text || "").slice(0, 1200)) + "</p>"
        : formatReportHtml((t.text || "").slice(0, 4000));
      return '<div class="conv-bubble ' + esc(role) + '"><div class="conv-role">' + esc(label) + "</div>" + body + "</div>";
    }).join("");
    if (pending) {
      html += '<div class="conv-bubble assistant pending"><div class="conv-role">Checking</div>Working on that question…</div>';
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

  function extractRawActions(data) {
    var raw = data && data.nextActions;
    if (raw && raw.length) return raw;
    if (data && data.safeActions && data.safeActions.length) return data.safeActions;
    var blocks = (data && data.agentPresentation && data.agentPresentation.blocks) || [];
    for (var i = 0; i < blocks.length; i++) {
      if (blocks[i].type !== "safe_actions") continue;
      var props = blocks[i].props || blocks[i].data || {};
      var items = props.items || [];
      if (items.length) return items;
    }
    return [];
  }

  function clipWords(text, maxWords) {
    var words = String(text || "").trim().split(/\s+/).filter(Boolean);
    if (words.length <= maxWords) return words.join(" ");
    return words.slice(0, maxWords).join(" ");
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
    // Board lock: the live backend regenerates verdict/headline/explanation/evidence
    // in place while answering a follow-up. The product rule is the board (stamp,
    // headline, tiles, exhibits) must NEVER change from a follow-up — only the
    // conversation thread may show the new answer. Pin everything unconditionally.
    var merged = Object.assign({}, data);
    merged.verdict = followupBaseline.verdict || merged.verdict;
    merged.headline = followupBaseline.headline || merged.headline;
    merged.explanation = followupBaseline.explanation || merged.explanation;
    merged.agentReasoning = followupBaseline.explanation || merged.agentReasoning;
    if (followupBaseline.presentation) merged.agentPresentation = followupBaseline.presentation;
    merged.evidence = followupBaseline.evidence || merged.evidence;
    merged.tactics = followupBaseline.tactics || merged.tactics;
    merged.nextActions = followupBaseline.nextActions || merged.nextActions;
    merged.conversationTurns = data.conversationTurns || merged.conversationTurns;
    return merged;
  }

  function renderResult(data, opts) {
    opts = opts || {};
    data = mergeFollowupSnapshot(data);
    if (opts.followupOnly) {
      var turnsOnly = (data.conversationTurns && data.conversationTurns.length)
        ? ensureFollowupAssistantTurn(data, extractFollowupAnswer(data))
        : optimisticTurns;
      $("conversation-host").innerHTML = renderConversationHtml(turnsOnly, conversationPending);
      return;
    }
    data.nextActions = normalizeActions(extractRawActions(data), data.verdict);
    lastData = data;
    document.body.setAttribute("data-verdict", normalize(data.verdict) || "");

    $("ruling-host").innerHTML = stampBoardHtml(data);

    var interimHeadline = INTERIM_REPLY_RE;
    var rawHeadline = (data.headline || "").trim();
    if (!rawHeadline || interimHeadline.test(rawHeadline)) {
      rawHeadline = (followupBaseline && followupBaseline.headline) || stampLabel(data.verdict);
    }
    CredaMotion.setHeadlineWords($("board-headline"), clipWords(rawHeadline, 22));

    // Optional one meta line (sender/domain) — never full URLs/email body
    var metaEl = $("board-meta");
    if (metaEl) {
      var meta = "";
      var claims = data.claims || [];
      for (var ci = 0; ci < claims.length; ci++) {
        var c = claims[ci] || {};
        var ck = normalize(c.check || c.type || "");
        if (/domain|mailbox|sender|email/.test(ck)) {
          meta = clipWords(String(c.value || c.text || c.claim || ck).replace(/https?:\/\/\S+/gi, ""), 6);
          break;
        }
      }
      if (!meta && data.employer) meta = clipWords(String(data.employer), 6);
      var channel = normalize(data.sourceChannel || data.channel || data.intakeChannel || "");
      if (channel === "telegram") meta = meta ? meta + " · Telegram" : "From Telegram";
      metaEl.textContent = meta;
      metaEl.classList.toggle("is-empty", !meta);
    }

    var consequenceEl = $("board-consequence");
    if (consequenceEl) consequenceEl.textContent = consequenceFor(data.verdict, null);

    // Action chips IMMEDIATELY under stamp/meta (2–3)
    if (followupBaseline && followupBaseline.nextActions && followupBaseline.nextActions.length) {
      var looksGeneric = data.nextActions.length <= 1 && /wait for the agent|review the stamps|review exhibits/i.test((data.nextActions[0] && data.nextActions[0].label) || "");
      if (!extractRawActions(data).length || looksGeneric) data.nextActions = followupBaseline.nextActions;
    }
    var statsEl = $("report-stats");
    if (statsEl) {
      var conf = data.confidence != null ? data.confidence : data.agentConfidence;
      statsEl.innerHTML = confBarHtml(conf) || "";
    }

    var why = (data.agentReasoning || data.explanation || "").trim();
    var judgmentHost = $("judgment-host");
    if (judgmentHost) {
      judgmentHost.classList.remove("hidden");
      judgmentHost.innerHTML = why
        ? '<p class="report-section-kicker">Why this stamp</p>' + findingsHtml(why)
        : "";
    }

    var actionList = (data.nextActions || []).slice(0, 4);
    $("orders-host").innerHTML = actionList.length
      ? '<p class="report-section-kicker">Do this next</p><div class="ticket-row">' + actionList.map(function (a, i) {
        var detail = a.detail && a.detail !== a.label ? clipWords(a.detail, 22) : "";
        return (
          '<div class="ticket">' +
            '<span class="ticket-icon">' + actionIconSvg(a.label) + "</span>" +
            '<span class="ticket-n">Step ' + (i + 1) + "</span>" +
            "<b>" + esc(clipWords(a.label, 18)) + "</b>" +
            (detail ? "<p>" + esc(detail) + "</p>" : "") +
          "</div>"
        );
      }).join("") + "</div>"
      : "";

    var citedIds = data.citedEvidenceIds || data.agentCitedEvidence || [];
    var evidence = data.evidence || [];
    var byId = {};
    evidence.forEach(function (ev) { if (ev && ev.id) byId[ev.id] = ev; });
    var sources = [];
    (Array.isArray(citedIds) ? citedIds : []).forEach(function (id) {
      var ev = typeof id === "string" ? byId[id] : (id && id.id ? byId[id.id] || id : id);
      if (ev && sources.indexOf(ev) < 0) sources.push(ev);
    });
    if (!sources.length) {
      evidence.forEach(function (ev) {
        if (ev && (ev.sourceUrl || ev.excerpt) && sources.length < 5) sources.push(ev);
      });
    }
    sources = sources.slice(0, 5);
    $("tactics-host").innerHTML = sources.length
      ? '<p class="report-section-kicker">Sources on file</p><div class="evidence-row">' + sources.map(function (ev, i) {
        var label = "";
        try {
          if (ev.sourceUrl) {
            var parsed = new URL(ev.sourceUrl);
            label = parsed.hostname.replace(/^www\./, "");
            var leaf = parsed.pathname.replace(/\/$/, "").split("/").filter(Boolean).pop() || "";
            if (leaf && leaf !== "en" && leaf.length < 40) label += " / " + leaf.replace(/[-_]/g, " ");
          }
        } catch (e1) {}
        if (!label) label = String(ev.check || ev.kind || "source").replace(/_/g, " ");
        var note = clipWords(humanizeEvidence(ev) || "", 20);
        var link = ev.sourceUrl
          ? '<a href="' + esc(ev.sourceUrl) + '" target="_blank" rel="noopener noreferrer">' + esc(label) + "</a>"
          : "<span>" + esc(label) + "</span>";
        return (
          '<div class="evidence-card">' +
            '<span class="evidence-index">' + (i + 1) + "</span>" +
            '<div class="evidence-body">' + link +
              (note ? '<p class="evidence-note">' + esc(note) + "</p>" : "") +
            "</div>" +
          "</div>"
        );
      }).join("") + "</div>"
      : "";

    if ($("exhibits-host")) $("exhibits-host").innerHTML = "";
    var researchHost = $("research-host");
    if (researchHost) researchHost.innerHTML = "";

    var turns;
    if (data.conversationTurns && data.conversationTurns.length) {
      turns = ensureFollowupAssistantTurn(data);
    } else if (optimisticTurns && optimisticTurns.length) {
      turns = ensureFollowupAssistantTurn(
        Object.assign({}, data, { conversationTurns: optimisticTurns }),
        conversationPending ? "" : extractFollowupAnswer(data)
      );
    } else {
      turns = [];
    }
    // Never leave interim "writing the explanation" as a final assistant bubble
    if (!conversationPending) {
      turns = ensureFollowupAssistantTurn(
        Object.assign({}, data, { conversationTurns: turns }),
        extractFollowupAnswer(data)
      );
      var last = turns.length ? turns[turns.length - 1] : null;
      if (last && normalize(last.role) !== "user" && isInterimText(last.text)) {
        turns = turns.slice(0, -1);
      }
    }
    $("conversation-host").innerHTML = renderConversationHtml(turns, conversationPending);

    renderChipRows(data);
    renderStickyUrgent(data);
    // Reset opacity/visibility before every reveal so 2nd/3rd cases never stay ghosted
    CredaMotion.forceRevealVisible();
    if (!opts.skipReveal) {
      requestAnimationFrame(function () { CredaMotion.resultReveal(); });
    } else {
      CredaMotion.forceRevealVisible();
    }
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
        var answer = extractFollowupAnswer(data);
        if (!answer) answer = "Couldn't verify that yet — the ruling above still stands.";
        optimisticTurns = ensureFollowupAssistantTurn(
          Object.assign({}, data, {
            conversationTurns: (data.conversationTurns && data.conversationTurns.length)
              ? data.conversationTurns
              : optimisticTurns
          }),
          answer
        );
        data.conversationTurns = optimisticTurns;
        var fb = $("btn-followup");
        if (fb) { fb.disabled = false; fb.textContent = "Send"; }
        var fi = $("followup-input");
        if (fi) fi.disabled = false;
        document.body.classList.remove("ui-waiting");
        document.body.classList.add("ui-ready");
        // conversationPending must clear before this render so the conversation
        // block doesn't append a stale "checking…" bubble after the real answer.
        // followupPollMode stays true through the render so mergeFollowupSnapshot
        // still pins the board (stamp/headline/tiles) to the pre-follow-up baseline.
        conversationPending = false;
        renderResult(data);
        followupPollMode = false;
        optimisticTurns = [];
        return;
      }
      renderResult(data, { skipReveal: true, followupOnly: true });
      if (Date.now() - pollStartedAt > POLL_MAX_MS) {
        stopPolling();
        var timeoutMsg = "I couldn't verify that domain yet";
        var baseTurns = (data.conversationTurns && data.conversationTurns.length)
          ? data.conversationTurns.slice()
          : (optimisticTurns || []).slice();
        // Drop interim assistant stubs, then append honest timeout
        var lu = -1;
        for (var ti = baseTurns.length - 1; ti >= 0; ti--) {
          if (normalize(baseTurns[ti].role) === "user") { lu = ti; break; }
        }
        var cleaned = [];
        for (var tj = 0; tj < baseTurns.length; tj++) {
          if (tj > lu && normalize(baseTurns[tj].role) !== "user" && isInterimText(baseTurns[tj].text)) continue;
          cleaned.push(baseTurns[tj]);
        }
        var hasReal = false;
        for (var tk = lu + 1; tk < cleaned.length; tk++) {
          if (normalize(cleaned[tk].role) !== "user" && (cleaned[tk].text || "").trim() && !isInterimText(cleaned[tk].text)) {
            hasReal = true; break;
          }
        }
        if (!hasReal) cleaned.push({ role: "assistant", text: timeoutMsg });
        data.conversationTurns = cleaned;
        optimisticTurns = cleaned;
        var fb2 = $("btn-followup");
        if (fb2) { fb2.disabled = false; fb2.textContent = "Send"; }
        var fi2 = $("followup-input");
        if (fi2) fi2.disabled = false;
        document.body.classList.remove("ui-waiting");
        document.body.classList.add("ui-ready");
        showError("followup-error", { code: "POLL_TIMEOUT", message: timeoutMsg + " — prior ruling kept." });
        conversationPending = false;
        renderResult(data, { skipReveal: true });
        followupPollMode = false;
        optimisticTurns = [];
        return;
      }
      pollTimer = setTimeout(function () { pollOnce().catch(function () {}); }, POLL_MS);
      return;
    }
    if (isReady(data)) {
      if (WaitStoryboard.isRunning()) {
        WaitStoryboard.markReady(data);
        if (!readySince) readySince = Date.now();
        // Safety net: the storyboard should finish within ~2x its own dwell
        // window of becoming ready. If it hasn't (any unforeseen stall),
        // stop waiting on it and show the result directly.
        if (Date.now() - readySince > WaitStoryboard.MIN_MS * 2 + 1000) {
          WaitStoryboard.reset();
          stopPolling();
          showView("result");
          renderResult(data);
          readySince = 0;
          return;
        }
        renderWait(data);
        pollTimer = setTimeout(function () { pollOnce().catch(function () {}); }, POLL_MS);
        return;
      }
      readySince = 0;
      stopPolling();
      showView("result");
      renderResult(data);
      return;
    }
    readySince = 0;
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
      readySince = 0;
      showView("wait");
      if ($("live-exhibits")) $("live-exhibits").innerHTML = "";
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
    setIntakeBusy(true);
    try {
      var payload = buildPayload();
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
      setIntakeBusy(false);
    }
    // On success startPolling→showView("wait") keeps intake busy
  }

  async function sendFollowup(presetText) {
    showError("followup-error", "");
    var q = (presetText || $("followup-input").value || "").trim();
    if (!q) { showError("followup-error", "Type a question first.", { focusId: "followup-input" }); return; }
    if (!session.caseId || !session.token) { showError("followup-error", "No active case.", { onRetry: resetToIntake }); return; }
    $("btn-followup").disabled = true;
    $("btn-followup").textContent = "Waiting…";
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
    followupGraceStartedAt = 0;
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
      if (!conversationPending) {
        $("btn-followup").disabled = false;
        $("btn-followup").textContent = "Send";
      }
    }
  }

  function setHidden(el, hide) {
    if (el) el.classList.toggle("hidden", !!hide);
  }

  function toggleReportPanel(open, mode) {
    if (mode) reportMode = mode;
    var sheet = $("report-sheet");
    if (sheet) sheet.classList.toggle("hidden", !open);
    showError("report-error", "");
    var titleEl = $("report-sheet-title");
    var kicker = $("report-kicker");
    var lede = $("report-lede");
    var sendBtn = $("btn-report-send");
    var cancelBtn = $("btn-report-cancel");
    var textArea = $("report-text");
    var kind = $("report-kind");
    var company = $("report-company");
    var isLimits = reportMode === "limits";
    var isCompany = reportMode === "company";
    setHidden($("report-limits-body"), !isLimits);
    setHidden($("report-form-body"), isLimits);
    if (sendBtn) sendBtn.classList.toggle("hidden", isLimits);
    if (cancelBtn) cancelBtn.textContent = isLimits ? "Close" : "Cancel";
    if (isLimits) {
      if (kicker) kicker.textContent = "Coverage";
      if (titleEl) titleEl.textContent = "What Creda can check today";
      if (lede) lede.textContent = "Text-only today. Screenshots and PDFs need a vision path we have not turned on.";
    } else if (isCompany) {
      if (kicker) kicker.textContent = "Registry";
      if (titleEl) titleEl.textContent = "Request a company";
      if (lede) lede.textContent = "Ask Creda to add an employer or scam pattern to the approved registry. This does not change the live ruling.";
      if (textArea) textArea.placeholder = "Why should this employer or pattern be in coverage?";
      if (sendBtn) sendBtn.textContent = "Send request";
      if (kind) kind.value = "company_request";
    } else {
      if (kicker) kicker.textContent = "Incident";
      if (titleEl) titleEl.textContent = "Report a missed scam";
      if (lede) lede.textContent = "File what the current ruling missed. It goes to the tactic registry, not the live judge.";
      if (textArea) textArea.placeholder = "Paste the offer or describe what Creda missed.";
      if (sendBtn) sendBtn.textContent = "Send report";
      if (kind) kind.value = "missed_scam";
    }
    if (open && !isLimits) {
      var prefill = ($("offer-text").value || "").trim();
      if (!prefill && lastData) prefill = (lastData.offerText || lastData.headline || "").trim();
      if (!prefill && lastData) {
        prefill = [lastData.headline, lastData.verdict, (lastData.links || []).join("\n")].filter(Boolean).join("\n\n");
      }
      if (isCompany && lastData && lastData.employer && company && !(company.value || "").trim()) {
        company.value = lastData.employer;
      }
      if (prefill && textArea && !(textArea.value || "").trim()) textArea.value = prefill;
      var focusEl = isCompany && company ? company : textArea;
      if (focusEl) focusEl.focus();
    } else if (!open) {
      reportMode = "scam";
    }
  }

  async function submitReport() {
    if (reportMode === "limits") {
      toggleReportPanel(false);
      return;
    }
    var text = ($("report-text").value || "").trim();
    var company = ($("report-company") && $("report-company").value || "").trim();
    var kind = ($("report-kind") && $("report-kind").value || "").trim();
    var url = ($("report-url") && $("report-url").value || "").trim();
    var contact = ($("report-contact") && $("report-contact").value || "").trim();
    if (reportMode === "company" && !company && !text) {
      showError("report-error", "Name the employer or pattern to add.", { focusId: "report-company" });
      return;
    }
    if (reportMode !== "company" && !text) {
      showError("report-error", "Paste the scam message or describe what Creda missed.", { focusId: "report-text" });
      return;
    }
    $("btn-report-send").disabled = true;
    showError("report-error", "");
    try {
      var body = {
        reportText: text || company,
        companyName: company || undefined,
        reportKind: kind || undefined,
        sourceUrl: url || undefined,
        reportType: reportMode === "company" || kind === "company_request" ? "company_request" : "missed_scam",
        notes: reportMode === "company"
          ? "Creda UI company/pattern request."
          : "Creda UI report. User believes a scam was missed.",
        contactConsent: !!contact,
        contact: contact || undefined
      };
      if (session.caseId) body.linkedCaseId = session.caseId;
      if (lastData && lastData.verdict) body.linkedVerdict = lastData.verdict;
      await apiFetch("/reports/scam", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      var sentCompany = reportMode === "company" || kind === "company_request";
      toggleReportPanel(false);
      $("report-text").value = "";
      if ($("report-company")) $("report-company").value = "";
      if ($("report-url")) $("report-url").value = "";
      if ($("report-contact")) $("report-contact").value = "";
      if (sentCompany) {
        var companyBtn = $("btn-limits-company");
        var companyLabel = companyBtn && companyBtn.querySelector("span:last-child");
        if (companyLabel) companyLabel.textContent = "Request sent";
        setTimeout(function () {
          if (companyLabel) companyLabel.textContent = "Request company";
        }, 2500);
      } else {
        $("btn-report").textContent = "Report sent";
        var reportChip = $("btn-limits-report") && $("btn-limits-report").querySelector("span:last-child");
        if (reportChip) reportChip.textContent = "Report sent";
        setTimeout(function () {
          $("btn-report").textContent = "Report a missed scam";
          if (reportChip) reportChip.textContent = "Report scam";
        }, 2500);
      }
      reportMode = "scam";
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
    followupGraceStartedAt = 0;
    CredaStageMachine.reset();
    WaitStoryboard.reset();
    CredaMotion.stopStageLoop();
    lastActiveStage = -1;
    toggleReportPanel(false);
    reportMode = "scam";
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
    var clearBtn = $("btn-clear");
    if (clearBtn) clearBtn.addEventListener("click", clearComposer);
    $("btn-cancel-wait").addEventListener("click", resetToIntake);
    $("btn-new").addEventListener("click", resetToIntake);
    $("btn-followup").addEventListener("click", function () { sendFollowup(); });
    $("followup-input").addEventListener("keydown", function (e) {
      if (e.key === "Enter") sendFollowup();
    });
    $("btn-report").addEventListener("click", function () { toggleReportPanel(true, "scam"); });
    $("btn-report-cancel").addEventListener("click", function () { toggleReportPanel(false); });
    $("btn-report-send").addEventListener("click", submitReport);
    var limitsInfo = $("btn-limits-info");
    var limitsReport = $("btn-limits-report");
    var limitsCompany = $("btn-limits-company");
    if (limitsInfo) limitsInfo.addEventListener("click", function () { toggleReportPanel(true, "limits"); });
    if (limitsReport) limitsReport.addEventListener("click", function () { toggleReportPanel(true, "scam"); });
    if (limitsCompany) limitsCompany.addEventListener("click", function () { toggleReportPanel(true, "company"); });
    var sheet = $("report-sheet");
    if (sheet) {
      sheet.addEventListener("click", function (e) {
        if (e.target === sheet) toggleReportPanel(false);
      });
    }
    // Only resume a case when arriving via an explicit deep link (?case=&token=,
    // e.g. shared from Telegram). A plain reload/hard-refresh must always land
    // on a clean intake, not silently re-open whatever case was last open —
    // sessionStorage otherwise survives refreshes and traps people on stale
    // wait/result screens they meant to abandon.
    var arrivedViaDeepLink = bootstrapSessionFromUrl();
    if (arrivedViaDeepLink) {
      checkHealth().then(function () {
        if (session.caseId && session.token) resumeSession();
      }).catch(function () {
        if (session.caseId && session.token) resumeSession();
      });
    } else {
      session.caseId = null;
      session.token = null;
      try { sessionStorage.removeItem("creda_case"); } catch (e) {}
      checkHealth().catch(function () {});
    }
  }

  window.CredaPreviewResult = function (data) {
    showView("result");
    renderResult(data || {});
  };

  try {
    wire();
  } catch (err) {
    console.error("creda wire failed", err);
  }

})();
