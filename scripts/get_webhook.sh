#!/usr/bin/env bash

TELEGRAM_TOKEN=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

curl "https://api.telegram.org/bot$TELEGRAM_TOKEN/getWebhookInfo"
