# dev-intel

A FastAPI + SQLite + NetworkX project for developer intelligence analysis.

## Setup

1.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    ```

2.  **Activate the virtual environment:**
    *   Windows: `.\venv\Scripts\activate`
    *   macOS/Linux: `source venv/bin/activate`

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**
    *   Copy `.env.example` to `.env`
    *   Update `.env` with your API keys

## Running the App

1.  **Start the backend:**
    ```bash
    uvicorn backend.app:app --reload
    ```

2.  **Access the API:**
    *   Open `http://localhost:8000` in your browser.
    *   API documentation: `http://localhost:8000/docs`
