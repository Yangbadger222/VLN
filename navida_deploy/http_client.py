from __future__ import annotations

import json
from urllib.request import Request, urlopen

from .codec import request_to_dict, response_from_dict
from .messages import InferenceRequest, InferenceResponse


def post_inference(url: str, request: InferenceRequest, timeout_s: float = 20.0) -> InferenceResponse:
    payload = json.dumps(request_to_dict(request)).encode("utf-8")
    http_request = Request(url, data=payload, method="POST")
    http_request.add_header("Content-Type", "application/json")

    with urlopen(http_request, timeout=timeout_s) as response:
        body = response.read()
    return response_from_dict(json.loads(body))
