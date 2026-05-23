#!/usr/bin/env python3
import time, threading
from flask import Flask, abort, Response
from update import generate_html_string

app = Flask(__name__)

cache = {}
cache_lock = threading.Lock()
CACHE_TTL = 30


def get_html(event_id):
    with cache_lock:
        entry = cache.get(event_id)
        if entry and time.time() - entry['ts'] < CACHE_TTL:
            return entry['html']

    html = generate_html_string(event_id)

    with cache_lock:
        cache[event_id] = {'html': html, 'ts': time.time()}

    return html


@app.route('/<event_id>/')
@app.route('/<event_id>')
def serve(event_id):
    if not event_id.isdigit():
        abort(404)
    try:
        html = get_html(event_id)
        return Response(html, mimetype='text/html')
    except Exception as e:
        print(f"Error fetching event {event_id}: {e}")
        abort(404)


@app.route('/')
def index():
    return Response('<h2>Укажи ID события: /15116/</h2>', mimetype='text/html')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
