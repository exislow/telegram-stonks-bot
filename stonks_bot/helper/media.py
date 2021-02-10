import giphy_client
from giphy_client.rest import ApiException


def gif_random(search_term: str) -> None:
    # create an instance of the API class
    api_instance = giphy_client.DefaultApi()
    api_key = 'ni2nGePDV3EGTmAFw45yPrVJEvOQ5Pm1'  # str | Giphy API Key.
    rating = 'r'  # str | Filters results by specified rating. (optional)
    fmt = 'json'  # str | Used to indicate the expected response format. Default is Json. (optional) (default to json)
    api_response = False

    try:
        # Random Endpoint
        api_response = api_instance.gifs_random_get(api_key, tag=search_term, rating=rating, fmt=fmt)
    except ApiException as e:
        print("Exception when calling DefaultApi->gifs_random_get: %s\n" % e)

    return api_response
