import logging
import json
import hashlib
import uuid
from order.models import Order
from django.forms.models import model_to_dict
import datetime

import pika

import spauser.utils


# Initialize our audit log structure in a global scope
log_message_cache = {
    'counter': 0,
    'message': '',
    'details': '',
}

class AuditEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            # if the obj is uuid, we simply return the value of uuid
            return obj.hex
        if isinstance(obj, Order):
            return model_to_dict(obj)
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)

def generate_trace_id():
    return uuid.uuid4()

# We assume all keys in our log_dictionary are strings, as otherwise order can change each time we hash.
def hash_log_message(log_dictionary):
    h = hashlib.sha256(json.dumps(log_dictionary, sort_keys=True, ensure_ascii=True).encode())
    return h.hexdigest()

def audit(message, details):
    hash_of_previous_log = hash_log_message(log_dictionary=log_message_cache)

    # Update globally scoped audit log structure
    log_message_cache['counter'] += 1
    log_message_cache['message'] = message

    # Format key=value
    log_message_cache['details'] = "%s|sha256=%s" % (json.dumps(details, cls=AuditEncoder), hash_of_previous_log)

    # @TODO: sign audit logs, send to remote server(s)
    logging.info("%d|%s|%s\n" % (log_message_cache['counter'], log_message_cache['message'], log_message_cache['details']))

def notify_middleware(message):
    try:
        queue = 'pushNotifications'
        mqconnection = pika.BlockingConnection(pika.ConnectionParameters('rabbit'))
        channel = mqconnection.channel()
        channel.queue_declare(queue=queue)
        channel.basic_publish(exchange='', routing_key=queue, body=json.dumps(message))
        mqconnection.close()
    except Exception as e:
        print("Failed to send notification to middleware: %s" % e)

def get_since_parameter(request):
    # Optional filter for trade history
    try:
        value = int(request.GET.get('since'))
    except Exception as e:
        # Default to 0, showing all trades
        value = 0

    if value < 0:
        status_code = status.HTTP_400_BAD_REQUEST
        data = {
            "status": "since must be a positive integer",
            "code": status_code,
            "debug": {
                "invalid value": value,
            },
            "data": {},
        }
        return data, status_code

    return value, True

# Helper to invoke /api/public/<cryptopair>/orderbook/ endpoint from a test.
def view_orderbook(self, cryptopair, token=None, data={}):
    url = '/api/public/%s/orderbook/' % cryptopair
    return spauser.utils.client_get_optional_jwt(self, url=url, token=token, data=data)

# Helper to invoke /api/public/<cryptopair>/trades/ endpoint from a test.
def view_trades(self, cryptopair, token=None, data={}, offset=None, since=None):
    url = '/api/public/%s/trades/' % cryptopair

    if offset is not None:
        try:
            url += "?offset=%d" % offset
        except:
            print("invalid offset (%s), must be integer" % offset)

    if since is not None:
        try:
            if offset is not None:
                url += "&since=%d" % since
            else:
                url += "?since=%d" % since
        except:
            print("invalid since (%s), must be integer" % since)

    return spauser.utils.client_get_optional_jwt(self, url=url, token=token, data=data)

def view_ticker(self, cryptopair, token=None, data={}):
    url = '/api/public/%s/ticker/' % cryptopair
    return spauser.utils.client_get_optional_jwt(self, url=url, token=token, data=data)
