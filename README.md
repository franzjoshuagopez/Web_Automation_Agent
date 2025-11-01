# Web_Automation_Agent
## Introduction
This is one of my learning projects where I try to implement multiple tools from selenium to allow AI agents to automate web based tasks.

Programming languages:
1. Python
2. HTML
3. CSS
4. Typescript

Frameworks:
1. Fast API
2. REACT

## Instructions

1. Clone this repository
2. In your code editor:
- Open project root folder
- In terminal run:
  ```powerhsell
  python -m venv venv
  ```
- Activate the virtual enviornment:
  ```
  .\venv\Scripts\activate
  ```
- install requirements:
  ```
  pip install -r requirements.txt
  ```
- Go to folder frotnend
```
cd frontend
```
- Run node js package installation
```
npm install
```
- Go back to to root folder
```
cd ..
```
3. Run the backend via uvicorn
```
$env:ENV="development"; uvicorn backend.main:app --reload
```
4. Run the frontend
- Open a separate terminal
```
cd frontend
```
```
npm run dev
```
5. Go to on your browser:
```
http://localhost:8080/
```

