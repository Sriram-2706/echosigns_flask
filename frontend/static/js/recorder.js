// Minimal live recording helper using MediaRecorder -> POST to backend
// NOTE: This buffers to .webm on server and does not auto-transcribe here.
// Use the "Upload" mode for WAV with VOSK, or add ffmpeg server-side to transcode.

let mediaRecorder;
let chunks = [];
let recId = null;

async function startLive(lang = "en") {
  chunks = [];
  const res = await fetch("/api/asr/live/start", { method: "POST" });
  const data = await res.json();
  recId = data.rec_id;

  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });

  mediaRecorder.ondataavailable = async (e) => {
    if (e.data && e.data.size > 0) {
      const buf = await e.data.arrayBuffer();
      await fetch(`/api/asr/live/append/${recId}`, {
        method: "POST",
        headers: { "Content-Type": "application/octet-stream" },
        body: buf
      });
    }
  };

  mediaRecorder.start(500); // send chunks every 500ms
  document.getElementById("live-status").innerText = "Recording…";
}

async function stopLive(lang = "en") {
  return new Promise((resolve) => {
    mediaRecorder.onstop = async () => {
      const res = await fetch(`/api/asr/live/stop/${recId}?lang=${lang}`, { method: "POST" });
      const data = await res.json();
      document.getElementById("live-status").innerText = data.note || "Stopped.";
      if (data.text) {
        document.getElementById("recognizedText").value = data.text;
      }
      resolve();
    };
    mediaRecorder.stop();
  });
}
