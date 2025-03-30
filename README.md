# Nexus AI Assistant

## Overview

Nexus is a web application featuring an AI assistant built with Flask (Python) for the backend and React (JavaScript) for the frontend. It utilizes a RAG (Retrieval-Augmented Generation) approach with local AI models (via Ollama) and tools to provide context-aware and capable responses.

## Project Structure

```
Nexus/
├── backend/ # Flask Application
│   ├── app/ # Main application package
│   │   ├── api/ # API Blueprints (auth, user, assistant)
│   │   ├── assistant/ # Core AI Logic (Orchestrator, LLM, RAG, Tools)
│   │   ├── models/ # SQLAlchemy DB Models
│   │   └── __init__.py # App factory
│   ├── migrations/ # Flask-Migrate scripts (created by 'flask db init')
│   ├── vector_db/ # Local vector store data (ChromaDB) - gitignored
│   ├── venv/ # Python virtual environment - gitignored
│   ├── .env # Environment variables - gitignored
│   ├── config.py # Configuration loading
│   ├── requirements.txt # Python dependencies
│   ├── run.py # App entry point / runner
│   └── manage.py # CLI for DB tasks, etc.
│
├── frontend/ # React Application (Setup separately)
│   ├── public/
│   ├── src/ # React source code (components, pages, context, api)
│   ├── package.json # Node dependencies
│   └── ...
│
├── .gitignore # Specifies intentionally untracked files
└── README.md # This file
```

## Prerequisites

*   **Python 3.8+** and `pip`
*   **Node.js** and `npm` (or `yarn`) - *For Frontend Setup*
*   **Database:**
    *   Default: SQLite (no external server needed).
    *   Optional: PostgreSQL Server (if you change `DATABASE_URL` in `backend/.env` and uncomment `psycopg2-binary` in `backend/requirements.txt`).
*   **Ollama** installed and running locally ([https://ollama.com/](https://ollama.com/))
*   **Required Ollama Models** (Pull these before starting):
    ```bash
    # Ensure Ollama service is running first
    ollama pull llama3:8b        # Or your preferred chat model from OLLAMA_DEFAULT_MODEL
    ollama pull nomic-embed-text # Or your preferred embedding model from OLLAMA_EMBEDDING_MODEL
    ```

## Backend Setup

1.  **Navigate to Backend:**
    ```bash
    cd Nexus/backend
    ```
2.  **Create Virtual Environment:**
    ```bash
    python -m venv venv
    # Activate the environment
    source venv/bin/activate  # macOS/Linux
    # venv\Scripts\activate    # Windows (Command Prompt/PowerShell)
    ```
3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Create `.env` File:**
    *   Copy the example: `cp .env .env` (or copy manually).
    *   **Crucially, generate and set a strong `SECRET_KEY`**.
    *   Verify `DATABASE_URL` (defaults to `sqlite:///app.db`).
    *   Verify `OLLAMA_*` variables match your setup (defaults should work if Ollama runs locally on port 11434).
    *   Verify `VECTOR_DB_PATH` (defaults to `./vector_db`).
5.  **Setup Database:**
    *   Ensure your database system is ready (if not using SQLite).
    *   Set the `FLASK_APP` environment variable (needed for Flask CLI commands):
        ```bash
        export FLASK_APP=manage.py  # macOS/Linux
        # set FLASK_APP=manage.py     # Windows (Command Prompt)
        # $env:FLASK_APP = "manage.py" # Windows (PowerShell)
        # (You might need to do this each time you open a new terminal, or add it to your shell profile/.env)
        ```
    *   Initialize and apply database migrations:
        ```bash
        flask db init    # Run only once to create the 'migrations' folder
        flask db migrate -m "Initial migration" # Create the first migration script
        flask db upgrade # Apply the migration to create tables
        ```
    *   *(Note: If `flask db init` says already exists, just run `migrate` and `upgrade`)*
6.  **(Optional) Seed Database:**
    ```bash
    flask seed_db # Creates a default admin user (admin/password)
    ```

## Frontend Setup (Example using Create React App)

*(These steps assume you will create the frontend separately)*

1.  **Navigate to Root Directory:**
    ```bash
    cd .. # From backend directory
    # or cd Nexus/ from anywhere
    ```
2.  **Create React App:**
    ```bash
    npx create-react-app frontend
    ```
3.  **Navigate to Frontend:**
    ```bash
    cd frontend
    ```
4.  **Install Dependencies:**
    ```bash
    npm install axios react-router-dom
    # or yarn add axios react-router-dom
    ```
5.  **Replace `src/` Contents:**
    *   Copy the provided frontend code snippets (`App.js`, `index.js`, `api/assistant.js`, `context/AuthContext.js`, `pages/...`) into the `frontend/src/` directory, creating subdirectories as needed.
6.  **(Optional) Configure Proxy:** To simplify API calls during development, add a proxy entry to `frontend/package.json`:
    ```json
    "proxy": "http://localhost:5000",
    ```
    (Restart the frontend server after adding this).

## Running the Application

1.  **Run Ollama:** Make sure your Ollama service is running in the background.
2.  **Run Backend Server:**
    *   Open a terminal in `Nexus/backend`.
    *   Activate the virtual environment (`source venv/bin/activate` or `venv\Scripts\activate`).
    *   Ensure `FLASK_APP=manage.py` is set (see Backend Setup step 5).
    *   Start the server:
        ```bash
        flask run --host=0.0.0.0 --port=5000
        # or python run.py
        ```
    *   The backend API will be available at `http://localhost:5000`.
3.  **Run Frontend Server:**
    *   Open a *separate* terminal in `Nexus/frontend`.
    *   Start the React development server:
        ```bash
        npm start
        # or yarn start
        ```
    *   This should open `http://localhost:3000` (or another port) in your browser. If the proxy is set up, API calls to `/api/...` will be forwarded to the backend.

## RAG Setup (Optional)

*   Documents for the RAG system need to be ingested. Create an ingestion script or add a command to `manage.py` that uses `app.assistant.rag.vector_store.add_document`.
*   Example (conceptual command): `flask rag_ingest --source ./path/to/your/documents`
*   The vector database (ChromaDB) will store data in the directory specified by `VECTOR_DB_PATH` in `backend/.env` (defaults to `backend/vector_db`).

## Contributing

[Details on contributing guidelines if applicable]

## License

[Specify your project's license, e.g., MIT, Apache 2.0]
