# Email sender

Email sender provides a API endpoint to send emails. It will try to
use Mailgun to do this. If Mailgun does not respond, it will fallback
to using Mandrill.

* [Details](#details)
* [Usage](#usage)

## Details

### Circuit breakers

The network calls to Mailgun and Mandrill are both wrapped in a circuit breaker. This
is done so that if Mailgun fails after so many times, future requests will fail faster and
Mandrill will be used instead. The circuit breaker also raises events for when the breaker
is called and if it was successful or failed which can be used to send metrics and to
determine if the service is healthy or not.

### Future improvements

It is likely that users of this service won't want to block waiting for the email to be sent.
Instead the service should probably use Google Pub/Sub to publish the request to a worker.

The authentication will also need changing to allow for more than one API key.

There are further features made available by Mailgun and Mandrill which could be exposed.

Add a health check endpoint.

### Thrid party code

The ``JSONTranslator`` in the ``utils.py`` file was taken from the Falcon quickstart guide.

The ``mandrill`` python library is used to simplify integration.

## API

### Send email

You can send an email with the following command.

```
curl https://email-sender --data '{"receiver": "test@test.com", "sender": "test@test.com", "subject": "Example", "text": "Example text message", "html": "Example html message", "key": "xxx"}' -H 'Content-Type: application/json'
```

*Change the `key` value to the API_KEY envvar value.*

*Replace the url with a real one*

### Force sending email using fallback

You can force email-sender to use the fallback service by adding
`'fallback': true` to the request body like so.

```
curl https://email-sender --data '{"receiver": "test@test.com", "sender": "test@test.com", "subject": "Example", "text": "Example text message", "html": "Example html message", "key": "xxx", "fallback": True}' -H 'Content-Type: application/json'
```

## Usage

### Configuration

The application is configured using environment variables
(as recommended by the 12 factor app). The following environment
variables must be available.

* ``MAILGUN_API_KEY``: a valid Mailgun API key.
* ``MAILGUN_DOMAIN``: the domain configured against the api key.
* ``MANDRILL_API_KEY``: a valid Mandrill API key.
* ``API_KEY``: random key used to validate requests to email sender.

The environment variables must be listed in the ```env``` file at
the project root e.g.

```
MAILGUN_API_KEY = 'your-mailgun-key'
MAILGUN_DOMAIN = 'your-mailgun-domain'
MANDRILL_API_KEY = 'your-mandrill-key'
API_KEY = 'you-api-key'
```

### Local installation

Email sender can be ran locally. Run the following to install the
application.

```
virtualenv venv
source venv/bin/activate
pip install -r requirements
```

You can run the app with the following command.

```
honcho start -e env
```

*``-e env`` references a file listing the environment variables.*

### Deploy to Google Managed VMs.

You will need to have a project already created and have the project
ID.

```
gcloud --project project-id preview app deploy --stop-previous-version
```

### Run tests

To run the tests, you need to install the dev requirements.

```
pip install -r requirements-dev.txt
```

You can now run the tests using py.test

```
py.test tests.py
```
