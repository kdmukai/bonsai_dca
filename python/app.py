
if __name__ == "__main__":
    from server import app
    from models import create_tables

    # Creates sqlite DB tables if necessary
    create_tables()

    app.run(port=61712)
