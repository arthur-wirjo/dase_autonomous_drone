#!/bin/bash
rpicam-vid -t 0 --codec yuv420 --width 1280 --height 720 --framerate 30 -o - | ffmpeg -f rawvideo -pix_fmt yuv420p -s 1280x720 -r 30 -i - -c:v libx264 -preset ultrafast -tune zerolatency -f mpegts udp://100.68.111.58:8888
