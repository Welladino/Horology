"""Gateway policy wrapper around shared HTTPS/public-address validation."""
from horology_runtime.urls import UnsafeURL, validate_public_https_url
from policy import Denied


def public_url(url):
    try:
        validate_public_https_url(url)
    except UnsafeURL as error:
        raise Denied(str(error)) from None


def approved_url(policy, config, url, provider='tavily'):
    """Tavily extraction retains its separately approved exact-URL policy."""
    if url not in policy.get(provider, {}).get('approved_urls', []) or url not in config.get('approved_urls', []):
        raise Denied('URL must be explicitly approved by the operator')
    public_url(url)
