import giphy_client
from giphy_client import InlineResponse2002
from giphy_client.api_client import ApiClient
from giphy_client.rest import ApiException

from stonks_bot import conf


def gif_random(search_term: str) -> dict:
    api_client = ApiClient()
    api_key = conf.API['giphy_key']  # str | Giphy API Key.
    rating = 'r'  # str | Filters results by specified rating. (optional)
    fmt = 'json'  # str | Used to indicate the expected response format. Default is Json. (optional) (default to json)
    api_response = False

    try:
        # Random Endpoint
        api_response = api_client.call_api('/gifs/random', 'GET', {},
                                           {'api_key': api_key, 'tag': search_term, 'rating': rating, 'fmt': fmt},
                                           {'Accept': 'application/json', 'Content-Type': 'application/json',
                                            'User-Agent': 'Swagger-Codegen/1.0.0/python'},
                                           body=None,
                                           post_params=[],
                                           files={},
                                           response_type=object,
                                           auth_settings=[],
                                           callback=None,
                                           _return_http_data_only=True,
                                           _preload_content=True,
                                           _request_timeout=None,
                                           collection_formats={})

    except ApiException as e:
        print("Exception when calling DefaultApi->gifs_random_get: %s\n" % e)

    return api_response


def gif_random_broken(search_term: str) -> InlineResponse2002:
    raise Exception('The Giphy SDK is broken. Thus this method does not work currently.')

    # create an instance of the API class
    api_instance = giphy_client.DefaultApi()
    api_key = conf.API['giphy_key']  # str | Giphy API Key.
    rating = 'r'  # str | Filters results by specified rating. (optional)
    fmt = 'json'  # str | Used to indicate the expected response format. Default is Json. (optional) (default to json)
    api_response = False

    try:
        # Random Endpoint
        api_response = api_instance.gifs_random_get(api_key, tag=search_term, rating=rating, fmt=fmt)
    except ApiException as e:
        print("Exception when calling DefaultApi->gifs_random_get: %s\n" % e)

    return api_response
