import { app, BrowserWindow, ipcMain, dialog } from "electron";
import * as path from "path";
import * as cp from "child_process";

let mainWindow: BrowserWindow | null = null;
let backendProcess: cp.ChildProcess | null = null;

const BACKEND_PORT = 18900;
const isDev = process.env.NODE_ENV === "development" || !app.isPackaged;

function getBackendPath(): string {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, "backend.exe");
  }
  return path.join(__dirname, "../../backend/server.py");
}

function startBackend() {
  const backendPath = getBackendPath();

  if (app.isPackaged) {
    backendProcess = cp.spawn(backendPath, [], {
      stdio: "pipe",
      env: { ...process.env },
    });
  } else {
    backendProcess = cp.spawn("python", ["-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", String(BACKEND_PORT)], {
      cwd: path.join(__dirname, "../../backend"),
      stdio: "pipe",
    });
  }

  backendProcess.stdout?.on("data", (data) => {
    console.log(`Backend: ${data}`);
  });

  backendProcess.stderr?.on("data", (data) => {
    console.log(`Backend: ${data}`);
  });

  backendProcess.on("error", (err) => {
    console.error("Backend failed to start:", err);
  });

  backendProcess.on("exit", (code) => {
    console.log(`Backend exited with code ${code}`);
    backendProcess = null;
  });
}

function stopBackend() {
  if (backendProcess) {
    backendProcess.kill();
    backendProcess = null;
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 700,
    title: "Devin Clone",
    backgroundColor: "#0a0a0f",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
    frame: false,
    titleBarStyle: "hiddenInset",
  });

  if (isDev) {
    mainWindow.loadURL("http://localhost:5173");
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, "../dist/index.html"));
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  startBackend();
  setTimeout(createWindow, 2000);

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  stopBackend();
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  stopBackend();
});

ipcMain.handle("select-folder", async () => {
  const result = await dialog.showOpenDialog(mainWindow!, {
    properties: ["openDirectory"],
    title: "Select Workspace Folder",
  });
  if (result.canceled) return null;
  return result.filePaths[0];
});

ipcMain.handle("select-file", async () => {
  const result = await dialog.showOpenDialog(mainWindow!, {
    properties: ["openFile"],
    title: "Select File",
  });
  if (result.canceled) return null;
  return result.filePaths[0];
});

ipcMain.on("window-minimize", () => mainWindow?.minimize());
ipcMain.on("window-maximize", () => {
  if (mainWindow?.isMaximized()) {
    mainWindow.unmaximize();
  } else {
    mainWindow?.maximize();
  }
});
ipcMain.on("window-close", () => mainWindow?.close());
