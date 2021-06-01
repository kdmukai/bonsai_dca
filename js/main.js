const { app, BrowserWindow, ipcMain } = require('electron')
const { spawn, exec } = require('child_process');
const path = require('path')
const fetch = require("node-fetch");

const serverURL = "http://127.0.0.1:61712";
const bonsaiServerPath = path.join(__dirname, "bonsai_dca_server")
const bonsaiDaemonPath = path.join(__dirname, "bonsai_dca_daemon")

console.log(bonsaiServerPath);

let bonsaiServerProcess
let bonsaiDaemonProcess
let mainWindow

// Flag the app was quitted
let quitted = false

let webPreferences = {
  worldSafeExecuteJavaScript: true,
  contextIsolation: true,
  // preload: path.join(__dirname, 'preload.js')
}


function createWindow () {
  mainWindow = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences
  })

  mainWindow.webContents.on('new-window', function(e, url) {
    console.log("webContents.on called!");
    console.log(url);
    e.preventDefault();
    shell.openExternal(url);
  });

}


app.commandLine.appendSwitch('ignore-certificate-errors');


let platformName = ''
switch (process.platform) {
  case 'darwin':
    platformName = 'osx'
    break
  case 'win32':
    platformName = 'win64'
    break
  case 'linux':
    platformName = 'x86_64-linux-gnu'
    break
}


function loadUrlWhenReady() {
  fetch(serverURL)
    .then(
      function(response) {
        if (response.status == 200) {
          console.log("Loading url");
          mainWindow.loadURL(serverURL);
          return
        } else {
          console.log(response);
          return loadUrlWhenReady();
        }
      }
    )
    .catch(function(err) {
      if (err.code == 'ECONNREFUSED' | err.code == 'EINVAL') {
        return loadUrlWhenReady();
      } else {
        console.log(err);
      }
    });
}


app.whenReady().then(() => {

  try {
    console.log("Creating the window")
    createWindow()

    app.on('activate', function () {
      if (BrowserWindow.getAllWindows().length === 0) createWindow()
    })

    // Start the flask server process
    console.log("Starting the server")
    bonsaiServerProcess = spawn(bonsaiServerPath, [], { stdio: ['pipe', process.stdout, process.stderr] });

    // LAME KLUDGE: Can't get the commented out section below to detect when Flask is ready
    //  to serve so instead we just wait 8 seconds. In order to try the stdout detection
    //  method again, must edit `spawn` call above to swap `process.stdout` with `'pipe'`.
    // setTimeout(() => {
    //   console.log("Loading url");
    //   mainWindow.loadURL(serverURL);
    // }, 10000);

    loadUrlWhenReady();

    // bonsaiServerProcess.stdout.on('data', (data) => {
    //   // console.log(data.toString());
    //   // console.log(data.toString().includes("Running on"));
    //   if(data.toString().includes("Running on")) {
    //     console.log("Loading url");
    //     mainWindow.loadURL(serverURL);
    //   }
    // });
    // bonsaiServerProcess.stderr.on('data', (data) => {
    //   // https://stackoverflow.com/questions/20792427/why-is-my-node-child-process-that-i-created-via-spawn-hanging
    //   // needed so bonsai won't get stuck
    //   console.log(data.toString());
    // });

    // Start the background daemon thread
    console.log("Starting the daemon")
    bonsaiDaemonProcess = spawn(bonsaiDaemonPath, [], { stdio: ['pipe', process.stdout, process.stderr] });
  } catch (e) {
    console.log(e);
  }
})


app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') {
    quitBonsai()
    app.quit()
  }
})


app.on('before-quit', () => {
  if (!quitted) {
    quitted = true
    quitBonsai()
  
    if (mainWindow && !mainWindow.isDestroyed()) {
       mainWindow.destroy()
       mainWindow = null
    }
  }
})


ipcMain.on('request-mainprocess-action', (event, arg) => {
  switch (arg.message) {
    case 'quit-app':
      quitBonsai()
      app.quit()
      break
  }
});


function quitBonsai() {
  quitProcess(bonsaiDaemonProcess, "bonsai_dca_daemon")
  quitProcess(bonsaiServerProcess, "bonsai_dca_server")
}


function quitProcess(proc, exe_name) {
  if (proc) {
    try {
      if (platformName == 'win64') {
        exec('taskkill /F /T /PID ' + proc.pid);
        exec('taskkill /IM ' + exe_name + '.exe ');
        process.kill(-proc.pid)
      }
      proc.kill('SIGINT')
    } catch (e) {
      console.log('Process quit warning: ' + e)
    }
  }
}
