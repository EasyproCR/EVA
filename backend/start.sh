#!/bin/bash

echo "Starting server..."

cd /c/Users/jimen/OneDrive/Escritorio/easypro/proyectos/eva/backend

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
