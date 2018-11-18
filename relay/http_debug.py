import logging
import aiohttp
import aiohttp.web

from collections import defaultdict


STATS = {
    'requests': defaultdict(int),
    'response_codes': defaultdict(int),
    'response_codes_per_domain': defaultdict(lambda: defaultdict(int)),
    'delivery_codes': defaultdict(int),
    'delivery_codes_per_domain': defaultdict(lambda: defaultdict(int)),
    'exceptions': defaultdict(int),
    'exceptions_per_domain': defaultdict(lambda: defaultdict(int)),
    'delivery_exceptions': defaultdict(int),
    'delivery_exceptions_per_domain': defaultdict(lambda: defaultdict(int))
}


async def on_request_start(session, trace_config_ctx, params):
    global STATS

    logging.debug("HTTP START [%r], [%r]", session, params)

    STATS['requests'][params.url.host] += 1


async def on_request_end(session, trace_config_ctx, params):
    global STATS

    logging.debug("HTTP END [%r], [%r]", session, params)

    host = params.url.host
    status = params.response.status

    STATS['response_codes'][status] += 1
    STATS['response_codes_per_domain'][host][status] += 1

    if params.method == 'POST':
        STATS['delivery_codes'][status] += 1
        STATS['delivery_codes_per_domain'][host][status] += 1


async def on_request_exception(session, trace_config_ctx, params):
    global STATS

    logging.debug("HTTP EXCEPTION [%r], [%r]", session, params)

    host = params.url.host
    exception = repr(params.exception)

    STATS['exceptions'][exception] += 1
    STATS['exceptions_per_domain'][host][exception] += 1

    if params.method == 'POST':
        STATS['delivery_exceptions'][exception] += 1
        STATS['delivery_exceptions_per_domain'][host][exception] += 1


def http_debug():
    trace_config = aiohttp.TraceConfig()
    trace_config.on_request_start.append(on_request_start)
    trace_config.on_request_end.append(on_request_end)
    trace_config.on_request_exception.append(on_request_exception)
    return trace_config
