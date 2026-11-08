import { Electrobun, BrowserWindow } from "electrobun";

const app = new Electrobun();

app.on("ready", () => {
  const win = new BrowserWindow({
    title: "Helios Router",
    width: 1280,
    height: 820,
    // In dev: point at Vite HMR dev server.
    // In prod: point at built dist/index.html.
    url: process.env.NODE_ENV === "production"
      ? "file://views/dashboard/index.html"
      : "http://localhost:5173",
  });

  win.show();
});

app.start();
