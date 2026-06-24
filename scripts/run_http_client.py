from navida_deploy.client import build_request
from navida_deploy.http_client import post_inference


if __name__ == "__main__":
    request = build_request("demo-session", 0, image_path="sample.jpg")
    response = post_inference("http://127.0.0.1:50051/v1/infer", request)
    print(response)

