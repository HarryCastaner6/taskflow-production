from flask import Blueprint, request, jsonify
from flask_login import login_required
from app.services.gemini_ai import gemini_ai

ai_bp = Blueprint('ai', __name__)

@ai_bp.route('/ai/generate-description', methods=['POST'])
@login_required
def generate_description():
    """Generate task description using Gemini AI"""
    data = request.get_json()

    if not data or 'title' not in data:
        return jsonify({'error': 'Task title is required'}), 400

    title = data.get('title')
    context = data.get('context', '')

    if not gemini_ai.is_configured():
        return jsonify({'error': 'AI service is not configured. Please add GEMINI_API_KEY to your environment variables.'}), 503

    description = gemini_ai.generate_task_description(title, context)

    if description:
        return jsonify({
            'success': True,
            'description': description
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': 'Failed to generate description. Please try again.'
        }), 500

@ai_bp.route('/ai/improve-description', methods=['POST'])
@login_required
def improve_description():
    """Improve existing task description using Gemini AI"""
    data = request.get_json()

    if not data or 'title' not in data or 'description' not in data:
        return jsonify({'error': 'Task title and description are required'}), 400

    title = data.get('title')
    current_description = data.get('description')

    if not gemini_ai.is_configured():
        return jsonify({'error': 'AI service is not configured. Please add GEMINI_API_KEY to your environment variables.'}), 503

    improved = gemini_ai.improve_task_description(title, current_description)

    if improved:
        return jsonify({
            'success': True,
            'description': improved
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': 'Failed to improve description. Please try again.'
        }), 500

@ai_bp.route('/ai/status', methods=['GET'])
@login_required
def ai_status():
    """Check if AI service is available"""
    return jsonify({
        'available': gemini_ai.is_configured(),
        'service': 'Gemini AI' if gemini_ai.is_configured() else None
    })