# bonsai_dca



## Local development
Run as a standard Flask server with:
```
python src/main.py
```

Run as a windowed GUI with:
```
python src/gui.py
```


## Building the app

### Mac build
```
brew install qt5
brew link qt5
```

```
cd src
pyinstaller --onefile --add-data 'templates:templates' --name bonsai_dca_server server.py
pyinstaller --onefile --name bonsai_dca_daemon daemon.py
```
