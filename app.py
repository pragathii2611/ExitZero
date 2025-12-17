import os
import json
import io
import zipfile
import re
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, send_file
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# --- CONFIGURATION ---
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

json_config = { "response_mime_type": "application/json" }
model = genai.GenerativeModel('models/gemini-2.5-flash', generation_config=json_config)

# --- PROMPTS ---
STRATEGY_PROMPT = """
You are a Senior Staff Engineer. Analyze the Job Description (JD).
1. Identify critical skills.
2. Design a "Proof of Work" project.
3. Return JSON.

JSON Schema:
{
  "title": "Project Name",
  "tagline": "Pitch.",
  "difficulty": "Intermediate",
  "tech_stack": "Tech 1 • Tech 2",
  "readme_content": "## Introduction\\n[Short Summary]...\\n\\n## Key Features\\n- Feature 1"
}
"""

# NEW PROMPT: Generates the "Premium Assets" inside the Zip
CODE_GEN_PROMPT = """
You are a DevOps Engineer. Generate the STARTER KIT for this project.
Project: {title}
Stack: {stack}

Return JSON where KEYS are filenames and VALUES are file content.
You MUST include these specific files:

1. README.md (Technical setup guide)
2. INTERVIEW_PREP.md (5 tough questions a recruiter will ask about this specific project and the perfect answers)
3. LINKEDIN_POST.txt (A viral, professional post announcing this project to get recruiter attention)
4. requirements.txt (Dependencies)
5. main.py (or App.js - the entry point code)

JSON Schema:
{{
  "README.md": "# Setup Guide...",
  "INTERVIEW_PREP.md": "# Interview Cheat Sheet...",
  "LINKEDIN_POST.txt": "🚀 Just built...",
  "requirements.txt": "flask",
  "main.py": "print('Hello')"
}}
"""

# --- ROUTES ---
@app.route('/')
def home(): return render_template('index.html')

@app.route('/how-it-works')
def how_it_works(): return render_template('how_it_works.html')

@app.route('/pricing')
def pricing(): return render_template('pricing.html')

@app.route('/privacy')
def privacy(): return render_template('privacy.html')

@app.route('/terms')
def terms(): return render_template('terms.html')

@app.route('/contact')
def contact(): return render_template('contact.html')

# NEW: Simple Success Page instead of Dashboard
@app.route('/success')
def success():
    return render_template('success.html')

# --- API ---
@app.route('/generate', methods=['POST'])
def generate_project():
    data = request.json
    try:
        full_prompt = f"{STRATEGY_PROMPT}\n\nJOB DESCRIPTION:\n{data.get('jd_text', '')}"
        response = model.generate_content(full_prompt)
        return jsonify(json.loads(response.text)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download-kit', methods=['POST'])
def download_kit():
    data = request.json
    try:
        # Generate the Enhanced Zip content
        prompt = CODE_GEN_PROMPT.format(title=data.get('title'), stack=data.get('tech_stack'))
        response = model.generate_content(prompt)
        files = json.loads(response.text)

        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for name, content in files.items():
                zf.writestr(name, content)

        memory_file.seek(0)
        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', data.get('title')).lower()
        
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"{safe_name}_kit.zip"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=8000)