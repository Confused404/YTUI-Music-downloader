#!/bin/bash
# Quick one-liner to open Google Cloud Console to create OAuth2 credentials

xdg-open "https://console.cloud.google.com/apis/credentials" 2>/dev/null || \
open "https://console.cloud.google.com/apis/credentials" 2>/dev/null || \
echo "Please open: https://console.cloud.google.com/apis/credentials"
