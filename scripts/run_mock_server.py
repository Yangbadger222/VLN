from navida_deploy.http_service import create_server


if __name__ == "__main__":
    server = create_server(("0.0.0.0", 50051))
    print("listening on http://0.0.0.0:50051/v1/infer")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()

