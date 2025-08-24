# CSE299

-----

# 📅 NSU Scheduler Project

A full-stack web application designed to help users schedule and manage their events, tasks, and reminders with seamless Google Calendar integration.

-----

## ✨ Features

  * **Event Creation:** Easily create, view, and manage different types of events like assignments, exams, projects, and reminders.
  * **Google Calendar Sync:** Automatically add and sync events with your primary Google Calendar.
  * **Secure Authentication:** User authentication handled via Google OAuth 2.0.
  * **Responsive UI:** Clean and modern user interface built with React and Tailwind CSS.

-----

## 🛠️ Tech Stack

  * **Frontend:** React, TypeScript, Vite, Tailwind CSS
  * **Backend:** Python, FastAPI, SQLModel, PostgreSQL
  * **Authentication:** Google OAuth 2.0

-----

## ✅ Prerequisites

Before you begin, ensure you have the following installed on your system:

  * [Node.js](https://nodejs.org/en/) (which includes npm)
  * [Python 3.8+](https://www.python.org/downloads/)
  * A running PostgreSQL database instance (e.g., via Docker, Neon, or a local installation).

-----

## 🚀 Getting Started

To get the project up and running on your local machine, follow these steps.

### **1. Clone the Repository**

First, clone the project from GitHub:

```bash
git clone <your-repository-url>
cd <your-project-folder>
```

### **2. Backend Setup**

The backend server connects to the database and handles all the core logic.

1.  **Navigate to the Backend Directory:**

    ```bash
    cd backend
    ```

2.  **Create and Activate a Virtual Environment:**

      * On **Windows**:
        ```bash
        python -m venv env
        env\Scripts\activate
        ```
      * On **macOS/Linux**:
        ```bash
        python3 -m venv env
        source env/bin/activate
        ```

3.  **Install Dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Set Up Environment Variables:**
    Create a file named `.env` in the `backend` directory and add your credentials. Use the `.env.example` file as a template.

    ```env
    DATABASE_URL="postgresql://user:password@host:port/dbname"
    GOOGLE_CLIENT_ID="your_google_client_id.apps.googleusercontent.com"
    GOOGLE_CLIENT_SECRET="your_google_client_secret"
    ```

5.  **Run the Backend Server:**

    ```bash
    uvicorn main:app --reload
    ```

    The backend API will now be running at `http://localhost:8000`. Keep this terminal open.

### **3. Frontend Setup**

The frontend provides the user interface. **Open a new terminal** for these steps.

1.  **Navigate to the Frontend Directory:**

    ```bash
    cd frontend
    ```

2.  **Install Dependencies:**

    ```bash
    npm install
    ```

3.  **Run the Frontend Development Server:**

    ```bash
    npm run dev
    ```

    The application will now be running and accessible in your browser.

    🎉 **Open your browser and navigate to: [http://localhost:5173](https://www.google.com/search?q=http://localhost:5173)**