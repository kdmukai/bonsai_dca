import datetime
import logging
import threading
import time

from flask import (
    Flask,
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
)

from decimal import Decimal

from models import APICredential, DCASchedule, Order
from exchanges.gemini import GeminiExchange


app = Flask(__name__)


@app.route("/")
def home():
    credentials = APICredential.select().order_by(APICredential.exchange)
    return render_template('index.html', credentials=credentials)



@app.route("/credential/create", methods=('GET', 'POST'))
def create_credential():
    if request.method == 'POST':
        exchange = request.form['exchange']
        client_key = request.form['client_key']
        client_secret = request.form['client_secret']

        credential = APICredential.create(
            exchange=exchange,
            client_key=client_key,
            client_secret=client_secret
        )
        return redirect(url_for('home'))

    return render_template('create_credential.html')



@app.route("/credential/<credential_id>", methods=('GET', 'POST'))
def view_credential(credential_id):
    credential = APICredential.get(id=credential_id)

    if request.method == 'POST':
        command = request.form['command']
        if command == 'DELETE':
            credential.delete_instance()
            return redirect(url_for('home'))

    recent_orders = Order.select().where(Order.credential == credential).order_by(Order.created.desc())

    return render_template(
        'view_credential.html',
        credential=credential,
        recent_orders=recent_orders,
        STATUS__OPEN=Order.STATUS__OPEN,
        STATUS__INSUFFICIENT_FUNDS=Order.STATUS__INSUFFICIENT_FUNDS,
        STATUS__CANCELLED=Order.STATUS__CANCELLED,
        STATUS__REJECTED=Order.STATUS__REJECTED,
        STATUS__COMPLETE=Order.STATUS__COMPLETE
    )



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

        return redirect(url_for('view_credential', credential_id=credential.id))

    return render_template(
        'create_schedule.html',
        credential=credential,
        DAYS=DCASchedule.DAYS,
        HOURS=DCASchedule.HOURS,
        MINUTES=DCASchedule.MINUTES,
    )



@app.route("/schedule/delete/<schedule_id>", methods=('POST',))
def delete_schedule(schedule_id):
    schedule = DCASchedule.get(id=schedule_id)

    if request.method == 'POST':
        credential_id = schedule.credential.id
        schedule.delete_instance()

        return redirect(url_for('view_credential', credential_id=credential_id))



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



@app.route("/order/manual/<credential_id>", methods=('GET', 'POST'))
def manual_order(credential_id):
    credential = APICredential.get(id=credential_id)

    if request.method == 'POST':
        market_name = request.form['market_name']
        order_side = request.form['order_side'].lower()
        amount = Decimal(request.form['amount'])
        amount_currency = request.form['amount_currency']

        exchange = GeminiExchange(credential)
        order = exchange.place_order(market_name, order_side, amount, amount_currency)
        return redirect(url_for('view_order', credential_id=credential.id, order_id=order.id))

    return render_template('manual_order.html', credential=credential)



@app.route("/order/<order_id>", methods=('GET',))
def view_order(order_id):
    order = Order.get(id=order_id)

    return render_template('view_order.html', credential=order.credential, order=order)



def timer_thread():
    while True:
        print("Checking DCASchedules")
        for schedule in DCASchedule.select().where(DCASchedule.is_active == True):
            if schedule.is_time_to_run:
                print(f"Running Schedule {schedule.id} {schedule.market_name}")
                schedule.last_run = datetime.datetime.now()
                schedule.save()

                if schedule.credential.exchange == APICredential.EXCHANGE__GEMINI:
                    exchange = GeminiExchange(schedule.credential)                    
                else:
                    raise Exception(f"Exchange {schedule.exchange} not implemented yet!")
                order = exchange.place_scheduled_order(schedule)

        # Update live orders
        for order in Order.select().where(Order.is_live):
            if order.credential.exchange == APICredential.EXCHANGE__GEMINI:
                exchange = GeminiExchange(order.credential)                
            else:
                raise Exception(f"Exchange {schedule.exchange} not implemented yet!")

            print(f"Updating Order {order.id}")
            exchange.update_order(order)

        time.sleep(10)



if __name__ == "__main__":
    import werkzeug
    from models import create_tables

    # Creates sqlite DB tables if necessary
    create_tables()

    # Start the schedule runner thread
    if not werkzeug.serving.is_running_from_reloader():
        # Prevent duplicates from being created by hot reloads
        print("starting thread")
        x = threading.Thread(target=timer_thread, daemon=True)
        x.start()

    app.run(port=61712)
