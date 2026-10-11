// Focus timer with optional voice recording.
(function () {
  var root = document.getElementById("focus");
  if (!root) return;
  var $ = function (id) { return document.getElementById(id); };
  var timeEl = $("time"), ring = $("ring"), minutesEl = $("minutes"), msg = $("focusMsg");
  var startBtn = $("startBtn"), pauseBtn = $("pauseBtn"), stopBtn = $("stopBtn");
  var CIRC = 2 * Math.PI * 54;
  ring.style.strokeDasharray = CIRC;

  var mode = "focus", total = 25 * 60, remaining = total, elapsed = 0, timer = null, running = false, started = false;
  var recorder = null, chunks = [], stream = null, recStart = 0, recTimer = null;

  function fmt(s) { var m = Math.floor(s / 60), r = s % 60; return m + ":" + (r < 10 ? "0" : "") + r; }
  function paint() {
    timeEl.textContent = fmt(remaining);
    ring.style.strokeDashoffset = CIRC * (1 - remaining / total);
    document.title = (running ? fmt(remaining) + " · " : "") + "Focus Timer · TaskFlow";
  }
  function setMinutes(m) {
    m = Math.max(1, Math.min(240, parseInt(m, 10) || 25));
    total = remaining = m * 60; elapsed = 0; paint();
  }

  document.querySelectorAll(".mode").forEach(function (b) {
    b.addEventListener("click", function () {
      if (started) return;
      document.querySelectorAll(".mode").forEach(function (x) { x.classList.remove("active"); });
      b.classList.add("active"); mode = b.dataset.mode;
      minutesEl.value = b.dataset.min; setMinutes(b.dataset.min);
    });
  });
  minutesEl.addEventListener("change", function () { if (!started) setMinutes(minutesEl.value); });

  function startRecording() {
    if (!navigator.mediaDevices || !window.MediaRecorder) {
      msg.textContent = "Voice recording is not supported in this browser."; TFSound.play("warning"); return Promise.resolve();
    }
    return navigator.mediaDevices.getUserMedia({ audio: true }).then(function (s) {
      stream = s; chunks = [];
      recorder = new MediaRecorder(s);
      recorder.ondataavailable = function (e) { if (e.data.size) chunks.push(e.data); };
      recorder.start();
      recStart = Date.now(); $("recBadge").hidden = false;
      recTimer = setInterval(function () { $("recTime").textContent = fmt(Math.floor((Date.now() - recStart) / 1000)); }, 500);
    }).catch(function () {
      msg.textContent = "Microphone permission denied — timer runs without recording."; TFSound.play("warning");
    });
  }
  function stopRecording() {
    clearInterval(recTimer); $("recBadge").hidden = true;
    return new Promise(function (resolve) {
      if (!recorder || recorder.state === "inactive") return resolve(null);
      recorder.onstop = function () {
        if (stream) stream.getTracks().forEach(function (t) { t.stop(); });
        resolve(chunks.length ? new Blob(chunks, { type: recorder.mimeType || "audio/webm" }) : null);
        recorder = null;
      };
      recorder.stop();
    });
  }

  function tick() {
    remaining -= 1; elapsed += 1; paint();
    if (remaining <= 0) finish(true);
  }

  startBtn.addEventListener("click", function () {
    var go = function () {
      running = true; timer = setInterval(tick, 1000);
      startBtn.disabled = true; pauseBtn.disabled = false; stopBtn.disabled = false; minutesEl.disabled = true;
      msg.textContent = mode === "focus" ? "Stay focused! 💪" : "Enjoy your break ☕";
    };
    if (!started) {
      started = true; TFSound.play("focus_start");
      if ($("recordToggle").checked) startRecording().then(go); else go();
    } else {
      if (recorder && recorder.state === "paused") recorder.resume();
      go();
    }
  });
  pauseBtn.addEventListener("click", function () {
    clearInterval(timer); running = false;
    if (recorder && recorder.state === "recording") recorder.pause();
    startBtn.disabled = false; startBtn.textContent = "▶ Resume"; pauseBtn.disabled = true;
    msg.textContent = "Paused."; TFSound.play("info"); paint();
  });
  stopBtn.addEventListener("click", function () { finish(false); });

  function finish(completed) {
    clearInterval(timer); running = false;
    startBtn.disabled = true; pauseBtn.disabled = true; stopBtn.disabled = true;
    TFSound.play(completed ? (mode === "focus" ? "focus_end" : "break_end") : "warning");
    if (completed && "Notification" in window && Notification.permission === "granted") {
      new Notification(mode === "focus" ? "Focus session complete!" : "Break is over — back to work!");
    }
    msg.textContent = "Saving session…";
    stopRecording().then(function (blob) {
      var fd = new FormData();
      fd.append("mode", mode);
      fd.append("planned_minutes", Math.round(total / 60));
      fd.append("actual_seconds", elapsed);
      fd.append("completed", completed ? "1" : "0");
      fd.append("task_id", $("task").value);
      fd.append("note", $("note").value);
      if (blob) fd.append("audio", blob, "recording.webm");
      return fetch(root.dataset.recordUrl, { method: "POST", body: fd, credentials: "same-origin" });
    }).then(function (r) {
      if (!r.ok) throw new Error();
      msg.textContent = "Session saved ✔"; TFSound.play("success");
      setTimeout(function () { location.reload(); }, 1200);
    }).catch(function () {
      msg.textContent = "Could not save the session."; TFSound.play("danger");
      startBtn.disabled = false;
    });
  }

  // Sound settings panel
  var soundOn = $("soundOn"), vol = $("volume");
  soundOn.checked = TFSound.enabled(); vol.value = TFSound.volume();
  soundOn.addEventListener("change", function () { TFSound.setEnabled(soundOn.checked); });
  vol.addEventListener("input", function () { TFSound.setVolume(vol.value); });
  vol.addEventListener("change", function () { TFSound.play("info", true); });
  document.querySelectorAll("[data-preview]").forEach(function (b) {
    b.addEventListener("click", function () { TFSound.play(b.dataset.preview, true); });
  });
  if ("Notification" in window && Notification.permission === "default") {
    startBtn.addEventListener("click", function () { Notification.requestPermission(); }, { once: true });
  }
  paint();
})();
