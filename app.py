import os
import json
import io
import zipfile
import re
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, send_file
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# --- CONFIGURATION ---
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("❌ ERROR: GEMINI_API_KEY not found in .env file")

genai.configure(api_key=api_key)

# Configure JSON Mode (Prevents the "Bad JSON" crashes)
json_config = { "response_mime_type": "application/json" }
model = genai.GenerativeModel(
    'models/gemini-1.5-flash',
    generation_config=json_config
)

# --- PROMPTS ---
# Note: Curly braces are doubled {{ }} to prevent Python format errors
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
  "readme_content": "## Introduction\\n[Short Summary Only]...\\n\\n## Key Features\\n- Feature 1\\n- Feature 2"
}
"""

CODE_GEN_PROMPT = """
You are a DevOps Engineer. Generate the STARTER CODE for this project.
Project: {title}
Stack: {stack}

Return JSON where KEYS are filenames and VALUES are file content.
Include:
1. README.md (Full details)
2. requirements.txt (Dependencies)
3. main_entry_file (e.g. app.py or App.js)
4. recruiter_dm.txt (LinkedIn script)

JSON Schema:
{{
  "README.md": "# Title\\n\\n...",
  "requirements.txt": "package1\\npackage2",
  "app.py": "print('Hello World')",
  "recruiter_dm.txt": "Hi [Name]..."
}}
"""

# --- PAGE ROUTES (THE FIX IS HERE) ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/how-it-works')
def how_it_works():
    return render_template('how_it_works.html')

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

@app.route('/dashboard')  # <--- THIS WAS LIKELY MISSING
def dashboard():
    return render_template('dashboard.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

# --- API ROUTES ---
@app.route('/generate', methods=['POST'])
def generate_project():
    data = request.json
    jd_text = data.get('jd_text', '')

    if not jd_text or len(jd_text) < 10:
        return jsonify({"error": "Job Description is too short."}), 400

    try:
        full_prompt = f"{STRATEGY_PROMPT}\n\nJOB DESCRIPTION:\n{jd_text}"
        
        if data.get('regenerate'):
            full_prompt += "\n\nIMPORTANT: Generate a DIFFERENT project idea than before."

        response = model.generate_content(full_prompt)
        project_data = json.loads(response.text)
        return jsonify(project_data), 200

    except Exception as e:
        print(f"❌ Generate Error: {e}")
        return jsonify({"error": "AI Error. Please try again."}), 500

@app.route('/download-kit', methods=['POST'])
def download_kit():
    data = request.json
    title = data.get('title')
    stack = data.get('tech_stack')

    if not title:
        return jsonify({"error": "Missing project data"}), 400

    try:
        prompt = CODE_GEN_PROMPT.format(title=title, stack=stack)
        
        response = model.generate_content(prompt)
        files_json = json.loads(response.text)

        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for filename, content in files_json.items():
                clean_name = filename.strip().replace('/', '_').replace('\\', '_')
                zf.writestr(clean_name, content)

        memory_file.seek(0)
        
        safe_filename = re.sub(r'[^a-zA-Z0-9]', '_', title).lower()
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"{safe_filename}_starter_kit.zip"
        )

    except Exception as e:
        print(f"❌ Zip Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Could not build the starter kit."}), 500

if __name__ == '__main__':
    # Running on port 8000 to match your Lemon Squeezy settings
    app.run(debug=True, port=8000)