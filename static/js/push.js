/* Push notification opt-in: registers the service worker and subscribes. */
(function () {
  const btn = document.getElementById("pushToggle");
  if (!btn || !("serviceWorker" in navigator) || !("PushManager" in window)) {
    if (btn) btn.style.display = "none";
    return;
  }

  function urlBase64ToUint8Array(base64String) {
    const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
    const raw = atob(base64);
    return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
  }

  async function refresh() {
    const reg = await navigator.serviceWorker.getRegistration();
    const sub = reg && (await reg.pushManager.getSubscription());
    btn.textContent = sub ? "🔕" : "🔔";
    btn.title = sub ? "Notifications on — click to turn off" : "Turn on notifications";
  }

  async function enable() {
    const permission = await Notification.requestPermission();
    if (permission !== "granted") return;
    const reg = await navigator.serviceWorker.register("/static/sw.js");
    const { publicKey } = await (await fetch("/push/vapid-public-key")).json();
    const sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(publicKey),
    });
    await fetch("/push/subscribe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(sub),
    });
  }

  async function disable() {
    const reg = await navigator.serviceWorker.getRegistration();
    const sub = reg && (await reg.pushManager.getSubscription());
    if (sub) {
      await fetch("/push/unsubscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ endpoint: sub.endpoint }),
      });
      await sub.unsubscribe();
    }
  }

  btn.addEventListener("click", async () => {
    const reg = await navigator.serviceWorker.getRegistration();
    const sub = reg && (await reg.pushManager.getSubscription());
    try {
      if (sub) await disable(); else await enable();
    } catch (e) {
      console.error("Push toggle failed", e);
    }
    refresh();
  });

  refresh();
})();
