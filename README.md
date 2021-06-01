# Bonsai DCA

_Buy many small stacks<br/>
Don't try to time the market<br/>
Pure serenity_


## Local development
Run as a local dev server and start the background daemon:
```
cd python
export FLASK_ENV=development && python server.py --daemon
```


Run as a windowed GUI with (daemon is automatically started by JS script):
```
cd js
npm start
```
_note: you have to build the app locally first (see below) for this `npm` call to work._


## Building the app

### Mac build
```
cd python
pyinstaller bonsai_dca_server.spec
pyinstaller bonsai_dca_daemon.spec

cd ../js
npm run dist
```
