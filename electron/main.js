const { app, BrowserWindow, ipcMain, shell, dialog, Menu } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');
const net = require('net');
const fs = require('fs');

const PROTOCOL = 'brainsquared';
const isDev = !app.isPackaged;

// File-based secret storage (avoids keychain ACL prompts on every dev rebuild —
// same workaround as UserDefaultsAuthStorage on the Swift side).
function secretsFile() { return path.join(app.getPath('userData'), 'secrets.json'); }
function loadSecrets() {
  try { return JSON.parse(fs.readFileSync(secretsFile(), 'utf8')); } catch { return {}; }
}
function saveSecrets(obj) {
  fs.mkdirSync(path.dirname(secretsFile()), { recursive: true });
  fs.writeFileSync(secretsFile(), JSON.stringify(obj, null, 2), { mode: 0o600 });
}
function secretsGet(account) { return loadSecrets()[account] || null; }
function secretsSet(account, value) { const s = loadSecrets(); s[account] = value; saveSecrets(s); }
function secretsDelete(account) { const s = loadSecrets(); delete s[account]; saveSecrets(s); }

let mainWindow = null;
let serverProcess = null;
let serverPort = 3000;
let pendingCallbackUrl = null;
let pendingSignOut = false;

// ── Custom URL scheme registration (brainsquared://) ─────────────────────────
if (isDev && process.argv.length >= 2) {
  app.setAsDefaultProtocolClient(PROTOCOL, process.execPath, [path.resolve(process.argv[1])]);
} else {
  app.setAsDefaultProtocolClient(PROTOCOL);
}

// Single-instance: brainsquared:// URL on macOS comes via open-url; on
// Windows/Linux it'd come as argv to a second instance. Route to the running
// instance instead of starting a fresh one.
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
  return;
}

app.on('second-instance', (_event, argv) => {
  const url = argv.find((arg) => arg.startsWith(`${PROTOCOL}://`));
  if (url) routeAuthCallback(url);
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.focus();
  }
});

app.on('open-url', (event, url) => {
  event.preventDefault();
  console.log('[auth] open-url received:', url);
  routeAuthCallback(url);
});

function routeAuthCallback(url) {
  console.log('[auth] routing callback to renderer:', url);
  if (mainWindow && mainWindow.webContents && !mainWindow.webContents.isLoading()) {
    mainWindow.webContents.send('auth-callback', url);
  } else {
    pendingCallbackUrl = url; // window not ready yet; deliver once it is
    console.log('[auth] window not ready; queued callback');
  }
}

// ── Python server lifecycle ──────────────────────────────────────────────────
async function findOpenPort(start) {
  for (let p = start; p < start + 20; p++) {
    const ok = await new Promise((resolve) => {
      const srv = net.createServer();
      srv.unref();
      srv.on('error', () => resolve(false));
      srv.listen(p, '127.0.0.1', () => srv.close(() => resolve(true)));
    });
    if (ok) return p;
  }
  throw new Error(`No port available starting at ${start}`);
}

function brainServerBinary() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'BrainServer', 'BrainServer');
  }
  return path.join(__dirname, 'resources', 'BrainServer', 'BrainServer');
}

async function startServer({ vaultPath, userId }) {
  if (serverProcess) stopServer();

  const binPath = brainServerBinary();
  if (!fs.existsSync(binPath)) {
    throw new Error(`BrainServer binary not found at ${binPath}. Run pyinstaller brain.spec from the repo root.`);
  }

  serverPort = await findOpenPort(3000);

  const env = { ...process.env };
  env.PATH = ['/opt/homebrew/bin', '/usr/local/bin', '/usr/bin', env.PATH || ''].join(':');
  if (userId) env.BRAIN_USER_ID = userId;

  const anthropicKey = secretsGet('anthropic_api_key');
  if (anthropicKey) env.ANTHROPIC_API_KEY = anthropicKey;
  const openaiKey = secretsGet('openai_api_key');
  if (openaiKey) env.OPENAI_API_KEY = openaiKey;

  serverProcess = spawn(binPath, ['--vault', vaultPath, '--port', String(serverPort)], { env });
  serverProcess.stdout.on('data', (d) => process.stdout.write(`[srv] ${d}`));
  serverProcess.stderr.on('data', (d) => process.stderr.write(`[srv] ${d}`));
  serverProcess.on('exit', (code) => {
    console.log(`[srv] exited with code ${code}`);
    serverProcess = null;
  });

  // Poll readiness
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    if (await ping(serverPort)) return `http://127.0.0.1:${serverPort}`;
    await sleep(300);
  }
  throw new Error('BrainServer failed to become ready within 30s');
}

function stopServer() {
  if (serverProcess) {
    try { serverProcess.kill('SIGTERM'); } catch (_) {}
    serverProcess = null;
  }
}

function ping(port) {
  return new Promise((resolve) => {
    const req = http.get(`http://127.0.0.1:${port}/`, (res) => {
      resolve(res.statusCode === 200);
      res.resume();
    });
    req.on('error', () => resolve(false));
    req.setTimeout(800, () => { req.destroy(); resolve(false); });
  });
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ── Window ───────────────────────────────────────────────────────────────────
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 900,
    minHeight: 650,
    titleBarStyle: 'hiddenInset',
    backgroundColor: '#FAFAF7',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));

  if (isDev) mainWindow.webContents.openDevTools({ mode: 'detach' });

  mainWindow.webContents.on('did-finish-load', () => {
    if (pendingSignOut) {
      pendingSignOut = false;
      mainWindow.webContents.send('sign-out');
    }
    if (pendingCallbackUrl) {
      mainWindow.webContents.send('auth-callback', pendingCallbackUrl);
      pendingCallbackUrl = null;
    }
  });

  // External links (everything not on 127.0.0.1) opens in default browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (!url.startsWith('http://127.0.0.1')) {
      shell.openExternal(url);
      return { action: 'deny' };
    }
    return { action: 'allow' };
  });
}

// ── IPC: bridge between renderer and main ────────────────────────────────────
ipcMain.handle('start-server', async (_e, payload) => {
  const url = await startServer(payload);
  return { url, port: serverPort };
});

ipcMain.handle('stop-server', async () => { stopServer(); return true; });

ipcMain.handle('open-external', async (_e, url) => { await shell.openExternal(url); return true; });

// Open Google/Supabase OAuth inside an Electron window. Reliably captures
// the brainsquared:// redirect via will-redirect, no OS protocol registration
// dance required.
ipcMain.handle('start-oauth', async (_e, authUrl) => {
  return new Promise((resolve, reject) => {
    const authWin = new BrowserWindow({
      width: 500,
      height: 700,
      modal: true,
      parent: mainWindow,
      title: 'Sign in to brain²',
      webPreferences: { nodeIntegration: false, contextIsolation: true, partition: 'auth' },
    });
    let settled = false;
    const finish = (fn) => { if (!settled) { settled = true; try { authWin.close(); } catch {} fn(); } };

    const inspect = (event, url) => {
      if (url && url.startsWith(`${PROTOCOL}://`)) {
        event.preventDefault();
        console.log('[auth] captured oauth redirect:', url);
        finish(() => resolve(url));
      }
    };

    authWin.webContents.on('will-redirect', inspect);
    authWin.webContents.on('will-navigate', inspect);
    // Some browsers/Supabase emit a navigation that fails to a custom scheme
    authWin.webContents.on('did-fail-load', (_e, _ec, _ed, validatedURL) => {
      if (validatedURL && validatedURL.startsWith(`${PROTOCOL}://`)) {
        finish(() => resolve(validatedURL));
      }
    });
    authWin.on('closed', () => { if (!settled) { settled = true; reject(new Error('Sign-in window closed before completing.')); } });

    authWin.loadURL(authUrl);
  });
});

ipcMain.handle('pick-vault', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory', 'createDirectory'],
    buttonLabel: 'Select',
    message: 'Choose a folder for your brain² vault.',
  });
  return result.canceled ? null : result.filePaths[0];
});

ipcMain.handle('keychain-get', async (_e, account) => secretsGet(account));
ipcMain.handle('keychain-set', async (_e, { account, value }) => secretsSet(account, value));
ipcMain.handle('keychain-delete', async (_e, account) => secretsDelete(account));

ipcMain.handle('load-main-ui', async (_e, url) => {
  if (mainWindow) mainWindow.loadURL(url);
});

ipcMain.handle('load-onboarding', async () => {
  if (mainWindow) mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));
});

// ── App lifecycle ────────────────────────────────────────────────────────────
app.whenReady().then(() => {
  createWindow();
  buildMenu();
});

app.on('window-all-closed', () => {
  stopServer();
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

app.on('before-quit', () => stopServer());

function buildMenu() {
  const isMac = process.platform === 'darwin';
  const template = [
    ...(isMac ? [{
      label: app.name,
      submenu: [
        { role: 'about' },
        { type: 'separator' },
        {
          label: 'Sign Out',
          accelerator: 'Cmd+Shift+Q',
          click: () => {
            stopServer();
            if (mainWindow) {
              pendingSignOut = true;
              mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));
            }
          },
        },
        { type: 'separator' },
        { role: 'quit' },
      ],
    }] : []),
    { role: 'editMenu' },
    { role: 'viewMenu' },
    { role: 'windowMenu' },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}
