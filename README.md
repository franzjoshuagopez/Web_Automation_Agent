# Web Automation Agent

## 📌 Introduction
This project is a learning experiment where I integrate Selenium with an AI agent system to perform automated web-based tasks.  
The goal is to enable an AI agent to interact with web pages and perform actions automatically.

---
## 🛠️ Tech Stack

### **Languages**
- Python
- TypeScript
- HTML / CSS

### **Frameworks / Tools**
- FastAPI (Backend)
- React + Vite (Frontend)
- Selenium (Web Automation)
- LangGraph / LLM Agents (AI Logic)

---

## 🚀 Features
- AI-driven web task automation
- API backend with FastAPI
- Web UI built using React
- Real-time WebSocket communication
- Selenium browser automation engine

---

## Instructions

1. Clone this repository
2. In your code editor:
- Open project root folder
- In terminal run:
  ```powerhsell
  python -m venv venv
  ```
- Activate the virtual enviornment:
  ```powerhsell
  .\venv\Scripts\activate
  ```
- install requirements:
  ```powershell
  pip install -r requirements.txt
  ```
- Go to folder frotnend
```powershell
cd frontend
```
- Run node js package installation
```powershell
npm install
```
- Go back to to root folder
```powershell
cd ..
```
3. Run the backend via uvicorn
```powershell
$env:ENV="development"; uvicorn backend.main:app --reload
```
4. Run the frontend
- Open a separate terminal
```powershell
cd frontend
```
```powershell
npm run dev
```
5. Go to on your browser:
```
http://localhost:8080/
```

