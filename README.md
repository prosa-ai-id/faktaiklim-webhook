<div align="center">
<p>
  <img src="images/logo.png" alt="Logo FaktaIklim">
</p>
</div>

# FaktaIklim Telegram API

FaktaIklim Telegram API is provides telegram webhook BOT API.

## Table of Contents

- [Components](#components)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Development](#development)
- [Production](#production)
- [Telegram Webhook Setup](#telegram-webhook-setup)

## Components

The project consists of two main components:
1. Telegram Webhook Service

## Prerequisites

- [uv package manager](https://docs.astral.sh/uv/)
- Docker (for RabbitMQ)

## Installation

### Telegram Webhook Setup

1. Synchronize dependencies:
    ```sh
    uv sync
    ```

2. Configure webhook environment:
    ```sh
    cp .env.example .env
    ```

### Running the Telegram Webhook

1. Start RabbitMQ:
    ```sh
    docker compose up rabbitmq
    ```

2. Launch the webhook:
    ```sh
    uv run python -m app.bot
    ```

3. Start the message processor:
    ```sh
    uv run python -m app.receiver
    ```

## Production

Follow the same steps as development setup, but ensure:
- RabbitMQ is properly configured for production use
- Environment variables are set for production
- Consider using process managers (e.g., PM2, Supervisor) for running the Python services

## Additional Notes

- The web application requires the backend service to be running
- Ensure all environment variables are properly configured before deployment
