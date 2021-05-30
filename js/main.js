const { app, BrowserWindow } = require('electron')
const { spawn, exec } = require('child_process');
const fetch = require("node-fetch");

const serverURL = "http://127.0.0.1:61712";
const bonsaiServerPath = "./../python/dist/bonsai_dca_server"
const bonsaiDaemonPath = "./../python/dist/bonsai_dca_daemon"
let bonsaiServerProcess
let bonsaiDaemonProcess
let mainWindow

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


app.whenReady().then(() => {

  console.log("Creating the window")
  createWindow()

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })

  // Start the flask server process
  console.log("Starting the server")
  bonsaiServerProcess = spawn(bonsaiServerPath, [], { stdio: ['pipe', process.stdout, process.stderr] });

  setTimeout(() => {
    console.log("Loading url");
    mainWindow.loadURL(serverURL);
  }, 8000);


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
})

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit()
})

