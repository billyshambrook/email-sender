"""A HA Falcon web application that sends emails."""
import json
import logging
import os

import falcon
import mandrill
import pybreaker
import requests

import utils


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LogListener(pybreaker.CircuitBreakerListener):
    """
    Listener used to log circuit breaker events.

    A further listener could be created to send metrics to a monitoring tool.
    """
    def __init__(self, breaker_name):
        """Give the circuit breaker name for reference."""
        self.breaker_name = breaker_name

    def before_call(self, cb, func, *args, **kwargs):
        """Called before the circuit breaker `cb` calls `func`."""
        logger.info('Attempting %s circuit breaker', self.breaker_name)

    def failure(self, cb, exc):
        """Called when a function invocation raises a system error."""
        logger.error('%s circuit breaker failed', self.breaker_name, exc_info=exc)

    def success(self, cb):
        """Called when a function invocation succeeds."""
        logger.info('%s circuit breaker call was successful.', self.breaker_name)


# Circuit breaker allows for failing fast when a network call is not working as expected after so many attempts.
mailgun_breaker = pybreaker.CircuitBreaker(fail_max=5, reset_timeout=60, listeners=[LogListener('mailgun')])
mandrill_breaker = pybreaker.CircuitBreaker(fail_max=5, reset_timeout=60, listeners=[LogListener('mandrill')])


@mailgun_breaker
def send_with_mailgun(sender, receiver, subject, text, html, raise_error=False):
    """
    Send message via Mailgun.

    Args:
        sender (str): Sender email address (from).
        receiver (str): Receiver email address (to).
        subject (str): Message subject.
        text (str): Body of message (text version).
        html (str): Body of message (html version).
        raise_error (bool): if true, function will raise a RuntimeError (default: False).
    """
    if raise_error:
        raise RuntimeError('Forcing mailgun to fail to test fallback.')

    domain = os.environ['MAILGUN_DOMAIN']
    api_key = os.environ['MAILGUN_API_KEY']
    body = {'from': sender, 'to': receiver, 'subject': subject, 'text': text, 'html': html}

    resp = requests.post('https://api.mailgun.net/v3/{}/messages'.format(domain), auth=('api', api_key), data=body)

    resp.raise_for_status()


@mandrill_breaker
def send_with_mandrill(sender, receiver, subject, text, html):
    """
    Send message via Mandrill.

    Args:
        sender (str): Sender email address (from).
        receiver (str): Receiver email address (to).
        subject (str): Message subject.
        text (str): Body of message (text version).
        html (str): Body of message (html version).
    """
    api_key = os.environ['MANDRILL_API_KEY']
    body = {'from_email': sender, 'to': [{'email': receiver}], 'subject': subject, 'text': text, 'html': html}

    mandrill_client = mandrill.Mandrill(api_key)
    mandrill_client.messages.send(message=body)


def send(sender, receiver, subject, text, html, fallback=False):
    """
    Send email.

    Mailgun will be attempted first, then mandrill if it fails.

    Args:
        sender (str): Sender email address (from).
        receiver (str): Receiver email address (to).
        subject (str): Message subject.
        text (str): Body of message (text version).
        html (str): Body of message (html version).
        fallback (bool): If true, the fallback will be used (default: False).
    """
    try:
        send_with_mailgun(sender, receiver, subject, text, html, raise_error=fallback)
    except:
        send_with_mandrill(sender, receiver, subject, text, html)


class EmailsResource(object):
    """
    Resource that handles email requests.

    The endpoint requires there to be a 'key' field in the body with the hardcoded API key.
    """

    def __init__(self, api_key=None):
        """
        Initialise the class.

        Args:
            api_key (str): A string used to authenticate the user.
        """
        self.api_key = api_key or os.getenv('API_KEY')

    def on_post(self, req, resp):
        """Handle post requests to the resource."""
        if req.context['doc'].get('key') != self.api_key:
            # Raise NotFound to hide the endpoint if not authenticated.
            raise falcon.HTTPNotFound()

        try:
            send(
                sender=req.context['doc']['sender'],
                receiver=req.context['doc']['receiver'],
                subject=req.context['doc']['subject'],
                text=req.context['doc']['text'],
                html=req.context['doc']['html'],
                fallback=req.context['doc'].get('fallback'))
        except KeyError as exc:
            logger.exception('Missing field from body %s', req.context['doc'])
            raise falcon.HTTPBadRequest('Missing field', '{} is missing from the body.'.format(exc))
        except:
            logger.exception('Unexpected exception.')
            raise

        resp.status = falcon.HTTP_204


# Create the falcon app.
app = api = falcon.API(middleware=[utils.JSONTranslator()])

# Add the required routes to the falcon app.
api.add_route('/emails', EmailsResource())
