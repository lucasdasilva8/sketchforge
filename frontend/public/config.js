// Production API URL — only used when not running the Vite dev server
if (
  window.location.hostname !== "localhost" &&
  window.location.hostname !== "127.0.0.1" &&
  window.location.port !== "5173"
) {
  window.SKETCHFORGE_API = "https://sketchforge-api.onrender.com";
}
