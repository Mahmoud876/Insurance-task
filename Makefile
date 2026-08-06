.PHONY: install dev build test lint format clean help

help:
	@echo "Available commands:"
	@echo "  make install   Install project dependencies"
	@echo "  make dev       Start the development server"
	@echo "  make build     Build the frontend"
	@echo "  make test      Run tests"
	@echo "  make lint      Run ESLint"
	@echo "  make format    Format the code"
	@echo "  make clean     Remove node_modules"

install:
	npm install

dev:
	npm run dev

build:
	npm run build

test:
	npm run test

lint:
	npm run lint

format:
	npm run format

clean:
	rm -rf node_modules
