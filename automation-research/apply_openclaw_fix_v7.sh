#!/bin/bash
# apply_openclaw_fix_v7.sh (Final Proxy Solution)
# Purpose: Bypass "Invalid config" errors by running OpenClaw on localhost:18799
# and using a Node.js Proxy on 0.0.0.0:18789.

CONFIG_FILE="$HOME/.openclaw/openclaw.json"
PROXY_SCRIPT="$HOME/.openclaw/proxy.js"
SERVICE_FILE="$HOME/.config/systemd/user/openclaw.service"
PROXY_SERVICE_FILE="$HOME/.config/systemd/user/openclaw-proxy.service"

echo "[INFO] implementing PORT SHIFT + PROXY Strategy..."

# 1. Update Config: Port 18799, Bind Loopback (Safe Mode)
sed -i 's/"port": 18789/"port": 18799/' "$CONFIG_FILE"
sed -i 's/"bind": "0.0.0.0"/"bind": "loopback"/' "$CONFIG_FILE"
sed -i 's/"bind": "all"/"bind": "loopback"/' "$CONFIG_FILE"
sed -i 's/"mode": "remote"/"mode": "local"/' "$CONFIG_FILE"

echo "[INFO] Verified Config:"
grep -A 5 '"gateway":' "$CONFIG_FILE"

# 2. Create Node.js Proxy Script
cat <<EOF > "$PROXY_SCRIPT"
const net = require('net');

const LOCAL_PORT = 18799;
const PUBLIC_PORT = 18789;
const HOST = '0.0.0.0';

const server = net.createServer((socket) => {
    const client = new net.Socket();
    
    client.connect(LOCAL_PORT, '127.0.0.1', () => {
        socket.pipe(client);
        client.pipe(socket);
    });

    client.on('error', (err) => {
        // console.error('Connection error:', err.message);
        socket.end();
    });

    socket.on('error', (err) => {
        // console.error('Socket error:', err.message);
        client.end();
    });
});

server.listen(PUBLIC_PORT, HOST, () => {
    console.log(\`Proxy listening on \${HOST}:\${PUBLIC_PORT} -> 127.0.0.1:\${LOCAL_PORT}\`);
});

server.on('error', (err) => {
    console.error('Server error:', err);
});
EOF

# 3. Create Proxy Service
cat <<EOF > "$PROXY_SERVICE_FILE"
[Unit]
Description=OpenClaw Public Proxy (18789 -> 18799)
After=network.target openclaw.service

[Service]
ExecStart=/usr/bin/env node %h/.openclaw/proxy.js
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
EOF

# 4. Update Main Service (Cleanup 18799)
cat <<EOF > "$SERVICE_FILE"
[Unit]
Description=OpenClaw AI Gateway Service (User - Local 18799)
After=network.target

[Service]
WorkingDirectory=%h/.openclaw
Type=simple
Environment="LANG=en_US.UTF-8"
EnvironmentFile=%h/.openclaw/.env

# Cleanup Internal Port
ExecStartPre=-/bin/sh -c '/usr/bin/lsof -t -i:18799 | xargs -r kill -9'

ExecStart=%h/.npm-global/bin/openclaw gateway run

Restart=always
RestartSec=3
SyslogIdentifier=openclaw-gateway

[Install]
WantedBy=default.target
EOF

echo "[INFO] Reloading Daemon..."
systemctl --user daemon-reload

echo "[INFO] Stopping Old Services..."
systemctl --user stop openclaw
systemctl --user stop openclaw-proxy 2>/dev/null
pkill -f "proxy.js"
lsof -t -i:18789 | xargs -r kill -9
lsof -t -i:18799 | xargs -r kill -9

echo "[INFO] Starting Services..."
systemctl --user start openclaw
sleep 2
systemctl --user start openclaw-proxy

echo "[INFO] Verifying..."
sleep 2
systemctl --user status openclaw --no-pager
systemctl --user status openclaw-proxy --no-pager
sudo lsof -i :18789
sudo lsof -i :18799
