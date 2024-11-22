from flask import Flask, request, render_template, session, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import openai
import re
import pandas as pd
import os
from MainFile import job_chatbot, normalize_input, normalize_location, normalize_remote_work, normalize_visa_sponsorship, filter_jobs, chat_with_Seeker
from flask_session import Session
# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Set OpenAI API key
#openai.api_key = "sk-UCiVzm0xlj6cS5UXHGV3wjhBSB8fhdWG2s8mUdcqCYT3BlbkFJag1xk-S_tQ92CrfVFHGIviQ5LR8GBAOt4SSxXlWrYA"
#api_key.text = "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"
with open("api_key.txt", "r") as file:
    openai.api_key = file.read().strip()

# Connect to the PostgreSQL database
DB_HOST = "localhost"
DB_NAME = "iui_project"
DB_USER = "postgres"
DB_PASS = "iui" # This works for Mahirah and Emory
# DB_PASS = "abcdefgh" # This only works for Amalesh

 
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

@app.route('/delete_job', methods=['DELETE'])
def delete_job():
    data = request.json
    job_id = data.get('job_id')
    user_id = session.get('user_id')

    # Check if job_id and user_id are valid
    if not job_id or not user_id:
        return jsonify({"status": "error", "message": "Invalid job ID or user session"}), 400

    cursor = conn.cursor()
    try:
        # Delete the job for the current user
        cursor.execute("DELETE FROM jobs WHERE job_id = %s AND user_id = %s", (job_id, user_id))
        conn.commit()
        if cursor.rowcount > 0:
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error", "message": "Job not found"}), 404
    except Exception as e:
        print("Error deleting job:", e)
        return jsonify({"status": "error", "message": str(e)}), 500



@app.route('/save_job', methods=['POST'])
def save_job():
    data = request.json
    job_id = data.get('job_id')
    user_id = session.get('user_id')

    # Check if job_id and user_id are valid
    if not job_id or not user_id:
        return jsonify({"status": "error", "message": "Invalid job ID or user session"}), 400

    # Fetch job details from job listings
    job = next((job for job in jobs_listings.to_dict(orient='records') if job['source_id'] == job_id), None)

    if job:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO jobs (job_id, user_id, title, company_name, location, type, remote)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING  -- Avoid duplicate entries
            """, (
                job['source_id'], user_id, job['title'], job['company'], job['location'],
                job['types'], job['remote_work_model']
            ))
            conn.commit()
            return jsonify({"status": "success"})
        except Exception as e:
            print("Error inserting job:", e)
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        return jsonify({"status": "error", "message": "Job not found"}), 404



# Function to normalize user input using GPT-3.5-turbo
def normalize_input(input_text, field_type):
    prompt = f"JobSeeker: Normalize this input '{input_text}' to a valid {field_type}. Please return only the normalized value. "
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

# Normalize location specifically for 'Remote' or a valid city
def normalize_location(input_text):
    prompt = f"JobSeeker: Normalize this input '{input_text}' to either a valid city or 'Remote'. Please return only the normalized value. "
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

# Normalize remote work to match "100% Remote", "Hybrid", or "No Remote"
def normalize_remote_work(input_text):
    input_text = input_text.lower()
    if "yes" in input_text:
        return "100% Remote"
    elif "work from home" in input_text or "wfh" in input_text or "maybe" in input_text:
        return "Hybrid"
    elif "no" in input_text:
        return "No Remote"
    else:
        prompt = f"JobSeeker: Normalize this input '{input_text}' to one of these options: '100% Remote', 'Hybrid', or 'No Remote'. Please return only one of these exact values."
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        normalized_value = response.choices[0].message.content.strip()

        # Treat any invalid value as "Not specified"
        if normalized_value not in ['100% Remote', 'Hybrid', 'No Remote']:
            return "Not specified"
        return normalized_value

# Normalize visa sponsorship specifically to either 'Yes' or 'No'
def normalize_visa_sponsorship(input_text):
    if "yes" in input_text.lower():
        return "Yes"
    elif "no" in input_text.lower():
        return "No"
    else:
        return "Not specified"

'''
def filter_jobs(title, location, contract_type, remote_work, visa_sponsorship):
    # Mock job filtering function, returns sample job recommendations
    return [{'source_id': 1, 'title': title, 'company': 'Company A', 'location': location, 'types': contract_type, 'remote_work_model': remote_work}]
'''

# Filter jobs with relaxed criteria
def filter_jobs(preferred_title, preferred_location, contract_type, remote_work_model, visa_sponsorship):
    # Initial filtering based on job title, location, contract type, and remote work model
    print("Filtering jobs based on preferences...")
    print(f"Title: {preferred_title}, Location: {preferred_location}, Contract Type: {contract_type}, Remote: {remote_work_model}, Visa: {visa_sponsorship}")
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

# def chatbot_logic(user_input):
    # Initialize conversation state if not set
    if 'step' not in session:
        session['step'] = 'start'

    # Step-based conversation handling
    if session['step'] == 'start':
        session['step'] = 'detailed_search'
        # return "Do you want a detailed job search? (Yes / No)"
        return {"response": "Do you want a detailed job search?", "options": ["Yes", "No"]}

    elif session['step'] == 'detailed_search':
        if user_input == 'yes':
            session['step'] = 'get_title'
            # return "What is your preferred job title?"
            return {"response": "What is your preferred job title?"}
        else:
            session['step'] = 'anything_else'
            # return "Anything else I can help you with? (Yes / No)"
            return {"response": "Anything else I can help you with?", "options": ["Yes", "No"]}

    elif session['step'] == 'get_title':
        session['preferred_title'] = normalize_input(user_input, "job title")
        print(f"Normalized Job Title: {session['preferred_title']}")  # Debug log
        session['step'] = 'get_location'
        # return "Preferred job location (e.g., Remote, specific city)?"
        return {"response": "Preferred job location (e.g., Remote, specific city)?"}

    elif session['step'] == 'get_location':
        session['preferred_location'] = normalize_location(user_input)
        print(f"Normalized Job Location: {session['preferred_location']}")  # Debug log
        session['step'] = 'get_contract_type'
        # return "What is your preferred contract type? (Full-time / Part-time)"
        return {"response": "What is your preferred contract type?", "options": ["Full-time", "Part-time"]}


    elif session['step'] == 'get_contract_type':
        session['contract_type'] = normalize_input(user_input, "contract type")
        print(f"Normalized Contract: {session['contract_type']}")  # Debug log
        session['step'] = 'get_remote_work'
        # return "Do you want remote work? (Yes / Maybe / No)"
        return {"response": "Do you want remote work?", "options": ["Yes", "Maybe", "No"]}


    elif session['step'] == 'get_remote_work':
        session['remote_work_model'] = normalize_remote_work(user_input)
        print(f"Normalized Remote work model: {session['remote_work_model']}")  # Debug log
        session['step'] = 'get_visa_sponsorship'
        # return "Do you need visa sponsorship? (Yes / No)"
        return {"response": "Do you need visa sponsorship?", "options": ["Yes", "No"]}


    elif session['step'] == 'get_visa_sponsorship':
        session['visa_sponsorship'] = normalize_visa_sponsorship(user_input)
        print(f"Normalized Visa Sponsorship: {session['visa_sponsorship']}")  # Debug log
        session['step'] = 'show_recommendations'
        return show_recommendations()

    elif session['step'] == 'show_recommendations':
        if user_input == 'yes':
            response = show_recommendations()
            if response['jobs']:
                return response
            else:
                session['step'] = 'anything_else'
                return "No more results available. Anything else I can help you with? (Yes / No)"
        else:
            session['step'] = 'anything_else'
            return "Anything else I can help you with? (Yes / No)"

    elif session['step'] == 'anything_else':
        if user_input == 'yes':
            session['step'] = 'start'  # Restart conversation
            return "What else can I help you with?"
        else:
            session.clear()
            return "Happy Hunting!"

    return "I'm not sure how to respond to that."

def chatbot_logic(user_input):
    # Initialize conversation state if not set
    if 'step' not in session:
        session['step'] = 'start'

    # Step-based conversation handling
    if session['step'] == 'start':
        session['step'] = 'detailed_search'
        return {"response": "Do you want a detailed job search?", "options": ["Yes", "No"]}

    elif session['step'] == 'detailed_search':
        if user_input == 'yes':
            session['step'] = 'get_title'
            return {"response": "What is your preferred job title?"}
        else:
            session['step'] = 'anything_else'
            return {"response": "Anything else I can help you with?", "options": ["Yes", "No"]}

    elif session['step'] == 'get_title':
        session['preferred_title'] = normalize_input(user_input, "job title")
        print(f"Normalized Job Title: {session['preferred_title']}")  # Debug log
        session['step'] = 'get_location'
        return {"response": "Preferred job location (e.g., Remote, specific city)?"}

    elif session['step'] == 'get_location':
        session['preferred_location'] = normalize_location(user_input)
        print(f"Normalized Job Location: {session['preferred_location']}")  # Debug log
        session['step'] = 'get_contract_type'
        return {"response": "What is your preferred contract type?", "options": ["Full-time", "Part-time"]}

    elif session['step'] == 'get_contract_type':
        session['contract_type'] = normalize_input(user_input, "contract type")
        print(f"Normalized Contract: {session['contract_type']}")  # Debug log
        session['step'] = 'get_remote_work'
        return {"response": "Do you want remote work?", "options": ["Yes", "Maybe", "No"]}

    elif session['step'] == 'get_remote_work':
        session['remote_work_model'] = normalize_remote_work(user_input)
        print(f"Normalized Remote work model: {session['remote_work_model']}")  # Debug log
        session['step'] = 'get_visa_sponsorship'
        return {"response": "Do you need visa sponsorship?", "options": ["Yes", "No"]}

    elif session['step'] == 'get_visa_sponsorship':
        session['visa_sponsorship'] = normalize_visa_sponsorship(user_input)
        print(f"Normalized Visa Sponsorship: {session['visa_sponsorship']}")  # Debug log
        session['step'] = 'show_recommendations'
        return show_recommendations()

    elif session['step'] == 'show_recommendations':
        if user_input == 'yes':
            response = show_recommendations()
            if response['jobs']:
                return response
            else:
                session['step'] = 'anything_else'
                return {"response": "No more results available. Anything else I can help you with?", "options": ["Yes", "No"]}
        else:
            session['step'] = 'anything_else'
            return {"response": "Anything else I can help you with?", "options": ["Yes", "No"]}

    elif session['step'] == 'anything_else':
        if user_input == 'yes':
            session['step'] = 'start'  # Restart conversation
            return {"response": "What else can I help you with?"}
        else:
            session.clear()
            return {"response": "Happy Hunting!"}

    # Default response if no valid step is found
    return {"response": "I'm not sure how to respond to that."}

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
    '''
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
    cursor.close()'''
    # Ensure batch index is tracked
    if 'batch_index' not in session:
        session['batch_index'] = 0

    batch_size = 5
    total_jobs = len(recommendations)
    batch_index = session['batch_index']

    # Get the current batch of jobs
    next_batch = recommendations[batch_index:batch_index + batch_size]
    session['batch_index'] += batch_size  # Update index for the next call
    
    '''if len(next_batch) == 0:
        return {
            'jobs': "There are no jobs that match your preferences.",
            'remaining': max(0, total_jobs - session['batch_index'])
        }
    
    else:'''

    return {
        'jobs': next_batch,
        'remaining': max(0, total_jobs - session['batch_index'])
    }



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


# @app.route('/profile')
# def profile():
#     if 'firstname' in session:
#         name = session['firstname']
#         return render_template('profile.html', name=name)
#     else:
#         flash('Please log in to access your profile.')
#         return redirect(url_for('login'))

@app.route('/profile')
def profile():
    if 'user_id' not in session:
            flash('Please log in to access your profile.')
            return redirect(url_for('login'))

    user_id = session['user_id']
    name = session.get('firstname', 'Guest')

    # Fetch user info
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT firstname, lastname, email
        FROM users 
        WHERE user_id = %s 
        """,
        (user_id,)
    )
    user_info = cursor.fetchone()
    cursor.close()

    # Fetch saved jobs for the logged-in user
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT title, company_name, location, type, remote
        FROM jobs
        WHERE user_id = %s
        """,
        (user_id,)
    )
    jobs = cursor.fetchall()
    cursor.close()

    # Pass saved jobs and user name to the profile template
    return render_template('profile.html', name=name, firstname=user_info[0], lastname=user_info[1], email=user_info[2], jobs=jobs)


@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Please log in"}), 403

    user_id = session['user_id']
    firstname = request.form.get('firstname')
    lastname = request.form.get('lastname')
    email = request.form.get('email')

    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE users 
            SET firstname = %s, lastname = %s, email = %s 
            WHERE user_id = %s
            """, 
            (firstname, lastname, email,  user_id))
        conn.commit()
        return jsonify({"status": "success", "message": "Profile updated successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    finally:
        cursor.close()


@app.route('/home')
def home():
    # Logic for the home page
    return render_template('index.html')
    # return render_template('home.html')

if __name__ == '__main__':
    app.run(debug=True)
