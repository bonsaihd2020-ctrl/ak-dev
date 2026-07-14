from __future__ import annotations
import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional


TEMPLATES = {
    "react-app": {
        "name": "React App",
        "description": "Modern React app with Vite + TypeScript",
        "category": "Frontend",
        "files": {
            "package.json": '''{
  "name": "my-react-app",
  "private": true,
  "version": "0.0.1",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0"
  }
}''',
            "index.html": '<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="UTF-8" />\n  <title>My App</title>\n</head>\n<body>\n  <div id="root"></div>\n  <script type="module" src="/src/main.tsx"></script>\n</body>\n</html>',
            "src/main.tsx": 'import React from "react";\nimport ReactDOM from "react-dom/client";\nimport App from "./App";\n\nReactDOM.createRoot(document.getElementById("root")!).render(\n  <React.StrictMode>\n    <App />\n  </React.StrictMode>\n);',
            "src/App.tsx": 'export default function App() {\n  return <div><h1>Hello World</h1></div>;\n}',
            "src/App.css": "body { font-family: sans-serif; margin: 0; padding: 20px; }",
            "tsconfig.json": '{\n  "compilerOptions": {\n    "target": "ES2020",\n    "useDefineForClassFields": true,\n    "lib": ["ES2020", "DOM", "DOM.Iterable"],\n    "module": "ESNext",\n    "skipLibCheck": true,\n    "moduleResolution": "bundler",\n    "allowImportingTsExtensions": true,\n    "resolveJsonModule": true,\n    "isolatedModules": true,\n    "noEmit": true,\n    "jsx": "react-jsx",\n    "strict": true\n  },\n  "include": ["src"]\n}',
            "vite.config.ts": 'import { defineConfig } from "vite";\nimport react from "@vitejs/plugin-react";\nexport default defineConfig({ plugins: [react()] });',
        },
    },
    "python-api": {
        "name": "Python FastAPI",
        "description": "FastAPI REST API with async endpoints",
        "category": "Backend",
        "files": {
            "main.py": 'from fastapi import FastAPI\nfrom pydantic import BaseModel\n\napp = FastAPI()\n\nclass Item(BaseModel):\n    name: str\n    price: float\n\n@app.get("/")\nasync def root():\n    return {"message": "Hello World"}\n\n@app.get("/items/{item_id}")\nasync def read_item(item_id: int):\n    return {"item_id": item_id}\n\n@app.post("/items/")\nasync def create_item(item: Item):\n    return item\n',
            "requirements.txt": "fastapi==0.115.0\nuvicorn[standard]==0.30.0\npydantic==2.5.0",
            "Dockerfile": "FROM python:3.11-slim\nWORKDIR /app\nCOPY . .\nRUN pip install -r requirements.txt\nEXPOSE 8000\nCMD [\"uvicorn\", \"main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\"]",
        },
    },
    "node-api": {
        "name": "Node.js Express API",
        "description": "Express.js REST API server",
        "category": "Backend",
        "files": {
            "package.json": '{\n  "name": "my-api",\n  "version": "1.0.0",\n  "main": "server.js",\n  "scripts": {\n    "start": "node server.js",\n    "dev": "nodemon server.js"\n  },\n  "dependencies": {\n    "express": "^4.18.0",\n    "cors": "^2.8.5"\n  }\n}',
            "server.js": "const express = require('express');\nconst cors = require('cors');\nconst app = express();\napp.use(cors());\napp.use(express.json());\n\napp.get('/', (req, res) => {\n  res.json({ message: 'Hello World' });\n});\n\napp.listen(3000, () => console.log('Server running on port 3000'));\n",
        },
    },
    "chrome-extension": {
        "name": "Chrome Extension",
        "description": "Manifest V3 Chrome Extension boilerplate",
        "category": "Extension",
        "files": {
            "manifest.json": '{\n  "manifest_version": 3,\n  "name": "My Extension",\n  "version": "1.0.0",\n  "description": "A Chrome extension",\n  "permissions": ["activeTab"],\n  "action": {\n    "default_popup": "popup.html",\n    "default_icon": "icon.png"\n  },\n  "background": {\n    "service_worker": "background.js"\n  }\n}',
            "popup.html": '<!DOCTYPE html>\n<html><head><style>body { width: 300px; padding: 10px; }</style></head><body>\n<h3>My Extension</h3>\n<p>Hello from the popup!</p>\n</body></html>',
            "popup.js": 'document.addEventListener("DOMContentLoaded", () => {\n  console.log("Popup loaded");\n});',
            "background.js": 'chrome.runtime.onInstalled.addListener(() => {\n  console.log("Extension installed");\n});',
        },
    },
    "python-ml": {
        "name": "Python ML Project",
        "description": "Machine learning project with scikit-learn",
        "category": "Data Science",
        "files": {
            "requirements.txt": "numpy\npandas\nscikit-learn\nmatplotlib\njupyter",
            "train.py": 'import pandas as pd\nfrom sklearn.model_selection import train_test_split\nfrom sklearn.ensemble import RandomForestClassifier\nfrom sklearn.metrics import accuracy_score\n\n# Load data\ndf = pd.read_csv("data.csv")\n\n# Split data\nX_train, X_test, y_train, y_test = train_test_split(\n    df.drop("target", axis=1), df["target"], test_size=0.2\n)\n\n# Train model\nmodel = RandomForestClassifier()\nmodel.fit(X_train, y_train)\n\n# Evaluate\npreds = model.predict(X_test)\nprint(f"Accuracy: {accuracy_score(y_test, preds):.2%}")\n',
            "notebooks/eda.ipynb": '{"cells": [{"cell_type": "markdown", "source": ["# EDA\\nExploratory Data Analysis"]}], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}',
        },
    },
    "docker-compose": {
        "name": "Docker Compose Full Stack",
        "description": "Full stack app with frontend + backend + database",
        "category": "DevOps",
        "files": {
            "docker-compose.yml": 'version: "3.8"\nservices:\n  frontend:\n    build: ./frontend\n    ports:\n      - "3000:3000"\n    depends_on:\n      - backend\n\n  backend:\n    build: ./backend\n    ports:\n      - "8000:8000"\n    environment:\n      - DATABASE_URL=postgres://user:pass@db:5432/mydb\n    depends_on:\n      - db\n\n  db:\n    image: postgres:16\n    environment:\n      - POSTGRES_USER=user\n      - POSTGRES_PASSWORD=pass\n      - POSTGRES_DB=mydb\n    volumes:\n      - pgdata:/var/lib/postgresql/data\n    ports:\n      - "5432:5432"\n\nvolumes:\n  pgdata:\n',
            "README.md": "# Full Stack App\\n\\n## Run\\n```bash\\ndocker-compose up --build\\n```\\n",
        },
    },
}


class TemplateManager:
    def __init__(self) -> None:
        self._custom_dir = Path.home() / ".devin-clone" / "templates"
        self._custom_dir.mkdir(parents=True, exist_ok=True)

    def list_templates(self) -> Dict[str, Any]:
        templates = []
        for tid, t in TEMPLATES.items():
            templates.append({
                "id": tid,
                "name": t["name"],
                "description": t["description"],
                "category": t["category"],
                "file_count": len(t["files"]),
            })
        for f in self._custom_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                templates.append({
                    "id": f.stem,
                    "name": data.get("name", f.stem),
                    "description": data.get("description", ""),
                    "category": data.get("category", "Custom"),
                    "file_count": len(data.get("files", {})),
                    "custom": True,
                })
            except Exception:
                continue
        return {"success": True, "templates": templates}

    def get_template(self, template_id: str) -> Dict[str, Any]:
        if template_id in TEMPLATES:
            return {"success": True, "template": TEMPLATES[template_id]}
        custom_file = self._custom_dir / f"{template_id}.json"
        if custom_file.exists():
            data = json.loads(custom_file.read_text(encoding="utf-8"))
            return {"success": True, "template": data}
        return {"success": False, "error": f"Template not found: {template_id}"}

    def create_project(self, template_id: str, target_dir: str, project_name: str = "") -> Dict[str, Any]:
        result = self.get_template(template_id)
        if not result.get("success"):
            return result
        template = result["template"]
        files = template.get("files", {})
        target = Path(target_dir)
        created_files = []
        try:
            for file_path, content in files.items():
                full_path = target / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                if project_name and "{{name}}" in content:
                    content = content.replace("{{name}}", project_name)
                full_path.write_text(content, encoding="utf-8")
                created_files.append(file_path)
            return {"success": True, "created_files": created_files, "target": str(target)}
        except Exception as e:
            return {"success": False, "error": str(e), "created_files": created_files}

    def save_custom_template(self, name: str, description: str, category: str, files: Dict[str, str]) -> Dict[str, Any]:
        try:
            data = {"name": name, "description": description, "category": category, "files": files}
            path = self._custom_dir / f"{name.lower().replace(' ', '_')}.json"
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return {"success": True, "path": str(path)}
        except Exception as e:
            return {"success": False, "error": str(e)}


_template_manager = TemplateManager()


def get_template_manager() -> TemplateManager:
    return _template_manager
