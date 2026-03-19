import os
import sys
import json
import requests
import re

# Fix encoding for Windows terminal
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def extract_json(text):
    """Robustly extract JSON from text even if there's markdown or extra text."""
    try:
        # Try finding JSON block in markdown
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        
        # Try finding first { and last }
        first_brace = text.find('{')
        last_brace = text.rfind('}')
        if first_brace != -1 and last_brace != -1:
            json_str = text[first_brace:last_brace+1]
            return json.loads(json_str)
            
        return json.loads(text)
    except Exception:
        return None

def create_skill(description):
    model = "qwen3.5:2b"
    url = "http://localhost:11434/api/generate"
    
    system_prompt = """You are an expert developer of Agent Skills following the agentskills.io standard.
Return ONLY a JSON object with this exact structure:
{
  "name": "hyphenated-name",
  "skill_md": "Markdown content (string) with YAML frontmatter (name, description, license: MIT, metadata: version: '1.0').",
  "scripts": {"main.py": "python code..."},
  "references": {"README.md": "documentation content..."},
  "assets": {"config.json": "content..."}
}
Keep scripts and files simple but functional. Do not include any text outside the JSON block."""

    prompt = f"Create a comprehensive Agent Skill for: {description}"

    try:
        print(f"Contacting Ollama using {model}...")
        response = requests.post(url, json={
            "model": model,
            "system": system_prompt,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }, timeout=180)
        
        response.raise_for_status()
        result = response.json()
        raw_content = result.get('response', '')
        
        data = extract_json(raw_content)
        if not data:
            print("Error: Could not parse JSON from model response.")
            print("Raw response:", raw_content)
            return
        
        skill_name = data.get('name', 'new-skill').lower().strip()
        # Clean name from any unwanted characters
        skill_name = re.sub(r'[^a-z0-9\-]', '', skill_name)
        
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        skill_dir = os.path.join(base_dir, 'skills', skill_name)
        
        print(f"Generating skill '{skill_name}' in {skill_dir}...")
        
        os.makedirs(skill_dir, exist_ok=True)
        os.makedirs(os.path.join(skill_dir, 'scripts'), exist_ok=True)
        os.makedirs(os.path.join(skill_dir, 'references'), exist_ok=True)
        os.makedirs(os.path.join(skill_dir, 'assets'), exist_ok=True)
        
        with open(os.path.join(skill_dir, 'SKILL.md'), 'w', encoding='utf-8') as f:
            f.write(data.get('skill_md', '# Skill\nNo content generated.'))
            
        for filename, content in data.get('scripts', {}).items():
            content_str = content if isinstance(content, str) else json.dumps(content, indent=2)
            with open(os.path.join(skill_dir, 'scripts', filename), 'w', encoding='utf-8') as f:
                f.write(content_str)
                
        for filename, content in data.get('references', {}).items():
            content_str = content if isinstance(content, str) else json.dumps(content, indent=2)
            with open(os.path.join(skill_dir, 'references', filename), 'w', encoding='utf-8') as f:
                f.write(content_str)
        
        for filename, content in data.get('assets', {}).items():
            content_str = content if isinstance(content, str) else json.dumps(content, indent=2)
            with open(os.path.join(skill_dir, 'assets', filename), 'w', encoding='utf-8') as f:
                f.write(content_str)

        print(f"Success: Skill '{skill_name}' created successfully.")
        
    except Exception as e:
        print(f"Error creating skill: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python create_skill.py 'Description of the skill'")
    else:
        create_skill(" ".join(sys.argv[1:]))
