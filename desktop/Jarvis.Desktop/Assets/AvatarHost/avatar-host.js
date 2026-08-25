const nameEl = document.getElementById("name");
const stateEl = document.getElementById("state");
const stateBadgeEl = document.getElementById("stateBadge");
const metaEl = document.getElementById("meta");
const viewer = document.getElementById("viewer");
const fallback = document.getElementById("fallback");
const fallbackText = document.getElementById("fallbackText");
const attributionEl = document.getElementById("attribution");

let currentManifest = null;
let currentAudio = null;
let currentAudioContext = null;
let currentAnalyser = null;
let amplitudeTimer = null;

nameEl.textContent = "JARVIS AVATAR";
metaEl.textContent = "Runtime initialized";
attributionEl.textContent = "";

const setFallback = (text) => {
  fallback.classList.remove("hidden");
  applyState("unavailable", "Fallback renderer mode");
  fallbackText.textContent = text;
  postMessageToHost("avatar.error", { code: "RUNTIME_FALLBACK", message: text });
};

const setBadgeClass = (name) => {
  stateBadgeEl.classList.remove("state-ready", "state-thinking", "state-speaking", "state-unavailable");
  stateBadgeEl.classList.add(name);
};

const applyState = (state, detail) => {
  const normalized = (state || "ready").toString().toLowerCase();
  const map = {
    loading: { label: "LOADING", text: "Loading", badge: "state-thinking" },
    thinking: { label: "THINKING", text: "Thinking", badge: "state-thinking" },
    speaking: { label: "SPEAKING", text: "Speaking", badge: "state-speaking" },
    ready: { label: "READY", text: "Ready for commands", badge: "state-ready" },
    unavailable: { label: "OFFLINE", text: "Unavailable", badge: "state-unavailable" }
  };
  const resolved = map[normalized] || map.ready;
  stateBadgeEl.textContent = resolved.label;
  stateEl.textContent = resolved.text;
  setBadgeClass(resolved.badge);
  if (detail && typeof detail === "string" && detail.trim().length > 0) {
    metaEl.textContent = detail;
  }
};

const loadLocalScript = (relativePath) => new Promise((resolve, reject) => {
  const script = document.createElement("script");
  script.type = "module";
  script.src = relativePath;
  script.onload = () => resolve();
  script.onerror = () => reject(new Error(`Failed to load ${relativePath}`));
  document.head.appendChild(script);
});

const postMessageToHost = (type, payload) => {
  if (!window.chrome || !window.chrome.webview) {
    return;
  }
  window.chrome.webview.postMessage({
    version: 1,
    type,
    requestId: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}`,
    payload
  });
};

const stopSpeech = () => {
  if (amplitudeTimer) {
    clearInterval(amplitudeTimer);
    amplitudeTimer = null;
  }
  if (currentAudio) {
    currentAudio.pause();
    currentAudio.src = "";
    currentAudio = null;
  }
  if (currentAudioContext) {
    currentAudioContext.close().catch(() => {});
    currentAudioContext = null;
  }
  currentAnalyser = null;
};

const startAmplitudeTracking = () => {
  if (!currentAnalyser) {
    return;
  }

  const bins = new Uint8Array(currentAnalyser.frequencyBinCount);
  amplitudeTimer = setInterval(() => {
    if (!currentAnalyser) {
      return;
    }
    currentAnalyser.getByteTimeDomainData(bins);
    let sum = 0;
    for (let i = 0; i < bins.length; i++) {
      const centered = (bins[i] - 128) / 128;
      sum += Math.abs(centered);
    }
    const amplitude = sum / bins.length;
    const intensity = Math.min(1, Math.max(0, amplitude * 3));
    viewer.style.filter = `brightness(${1 + intensity * 0.18})`;
  }, 60);
};

const ensureModelViewerRuntime = async () => {
  if (window.customElements && window.customElements.get("model-viewer")) {
    return;
  }
  await loadLocalScript("./vendor/model-viewer.min.js");
};

const loadAvatarFromManifest = async (manifestUrl, selectedAvatarId) => {
  const response = await fetch(manifestUrl, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Avatar manifest request failed: ${response.status}`);
  }
  const manifest = await response.json();
  currentManifest = manifest;
  const format = String(manifest.format || "unknown").toLowerCase();
  const modelName = manifest.model || manifest.modelFile;
  if (!modelName) {
    throw new Error("Manifest does not define model/modelFile.");
  }

  if (format === "vrm") {
    throw new Error("VRM runtime is not bundled yet. Add a local VRM adapter under Assets/AvatarHost/vendor/.");
  }
  if (format !== "glb" && format !== "gltf") {
    throw new Error(`Unsupported avatar format '${format}'.`);
  }

  await ensureModelViewerRuntime();

  const modelUrl = new URL(modelName, manifestUrl).toString();
  viewer.src = "";
  viewer.src = modelUrl;
  nameEl.textContent = String(manifest.displayName || selectedAvatarId || "Jarvis Avatar").toUpperCase();
  attributionEl.textContent = manifest.attribution ? `Attribution: ${manifest.attribution}` : "";
  metaEl.textContent = `Model format: ${format}`;
  fallback.classList.add("hidden");

  postMessageToHost("avatar.ready", {
    avatarId: selectedAvatarId || manifest.id || "unknown",
    animations: Object.values(manifest.animationNames || {}),
    morphTargets: Object.values(manifest.morphTargets || {})
  });
  applyState("ready", "Avatar loaded");
};

const handleEnvelope = async (envelope) => {
  if (!envelope || envelope.version !== 1 || !envelope.type) {
    return;
  }

  const payload = envelope.payload || {};

  try {
    switch (envelope.type) {
      case "avatar.load": {
        const manifestUrl = payload.manifestUrl;
        const selectedAvatarId = payload.selectedAvatarId;
        if (!manifestUrl) {
          throw new Error("avatar.load payload is missing manifestUrl.");
        }
        applyState("loading", "Loading avatar manifest");
        await loadAvatarFromManifest(manifestUrl, selectedAvatarId);
        break;
      }
      case "avatar.state": {
        applyState(payload.state || "ready", payload.detail || "");
        break;
      }
      case "avatar.expression": {
        const expression = payload.expression || "neutral";
        const intensity = Number(payload.intensity || 1);
        metaEl.textContent = `Expression: ${expression} (${intensity.toFixed(2)})`;
        break;
      }
      case "avatar.speech.start": {
        const audioUrl = payload.audioUrl;
        if (!audioUrl) {
          throw new Error("avatar.speech.start payload missing audioUrl.");
        }
        stopSpeech();
        currentAudio = new Audio(audioUrl);
        currentAudio.crossOrigin = "anonymous";
        applyState("speaking", "Speech playback started");
        currentAudioContext = new (window.AudioContext || window.webkitAudioContext)();
        const source = currentAudioContext.createMediaElementSource(currentAudio);
        currentAnalyser = currentAudioContext.createAnalyser();
        currentAnalyser.fftSize = 256;
        source.connect(currentAnalyser);
        currentAnalyser.connect(currentAudioContext.destination);
        startAmplitudeTracking();
        currentAudio.onended = () => {
          stopSpeech();
          viewer.style.filter = "none";
          applyState("ready", "Speech playback complete");
        };
        await currentAudio.play();
        break;
      }
      case "avatar.speech.stop": {
        stopSpeech();
        viewer.style.filter = "none";
        applyState("ready", "Speech cancelled");
        break;
      }
      default:
        postMessageToHost("avatar.error", {
          code: "UNKNOWN_MESSAGE_TYPE",
          message: `Unknown message type '${envelope.type}'.`
        });
        break;
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown runtime failure";
    setFallback(message);
  }
};

if (window.chrome && window.chrome.webview) {
  window.chrome.webview.addEventListener("message", (event) => {
    handleEnvelope(event.data);
  });
}

postMessageToHost("avatar.ready", {
  avatarId: currentManifest?.id || "unloaded",
  animations: [],
  morphTargets: []
});
