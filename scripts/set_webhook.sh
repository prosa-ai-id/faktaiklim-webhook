#!/usr/bin/env bash

TELEGRAM_TOKEN=XXXXXXXXXXXXXXXXXXXXXXX
WEBHOOK_URL=https://example.webhook.com

curl "https://api.telegram.org/bot$TELEGRAM_TOKEN/setWebhook?url=$WEBHOOK_URL"
