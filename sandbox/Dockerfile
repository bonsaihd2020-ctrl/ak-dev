FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:1
ENV VNC_PORT=5900
ENV NOVNC_PORT=6080

RUN apt-get update && apt-get install -y \
    xfce4 xfce4-goodies \
    x11vnc xvfb \
    novnc websockify \
    chromium-browser \
    git python3 python3-pip nodejs npm \
    build-essential curl wget sudo \
    dbus-x11 \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y \
    gnome-terminal \
    thunar \
    mousepad \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash devin && echo "devin:devin" | chpasswd && adduser devin sudo

WORKDIR /home/devin

COPY start.sh /home/devin/start.sh
RUN chmod +x /home/devin/start.sh

EXPOSE 5900 6080

USER devin
WORKDIR /workspace

CMD ["/home/devin/start.sh"]
