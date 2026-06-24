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
- a remote inference server skeleton
- a Jetson client skeleton
- a small simulator for offline testing

## What is not included yet

- Jetson-specific ROS2 launch files
- real model weights loading
- vehicle control integration

