import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for
from pypdf import PdfReader

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
DB_NAME = "talent_screener.db"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS screening_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            requested_keywords TEXT,
            match_percentage INTEGER,
            found_keywords TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def screen_resume_offline(file_path, target_keywords):
    try:
        reader = PdfReader(file_path)
        full_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
        
        # Standardize structural text values to lowercase for exact local pattern matching
        lower_text = full_text.lower()
        
        # Cleanly split keywords by commas and drop empty entries
        targets = [kw.strip().lower() for kw in target_keywords.split(",") if kw.strip()]
        if not targets:
            return 0, "No criteria specified."
            
        matched_list = []
        for kw in targets:
            if kw in lower_text:
                matched_list.append(kw.upper()) # Capitalize findings for high-visibility UI badges
                
        # Handle dynamic matching math calculations natively
        score = int((len(matched_list) / len(targets)) * 100)
        matched_str = ", ".join(matched_list) if matched_list else "None matched."
        
        return score, matched_str
        
    except Exception as e:
        print(f"❌ Local string parsing match error: {e}")
        return 0, "Error reading document text."

@app.route("/", methods=["GET"])
def index():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT filename, requested_keywords, match_percentage, found_keywords FROM screening_history ORDER BY id DESC")
    db_rows = cursor.fetchall()
    conn.close()
    return render_template("index.html", history=db_rows)

@app.route("/upload", methods=["POST"])
def upload():
    keywords_input = request.form.get("target_keywords", "")
    file = request.files.get("resume_pdf")
    
    if file and file.filename != "":
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        
        # Compute multi-keyword search index scores local-side
        match_score, discovered_items = screen_resume_offline(file_path, keywords_input)
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO screening_history (filename, requested_keywords, match_percentage, found_keywords)
            VALUES (?, ?, ?, ?)
        """, (file.filename, keywords_input, match_score, discovered_items))
        conn.commit()
        conn.close()
        
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True, port=5000)