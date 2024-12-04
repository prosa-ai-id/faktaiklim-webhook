webhook:
	uv run python -m app.bot

processor:
	uv run python -m app.receive 1

ngrok:
	ngrok http http://localhost:8711
