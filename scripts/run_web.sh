#!/bin/zsh
cd ~/Desktop/mcp-map-company/web
/usr/bin/python3 -m http.server 3000 >> ../scripts/web_server.log 2>&1
