#!/bin/bash
rpicam-vid -t 0 --codec mjpeg --width 1280 --height 720 --framerate 30 --listen -o tcp://0.0.0.0:8888
