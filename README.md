# Deploy

Nothing is stored in the app - the data is fetched from a CSV at a URL you define (e.g. from a Google Sheet) and then sent to HMRC. Therefore, you can take advantage of Heroku's free deploy tier to do this instantly.  You'll need to register an application with HMRC (see below) and fill out the `client_id`, `client_secret`, and a URL to the CSV:

[![Deploy](https://www.herokucdn.com/deploy/button.png)](https://heroku.com/deploy)


# Develop


* [Register application](https://developer.service.hmrc.gov.uk/developer/applications/) and note the `client_id` and `client_secret`
* [Create test user](https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/api-platform-test-user/1.0) and note the login number, password, and vat number

Set environment variables, then:

    FLASK_APP=vatreturn FLASK_DEBUG=1 flask run


# Google Sheets format

The CSV you've prepared must match this format. The column headers matter (at the moment):

    VAT period   SUM of Fee  SUM of VAT
          17A3        1800        360
          17A4        2900        590
          18A1        1400        290
          18A2         920        180

For me this is a pivot table generated off my invoices spreadsheet,
and I share it using the Google Sheets "publish as CSV" functionality.
