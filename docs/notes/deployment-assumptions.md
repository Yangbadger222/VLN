# Deployment assumptions

- Jetson runs the vehicle-side client.
- RTX 4070 runs the inference service.
- The first version uses a mock inference path so the repo is usable before hardware is ready.
- The model interface is chunk-based rather than single-action only.

