const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // API communication
  apiRequest: (args) => ipcRenderer.invoke('api:request', args),
  
  // Auth token management with 'remember me' support
  storeAuthToken: (options) => ipcRenderer.invoke('auth:storeToken', options),
  hasAuthToken: () => ipcRenderer.invoke('auth:hasToken'),
  getAuthToken: () => ipcRenderer.invoke('auth:getToken'),
  clearAuthToken: () => ipcRenderer.invoke('auth:clearToken'),
  
  // System functionality
  minimize: () => ipcRenderer.send('window:minimize'),
  maximize: () => ipcRenderer.send('window:maximize'),
  close: () => ipcRenderer.send('window:close'),
  
  // App management
  restartApp: () => ipcRenderer.send('app:restart')
});
