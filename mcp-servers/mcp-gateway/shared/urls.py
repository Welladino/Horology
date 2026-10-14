"""Gateway policy wrapper around shared HTTPS/public-address validation."""
from horology_runtime.urls import UnsafeURL, validate_public_https_url
from policy import Denied


def public_url(url):
    try:
        validate_public_https_url(url)
    except UnsafeURL as error:
        raise Denied(str(error)) from None

