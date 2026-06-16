const { contextBridge, ipcRenderer } = require('electron');
const path = require('path');

let supabaseConfig = null;
try {
  supabaseConfig = require(path.join(__dirname, 'SupabaseConfig.js'));
} catch (err) {
  console.error('SupabaseConfig.js not found — copy SupabaseConfig.js.template and fill in values.');
}

contextBridge.exposeInMainWorld('supabaseConfig', supabaseConfig);

contextBridge.exposeInMainWorld('electron', {
  startServer: ({ vaultPath, userId }) => ipcRenderer.invoke('start-server', { vaultPath, userId }),
  stopServer: () => ipcRenderer.invoke('stop-server'),
  pickVault: () => ipcRenderer.invoke('pick-vault'),
  openExternal: (url) => ipcRenderer.invoke('open-external', url),
  startOAuth: (authUrl) => ipcRenderer.invoke('start-oauth', authUrl),
  keychain: {
    get: (account) => ipcRenderer.invoke('keychain-get', account),
    set: (account, value) => ipcRenderer.invoke('keychain-set', { account, value }),
    delete: (account) => ipcRenderer.invoke('keychain-delete', account),
  },
  loadMainUI: (url) => ipcRenderer.invoke('load-main-ui', url),
  loadOnboarding: () => ipcRenderer.invoke('load-onboarding'),
  onAuthCallback: (handler) => {
    ipcRenderer.removeAllListeners('auth-callback');
    ipcRenderer.on('auth-callback', (_e, url) => handler(url));
  },
  onSignOut: (handler) => {
    ipcRenderer.removeAllListeners('sign-out');
    ipcRenderer.on('sign-out', () => handler());
  },
});
