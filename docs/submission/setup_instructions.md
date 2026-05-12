# 🚀 Setup Instructions: Iris. Analytics Platform

This guide will help you get the Iris. Operational Intelligence platform up and running in both Docker and Local Development environments.

## 🔑 Prerequisites

- **Node.js 18+** (For local frontend development)
- **Python 3.11+** (For local backend development)
- **Gemini API Key**: Required for the synthesis and reasoning layer. [Get it here](https://aistudio.google.com/app/apikey).

---

Docker 
This is the fastest way to launch the entire stack with persistence and automatic bootstrapping.

1.  **Clone the Repository**:
    ```bash
    git clone <repo-url>
    cd futures-first
    ```

2.  **Configure Environment (⚠️ REQUIRED)**:
    Before starting the application, you **must** configure your environment variables by copying the example file.

    ```bash
    # Copy the example config to create your actual config file
    cp .env.example .env
    ```

    Open the newly created `.env` file in a text editor and add your Gemini API Key:
    ```env
    GEMINI_API_KEY=your_actual_key_here
    APP_ENV=production
    ```
    *Note: Without this key, the AI response generation features will not function.*

3.  **Launch the Stack**:
    ```bash
    docker compose up --build
    ```
    - The system will automatically detect the first run and trigger the **Bootstrap Pipeline** to ingest CSV data and index PDF documents.
    - **Frontend**: [http://localhost:5173](http://localhost:5173)
    - **Backend API**: [http://localhost:8000](http://localhost:8000)

4.  **Shutdown**:
    ```bash
    docker compose down
    ```

---

## 💻 Option 2: Local Development
Use this if you want to modify code and see changes instantly.

### 1. Backend Setup
1.  **Navigate to root**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Initialize Data**:
    ```bash
    python -m backend.bootstrap
    ```
3.  **Start Server**:
    ```bash
    uvicorn backend.api.app:app --host 0.0.0.0 --port 8000 --reload
    ```

### 2. Frontend Setup
1.  **Navigate to frontend folder**:
    ```bash
    cd frontend
    npm install
    ```
2.  **Start Dev Server**:
    ```bash
    npm run dev
    ```
    - Access at [http://localhost:5173](http://localhost:5173)

---

## 🛠 Troubleshooting
- **Port Conflict**: Ensure ports `8000` and `5173` are not occupied.
- **Missing Data**: If the UI shows no sessions, ensure the `backend.bootstrap` command finished successfully.
- **API Errors**: Check the `logs/` directory for detailed backend error traces.
