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
let blinkTimer = null;
let speakingTimer = null;
let eyePulseTimer = null;
let speechCueTimers = [];
let morphTargetNames = {};
let animationNames = {};

nameEl.textContent = "A.E.G.I.S.-9";
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

const setRuntimeStateClass = (state) => {
  for (const className of Array.from(document.body.classList)) {
    if (className.startsWith("runtime-")) {
      document.body.classList.remove(className);
    }
  }
  document.body.classList.add(`runtime-${state}`);
};

const applyState = (state, detail) => {
  const normalized = (state || "ready").toString().toLowerCase();
  const map = {
    loading: { label: "LOADING", text: "Loading", badge: "state-thinking" },
    thinking: { label: "THINKING", text: "Thinking", badge: "state-thinking" },
    speaking: { label: "SPEAKING", text: "Speaking", badge: "state-speaking" },
    listening: { label: "LISTENING", text: "Listening", badge: "state-ready" },
    idle: { label: "READY", text: "Ready for commands", badge: "state-ready" },
    error: { label: "FAULT", text: "Attention required", badge: "state-unavailable" },
    offline: { label: "OFFLINE", text: "System link offline", badge: "state-unavailable" },
    ready: { label: "READY", text: "Ready for commands", badge: "state-ready" },
    unavailable: { label: "OFFLINE", text: "Unavailable", badge: "state-unavailable" }
  };
  const resolved = map[normalized] || map.ready;
  setRuntimeStateClass(normalized);
  playAnimation(resolved.animation || animationNames[normalized] || animationNames.idle, normalized === "thinking" || normalized === "speaking");
  stateBadgeEl.textContent = resolved.label;
  stateEl.textContent = resolved.text;
  setBadgeClass(resolved.badge);
  if (normalized === "speaking") {
    startSpeakingMotion();
    startEyePulse();
  } else if (normalized !== "loading") {
    stopSpeakingMotion();
    stopEyePulse();
  }
  if (detail && typeof detail === "string" && detail.trim().length > 0) {
    metaEl.textContent = detail;
  }
};

const playAnimation = (name, loop = false) => {
  const modelViewer = viewer;
  if (!name || !modelViewer) {
    return;
  }
  modelViewer.animationName = name;
  modelViewer.currentTime = 0;
  if (typeof modelViewer.play === "function") {
    modelViewer.play({ repetitions: loop ? Infinity : 1 });
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
  for (const timer of speechCueTimers) {
    clearTimeout(timer);
  }
  speechCueTimers = [];
  document.documentElement.style.setProperty("--speech-energy", "0");
  stopSpeakingMotion();
  stopEyePulse();
};

const scheduleSpeechCues = (cues) => {
  if (!Array.isArray(cues)) {
    return;
  }
  for (const cue of cues) {
    const target = morphTargetNames[cue.viseme] || cue.viseme;
    const delay = Math.max(0, Number(cue.timeMs) || 0);
    const weight = Math.max(0, Math.min(1, Number(cue.weight) || 0));
    speechCueTimers.push(setTimeout(() => setMorphTarget(target, weight), delay));
  }
};

const forEachMorphMesh = (callback) => {
  const scene = viewer?.model?.scene;
  if (!scene || typeof scene.traverse !== "function") {
    return;
  }
  scene.traverse((node) => {
    if (node.morphTargetDictionary && node.morphTargetInfluences) {
      callback(node);
    }
  });
};

const setMorphTarget = (name, value) => {
  if (!name) {
    return;
  }
  forEachMorphMesh((mesh) => {
    const index = mesh.morphTargetDictionary[name];
    if (typeof index === "number") {
      mesh.morphTargetInfluences[index] = Math.max(0, Math.min(1, value));
    }
  });
};

const clearMorphTarget = (name) => setMorphTarget(name, 0);

const blink = () => {
  const left = morphTargetNames.blinkLeft;
  const right = morphTargetNames.blinkRight;
  const combined = morphTargetNames.blink;
  if (combined) {
    setMorphTarget(combined, 1);
    setTimeout(() => clearMorphTarget(combined), 130);
    return;
  }
  setMorphTarget(left, 1);
  setMorphTarget(right, 1);
  setTimeout(() => {
    clearMorphTarget(left);
    clearMorphTarget(right);
  }, 130);
};

const scheduleBlink = () => {
  if (blinkTimer) {
    clearTimeout(blinkTimer);
  }
  blinkTimer = setTimeout(() => {
    blink();
    scheduleBlink();
  }, 3500 + Math.random() * 3500);
};

const stopSpeakingMotion = () => {
  if (speakingTimer) {
    clearInterval(speakingTimer);
    speakingTimer = null;
  }
  clearMorphTarget(morphTargetNames.jawOpen);
  clearMorphTarget(morphTargetNames.mouthOpen);
};

const startSpeakingMotion = () => {
  stopSpeakingMotion();
  const jaw = morphTargetNames.jawOpen || morphTargetNames.mouthOpen;
  if (!jaw) {
    return;
  }
  speakingTimer = setInterval(() => {
    const intensity = currentAnalyser ? 0.25 + Math.random() * 0.55 : 0.45;
    setMorphTarget(jaw, intensity);
  }, 90);
};

const setEyeEmission = (red, green, blue) => {
  const isEyeMaterial = (material) => String(material?.name || "").toLowerCase().includes("jarvis_eyes");
  for (const material of Array.from(viewer?.model?.materials || []).filter(isEyeMaterial)) {
    if (typeof material.setEmissiveFactor === "function") {
      material.setEmissiveFactor([red, green, blue]);
    }
  }

  const scene = viewer?.model?.scene;
  if (!scene || typeof scene.traverse !== "function") return;
  scene.traverse((node) => {
    const materials = Array.isArray(node.material) ? node.material : [node.material];
    for (const material of materials.filter(isEyeMaterial)) {
      if (material?.emissive?.setRGB) {
        material.emissive.setRGB(red, green, blue);
        material.emissiveIntensity = 1.15;
        material.needsUpdate = true;
      }
    }
  });
};

const stopEyePulse = () => {
  if (eyePulseTimer) {
    clearInterval(eyePulseTimer);
    eyePulseTimer = null;
  }
  setEyeEmission(1.0, 0.55, 0.0);
};

const startEyePulse = () => {
  stopEyePulse();
  const started = performance.now();
  eyePulseTimer = setInterval(() => {
    const blend = (Math.sin((performance.now() - started) / 260) + 1) / 2;
    setEyeEmission(1.0, 0.55 * (1 - blend) + 0.03 * blend, 0.005);
  }, 45);
};

const applyExpression = (expression, intensity) => {
  const amount = Math.max(0, Math.min(1, Number(intensity) || 1));
  if (expression === "happy" || expression === "smile") {
    setMorphTarget(morphTargetNames.mouthSmile, amount);
    setMorphTarget(morphTargetNames.mouthSmileLeft, amount);
    setMorphTarget(morphTargetNames.mouthSmileRight, amount);
  } else if (expression === "neutral") {
    clearMorphTarget(morphTargetNames.mouthSmile);
    clearMorphTarget(morphTargetNames.mouthSmileLeft);
    clearMorphTarget(morphTargetNames.mouthSmileRight);
  }
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
    const modelViewer = viewer;
    if (modelViewer) {
      document.documentElement.style.setProperty("--speech-energy", intensity.toFixed(3));
    }
  }, 60);
};

const ensureModelViewerRuntime = async () => {
  if (window.customElements && window.customElements.get("model-viewer")) {
    return;
  }
  await loadLocalScript("./vendor/model-viewer.min.js");
};

const loadAvatarFromManifest = async (manifestUrl, selectedAvatarId, compact = false) => {
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
  const modelViewer = viewer;
  if (!modelViewer) {
    throw new Error("Wolforge model viewer element is unavailable.");
  }
  modelViewer.src = "";
  modelViewer.src = modelUrl;
  modelViewer.cameraControls = !compact;
  modelViewer.interactionPrompt = compact ? "none" : "auto";
  modelViewer.fieldOfView = compact ? "24deg" : "28deg";
  modelViewer.minFieldOfView = "16deg";
  modelViewer.maxFieldOfView = "36deg";
  modelViewer.exposure = 0.82;
  modelViewer.shadowIntensity = 0.18;
  if (Array.isArray(manifest.cameraTarget) && manifest.cameraTarget.length === 3) {
    const target = manifest.cameraTarget;
    modelViewer.cameraTarget = target.map((value) => `${Number(value) || 0}m`).join(" ");
  }
  if (manifest.cameraOrbit) {
    modelViewer.cameraOrbit = String(manifest.cameraOrbit);
  }
  modelViewer.addEventListener("error", () => {
    setFallback("The avatar model could not be rendered by the local WebView2 runtime.");
  }, { once: true });
  morphTargetNames = manifest.morphTargets || {};
  animationNames = manifest.animationNames || {};
  const availableAnimations = Object.values(animationNames);
  if (availableAnimations.length > 0) {
    modelViewer.animationName = availableAnimations[0];
  }
  modelViewer.addEventListener("load", () => {
    scheduleBlink();
  }, { once: true });
  nameEl.textContent = String(manifest.displayName || selectedAvatarId || "A.E.G.I.S.-9").toUpperCase();
  attributionEl.textContent = manifest.attribution ? `Attribution: ${manifest.attribution}` : "";
  metaEl.textContent = `Model format: ${format}`;
  fallback.classList.add("hidden");

  postMessageToHost("avatar.ready", {
    avatarId: selectedAvatarId || manifest.id || "unknown",
    animations: availableAnimations,
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
        document.body.classList.toggle("compact", payload.compact === true);
        if (!manifestUrl) {
          throw new Error("avatar.load payload is missing manifestUrl.");
        }
        applyState("loading", "Loading avatar manifest");
        await loadAvatarFromManifest(manifestUrl, selectedAvatarId, payload.compact === true);
        break;
      }
      case "avatar.state": {
        applyState(payload.state || "ready", payload.detail || "");
        break;
      }
      case "avatar.expression": {
        const expression = payload.expression || "neutral";
        const intensity = Number(payload.intensity || 1);
        applyExpression(expression, intensity);
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
        startSpeakingMotion();
        scheduleSpeechCues(payload.cues);
        currentAudio.onended = () => {
          stopSpeech();
          applyState("ready", "Speech playback complete");
        };
        await currentAudio.play();
        break;
      }
      case "avatar.speech.stop": {
        stopSpeech();
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
