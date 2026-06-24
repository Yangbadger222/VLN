# VLN Deployment Scaffold

This repo is a starter scaffold for deploying the NaVIDA model to a Jetson-based robot with remote inference on an RTX 4070.

## Layout

- `navida_deploy/`: core Python package
- `configs/`: runtime config templates
- `scripts/`: local simulation and service entrypoints
- `docs/notes/`: design notes and deployment assumptions

## First goal

Run a local remote-inference mock, then point a Jetson-side client at it later.

## What is included

- request/response message types
- JSON codec for requests and responses
- a stdlib HTTP inference bridge
- a remote inference server skeleton
- a Jetson client skeleton
- a ROS2-friendly bridge layer that stays importable without ROS2
- a small simulator for offline testing

## Local smoke test

1. `python3 scripts/run_mock_server.py`
2. In another shell: `python3 scripts/run_http_client.py`

## Jetson path

The Jetson-side integration point lives in `navida_deploy/ros2_bridge.py`.
It is kept ROS-free for now so the repo can be developed before a Jetson
runtime is available.

## What is not included yet

- Jetson-specific ROS2 launch files
- real model weights loading
- vehicle control integration
