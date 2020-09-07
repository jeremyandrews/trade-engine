class SixDigitTOTP:
    """
    Our TOTP implementation only accepts 6 digit codes, all integers.
    See https://docs.djangoproject.com/en/2.1/topics/http/urls/#registering-custom-path-converters
    """
    regex = '[0-9]{6}'

    def to_python(self, value):
        return int(value)

    def  to_url(self, value):
        return '%06d' % value

class SevenEightCharStatic:
    """
    Our Static recovery codes can be 7 or 8 characters long, alphanumeric (minus 0 and 1)
    See https://docs.djangoproject.com/en/2.1/topics/http/urls/#registering-custom-path-converters
    """
    regex = '[a-z2-9]{7,8}'

    def to_python(self, value):
        return str(value)

    def to_url(self, value):
        # @TODO: do we need to better-sanitize this?
        return value.encode()
