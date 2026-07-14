#!/bin/bash
set -e

Xvfb :1 -screen 0 1920x1080x24 &
sleep 2

export DISPLAY=:1

xfce4-session &
sleep 3

x11vnc -display :1 -nopw -listen 0.0.0.0 -rfbport 5900 -forever -shared &
sleep 1

websockify --web=/usr/share/novnc 6080 localhost:5900 &
sleep 1

echo "====================================="
echo "Sandbox ready!"
echo "noVNC: http://localhost:6080/vnc.html"
echo "VNC:   localhost:5900"
echo "====================================="

mkdir -p /workspace
tail -f /dev/null
