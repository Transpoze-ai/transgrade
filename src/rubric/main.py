#!/usr/bin/env python
import sys
import warnings
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

# Import the Rubric crew ONLY when needed to avoid auto-execution
# from rubric.crew import Rubric

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

def process_rubric(question_paper_text, vlm_description):
    """
    Process the rubric generation with the provided inputs.
    """
    # Import here to avoid auto-execution on module load
    from rubric.crew import Rubric
    
    inputs = {
        'question_paper_text': question_paper_text,
        'vlm_description': vlm_description,
        'question_analysis_results': '',  # Will be filled by the first task
        'diagram_interpretation_results': ''  # Will be filled by the second task
    }
    
    try:
        result = Rubric().crew().kickoff(inputs=inputs)
        return result
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")
#hi
@app.route('/rubric/generate-rubric', methods=['POST'])
def generate_rubric():
    """
    API endpoint to generate educational assessment rubric.
    Expects JSON payload with 'question_paper_text' and 'vlm_description'.
    """
    try:
        # Get JSON data from request
        data = request.get_json()
        
        # Validate required fields
        if not data:
            return jsonify({
                'error': 'No JSON data provided',
                'status': 'error'
            }), 400
        
        question_paper_text = data.get('question_paper_text')
        vlm_description = data.get('vlm_description')
        
        if not question_paper_text:
            return jsonify({
                'error': 'question_paper_text is required',
                'status': 'error'
            }), 400
        
        if not vlm_description:
            return jsonify({
                'error': 'vlm_description is required',
                'status': 'error'
            }), 400
        
        # Process the rubric generation
        result = process_rubric(question_paper_text, vlm_description)
        
        return jsonify({
            'result': str(result),
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'message': 'Rubric generation completed successfully'
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/rubric/health', methods=['GET'])
def health_check():
    """
    Health check endpoint to verify API is running.
    """
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'message': 'Rubric Generation API is running'
    }), 200

@app.route('/rubric/', methods=['GET'])
def home():
    """
    Home endpoint with API documentation.
    """
    return jsonify({
        'message': 'Rubric Generation API',
        'version': '1.0.0',
        'endpoints': {
            'POST /generate-rubric': {
                'description': 'Generate educational assessment rubric',
                'required_fields': ['question_paper_text', 'vlm_description'],
                'example_payload': {
                    'question_paper_text': 'Your question paper text here...',
                    'vlm_description': 'Your VLM description here...'
                }
            },
            'GET /health': 'Health check endpoint',
            'GET /': 'API documentation'
        }
    }), 200

def run():
    """
    Main function to start the Flask server
    This will be called by 'crewai run'
    """
    print("Starting Rubric Generation Flask Server...")
    print("Server will be available at: http://localhost:5000")
    print("Health check: http://localhost:5000/")
    print("Rubric generation endpoint: POST http://localhost:5000/generate-rubric")
    print("\nAvailable endpoints:")
    print("  GET  / - API documentation")
    print("  GET  /health - Health check")
    print("  POST /generate-rubric - Generate rubric")
    print("\nExample POST request to /generate-rubric:")
    print("""
    {
        "question_paper_text": "Your question paper text here...",
        "vlm_description": "Your VLM description here..."
    }
    """)
    app.run(debug=True, host='0.0.0.0', port=5033)

def run_crew_directly():
    """
    Run the crew for educational assessment rubric generation directly.
    (For testing purposes)
    """
    from rubric.crew import Rubric
    
    inputs = {
        'question_paper_text': '''
        3\n7E\nIV. study the following pie chart and then answer the questions: 5 x 1 = 5\nThe below pie chart shows the sale of different fruits in a day for a shop\nOthers .\n20%\n:20%\nBanana\n.30%\nOrange\n15%\nGrapes\nApple\n10%\n25%\nNow answer the following questions based on the pie chart:\n1. What does the pie chart show?\n2. How many types of fruits mentioned in the chart?\n3. Which is the highest selling fruit?\n4. Which fruit is sold the least in the shop?\n5. What is the percentage of sales of Oranges ,?\nV. Observe the following picture carefully and write any FIVE sentences\nrelated to it:\n5 M."
        },
        ''',
        'vlm_description': '''
        Diagram 1: Pie chart showing the sale of different fruits in a day for a shop. The chart is divided into sections with the following labels and percentages: Banana 30%, Grapes 10%, Apple 25%, Orange 15%, Others 20%. The sections are separated by solid lines, and each section is shaded differently. The chart is neat and printed.
        Diagram 2: Sketch with three scenes. Scene 1: Two children climbing a tree, one child is reaching for something. Scene 2: Two children sitting under a tree, one child is handing something to the other. Scene 3: A woman talking to two children, one child is holding something. All sketches are hand-drawn, neat, with solid lines. No text labels or measurements.
        ''',
        'question_analysis_results': '',  # Will be filled by the first task
        'diagram_interpretation_results': ''  # Will be filled by the second task
    }
    
    try:
        result = Rubric().crew().kickoff(inputs=inputs)
        return result
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")

def train():
    """
    Train the crew for a given number of iterations.
    """
    from rubric.crew import Rubric
    
    inputs = {
        'question_paper_text': '''
        1. What do you understand by resource? (1 mark)
        2. Explain the water cycle with the help of a diagram. (5 marks)
        3. Compare renewable and non-renewable resources. (3 marks)
        ''',
        'vlm_description': '''
        Diagram showing water cycle with evaporation, condensation, precipitation processes.
        ''',
        'question_analysis_results': '',
        'diagram_interpretation_results': ''
    }
    
    try:
        Rubric().crew().train(n_iterations=int(sys.argv[2]), filename=sys.argv[3], inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")

def replay():
    """
    Replay the crew execution from a specific task.
    """
    from rubric.crew import Rubric
    
    try:
        Rubric().crew().replay(task_id=sys.argv[2])
    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

def test():
    """
    Test the crew execution and returns the results.
    """
    from rubric.crew import Rubric
    
    inputs = {
        'question_paper_text': '''
        1. Define photosynthesis. (2 marks)
        2. Draw and label a plant cell. (4 marks)
        3. Explain the process of respiration in plants. (3 marks)
        ''',
        'vlm_description': '''
        Diagram of a plant cell showing: cell wall, cell membrane, nucleus, 
        chloroplasts, vacuole, mitochondria, and other organelles with proper labels.
        ''',
        'question_analysis_results': '',
        'diagram_interpretation_results': ''
    }
    
    try:
        Rubric().crew().test(n_iterations=int(sys.argv[2]), eval_llm=sys.argv[3], inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")

if __name__ == '__main__':
    # Handle command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "--server" or command == "flask":
            # Explicit server start command with optional port
            port = int(sys.argv[2]) if len(sys.argv) > 2 else 5033
            print(f"Starting Flask API server on port {port}...")
            app.run(debug=True, host='0.0.0.0', port=port)
        elif command == "crew":
            # Run the original crew logic directly
            result = run_crew_directly()
            print("Rubric generation completed!")
            print(f"Results: {result}")
        elif command == "train" and len(sys.argv) >= 4:
            train()
        elif command == "test" and len(sys.argv) >= 4:
            test()
        elif command == "replay" and len(sys.argv) >= 3:
            replay()
        else:
            print("Usage:")
            print("  python main.py                         # Start Flask API (default)")
            print("  python main.py --server [port]         # Start Flask API on specific port")
            print("  python main.py flask [port]            # Start Flask API on specific port")
            print("  python main.py crew                     # Run crew logic directly")
            print("  python main.py train <iterations> <filename>")
            print("  python main.py test <iterations> <eval_llm>")
            print("  python main.py replay <task_id>")
    else:
        # Default behavior: Start Flask server
        # This is what gets called by 'crewai run'
        run()