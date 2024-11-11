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
jobs_listings = pd.read_csv("us-software-engineer-jobs-updated.csv")

@app.route('/')
def index():
    return render_template('index.html', logged_in='user_id' in session)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('email', None)
    return redirect(url_for('login'))

@app.route('/jobs')
@app.route('/jobs.html')
def jobs():
    # Check if user is logged in
    if 'user_id' not in session:
        flash("Please log in to view your jobs.")
        return redirect(url_for('login'))

    user_id = session['user_id']
    cursor = conn.cursor()

    # Query to retrieve jobs for the logged-in user
    cursor.execute(
        """
        SELECT title, company_name, location, type, remote
        FROM jobs
        WHERE user_id = %s
        """,
        (user_id,)
    )
    
    # Fetch all jobs associated with the user
    jobs = cursor.fetchall()
    cursor.close()

    # Pass job data to the template
    return render_template('jobs.html', jobs=jobs)




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
    print("jobs type: ", type(jobs_listings))
    filtered_jobs = jobs_listings[
        (jobs_listings['title'].str.contains(preferred_title, case=False, na=False)) &
        (jobs_listings['location'].str.contains(preferred_location, case=False, na=False)) &
        (jobs_listings['types'].str.contains(contract_type, case=False, na=False))
    ]
    # Apply remote work filter only if it is not "Not specified"
    if remote_work_model != "Not specified":
        filtered_jobs = filtered_jobs[filtered_jobs['remote_work_model'].str.contains(remote_work_model, case=False, na=False)]  # Filter by remote work model
    
    # Apply visa sponsorship filter if the user says "Yes" or "No"
    if visa_sponsorship.lower() == "yes":
        filtered_jobs = filtered_jobs[filtered_jobs['sponsored'] == "Yes"]
    elif visa_sponsorship.lower() == "no":
        filtered_jobs = filtered_jobs[filtered_jobs['sponsored'] == "No"]

    # If no matches are found, relax the visa sponsorship requirement
    if filtered_jobs.empty:
        print("\nJobSeeker: No exact matches found, ignoring visa sponsorship requirement... ")
        filtered_jobs = jobs_listings[
            (jobs_listings['title'].str.contains(preferred_title, case=False, na=False)) &
            (jobs_listings['location'].str.contains(preferred_location, case=False, na=False)) &
            (jobs_listings['types'].str.contains(contract_type, case=False, na=False))
        ]
    
    return filtered_jobs[['title', 'company', 'location', 'types', 'remote_work_model','source_id']].to_dict(orient='records')

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
    # Store required keys in a temporary dictionary
    preserved_session_data = {
        'user_id': session.get('user_id'),
        'email': session.get('email'),
        'firstname': session.get('firstname')
    }
    
    # Clear the session
    session.clear()
    
    # Restore the preserved data
    session.update(preserved_session_data)
    
    return render_template('chatbot.html')



@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json.get('message', '').lower()
    response = chatbot_logic(user_input)
    #return jsonify({'response': response})
    if isinstance(response, dict):
        return jsonify(response)
    else:
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

    # Get recommendations from `filter_jobs`
    recommendations = filter_jobs(title, location, contract_type, remote_work, visa_sponsorship)
    #print("Recommendations received:", recommendations)  # Debug: Print recommendations

    # Check email presence in session and retrieve user_id from database
    email = session.get('email')
    print("Email from session:", email)  # Debug: Print email

    
# Retrieve user_id from session
    user_id = session.get('user_id')
    if not user_id:
        flash("Could not store recommendations. User ID not found.")
        return {"error": "User ID not found, please try again."}

    cursor = conn.cursor()

    # Insert each job into the jobs table
    for job in recommendations[:5]:
        try:
            cursor.execute(
                """
                INSERT INTO jobs (job_id, user_id, title, company_name, location, type, remote)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (job_id, user_id) DO NOTHING
                """,
                (job['source_id'], user_id, job['title'], job['company'], job['location'], job['types'], job['remote_work_model'])
            )
        except Exception as e:
            print(f"Error inserting job {job['source_id']}: {e}")
    
    # Commit the transaction to save changes
    conn.commit()
    cursor.close()
    # Ensure batch index is tracked
    if 'batch_index' not in session:
        session['batch_index'] = 0

    batch_size = 5
    total_jobs = len(recommendations)
    batch_index = session['batch_index']

    # Get the current batch of jobs
    next_batch = recommendations[batch_index:batch_index + batch_size]
    session['batch_index'] += batch_size  # Update index for the next call

    # Prepare response for the client
    response = {
        'jobs': next_batch,
        'remaining': max(0, total_jobs - session['batch_index'])
    }
    
    print("Response sent to client:", response)  # Debugging output
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
            flash('You have successfully registered! Please log in.')
            return redirect(url_for('login')) 
            # Store user info in the session
            session['user_id'] = cursor.lastrowid  # or use the ID if it's returned automatically
            session['firstname'] = firstname
            
            return redirect(url_for('profile'))  # Redirect to the profile page
    elif request.method == 'POST':
        flash('Please fill out the form completely!')
    
    return render_template('register.html')
'''
@app.route('/login', methods=['GET', 'POST'])
def login():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
   
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']
 
        # Check if account exists
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        account = cursor.fetchone()
 
        if account:
            password_rs = account['password']
            if check_password_hash(password_rs, password):
                # Store user information in session
                session['user_id'] = account['user_id']
                session['firstname'] = account['firstname']
                session['email'] = account['email']
                return redirect(url_for('profile'))
            else:
                flash('Incorrect email/password')
        else:
            flash('Incorrect email/password')
 
    return render_template('login.html')
'''

@app.route('/login', methods=['GET', 'POST'])
def login():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
   
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']
 
        # Check if account exists
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        account = cursor.fetchone()
 
        if account:
            password_rs = account['password']
            if check_password_hash(password_rs, password):
                # Store user information in session
                session['user_id'] = account['user_id']
                session['firstname'] = account['firstname']
                session['email'] = account['email']  # Ensure email is stored here
                return redirect(url_for('profile'))
            else:
                flash('Incorrect email/password')
        else:
            flash('Incorrect email/password')
 
    return render_template('login.html')


@app.route('/profile')
def profile():
    if 'firstname' in session:
        name = session['firstname']
        return render_template('profile.html', name=name)
    else:
        flash('Please log in to access your profile.')
        return redirect(url_for('login'))


@app.route('/home')
def home():
    # Logic for the home page
    return render_template('home.html')

if __name__ == '__main__':
    app.run(debug=True)