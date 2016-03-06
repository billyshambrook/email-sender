"""Email sender tests."""
import falcon
import mock
import pytest

import main


@pytest.fixture
def request():
    """Mock request."""
    return mock.Mock()


@pytest.fixture
def response():
    """Mock response."""
    return mock.Mock()


@pytest.fixture
def request_body():
    """Test request body."""
    return {
        'sender': 'test@test.com',
        'receiver': 'test@test.com',
        'subject': 'Example',
        'text': 'A text example',
        'html': 'A html example'
    }


class TestEmailsResource(object):
    """Test the emails resource."""

    @classmethod
    def setup_class(cls):
        """Set up the resource with a API key."""
        cls.api_key = 'abc'
        cls.resource = main.EmailsResource(api_key=cls.api_key)

    def test_no_key(self, request, response):
        """Ensure NotFound if no key field in request."""
        request.context = {'doc': {}}

        with pytest.raises(falcon.HTTPNotFound):
            self.resource.on_post(request, response)

    def test_incorrect_key(self, request, response):
        """Ensure NotFound if the given key does not match."""
        request.context = {'doc': {'key': 'xyz'}}

        with pytest.raises(falcon.HTTPNotFound):
            self.resource.on_post(request, response)

    def test_missing_field(self, request, response):
        """Ensure a BadRequest error if any required field is missing in the request."""
        request.context = {'doc': {'key': 'abc'}}

        with pytest.raises(falcon.HTTPBadRequest) as exc:
            self.resource.on_post(request, response)

    @mock.patch('main.send_with_mandrill')
    @mock.patch('main.send_with_mailgun')
    def test_mailgun(self, mocked_mailgun, mocked_mandrill, request, response, request_body):
        """Ensure mailgun is tried first, and that the fallback is not used."""
        request_body['key'] = self.api_key
        request.context = {'doc': request_body}

        self.resource.on_post(request, response)

        assert mocked_mailgun.called
        assert not mocked_mandrill.called

    @mock.patch('main.send_with_mandrill')
    @mock.patch('main.send_with_mailgun')
    def test_fallback(self, mocked_mailgun, mocked_mandrill, request, response, request_body):
        """Ensure the fallback is used when the first service raises a exception."""
        request_body['key'] = self.api_key
        request.context = {'doc': request_body}
        mocked_mailgun.side_effect = RuntimeError

        self.resource.on_post(request, response)

        assert mocked_mailgun.called
        assert mocked_mandrill.called
