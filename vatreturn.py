from functools import wraps
import json
import os
import requests
import datetime

from flask import Flask, redirect, url_for
from flask import send_from_directory
from flask import render_template, g
from flask import request
from flask import session
from hmrc_provider import make_hmrc_blueprint, hmrc

import pandas as pd


app = Flask(__name__, static_url_path='')
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersekrit")
app.config["HMRC_OAUTH_CLIENT_ID"] = os.environ.get("HMRC_OAUTH_CLIENT_ID")
app.config["HMRC_OAUTH_CLIENT_SECRET"] = os.environ.get("HMRC_OAUTH_CLIENT_SECRET")
app.config["HMRC_API_HOST"] = os.environ.get("HMRC_API_HOST")
hmrc_bp = make_hmrc_blueprint(
    api_host=app.config['HMRC_API_HOST'],
    scope='read:vat write:vat',
    client_id=app.config["HMRC_OAUTH_CLIENT_ID"],
    client_secret=app.config["HMRC_OAUTH_CLIENT_SECRET"],
    redirect_to="obligations"
)
app.register_blueprint(
    hmrc_bp,
    url_prefix="/login",)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hmrc.authorized:
            return redirect(url_for("hmrc.login"))
        else:
            if 'hmrc_vat_number' not in session:
                return redirect(url_for('get_vat_number', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/privacy")
def privacy():
    return render_template('privacy.html')


@app.route("/making_tax_digital")
def making_tax_digital():
    return render_template('making_tax_digital.html')


@app.route("/tandc")
def tandc():
    return render_template('tandc.html')


@app.route("/get_vat_number", methods=('GET', 'POST',))
def get_vat_number():
    if request.method == 'GET':
        return render_template('get_vat_number.html')
    elif request.method == 'POST':
        session['hmrc_vat_number'] = request.form['hmrc_vat_number']
        return redirect(request.args.get('next'))


@app.route("/")
def index():
    return render_template('index.html')


def get_fraud_headers():
    # These should all be in the request, mostly because they've been
    # injected into any form as hidden fields by javascript
    headers = {
        'Gov-Client-Connection-Method': 'WEB_APP_VIA_SERVER',
        'Gov-Client-Public-IP': request.cookies.get(
            'public_ip', None),
        'Gov-Client-Timezone': request.cookies.get(
            'user_timezone', None),
        'Gov-Client-Window-Size': request.cookies.get(
            'client_window', None),
        'Gov-Client-Browser-JS-User-Agent': request.cookies.get(
            'client_user_agent', None),
        'Gov-Client-Browser-Plugins': request.cookies.get(
            'client_browser_plugins', None),
        'Gov-Client-Browser-Do-Not-Track': request.cookies.get(
            'client_do_not_track', None),
        'Gov-Client-Screens': request.cookies.get(
            'client_screens', None),
        'Gov-Client-Device-ID': request.cookies.get(
            'device_id', None),
        'Gov-Vendor-Version': 'v=0.1',
        'Gov-Vendor-Public-IP': None,  # hosted in Heroku, will change
        'Gov-Client-User-IDs': None,  # not available
        'Gov-Vendor-Public-Port': None
    }
    return dict([(k, v) for k, v in headers.items() if v])


def do_action(action, endpoint, params={}, data={}):
    url = "/organisations/vat/{}/{}".format(
        session['hmrc_vat_number'], endpoint)
    if action == 'get':
        response = hmrc.get(url, params=params, headers=get_fraud_headers())
    elif action == 'post':
        response = hmrc.post(url, json=data, headers=get_fraud_headers())
    if not response.ok:
        try:
            error = response.json()
        except json.decoder.JSONDecodeError:
            error = response.text
        return {'error': error}
    else:
        return response.json()


@app.route("/obligations")
@login_required
def obligations(show_all=False):
    if show_all:
        today = datetime.date.today()
        from_date = today - datetime.timedelta(days=365*2)
        to_date = today
        params = {
            'from': from_date.strftime("%Y-%m-%d"),
            'to': to_date.strftime("%Y-%m-%d")
        }
    else:
        params = {'status': 'O'}
    obligations = do_action('get', 'obligations', params)
    if 'error' in obligations:
        g.error = obligations['error']
    else:
        g.obligations = obligations['obligations']
    return render_template('obligations.html')


def return_data(period_key, period_end, vat_csv):
    df = pd.read_csv(vat_csv)
    assert list(df.columns) == ["VAT period", "SUM of Fee", "SUM of VAT", "VAT rate"]

    period = df[df["VAT period"] == period_end]
    net_fee = int(period["SUM of Fee"].iloc[0])
    vat = int(period["SUM of VAT"].iloc[0])
    vat_rate = float(period["VAT rate"].iloc[0]) / 100
    gross_receipts = net_fee + vat
    vat_due = round(gross_receipts * vat_rate, 2)
    box_1 = vat_due
    box_2 = 0  # vat due on acquisitions
    box_3 = box_1 + box_2  # total vat due - calculated: Box1 + Box2
    box_4 = 0  # vat reclaimed for current period
    box_5 = abs(box_3 - box_4)  # net vat due (amount to be paid). Calculated: take the figures from Box 3 and Box 4. Deduct the smaller figure from the larger one and use the difference
    box_6 = gross_receipts  # total value sales ex vat
    box_7 = 0  # total value purchases ex vat
    box_8 = 0  # total value goods supplied ex vat
    box_9 = 0  # total acquisitions ex vat
    data = {
        "periodKey": period_key,
        "vatDueSales": box_1,
        "vatDueAcquisitions": box_2,
        "totalVatDue": box_3,
        "vatReclaimedCurrPeriod": box_4,
        "netVatDue": box_5,
        "totalValueSalesExVAT": box_6,
        "totalValuePurchasesExVAT": box_7,
        "totalValueGoodsSuppliedExVAT": box_8,
        "totalAcquisitionsExVAT": box_9,
        "finalised": True  # declaration
    }
    return data


@app.route("/<string:period_key>/preview")
@login_required
def preview_return(period_key):
    g.period_key = period_key
    g.vat_csv = request.args.get('vat_csv', '')
    g.period_end = request.args.get('period_end', '')
    if g.vat_csv:
        g.data = return_data(g.period_key, g.period_end, g.vat_csv)
    return render_template('preview_return.html')


@app.route("/<string:period_key>/send", methods=('POST',))
@login_required
def send_return(period_key):
    confirmed = request.form.get('complete', None)
    vat_csv = request.form.get('vat_csv')
    g.period_end = request.form.get('period_end', '')
    if not confirmed:
        return redirect(url_for(
            "preview_return",
            period_key=period_key,
            period_end=g.period_end,
            confirmation_error=True))
    else:
        g.data = return_data(period_key, g.period_end, vat_csv)
        g.response = do_action('post', 'returns', data=g.data)
        return render_template('send_return.html')


@app.route("/logout")
def logout():
    del(session['hmrc_oauth_token'])
    del(session['hmrc_vat_number'])
    return redirect(url_for("index"))


def create_test_user():
    url = '/create-test-user/individuals'
    return requests.post(
        API_HOST + url,
        data={
            "serviceNames": [
                "national-insurance",
                "self-assessment",
                "mtd-income-tax",
                "customs-services",
            "mtd-vat"
            ]
        })


@app.route('/js/<path:path>')
def send_js(path):
    return send_from_directory('js', path)


@app.route('/img/<path:path>')
def send_img(path):
    return send_from_directory('img', path)
