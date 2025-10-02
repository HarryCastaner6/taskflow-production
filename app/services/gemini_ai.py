import os
import requests
import json
from typing import Optional

class GeminiAI:
    def __init__(self):
        self.api_key = os.environ.get('GEMINI_API_KEY')
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"

    def is_configured(self) -> bool:
        """Check if Gemini AI is properly configured"""
        return bool(self.api_key)

    def generate_task_description(self, title: str, context: Optional[str] = None) -> Optional[str]:
        """
        Generate a task description using Gemini AI

        Args:
            title: The task title
            context: Optional additional context about the task

        Returns:
            Generated description or None if failed
        """
        if not self.is_configured():
            return None

        prompt = f"""Generate a clear and concise task description for the following task:

Task Title: {title}
"""

        if context:
            prompt += f"Additional Context: {context}\n"

        prompt += """
Please provide a detailed description that includes:
1. What needs to be done
2. Key objectives or deliverables
3. Any important considerations

Keep the description professional, actionable, and under 200 words."""

        try:
            headers = {
                'Content-Type': 'application/json',
            }

            data = {
                'contents': [{
                    'parts': [{
                        'text': prompt
                    }]
                }],
                'generationConfig': {
                    'temperature': 0.7,
                    'topK': 1,
                    'topP': 1,
                    'maxOutputTokens': 2048,
                },
                'safetySettings': [
                    {
                        'category': 'HARM_CATEGORY_HARASSMENT',
                        'threshold': 'BLOCK_MEDIUM_AND_ABOVE'
                    },
                    {
                        'category': 'HARM_CATEGORY_HATE_SPEECH',
                        'threshold': 'BLOCK_MEDIUM_AND_ABOVE'
                    },
                    {
                        'category': 'HARM_CATEGORY_SEXUALLY_EXPLICIT',
                        'threshold': 'BLOCK_MEDIUM_AND_ABOVE'
                    },
                    {
                        'category': 'HARM_CATEGORY_DANGEROUS_CONTENT',
                        'threshold': 'BLOCK_MEDIUM_AND_ABOVE'
                    }
                ]
            }

            response = requests.post(
                f"{self.base_url}?key={self.api_key}",
                headers=headers,
                json=data,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    candidate = result['candidates'][0]
                    if 'content' in candidate and 'parts' in candidate['content']:
                        return candidate['content']['parts'][0]['text'].strip()

            return None

        except Exception as e:
            print(f"Error generating task description: {str(e)}")
            return None

    def improve_task_description(self, title: str, current_description: str) -> Optional[str]:
        """
        Improve an existing task description using Gemini AI

        Args:
            title: The task title
            current_description: The current description to improve

        Returns:
            Improved description or None if failed
        """
        if not self.is_configured():
            return None

        prompt = f"""Improve and enhance the following task description:

Task Title: {title}
Current Description: {current_description}

Please improve this description by:
1. Making it clearer and more specific
2. Adding any missing important details
3. Ensuring it's actionable and well-structured
4. Keeping it concise (under 200 words)

Provide only the improved description, nothing else."""

        try:
            headers = {
                'Content-Type': 'application/json',
            }

            data = {
                'contents': [{
                    'parts': [{
                        'text': prompt
                    }]
                }],
                'generationConfig': {
                    'temperature': 0.7,
                    'topK': 1,
                    'topP': 1,
                    'maxOutputTokens': 2048,
                }
            }

            response = requests.post(
                f"{self.base_url}?key={self.api_key}",
                headers=headers,
                json=data,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    candidate = result['candidates'][0]
                    if 'content' in candidate and 'parts' in candidate['content']:
                        return candidate['content']['parts'][0]['text'].strip()

            return None

        except Exception as e:
            print(f"Error improving task description: {str(e)}")
            return None

# Create a singleton instance
gemini_ai = GeminiAI()