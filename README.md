# Jumperless

An interactive shell for the [Jumperless Breadboard](https://github.com/Architeuthis-Flux/Jumperless).

## Commands

##### 1. Connecting two rails:
```
5V-12
```

##### 2. Connecting a series:
```
1-2-3-4-5
```

##### 3. Remove a rail from a net
 ```
-20
```
Remove rail 20.

##### 4. Chain multiple commands with commas:
```
VCC-1, GND-8, -20, 20-40
```
Here we're saying: connect VCC to rail 1, connect GND to rail 8, disconnect rail 20 (from its current net), and reconnect it to rail 40.

##### 5. Series expansion:
Let's say you have some sensor with 6 pins in a row, and each pin needs to go somewhere. You place the sensor's `pin 1` on rail 10.
```
10++(GND, VCC, 33, 35, x, D10)
```
Will create the following connections: `10-GND`, `11-VCC`, `12-33`, `13-35`, and `15-D10`. Use `x` to skip.

## Other features

The shell supports saving and loading nets to/from file with the `save` and `load` commands.

Entering `flash` will put the attached Arduino Nano into "flash mode" which lets you upload sketches/firmware from other apps.


## Usage

Just run `python jumperless.py`

Tested on Windows running Python 3.12 with [1.1.1.7](https://github.com/Architeuthis-Flux/Jumperless/releases/download/1.1.1.1.7/firmware.uf2) firmware.
