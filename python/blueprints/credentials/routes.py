from flask import Blueprint, jsonify, render_template, request

from models import APICredential, DCASchedule, Order



credentials_routes = Blueprint('credentials', __name__, template_folder='_templates')



@credentials_routes.route("/create", methods=('GET', 'POST'))
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

    return render_template('credentials/create_credential.html')



@credentials_routes.route("/<credential_id>", methods=('GET', 'POST'))
def view_credential(credential_id):
    credential = APICredential.get(id=credential_id)

    if request.method == 'POST':
        command = request.form['command']
        if command == 'DELETE':
            credential.delete_instance()
            return redirect(url_for('home'))

    recent_orders = Order.select(
    ).where(
    	Order.credential == credential
	).order_by(
		Order.created.desc()
	).limit(10)

    return render_template(
        'credentials/view_credential.html',
        credential=credential,
        recent_orders=recent_orders,
        STATUS__OPEN=Order.STATUS__OPEN,
        STATUS__INSUFFICIENT_FUNDS=Order.STATUS__INSUFFICIENT_FUNDS,
        STATUS__CANCELLED=Order.STATUS__CANCELLED,
        STATUS__REJECTED=Order.STATUS__REJECTED,
        STATUS__COMPLETE=Order.STATUS__COMPLETE
    )

