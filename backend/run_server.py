#!/usr/bin/env python3
"""Script simple para ejecutar el servidor FastAPI sin contexto de bash"""

import os
import sys

# Asegurar que estamos en el directorio correcto
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Agregar el directorio actual al path para los imports
sys.path.insert(0, os.getcwd())

if __name__ == "__main__":
    import uvicorn

    print(">>> Iniciando servidor FastAPI en puerto 8000...")
    print(">>> URL: http://localhost:8000")
    print(">>> Docs: http://localhost:8000/docs")

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
