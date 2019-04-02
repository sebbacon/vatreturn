import json
import os
import requests

from flask import Flask, redirect, url_for
from hmrc_provider import make_hmrc_blueprint, hmrc

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersekrit")
app.config["HMRC_OAUTH_CLIENT_ID"] = os.environ.get("HMRC_OAUTH_CLIENT_ID")
app.config["HMRC_OAUTH_CLIENT_SECRET"] = os.environ.get("HMRC_OAUTH_CLIENT_SECRET")
hmrc_bp = make_hmrc_blueprint(
    scope='read:vat write:vat hello',
    client_id=app.config["HMRC_OAUTH_CLIENT_ID"],
    client_secret=app.config["HMRC_OAUTH_CLIENT_SECRET"]
)
app.register_blueprint(hmrc_bp, url_prefix="/login")


API_HOST = 'https://test-api.service.hmrc.gov.uk'


@app.route("/hello")
def hello():
    url = 'https://test-api.service.hmrc.gov.uk/hello/user'
    return "{}".format(hmrc.get(url).json())

@app.route("/")
def index():
    if not hmrc.authorized:
        return redirect(url_for("hmrc.login"))
    ob = get_obligations().json()
    return "You have <pre>{ob}</pre> obligations on HMRC".format(ob=ob)

@app.route("/submit")
def submit():
    if not hmrc.authorized:
        return redirect(url_for("hmrc.login"))
    else:
        ob = set_returns().json()
        return "You have returned thusly <pre>{ob}</pre>".format(ob=ob)


# VAT endpoints
# https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/vat-api/1.0
def get_obligations():
    url = "/organisations/vat/393706722/obligations"
    # status O means Open
    params = {'status': 'O'}  # open
    return hmrc.get(url, params=params)


def set_returns():
    data = {
        "periodKey": "18A1",
        "vatDueSales": 105.50,  # box 1 on the VAT Return form
        "vatDueAcquisitions": -100.45, # box 2
        "totalVatDue": 5.05, # box 3
        "vatReclaimedCurrPeriod": 105.15,  # box 4
        "netVatDue": 100.10,  # box 5
        "totalValueSalesExVAT": 300, # box 6
        "totalValuePurchasesExVAT": 300, # box7
        "totalValueGoodsSuppliedExVAT": 3000, # box8
        "totalAcquisitionsExVAT": 3000, # box 9
        "finalised": True  # declaration
    }
    url = "/organisations/vat/393706722/returns"
    return hmrc.post(
        url,
        data=data)

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
