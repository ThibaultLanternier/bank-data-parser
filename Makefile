test:
	poetry run pytest -v src/tests

extract:
	poetry run python src/bilig-cli.py extract

lint:
	poetry run ruff check --fix src
