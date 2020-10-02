**WARNING!** I've not used this software myself for a year. It may well no longer work. I'm leaving it here in case others find the code useful. But I don't recommend using it yourself unless you understand how to hack the code!

Free, Open Source software for submitting VAT returns to HMRC under their MTD (Making Tax Digital) scheme. Needs some work to support any kind of VAT return.

# About

This software logs you into the HMRC VAT system, and then submits a spreadsheet (which must be in a particular format) as your VAT return. At the moment it only supports flat rate, because that's all I need.

You could deploy this to Heroku yourself for free (use the button below), or you can use my deployment at https://vatreturn.herokuapp.com - it doesn't store any data, so it's safe to use it from a security point of view. You'll either have to read the code or trust me that the calculations it submits are correct, though.

Read more about the app at https://vatreturn.herokuapp.com


# Deploy

Nothing is stored in the app - the data is fetched from a CSV at a URL you define (e.g. from a Google Sheet) and then sent to HMRC. Therefore, you can take advantage of Heroku's free deploy tier to do this instantly.  You'll need to register an application with HMRC (see below) and fill out the `client_id`, `client_secret`, and a URL to the CSV:

[![Deploy](https://www.herokucdn.com/deploy/button.png)](https://heroku.com/deploy)


# Develop


* [Register application](https://developer.service.hmrc.gov.uk/developer/applications/) and note the `client_id` and `client_secret`
  * Set up http://localhost:5000/ as a callback URL within the application registration section of the HMRC interface
* [Create test user](https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/api-platform-test-user/1.0) and note the login number, password, and vat number

Set environment variables, then:

    OAUTHLIB_INSECURE_TRANSPORT=1LASK_DEBUG=1 FLASK_APP=vatreturn.py flask run


# Google Sheets format

The CSV you've prepared must match this format. The column headers matter (at the moment):

    VAT period   SUM of Fee  SUM of VAT   VAT rate
    2019-06-30          1800        360     16.5
    2019-06-30          1400        290     16.5
    2019-06-30          920         180     16.5

For me this is a pivot table generated off my invoices spreadsheet,
and I share it using the Google Sheets "publish as CSV" functionality.
