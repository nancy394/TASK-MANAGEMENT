// Plays a different sound for each kind of notification.
(function () {
  var base = document.body.getAttribute("data-sounds") || "/static/sounds/";
  function enabled() { return localStorage.getItem("tf_sound") !== "off"; }
  function volume() { var v = parseFloat(localStorage.getItem("tf_volume")); return isNaN(v) ? 0.7 : v; }

  window.TFSound = {
    play: function (name, force) {
      if (!force && !enabled()) return;
      try {
        var a = new Audio(base + name + ".wav");
        a.volume = volume();
        var p = a.play();
        if (p && p.catch) p.catch(function () {});
      } catch (e) {}
    },
    enabled: enabled, volume: volume,
    setEnabled: function (on) { localStorage.setItem("tf_sound", on ? "on" : "off"); },
    setVolume: function (v) { localStorage.setItem("tf_volume", String(v)); }
  };

  document.addEventListener("DOMContentLoaded", function () {
    // Sound for page messages (saved, completed, warning, error ...)
    var first = document.querySelector(".alert[data-sound]");
    if (first) TFSound.play(first.getAttribute("data-sound"));
    // Auto-hide messages
    document.querySelectorAll(".alert").forEach(function (el) {
      setTimeout(function () { el.classList.add("fade"); }, 5000);
    });
    // Sound toggle in the top bar
    var btn = document.getElementById("soundToggle");
    if (btn) {
      var paint = function () { btn.textContent = enabled() ? "🔔" : "🔕"; btn.title = enabled() ? "Sounds on" : "Sounds off"; };
      paint();
      btn.addEventListener("click", function () { TFSound.setEnabled(!enabled()); paint(); if (enabled()) TFSound.play("info"); });
    }
  });
})();
