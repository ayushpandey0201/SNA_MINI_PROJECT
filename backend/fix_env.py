"""
Utility script to fix .env file structure.
This script should not contain hardcoded API keys.
API keys should be manually added to the .env file.
"""

import os

env_path = ".env"

if not os.path.exists(env_path):
    print(f".env file not found at {env_path}")
    print("Please create .env file manually with your API keys.")
    exit(1)

# Read and clean .env file
new_lines = []
has_gemini = False
has_groq = False
has_github = False

if os.path.exists(env_path):
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                new_lines.append(line)
                continue
            
            # Keep existing valid lines
            if line.startswith("DATABASE_URL="):
                new_lines.append(line)
            elif line.startswith("GITHUB_TOKEN=") or line.startswith("GITHUB_API_TOKEN="):
                new_lines.append(line)
                has_github = True
            elif line.startswith("GEMINI_API_KEY="):
                new_lines.append(line)
                has_gemini = True
            elif line.startswith("GROQ_API_KEY="):
                new_lines.append(line)
                has_groq = True
            elif "=" in line:
                # Other valid environment variables
                new_lines.append(line)
            else:
                # Invalid line, skip it
                pass

# Add missing keys as placeholders (user must fill them)
if not has_github:
    new_lines.append("# GitHub API Token (Optional)")
    new_lines.append("GITHUB_API_TOKEN=your_github_token_here")

if not has_groq:
    new_lines.append("# Groq API Key (Required)")
    new_lines.append("GROQ_API_KEY=your_groq_api_key_here")

if not has_gemini:
    new_lines.append("# Gemini API Key (Optional)")
    new_lines.append("GEMINI_API_KEY=your_gemini_api_key_here")

with open(env_path, "w") as f:
    f.write("\n".join(new_lines))
    
print("Cleaned .env file structure.")
print("Please manually add your API keys to the .env file.")
