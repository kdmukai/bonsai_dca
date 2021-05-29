import threading
from main import app, timer_thread
from models import create_tables
from webui import WebUI


# Creates sqlite DB tables if necessary
create_tables()

x = threading.Thread(target=timer_thread, daemon=True)
x.start()

ui = WebUI(app, debug=True)
ui.run()
