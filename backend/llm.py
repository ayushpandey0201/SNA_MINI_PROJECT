import os
import sys
import logging
import json

# Append parent directory to sys.path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.config import GROQ_API_KEY
from groq import Groq

# Track quota status to avoid repeated API calls when quota is exhausted
_quota_exhausted = False
logger = logging.getLogger(__name__)

def _is_quota_error(exception):
    """Check if exception is a quota/resource exhaustion error."""
    error_str = str(exception).lower()
    error_type = str(type(exception).__name__)
    return (
        "quota" in error_str or 
        "ResourceExhausted" in error_type or
        "429" in error_str or
        "exceeded" in error_str
    )

def generate_gemini_summary(text_corpus: str) -> str:
    """
    Generates a concise 5-6 line summary of a developer based on their text corpus using Groq AI.
    (Function name kept for backward compatibility, but now uses Groq instead of Gemini)
    
    Args:
        text_corpus (str): The combined text from bio, readmes, etc.
        
    Returns:
        dict: Dictionary with "role" and "summary" keys.
    """
    global _quota_exhausted
    
    if not GROQ_API_KEY:
        logger.warning("GROQ_API_KEY is missing. AI analysis unavailable.")
        return {
            "role": None,
            "summary": "AI analysis unavailable (API Key missing)."
        }
    
    # Skip API call if quota is known to be exhausted
    if _quota_exhausted:
        return {
            "role": None,
            "summary": "AI analysis temporarily unavailable (API quota exceeded)."
        }

    try:
        client = Groq(api_key=GROQ_API_KEY)
        
        prompt = f"""You are an expert technical recruiter and developer profiler. 
Analyze the following text corpus comprising a developer's GitHub bio, repository READMEs, and other metadata.

Task:
1. Identify the user's specific professional role based on their actual work, technologies, and projects. 
   Choose from these categories (be specific):
   - "Data Scientist" or "ML Engineer" (for ML/AI work)
   - "Frontend Developer" (for React/Vue/Angular/UI work)
   - "Backend Developer" (for API/server/database work)
   - "Full Stack Developer" (for both frontend and backend)
   - "DevOps Engineer" (for infrastructure/CI-CD work)
   - "Mobile Developer" (for iOS/Android work)
   - "Security Engineer" (for security-focused work)
   - "Game Developer" (for game development)
   - Or a specific role like "Senior Frontend Engineer", "ML Researcher", etc.
   
   IMPORTANT: Analyze the actual content - don't default to "Frontend Developer". Look at:
   - Programming languages used
   - Types of projects (web apps, ML models, APIs, mobile apps, etc.)
   - Technologies and frameworks mentioned
   - The nature of their work

2. Generate a professional summary in exactly 5-6 lines (medium length, not too short, not too long). 
   The summary should be comprehensive and cover:
   - Their professional identity and expertise
   - Key technologies and skills
   - Notable projects or contributions
   - Community involvement (if significant)
   - Research interests or specializations (if applicable)
   
   Each line should be a complete sentence. Total length should be approximately 100-150 words.

Output Format:
Return ONLY a JSON object with the following keys:
{{
    "role": "The specific role title based on actual analysis",
    "summary": "The professional summary text"
}}

Text Corpus:
{text_corpus[:10000]}"""

        # Use Groq's fast model - try different models if one fails
        try:
            response = client.chat.completions.create(
                model="llama-3.1-70b-versatile",  # Fast and capable model
                messages=[
                    {"role": "system", "content": "You are an expert technical recruiter. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500,
                response_format={"type": "json_object"}  # Force JSON response
            )
        except Exception as model_error:
            # If json_object format not supported, try without it
            logger.warning(f"JSON format not supported, trying without: {model_error}")
            response = client.chat.completions.create(
                model="llama-3.1-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are an expert technical recruiter. Always respond with valid JSON only in this format: {\"role\": \"...\", \"summary\": \"...\"}"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
        
        # Reset quota flag on success
        _quota_exhausted = False
        
        # Extract response text
        response_text = response.choices[0].message.content.strip()
        
        # Clean response text (sometimes model adds markdown code blocks)
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
            
        try:
            result = json.loads(response_text.strip())
            # Ensure it has the expected structure
            if "role" not in result:
                result["role"] = None
            if "summary" not in result:
                result["summary"] = response_text.strip()
            return result
        except json.JSONDecodeError:
            # Fallback if valid JSON isn't returned
            logger.warning(f"Groq returned invalid JSON, using fallback")
            # Try to extract role from the text if possible
            role = None
            if "role" in response_text.lower() or "developer" in response_text.lower():
                # Try to find a role in the text
                import re
                role_match = re.search(r'(?:role|title)[\s:"]*([^",\n]+)', response_text, re.IGNORECASE)
                if role_match:
                    role = role_match.group(1).strip()
            
            return {
                 "role": role,  # Return None if we can't extract, so it falls back to text classifier
                 "summary": response_text.strip()
            }
        
    except Exception as e:
        # Log the actual error so we can debug
        error_msg = str(e)
        error_type = type(e).__name__
        logger.error(f"Groq API Error: {error_type}: {error_msg}")
        print(f"ERROR: Groq API call failed: {error_type}: {error_msg}")
        
        # Check if this is a quota error
        if _is_quota_error(e):
            _quota_exhausted = True
            logger.warning("Groq API quota exceeded. AI features disabled. App will continue with fallback methods.")
            return {
                "role": None,
                "summary": "AI analysis temporarily unavailable (API quota exceeded). Using rule-based analysis instead."
            }
        else:
            # Other errors - log the full error and don't set quota flag
            # This allows retry on next call
            logger.warning(f"Groq API error (will retry next time): {error_type}: {error_msg[:200]}")
            print(f"WARNING: Groq API failed: {error_type}: {error_msg}")
            # Return None for role so it falls back to text classifier
            return {
                "role": None,
                "summary": None  # Return None so it uses rule-based summary instead
            }

def rank_recommendations_with_gemini(candidates: list, profile_context: str) -> list:
    """
    Ranks a list of candidate nodes using Groq AI based on relevance to the user profile.
    (Function name kept for backward compatibility, but now uses Groq instead of Gemini)
    
    Args:
        candidates (list): List of candidate dicts (must contain 'label', 'description', etc.).
        profile_context (str): Summary or bio of the target user.
        
    Returns:
        list: Top 4-5 ranked candidates.
    """
    global _quota_exhausted
    
    if not GROQ_API_KEY:
        logger.debug("GROQ_API_KEY is missing. Using original ranking order.")
        return candidates[:5]
    
    # Skip API call if quota is known to be exhausted
    if _quota_exhausted:
        logger.debug("Groq quota exhausted. Using original ranking order.")
        return candidates[:5]

    try:
        client = Groq(api_key=GROQ_API_KEY)
        
        # Prepare candidate descriptions for the prompt
        candidates_text = ""
        for i, cand in enumerate(candidates):
            candidates_text += f"{i}. Name: {cand.get('label')}\n   Type: {cand.get('type')}\n   Desc: {cand.get('description', 'N/A')}\n   Lang: {cand.get('language', 'N/A')}\n\n"
            
        prompt = f"""You are an expert developer matching engine.

Target User Profile:
{profile_context[:2000]}

Candidate Repositories/Developers:
{candidates_text}

Task:
Select the top 5 candidates that are most relevant to the target user's interests, tech stack, and profile.
Return ONLY the indices of the selected candidates in a comma-separated list (e.g., "0, 3, 1, 4").
Order them by relevance (most relevant first)."""
        
        response = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[
                {"role": "system", "content": "You are an expert developer matching engine. Return only comma-separated indices."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=100
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Reset quota flag on success
        _quota_exhausted = False
        
        # Parse indices
        try:
            # simple parsing assuming output is like "0, 2, 5"
            indices = [int(idx.strip()) for idx in response_text.split(',') if idx.strip().isdigit()]
            
            ranked_candidates = []
            for idx in indices:
                if 0 <= idx < len(candidates):
                    ranked_candidates.append(candidates[idx])
            
            # If Model fails to return valid indices, fallback to original top 5
            if not ranked_candidates:
                return candidates[:5]
                
            return ranked_candidates[:5]
            
        except ValueError:
            logger.debug(f"Error parsing Groq ranking response, using original order")
            return candidates[:5]
            
    except Exception as e:
        # Check if this is a quota error
        if _is_quota_error(e):
            _quota_exhausted = True
            logger.debug("Groq API quota exceeded for ranking. Using original order.")
        else:
            # Other errors
            logger.debug(f"Error in Groq ranking: {type(e).__name__}")
        
        return candidates[:5]
