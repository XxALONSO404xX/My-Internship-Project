const { app, BrowserWindow, ipcMain, Menu, Tray } = require('electron');
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');
const url = require('url');

// Improved development detection
const isDev = process.env.NODE_ENV === 'development';
console.log('Development mode:', isDev);

let mainWindow;
let tray;

// Simple encryption for token storage
// In a production app, use a more robust solution like keytar or electron-store with proper encryption
const ENCRYPTION_KEY = 'iot-platform-secure-storage-key'; // In production, use a secure generated key
const IV_LENGTH = 16; // For AES, this is always 16 bytes

function encrypt(text) {
  const iv = crypto.randomBytes(IV_LENGTH);
  const cipher = crypto.createCipheriv('aes-256-cbc', Buffer.from(ENCRYPTION_KEY), iv);
  let encrypted = cipher.update(text);
  encrypted = Buffer.concat([encrypted, cipher.final()]);
  return iv.toString('hex') + ':' + encrypted.toString('hex');
}

function decrypt(text) {
  const textParts = text.split(':');
  const iv = Buffer.from(textParts.shift(), 'hex');
  const encryptedText = Buffer.from(textParts.join(':'), 'hex');
  const decipher = crypto.createDecipheriv('aes-256-cbc', Buffer.from(ENCRYPTION_KEY), iv);
  let decrypted = decipher.update(encryptedText);
  decrypted = Buffer.concat([decrypted, decipher.final()]);
  return decrypted.toString();
}

// Token storage
const tokenStoragePath = path.join(app.getPath('userData'), 'auth-token.dat');
let memoryToken = null; // For non-persistent storage

// Load persisted token on startup
function loadPersistedToken() {
  try {
    if (fs.existsSync(tokenStoragePath)) {
      const encryptedToken = fs.readFileSync(tokenStoragePath, 'utf8');
      return decrypt(encryptedToken);
    }
  } catch (error) {
    console.error('Error loading persisted token:', error);
    // If token file is corrupted, delete it
    try { fs.unlinkSync(tokenStoragePath); } catch (e) {}
  }
  return null;
}

function createWindow() {
  // Enable detailed logging
  console.log('Creating main window in environment:', process.env.NODE_ENV);
  console.log('Current working directory:', process.cwd());
  
  // Try to locate an icon file
  let iconPath = null;
  const possibleIcons = [
    path.join(__dirname, '../public/icon.png'),
    path.join(__dirname, '../public/icon.svg'),
    path.join(__dirname, '../src/assets/icon.png'),
    path.join(__dirname, '../src/assets/icon.svg')
  ];
  
  for (const icon of possibleIcons) {
    try {
      if (fs.existsSync(icon)) {
        iconPath = icon;
        console.log('Found icon at:', icon);
        break;
      }
    } catch (e) {
      console.error('Error checking icon:', e);
    }
  }
  
  if (!iconPath) {
    console.log('No icon found, using default icon');
  }

  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    icon: iconPath,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
      // Allow insecure content in development only
      webSecurity: !isDev
    }
  })
  
  // Add debugging event listeners
  mainWindow.webContents.on('did-start-loading', () => {
    console.log('Page started loading');
  });

  // Add debugging event listeners
  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    console.error('Failed to load:', errorCode, errorDescription);
  });

  mainWindow.webContents.on('did-finish-load', () => {
    console.log('Page finished loading');
  });

  mainWindow.webContents.on('dom-ready', () => {
    console.log('DOM ready');
  });

  mainWindow.webContents.on('console-message', (event, level, message, line, sourceId) => {
    console.log(`Renderer Console [${level}]:`, message);
  });

  // Load the app
  if (isDev) {
    // Try to connect to Vite dev server
    const tryLoadDevServer = async () => {
      // First check if we have a specified URL in environment variables
      const envServerUrl = process.env.VITE_DEV_SERVER_URL;
      
      if (envServerUrl) {
        console.log(`Using specified Vite server URL from environment: ${envServerUrl}`);
        try {
          await mainWindow.loadURL(envServerUrl);
          console.log(`Successfully connected to Vite dev server at ${envServerUrl}`);
          return true;
        } catch (err) {
          console.error(`Failed to connect to specified Vite server at ${envServerUrl}:`, err.message);
          // Fall through to port scanning if the env URL fails
        }
      }
      
      // If no env URL or it failed, try common Vite ports in sequence
      const ports = [5173, 5174, 5175, 5176, 5177];
      
      for (const port of ports) {
        const url = `http://localhost:${port}`;
        console.log(`Attempting to connect to Vite dev server at ${url}`);
        
        try {
          // Try to load the URL
          await mainWindow.loadURL(url);
          console.log(`Successfully connected to Vite dev server at ${url}`);
          return true; // Success
        } catch (err) {
          console.log(`Failed to connect to ${url}:`, err.message);
          // Continue to next port
        }
      }
      
      // If we get here, all attempts failed
      console.error('Failed to connect to any Vite dev server port');
      return false;
    };
    
    // Try to connect to dev server
    tryLoadDevServer().then(success => {
      if (success) {
        // Open DevTools on successful connection
        mainWindow.webContents.openDevTools();
      } else {
        // Show error page if all connection attempts failed
        mainWindow.webContents.loadFile(path.join(__dirname, '../public/error.html'));
      }
    });
  } else {
    // In production mode, load from built files
    const indexPath = path.join(__dirname, '../dist/index.html');
    console.log('Loading from production build at', indexPath);
    mainWindow.loadFile(indexPath);
  }

  // Skip system tray for development testing
  console.log('Skipping system tray creation for development testing');
  /* Uncomment this when icon issues are resolved
  if (iconPath) {
    try {
      tray = new Tray(iconPath);
      const contextMenu = Menu.buildFromTemplate([
        { 
          label: 'Show App', 
          click: () => mainWindow.show() 
        },
        { 
          label: 'Quit', 
          click: () => app.quit() 
        },
      ]);
      tray.setToolTip('IoT Platform');
      tray.setContextMenu(contextMenu);
      
      tray.on('click', () => {
        mainWindow.isVisible() ? mainWindow.hide() : mainWindow.show();
      });
    } catch (e) {
      console.log('Failed to create tray icon:', e);
    }
  }
  */

  // For development testing, allow normal window closing instead of minimizing to tray
  // Comment this back in when tray functionality is restored
  /*
  mainWindow.on('close', (event) => {
    event.preventDefault();
    mainWindow.hide();
    return false;
  });
  */
}

// Setup all IPC handlers
function setupIpcHandlers() {
  // IPC handlers for API communication
  ipcMain.handle('api:request', async (event, args) => {
    try {
      // Extract parameters from args object to match preload.js structure
      const { url, method, body, headers } = args;
      console.log('API Request DETAILS:', { 
        url, 
        method, 
        body: JSON.stringify(body),
        headers 
      });
      
      // Add authorization header if we have a token
      const token = memoryToken || loadPersistedToken();
      const authHeaders = token ? { 'Authorization': `Bearer ${token}` } : {};
      console.log('Token available:', !!token);
      
      // Parse the URL to get hostname, port, and path
      const urlObj = new URL(url);
      
      // Force IPv4 for localhost connections to avoid IPv6 issues
      let hostname = urlObj.hostname;
      if (hostname === 'localhost' || hostname === '::1') {
        hostname = '127.0.0.1';
        console.log('Converting localhost/::1 to IPv4 address 127.0.0.1');
      }
      
      // Prepare the request options for http module
      const requestOptions = {
        hostname: hostname,
        port: urlObj.port || (urlObj.protocol === 'https:' ? 443 : 80),
        path: `${urlObj.pathname}${urlObj.search}`,
        method: method,
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders,
          ...headers
        }
      };
      
      console.log('Full request options:', JSON.stringify(requestOptions));
      
      // Use http or https module based on protocol
      const httpModule = urlObj.protocol === 'https:' ? require('https') : require('http');
      
      // Return a new Promise to handle the async HTTP request
      return new Promise((resolve, reject) => {
        const req = httpModule.request(requestOptions, (res) => {
          let responseData = '';
          
          // Collect data chunks
          res.on('data', (chunk) => {
            responseData += chunk;
          });
          
          // Process complete response
          res.on('end', () => {
            console.log('Raw API Response:', responseData);
            
            // Get headers
            const headers = res.headers;
            
            // Try to parse the response as JSON
            let data;
            try {
              data = responseData ? JSON.parse(responseData) : {};
            } catch (parseError) {
              console.error('Failed to parse response as JSON:', parseError);
              data = { parseError: true, message: 'Failed to parse response' };
            }
            
            console.log('API Response DETAILS:', { 
              status: res.statusCode, 
              ok: res.statusCode >= 200 && res.statusCode < 300,
              headers: headers,
              data: JSON.stringify(data)
            });
            
            // Return formatted response
            resolve({ 
              ok: res.statusCode >= 200 && res.statusCode < 300, 
              status: res.statusCode, 
              data,
              headers
            });
          });
        });
        
        // Handle request errors
        req.on('error', (error) => {
          console.error('API request error DETAILS:', error);
          resolve({ ok: false, error: error.message, stack: error.stack });
        });
        
        // Send request body if present
        if (body) {
          req.write(JSON.stringify(body));
        }
        
        // End the request
        req.end();
      });
    } catch (error) {
      console.error('API request setup error DETAILS:', error);
      return { ok: false, error: error.message, stack: error.stack };
    }
  });

  // Store auth token securely
  ipcMain.handle('auth:storeToken', async (event, options) => {
    try {
      // Extract parameters from options object to match preload.js structure
      const { token, persistent } = options;
      console.log('Storing auth token, persistent:', persistent);
      
      if (persistent) {
        // Store encrypted token to file system for 'remember me' functionality
        const encryptedToken = encrypt(token);
        fs.writeFileSync(tokenStoragePath, encryptedToken);
      } else {
        // Store in memory only for session-only auth
        memoryToken = token;
        
        // Make sure there's no persisted token
        if (fs.existsSync(tokenStoragePath)) {
          fs.unlinkSync(tokenStoragePath);
        }
      }
      
      return { success: true };
    } catch (error) {
      console.error('Error storing token:', error);
      return { success: false, error: error.message };
    }
  });

  // Check if app has an auth token (either in memory or persistent)
  ipcMain.handle('auth:hasToken', async () => {
    const persistentToken = loadPersistedToken();
    return !!memoryToken || !!persistentToken;
  });

  // Get the auth token (either from memory or persistent storage)
  ipcMain.handle('auth:getToken', async () => {
    return memoryToken || loadPersistedToken();
  });

  // Clear auth token (both memory and persistent)
  ipcMain.handle('auth:clearToken', async () => {
    try {
      // Clear memory token
      memoryToken = null;
      
      // Remove persistent token if it exists
      if (fs.existsSync(tokenStoragePath)) {
        fs.unlinkSync(tokenStoragePath);
      }
      
      return { success: true };
    } catch (error) {
      console.error('Error clearing token:', error);
      return { success: false, error: error.message };
    }
  });

  // Window control handlers
  ipcMain.on('window:minimize', () => {
    if (mainWindow) mainWindow.minimize();
  });
  
  ipcMain.on('window:maximize', () => {
    if (mainWindow) {
      if (mainWindow.isMaximized()) {
        mainWindow.unmaximize();
      } else {
        mainWindow.maximize();
      }
    }
  });
  
  ipcMain.on('window:close', () => {
    if (mainWindow) mainWindow.close();
  });
  
  // App restart handler
  ipcMain.on('app:restart', () => {
    console.log('Restarting application...');
    app.relaunch();
    app.exit();
  });
}

app.whenReady().then(() => {
  createWindow();

  // Set up IPC handlers
  setupIpcHandlers();

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit();
});
