.PHONY: up down test ingest-sample ask ready health eval-ragas

up:
	docker compose up -d --build --wait

down:
	docker compose down

test:
	uv run pytest -v

ingest-sample:
	docker compose exec -T api uv run python -m ingestion.cli ingest data/sample/faq.md
	docker compose exec -T api uv run python -m ingestion.cli ingest data/sample/policies.md

ask:
	curl -s -X POST http://localhost:8000/ask \
		-H "Content-Type: application/json" \
		-d '{"query": "$(QUERY)"}' | python3 -m json.tool

ready:
	curl -s http://localhost:8000/ready | python3 -m json.tool

health:
	curl -s http://localhost:8000/health | python3 -m json.tool

eval-ragas:
	uv run python -m eval.ragas_run
