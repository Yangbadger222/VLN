# Deployment assumptions

- Jetson runs the vehicle-side client.
- RTX 4070 runs the inference service.
- The first version keeps a mock inference path so the repo is usable before hardware is ready.
- The 4070 service is HTTP on port 50051:
  - `GET /health`
  - `POST /v1/infer`
- The model interface is chunk-based rather than single-action only.
- The vehicle already has an STM32 chassis controller compatible with `serial_twistctl`.
- The Jetson runtime publishes `geometry_msgs/msg/Twist` to `/cmd_vel`; `serial_twistctl` forwards it to `/dev/serial_twistctl`.
- Positive `angular.z` is assumed to mean left turn. If the vehicle turns the opposite way, set `angular_z_scale: -1.0`.
