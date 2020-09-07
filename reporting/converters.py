class CryptoPair:
    """
    Cryptopairs are up to 16 capital letters, followed by a dash, followed by up to 16 capital letters.
    See https://docs.djangoproject.com/en/2.1/topics/http/urls/#registering-custom-path-converters
    """
    regex = '[A-Z]{1,16}-[A-Z]{1,16}'

    def to_python(self, value):
        return str(value)

    def to_url(self, value):
        # @TODO: do we need to better-sanitize this?
        return value.encode()


