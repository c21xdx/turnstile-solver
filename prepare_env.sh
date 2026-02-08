#!/bin/bash

set -e

PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true npm install puppeteer

apt-get update
apt-get install -y \
    fonts-ipafont-gothic \
    fonts-wqy-zenhei \
    fonts-thai-tlwg \
    fonts-kacst \
    fonts-freefont-ttf \
    libxss1 \
    --no-install-recommends

ARCH=$(dpkg --print-architecture)

if [ "$ARCH" = "amd64" ]; then
    apt-get install -y wget gnupg
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google.list
    apt-get update
    apt-get install -y google-chrome-stable --no-install-recommends
    BROWSER_EXEC="google-chrome-stable"
elif [ "$ARCH" = "arm64" ]; then
    apt-get install -y chromium --no-install-recommends
    BROWSER_EXEC="chromium"
else
    exit 1
fi

rm -rf /var/lib/apt/lists/*

chrome_path=$(which "$BROWSER_EXEC")
mv "$chrome_path" ./google-chrome-stable

npm install

echo "Setup complete"
