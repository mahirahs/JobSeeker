from flask import Flask, request, render_template, session, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import openai
import re
import pandas as pd
from MainFile import job_chatbot, normalize_input, normalize_location, normalize_remote_work, normalize_visa_sponsorship, filter_jobs, chat_with_Seeker
from flask_session import Session
# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Set OpenAI API key
openai.api_key = "sk-UCiVzm0xlj6cS5UXHGV3wjhBSB8fhdWG2s8mUdcqCYT3BlbkFJag1xk-S_tQ92CrfVFHGIviQ5LR8GBAOt4SSxXlWrYA"

# Connect to the PostgreSQL database
DB_HOST = "localhost"
DB_NAME = "iui_project"
DB_USER = "postgres"
DB_PASS = "iui"
 
conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
'''
class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(50), nullable=False)
    lastname = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=False, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    
'''

# Load job data
jobs = pd.read_csv("us-software-engineer-jobs-updated.csv")

@app.route('/')
def index():
    return render_template('index.html', logged_in='user_id' in session)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('email', None)
    return redirect(url_for('login'))

@app.route('/profile.html')
def profile():
    return render_template('profile.html')


@app.route('/jobs.html')
def jobs():
    return render_template('jobs.html')



def normalize_input(input_text, input_type):
    # Mock normalization function
    return input_text.lower()
'''
def filter_jobs(title, location, contract_type, remote_work, visa_sponsorship):
    # Mock job filtering function, returns sample job recommendations
    return [{'source_id': 1, 'title': title, 'company': 'Company A', 'location': location, 'types': contract_type, 'remote_work_model': remote_work}]
'''

# Filter jobs with relaxed criteria
def filter_jobs(preferred_title, preferred_location, contract_type, remote_work_model, visa_sponsorship):
    # Initial filtering based on job title, location, contract type, and remote work model
    filtered_jobs = jobs[
        (jobs['title'].str.contains(preferred_title, case=False, na=False)) &
        (jobs['location'].str.contains(preferred_location, case=False, na=False)) &
        (jobs['types'].str.contains(contract_type, case=False, na=False))
    ]
    # Apply remote work filter only if it is not "Not specified"
    if remote_work_model != "Not specified":
        filtered_jobs = filtered_jobs[filtered_jobs['remote_work_model'].str.contains(remote_work_model, case=False, na=False)]
    
    # Apply visa sponsorship filter if the user says "Yes" or "No"
    if visa_sponsorship.lower() == "yes":
        filtered_jobs = filtered_jobs[filtered_jobs['sponsored'] == "Yes"]
    elif visa_sponsorship.lower() == "no":
        filtered_jobs = filtered_jobs[filtered_jobs['sponsored'] == "No"]

    # If no matches are found, relax the visa sponsorship requirement
    if filtered_jobs.empty:
        print("\nJobSeeker: No exact matches found, ignoring visa sponsorship requirement... ")
        filtered_jobs = jobs[
            (jobs['title'].str.contains(preferred_title, case=False, na=False)) &
            (jobs['location'].str.contains(preferred_location, case=False, na=False)) &
            (jobs['types'].str.contains(contract_type, case=False, na=False))
        ]

    # Convert the filtered DataFrame to a list of dictionaries for compatibility
    return filtered_jobs[['title', 'company', 'location', 'types', 'remote_work_model', 'source_id']].to_dict(orient='records')

# Return recommendations as a list of dictionaries
def get_job_recommendations(preferred_title, preferred_location, contract_type, remote_work_model, visa_sponsorship):
    recommendations = filter_jobs(preferred_title, preferred_location, contract_type, remote_work_model, visa_sponsorship)
    # Return recommendations as a list of dictionaries for easy JSON serialization
    return recommendations.to_dict(orient="records")

# Chat with the Seeker using GPT-3.5-turbo
def chat_with_Seeker(prompt):
    response = openai.ChatCompletion.create(
        model = "gpt-3.5-turbo",
        messages = [{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()



@app.route('/chatbot.html')
def chatbot():
    session.clear()  # Clear session for a new conversation
    return render_template('chatbot.html')


@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json.get('message', '').lower()
    response = chatbot_logic(user_input)
    return jsonify({'response': response})

def chatbot_logic(user_input):
    # Initialize conversation state if not set
    if 'step' not in session:
        session['step'] = 'start'

    # Step-based conversation handling
    if session['step'] == 'start':
        session['step'] = 'detailed_search'
        return "Do you want a detailed job search? (yes or no)"

    elif session['step'] == 'detailed_search':
        if user_input == 'yes':
            session['step'] = 'get_title'
            return "What is your preferred job title?"
        else:
            session['step'] = 'anything_else'
            return "Anything else I can help you with? (yes or no)"

    elif session['step'] == 'get_title':
        session['preferred_title'] = normalize_input(user_input, "job title")
        session['step'] = 'get_location'
        return "Preferred job location (e.g., Remote, specific city)?"

    elif session['step'] == 'get_location':
        session['preferred_location'] = normalize_input(user_input, "location")
        session['step'] = 'get_contract_type'
        return "What is your preferred contract type? (Full-time or Part-time)"

    elif session['step'] == 'get_contract_type':
        session['contract_type'] = normalize_input(user_input, "contract type")
        session['step'] = 'get_remote_work'
        return "Do you want remote work? (100% Remote, Hybrid, or No Remote)"

    elif session['step'] == 'get_remote_work':
        session['remote_work_model'] = normalize_input(user_input, "remote work")
        session['step'] = 'get_visa_sponsorship'
        return "Do you need visa sponsorship? (yes or no)"

    elif session['step'] == 'get_visa_sponsorship':
        session['visa_sponsorship'] = normalize_input(user_input, "visa sponsorship")
        session['step'] = 'show_recommendations'
        return show_recommendations()

    elif session['step'] == 'show_recommendations':
        if user_input == 'yes':
            session['step'] = 'get_title'  # Start a new search
            return "What is your preferred job title?"
        else:
            session['step'] = 'anything_else'
            return "Anything else I can help you with? (yes or no)"

    elif session['step'] == 'anything_else':
        if user_input == 'yes':
            session['step'] = 'start'  # Restart conversation
            return "What else can I help you with?"
        else:
            session.clear()
            return "Happy Hunting!"

    return "I'm not sure how to respond to that."

def show_recommendations():
    # Retrieve user preferences from session
    title = session.get('preferred_title')
    location = session.get('preferred_location')
    contract_type = session.get('contract_type')
    remote_work = session.get('remote_work_model')
    visa_sponsorship = session.get('visa_sponsorship')

    # Filter jobs based on user input (replace this with actual job data filtering)
    '''
    recommendations = filter_jobs(title, location, contract_type, remote_work, visa_sponsorship)

    if recommendations:
        jobs = "\n".join([f"Job ID: {job['source_id']}, Title: {job['title']}, Location: {job['location']}" for job in recommendations])
        return f"Here are some job recommendations for you:\n{jobs}\nDo you want to search for more jobs? (yes or no)"
    else:
        return "Sorry, no job recommendations match your criteria. Do you want to try another search? (yes or no)"
    '''
    
    
    recommendations = filter_jobs(title, location, contract_type, remote_work, visa_sponsorship)
            
    if 'batch_index' not in session:
        session['batch_index'] = 0

    batch_size = 5
    total_jobs = len(recommendations)
    batch_index = session['batch_index']
    
    # Get the current batch of jobs
    next_batch = recommendations[batch_index:batch_index + batch_size]
    session['batch_index'] += batch_size  # Update index for the next call

    # Format response as a list of job descriptions
    jobs = [f"Job ID: {job['source_id']}, Title: {job['title']}, Company: {job['company']}, Location: {job['location']}, "
            f"Type: {job['types']}, Remote Work: {job['remote_work_model']}" for job in next_batch]
    
    response = {
        'jobs': jobs,
        'remaining': max(0, total_jobs - session['batch_index'])
    }

    return response

@app.route('/register', methods=['GET', 'POST'])
def register():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
 
    if request.method == 'POST' and 'firstname' in request.form and 'lastname' in request.form and 'password' in request.form and 'email' in request.form:
        # Retrieve form data
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        password = request.form['password']
        email = request.form['email']
        
        # Hash the password
        _hashed_password = generate_password_hash(password)
 
        # Check if account with the same email already exists
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        account = cursor.fetchone()
        
        # Validate the form and display appropriate messages
        if account:
            flash('An account with this email already exists!')
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash('Invalid email address!')
        elif not firstname or not lastname or not password or not email:
            flash('Please fill out the form completely!')
        else:
            # Insert a new record, omitting user_id (PostgreSQL will auto-generate it)
            cursor.execute("INSERT INTO users (firstname, lastname, password, email) VALUES (%s, %s, %s, %s)", (firstname, lastname, _hashed_password, email))
            conn.commit()
            flash('You have successfully registered!')
            return redirect(url_for('login'))  # Redirect to the login page (assuming a login route exists)
    elif request.method == 'POST':
        flash('Please fill out the form completely!')
    
    # Show the registration form
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
   
    # Check if "email" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']
        print(password)
 
        # Check if account exists using PostgreSQL
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        # Fetch one record and return result
        account = cursor.fetchone()
 
        if account:
            password_rs = account['password']
            print(password_rs)
            # If account exists in the users table in our database
            if check_password_hash(password_rs, password):
                # Create session data; we can access this data in other routes
                session['loggedin'] = True
                session['user_id'] = account['user_id']
                session['email'] = account['email']
                # Redirect to the home page
                return redirect(url_for('home'))
            else:
                # Account doesn't exist or email/password incorrect
                flash('Incorrect email/password')
        else:
            # Account doesn't exist or email/password incorrect
            flash('Incorrect email/password')
 
    return render_template('login.html')


@app.route('/home')
def home():
    # Logic for the home page
    return render_template('home.html')

if __name__ == '__main__':
    app.run(debug=True)