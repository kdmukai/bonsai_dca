import datetime
import logging
import os
import sys
import threading
import time

from decimal import Decimal
from flask import (
    Flask,
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
)

from blueprints.credentials import credentials_routes
from blueprints.orders import orders_routes
from models import APICredential, DCASchedule, Order
from exchanges.gemini import GeminiExchange, GeminiRequestException



template_folder = "_templates"
static_folder = "_static"
if getattr(sys, 'frozen', False):
    # We're running from PyInstaller's internal temp dir and have to point folder refs
    #   accordingly.
    template_folder = os.path.join(sys._MEIPASS, template_folder)
    static_folder = os.path.join(sys._MEIPASS, static_folder)

app = Flask(__name__,
            static_url_path='',
            static_folder=static_folder,
            template_folder=template_folder)

# app.config["EXPLAIN_TEMPLATE_LOADING"] = True

app.register_blueprint(credentials_routes, url_prefix="/credentials")
app.register_blueprint(orders_routes, url_prefix="/orders")



@app.route("/")
def home():
    credentials = APICredential.select().order_by(APICredential.exchange)
    return render_template('index.html', credentials=credentials)



@app.route("/schedule/create/<credential_id>", methods=('GET', 'POST'))
def create_schedule(credential_id):
    credential = APICredential.get(id=credential_id)

    if request.method == 'POST':
        market_name = request.form['market_name']
        order_side = request.form['order_side'].lower()
        amount = Decimal(request.form['amount'])
        amount_currency = request.form['amount_currency']
        repeat_duration = Decimal(request.form['repeat_duration'])
        repeat_timescale = request.form['repeat_timescale']

        schedule = DCASchedule.create(
            credential=credential,
            market_name=market_name,
            order_side=order_side,
            amount=amount,
            amount_currency=amount_currency,
            repeat_duration=repeat_duration,
            repeat_timescale=repeat_timescale
        )

        return redirect(url_for('credentials.view_credential', credential_id=credential.id))

    return render_template(
        'create_schedule.html',
        credential=credential,
        DAYS=DCASchedule.DAYS,
        HOURS=DCASchedule.HOURS,
        MINUTES=DCASchedule.MINUTES,
    )



@app.route("/schedule/update/<schedule_id>", methods=('GET', 'POST'))
def update_schedule(credential_id):
    schedule = DCASchedule.get(id=schedule_id)

    # Don't actually update a schedule if it has existing Orders in order to preserve
    #   historical lookups.
    # Instead set is_active = False and create a new schedule.

    return render_template(
        'update_schedule.html',
        credential=credential,
        DAYS=DCASchedule.DAYS,
        HOURS=DCASchedule.HOURS,
        MINUTES=DCASchedule.MINUTES,
    )



@app.route("/schedule/pause/<schedule_id>", methods=['POST'])
def pause_schedule(schedule_id):
    schedule = DCASchedule.get(id=schedule_id)
    schedule.is_active = True;
    schedule.is_paused = True;
    schedule.save()

    return redirect(url_for('credentials.view_credential', credential_id=schedule.credential.id))



@app.route("/schedule/unpause/<schedule_id>", methods=['POST'])
def unpause_schedule(schedule_id):
    schedule = DCASchedule.get(id=schedule_id)
    schedule.is_paused = False;
    schedule.save()

    return redirect(url_for('credentials.view_credential', credential_id=schedule.credential.id))



@app.route("/schedule/delete/<schedule_id>", methods=('POST',))
def delete_schedule(schedule_id):
    schedule = DCASchedule.get(id=schedule_id)

    if request.method == 'POST':
        credential_id = schedule.credential.id
        schedule.delete_instance()

        return redirect(url_for('credentials.view_credential', credential_id=credential_id))



if __name__ == "__main__":
    import argparse
    import werkzeug
    from models import create_tables

    parser = argparse.ArgumentParser(
        description="""
            Bonsai DCA - local dev server
        """,
        formatter_class=argparse.RawTextHelpFormatter
    )

    # options
    parser.add_argument('-d', '--daemon',
                        action="store_true",
                        default=False,
                        dest="start_daemon",
                        help="Start the background daemon")

    args = parser.parse_args()
    start_daemon = args.start_daemon

    # Creates sqlite DB tables if necessary
    create_tables()

    if start_daemon:
        # Start the schedule runner thread
        # Prevent duplicates from being created by hot reloads
        if not werkzeug.serving.is_running_from_reloader():
            from daemon import timer_thread
            x = threading.Thread(target=timer_thread, daemon=True)
            x.start()

    app.run(port=61712)
