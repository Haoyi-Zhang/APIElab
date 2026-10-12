"""One-call polarity adaptation for a logical Boolean request.

The source request returns its argument. A target decoder returns b XOR s_v,
where s_v is the supplied version's encoding polarity. The compiler fixes a
before runtime input and elaborates the request to decode(e XOR a).
These are authored model semantics, not extracted behavior of a deployed API.
"""
from copy import deepcopy


def elaborate_request(expression, polarity):
    """Return a target term; expression must be well-scoped over input x.

    The existing independent admission/checking paths validate the resulting
    term. This helper is not a general source-language parser or compiler.
    """
    if type(polarity) is not int or polarity not in (0, 1):
        raise ValueError('polarity must be integer zero or one')
    argument = deepcopy(expression)
    if polarity:
        argument = {'not': argument}
    return {'op': 'let', 'name': 'request_result', 'api': 'decode',
            'arg': argument,
            'body': {'op': 'return', 'value': {'var': 'request_result'}}}
