from flask import Flask, request, render_template, session, jsonify
import openai
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from MainFile import job_chatbot, normalize_input, normalize_location, normalize_remote_work, normalize_visa_sponsorship, filter_jobs, chat_with_Seeker

# Initialize Flask app
app = Flask(__name__)
app.secret_key = "your_secret_key"

# Set OpenAI API key
openai.api_key = "sk-UCiVzm0xlj6cS5UXHGV3wjhBSB8fhdWG2s8mUdcqCYT3BlbkFJag1xk-S_tQ92CrfVFHGIviQ5LR8GBAOt4SSxXlWrYA"

# Connect to the PostgreSQL database
DATABASE_URL = "postgresql+psycopg2://postgres:iui@localhost:5432/iui_project"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session_db = Session()

# Load job data
jobs = pd.read_csv("us-software-engineer-jobs-updated.csv")

# Initialize chatbot session and start with a welcome message
@app.route("/", methods=["GET"])
def chat():
    # Initialize messages session if it doesn't exist
    if 'messages' not in session:
        session['messages'] = []
        # Start chatbot and add the initial message
        welcome_message = "Hello! I am JobSeeker, here to help you find job recommendations."
        session['messages'].append({"sender": "bot", "text": welcome_message})

    return render_template("chatbot.html", messages=session['messages'])

@app.route("/get_response", methods=["POST"])
def get_response():
    user_input = request.json.get("message")
    session['messages'].append({"sender": "user", "text": user_input})

    # Get bot response based on user input
    response_text = chat_with_Seeker(user_input)
    session['messages'].append({"sender": "bot", "text": response_text})

    return jsonify({"response": response_text})

if __name__ == "__main__":
    app.run(debug=True)
