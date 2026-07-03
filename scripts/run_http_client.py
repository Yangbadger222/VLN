from navida_deploy.client import MINIMAL_JPEG, build_request
from navida_deploy.http_client import post_inference
from navida_deploy.messages import Observation


if __name__ == "__main__":
    request = build_request(
        "demo-session",
        0,
        "go forward",
        observation=Observation(
            image_bytes=MINIMAL_JPEG,
            history_image_bytes=[],
            metadata={"camera": "demo"},
        ),
    )
    response = post_inference(
        "http://127.0.0.1:50051/v1/infer",
        request,
    )
    print(response)
