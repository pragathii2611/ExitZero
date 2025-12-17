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

# --- THE FIX: FORCE JSON MODE ---
# This configuration forces Gemini to return ONLY valid JSON. 
# No markdown, no chatting, no errors.
json_config = {
    "response_mime_type": "application/json"
}

model = genai.GenerativeModel(
    'models/gemini-2.5-flash',
    generation_config=json_config
)

# --- PROMPTS ---
STRATEGY_PROMPT = """
You are a Senior Staff Engineer. Analyze the Job Description (JD).
1. Identify the 3 most critical hard skills.
2. Design a "Proof of Work" project that uses these skills.
3. The project must be complex enough to impress (e.g. System Design, not just To-Do apps).

Return a JSON object with this structure:
{
  "title": "Project Name",
  "tagline": "One sentence pitch.",
  "difficulty": "Intermediate",
  "tech_stack": "Tech 1 • Tech 2 • Tech 3",
  "readme_content": "# Project Title\\n\\n[Full Professional Markdown Readme]..."
}
"""

CODE_GEN_PROMPT = """
You are a DevOps Engineer. Generate the STARTER CODE for this specific project.
Project: {title}
Stack: {stack}

Return a JSON object where KEYS are filenames and VALUES are the file content.
Include:
1. A 'README.md' (Professional, explaining the project)
2. A dependency file ('requirements.txt' or 'package.json' based on stack)
3. A main entry file ('app.py', 'index.js', or 'main.go') containing basic setup/boilerplate.
4. A text file 'recruiter_dm.txt' with a professional LinkedIn message script.

JSON Structure:
{
  "README.md": "# Content...",
  "requirements.txt": "flask\\npandas...",
  "app.py": "print('Starting project...')",
  "recruiter_dm.txt": "Hi [Name], I built..."
}
"""

# --- PAGE ROUTES ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/how-it-works')
def how_it_works():
    return render_template('how_it_works.html')

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

# --- API ROUTE: GENERATE STRATEGY ---
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

        # Since we use JSON mode, response.text IS valid JSON. No cleaning needed.
        response = model.generate_content(full_prompt)
        project_data = json.loads(response.text)
        
        return jsonify(project_data), 200

    except Exception as e:
        print(f"❌ Generate Error: {e}")
        # Print raw response to debug if needed
        try: print(f"Raw AI Response: {response.text}") 
        except: pass
        return jsonify({"error": "AI Error. Please try again."}), 500

# --- API ROUTE: DOWNLOAD KIT ---
@app.route('/download-kit', methods=['POST'])
def download_kit():
    data = request.json
    title = data.get('title')
    stack = data.get('tech_stack')

    if not title:
        return jsonify({"error": "Missing project data"}), 400

    try:
        prompt = CODE_GEN_PROMPT.format(title=title, stack=stack)
        
        # JSON Mode ensures this never fails
        response = model.generate_content(prompt)
        files_json = json.loads(response.text)

        # Create ZIP in Memory
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for filename, content in files_json.items():
                # Clean filename just in case
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
        try: print(f"Raw AI Response: {response.text}") 
        except: pass
        return jsonify({"error": "Could not build the starter kit. Please try again."}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)