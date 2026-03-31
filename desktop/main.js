const { app, BrowserWindow, dialog } = require('electron');
const path = require('path');
const { spawn, exec } = require('child_process');
const isDev = !app.isPackaged;
const waitOn = require('wait-on');

let mainWindow;
let pythonProcess;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    title: "AI CHUSEN | MATRIX MONITORING SYSTEM",
    icon: path.join(__dirname, 'assets/icon.png'),
    backgroundColor: '#010801',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  // Start Streamlit Backend
  const pythonBin = isDev 
    ? path.join(__dirname, 'backend/py_env/bin/python3')
    : path.join(__dirname, '../backend/py_env/bin/python3');
  
  const scriptPath = 'app_ui.py';
  const backendFolder = isDev
    ? path.join(__dirname, 'backend')
    : path.join(__dirname, '../backend');

  console.log(`Starting Matrix Backend using ${pythonBin} in ${backendFolder}...`);
  
  // Use spawn to launch streamlit in detached mode
  pythonProcess = spawn(pythonBin, ['-m', 'streamlit', 'run', scriptPath, '--server.port', '8501', '--server.headless', 'true'], {
    cwd: backendFolder,
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
    detached: true // Allow killing the whole process group
  });

  pythonProcess.stdout.on('data', (data) => console.log(`[Streamlit] ${data}`));
  pythonProcess.stderr.on('data', (data) => console.log(`[Streamlit Error] ${data}`));

  // Wait for server to be ready
  const opts = { resources: ['http://localhost:8501'], timeout: 30000 };

  waitOn(opts).then(() => {
    mainWindow.loadURL('http://localhost:8501');
  }).catch((err) => {
    dialog.showErrorBox("MATRIX_LINK_FAILURE", "Backend engine failed to respond.");
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.on('ready', createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
  if (pythonProcess && pythonProcess.pid) {
    try {
      // Kill the entire process group
      process.kill(-pythonProcess.pid, 'SIGINT');
    } catch (e) {
      pythonProcess.kill();
    }
  }
});
