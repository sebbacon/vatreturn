import os
import requests

from flask import Flask, redirect, url_for
from hmrc_provider import make_hmrc_blueprint, hmrc

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersekrit")
app.config["HMRC_OAUTH_CLIENT_ID"] = os.environ.get("HMRC_OAUTH_CLIENT_ID")
app.config["HMRC_OAUTH_CLIENT_SECRET"] = os.environ.get("HMRC_OAUTH_CLIENT_SECRET")
hmrc_bp = make_hmrc_blueprint(scope='read:vat+write:vat')
app.register_blueprint(hmrc_bp, url_prefix="/login")


API_HOST = 'https://test-api.service.hmrc.gov.uk'


@app.route("/")
def index():
    if not hmrc.authorized:
        return redirect(url_for("hmrc.login"))
    resp = hmrc.get("/user")
    assert resp.ok
    return "You are @{login} on HMRC".format(login=resp.json()["login"])


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
