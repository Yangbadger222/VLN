# VLN NaVIDA Deployment

This repo prepares a Jetson vehicle runtime that sends camera frames to a remote RTX 4070 inference service running `waynechu/NaVIDA`, then publishes safe `geometry_msgs/msg/Twist` commands to the chassis.

## Runtime Chain

1. Jetson camera node publishes `/navida/camera/image_raw`.
2. Jetson controller posts image + instruction to `http://REMOTE_INFERENCE_HOST:50051/v1/infer`.
3. The 4070 service runs the NaVIDA backend and returns action chunks.
4. Jetson maps actions to clamped `Twist` commands on `/cmd_vel`.
5. `serial_twistctl` subscribes `/cmd_vel` and writes STM32 serial commands like `vcx=0.200,wc=0.800`.

The copied chassis bridge lives under `ros2_ws/src/sensor_drivers/serial_twistctl`, with its local `serial` dependency in `ros2_ws/src/sensor_drivers/serial`.

## Local Smoke Test

```bash
python3 -m pip install -e ".[dev]"
python3 scripts/run_inference_server.py --backend mock --host 127.0.0.1 --port 50051
```

In another shell:

```bash
python3 scripts/run_http_client.py
python3 scripts/run_ros2_node.py
python3 -m pytest -q
```

## 4070 Inference Host

Host: `user@REMOTE_INFERENCE_HOST`

```bash
git clone https://github.com/Yangbadger222/VLN.git
cd VLN
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install --index-url https://download.pytorch.org/whl/cu121 torch torchvision torchaudio
python -m pip install -e ".[server]"
python scripts/run_inference_server.py --backend hf --host 0.0.0.0 --port 50051 --model-id waynechu/NaVIDA --device cuda --load-in-4bit
```

Health check:

```bash
curl http://127.0.0.1:50051/health
```

Use `--backend mock` first if CUDA/model dependencies are not ready yet.

## Jetson Vehicle Host

Host: `user@JETSON_HOST`

```bash
git clone https://github.com/Yangbadger222/VLN.git
cd VLN
python3 -m pip install -e .
sudo apt update
sudo apt install -y python3-opencv
cd ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
ros2 launch navida_vehicle navida_jetson.launch.py \
  inference_url:=http://REMOTE_INFERENCE_HOST:50051/v1/infer \
  serial_port:=/dev/serial_twistctl
```

`camera_device` now defaults to `auto`, which probes `/dev/video0` through `/dev/video5` and picks the first device that can return a frame. Override it explicitly with `camera_device:=/dev/video4` when you already know the correct capture node.

The Jetson-side bridge now JPEG-compresses ROS image frames before posting them to the 4070. That makes the payload a real decodable image for the HF backend and keeps the request size low enough for Tailscale links. `inference_timeout_s` defaults to `20.0` and can be raised further during first on-car tests.

If `/dev/serial_twistctl` does not exist yet, launch with the actual device, for example `serial_port:=/dev/ttyUSB0`. If turning is reversed, add `angular_z_scale:=-1.0`.

## ROS 2 Topics

- `/navida/camera/image_raw`: `sensor_msgs/msg/Image`, published by `navida_vehicle camera_publisher`.
- `/cmd_vel`: `geometry_msgs/msg/Twist`, published by `navida_vehicle remote_controller`.
- `serial_twistctl_node` subscribes `/cmd_vel` and sends serial chassis commands.

## Safety Defaults

- `max_linear_x: 0.3`
- `max_angular_z: 1.0`
- `command_timeout_s: 0.75`
- inference failure immediately publishes zero `Twist`

Tune these in `ros2_ws/src/navida_vehicle/config/navida_jetson.yaml` or through launch arguments.
