let cameraStream = null;

async function startCamera() {
  const video = document.getElementById("camera");
  if (!video) return;
  try {
    if (cameraStream) {
      cameraStream.getTracks().forEach(track => track.stop());
    }
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: { ideal: "environment" },
        width: { ideal: 1280 },
        height: { ideal: 720 },
        zoom: 1
      },
      audio: false
    });
    video.srcObject = cameraStream;
    await video.play();
  } catch (error) {
    alert("Camera could not be opened. Please allow camera permission and use HTTPS.");
    console.error(error);
  }
}

function canvasToFile(canvas, filename, quality = 0.82) {
  return new Promise(resolve => {
    canvas.toBlob(blob => {
      if (!blob) return resolve(null);
      resolve(new File([blob], filename, { type: "image/jpeg" }));
    }, "image/jpeg", quality);
  });
}

async function captureCamera() {
  const video = document.getElementById("camera");
  const canvas = document.getElementById("snapshot");
  const input = document.getElementById("imageInput");
  if (!video || !canvas || !input || !video.srcObject) {
    alert("Open the camera first.");
    return;
  }

  const maxSide = 1600;
  const scale = Math.min(1, maxSide / Math.max(video.videoWidth, video.videoHeight));
  canvas.width = Math.max(1, Math.round(video.videoWidth * scale));
  canvas.height = Math.max(1, Math.round(video.videoHeight * scale));
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  const file = await canvasToFile(canvas, "camera-capture.jpg");
  if (!file) return;
  const transfer = new DataTransfer();
  transfer.items.add(file);
  input.files = transfer.files;
  alert("Photo captured. Click Identify Waste.");
}

async function compressImageFile(file) {
  if (!file || !file.type.startsWith("image/") || file.size <= 2 * 1024 * 1024) {
    return file;
  }

  const bitmap = await createImageBitmap(file);
  const maxSide = 1600;
  const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(bitmap.width * scale));
  canvas.height = Math.max(1, Math.round(bitmap.height * scale));
  canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();

  let quality = 0.82;
  let compressed = await canvasToFile(canvas, "waste-image.jpg", quality);

  while (compressed && compressed.size > 2 * 1024 * 1024 && quality > 0.55) {
    quality -= 0.07;
    compressed = await canvasToFile(canvas, "waste-image.jpg", quality);
  }
  return compressed || file;
}

document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("imageInput");
  if (!input) return;

  input.addEventListener("change", async () => {
    const file = input.files && input.files[0];
    if (!file) return;
    try {
      const optimized = await compressImageFile(file);
      if (optimized && optimized !== file) {
        const transfer = new DataTransfer();
        transfer.items.add(optimized);
        input.files = transfer.files;
      }
    } catch (error) {
      console.warn("Image compression skipped:", error);
    }
  });
});
