import json
import os
import requests
import datetime

from flask import Flask, redirect, url_for
from flask import render_template, g
from flask import request
from hmrc_provider import make_hmrc_blueprint, hmrc

import pandas as pd


app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersekrit")
app.config["HMRC_OAUTH_CLIENT_ID"] = os.environ.get("HMRC_OAUTH_CLIENT_ID")
app.config["HMRC_OAUTH_CLIENT_SECRET"] = os.environ.get("HMRC_OAUTH_CLIENT_SECRET")
app.config["VAT_NUMBER"] = os.environ.get("VAT_NUMBER")
hmrc_bp = make_hmrc_blueprint(
    scope='read:vat write:vat hello',
    client_id=app.config["HMRC_OAUTH_CLIENT_ID"],
    client_secret=app.config["HMRC_OAUTH_CLIENT_SECRET"]
)
app.register_blueprint(hmrc_bp, url_prefix="/login")


API_HOST = 'https://test-api.service.hmrc.gov.uk'


@app.route("/privacy")
def privacy():
    return render_template('privacy.html')


@app.route("/tandc")
def tandc():
    return render_template('tandc.html')


@app.route("/hello")
def hello():
    url = 'https://test-api.service.hmrc.gov.uk/hello/user'
    if hmrc.get(url).json()['message'] == 'Hello User':
        g.ok = True
    else:
        g.ok = False
    return render_template('hello.html')


@app.route("/")
def index():
    return render_template('index.html')


def get_endpoint(endpoint, params={}):
    url = "/organisations/vat/{}/{}".format(app.config["VAT_NUMBER"], endpoint)
    response = hmrc.get(url, params=params)

    if not response.ok:
        try:
            error = response.json()
        except json.decoder.JSONDecodeError:
            error = response.text
        return {'error': error}
    else:
        return response.json()


@app.route("/obligations")
def obligations(show_all=False):
    if not hmrc.authorized:
        return redirect(url_for("hmrc.login"))
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
    obligations = get_endpoint('obligations', params)
    if 'error' in obligations:
        g.error = obligations['error']
    else:
        g.obligations = obligations['obligations']
    return render_template('obligations.html')


def return_data(period_key, vat_csv):
    df = pd.read_csv(vat_csv)
    assert list(df.columns) == ['VAT period', 'SUM of Fee', 'SUM of VAT']
    period = df[df['VAT period'] == period_key]
    net_fee = int(period['SUM of Fee'].iloc[0])
    vat = int(period['SUM of VAT'].iloc[0])
    gross_receipts = net_fee + vat
    vat_due = gross_receipts * 0.165
    box_1 = vat_due
    box_2 = 0  # vat due on acquisitions
    box_3 = box_1 + box_2  # total vat due - calculated: Box1 + Box2
    box_4 = 0  # vat reclaimed for current period
    box_5 = abs(box_3 - box_4)  # net vat due - calculate - amount to be paid. Take the figures from Box 3 and Box 4. Deduct the smaller figure from the larger one and put the difference
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
def preview_return(period_key):
    g.period_key = period_key
    g.vat_csv = request.args.get('vat_csv', '')
    if g.vat_csv:
        g.data = return_data(period_key, g.vat_csv)
    return render_template('preview_return.html')


@app.route("/<string:period_key>/send", methods=('POST',))
def send_return(period_key):
    vat_csv = request.form.get('vat_csv')
    data = return_data(period_key, vat_csv)
    url = "/organisations/vat/{}/returns".format(app.config["VAT_NUMBER"])
    response = hmrc.post(
        url,
        data=data)
    if not response.ok:
        try:
            error = response.json()
        except json.decoder.JSONDecodeError:
            error = response.text
        g.error = error
    g.data = response.json()
    return render_template('send_return.html')


@app.route("/logout")
def logout():
    #logout_user()
    return redirect('/')


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
