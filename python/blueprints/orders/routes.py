from decimal import Decimal
from flask import (Blueprint, jsonify, render_template, request, redirect,
    url_for)

from exchanges.gemini import GeminiExchange, GeminiRequestException
from models import APICredential, DCASchedule, Order



orders_routes = Blueprint('orders', __name__, template_folder='_templates')


@orders_routes.route("/<order_id>", defaults={"order_id": ""})
@orders_routes.route("/<order_id>")
def view_order(order_id):
    order = Order.get(id=order_id)
    return render_template('orders/view_order.html', order=order, credential=order.credential)



@orders_routes.route('/recent')
def recent_orders():
    data = []
    for order in Order.select().order_by(Order.created.desc()).limit(10):
        entry = order.to_json()
        entry["exchange"] = order.credential.exchange
        data.append(entry)

    return jsonify(data)



@orders_routes.route("/manual/<credential_id>", methods=('GET', 'POST'))
def manual_order(credential_id):
    credential = APICredential.get(id=credential_id)

    if request.method == 'POST':
        market_name = request.form['market_name']
        order_side = request.form['order_side'].lower()
        amount = Decimal(request.form['amount'])
        amount_currency = request.form['amount_currency']

        exchange = GeminiExchange(credential)
        order = exchange.place_order(market_name, order_side, amount, amount_currency)
        return redirect(url_for('orders.view_order', order_id=order.id))

    return render_template('orders/manual_order.html', credential=credential)


