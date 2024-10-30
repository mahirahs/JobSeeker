from flask import Flask, render_template, request, jsonify
from MainFile import get_job_recommendations, chat_with_Seeker

app = Flask(__name__)

# Open JobSeeker website interface
@app.route("/")
def index():
    return render_template("index.html")

# Handle job recommendations
@app.route('/search_jobs', methods=['POST'])
def search_jobs():
    # Get user preferences from the form
    preferences = request.json  # Expecting JSON data
    recommendations = get_job_recommendations(
        preferences.get('title'),
        preferences.get('location'),
        preferences.get('contract_type'),
        preferences.get('remote_work'),
        preferences.get('visa_sponsorship')
    )
    return jsonify({"jobs": recommendations})

# Handle chatbot responses
@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get("message")
    # Call the function from MainFile.py to get the chatbot response
    bot_response = chat_with_Seeker(user_message)
    return jsonify({"response": bot_response})

if __name__ == "__main__":
    app.run(debug=True)