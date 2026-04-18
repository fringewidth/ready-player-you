# Prototype

Temporary Blender workspace for piloting the avatar scene.

Drop the working `.blend` file in this folder and use it as the live control target.

## Purpose

This folder exists to learn the control surface before building the cleaner generator.
Use it to:

- load and inspect the scene
- apply commands to avatar parameters
- test camera and lighting presets
- verify render output quickly in headless mode

## Expected files

- `scene.blend` or another working Blender file
- optional notes or command scripts while iterating

## Pilot workflow

The prototype should be driven by commands like:

- set slider values
- switch camera presets
- switch HDRI presets
- choose asset variants
- render current frame

The implementation here should stay minimal and disposable.

