import openai
import pandas as pd
from sqlalchemy import create_engine, Table, Column, Integer, MetaData, insert
from sqlalchemy.orm import sessionmaker

# Set OpenAI API key (Make sure you securely load your API key)
openai.api_key = "sk-UCiVzm0xlj6cS5UXHGV3wjhBSB8fhdWG2s8mUdcqCYT3BlbkFJag1xk-S_tQ92CrfVFHGIviQ5LR8GBAOt4SSxXlWrYA"
# Load the dataset
jobs = pd.read_csv("us-software-engineer-jobs-updated.csv")

# connect to psql database
DATABASE_URL = "postgresql+psycopg2://postgres:iui@localhost:5432/iui_project"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()
metadata = MetaData()

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
        filtered_jobs = filtered_jobs[filtered_jobs['remote_work_model'].str.contains(remote_work_model, case=False, na=False)]  # Filter by remote work model
    
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
    
    return filtered_jobs[['title', 'company', 'location', 'types', 'remote_work_model','source_id']]

# Chat with the Seeker using GPT-3.5-turbo
def chat_with_Seeker(prompt):
    response = openai.ChatCompletion.create(
        model = "gpt-3.5-turbo",
        messages = [{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

# Chatbot flow
def job_chatbot():
    while True:
        detailed_search = input("\nJobSeeker:  Do you want a detailed job search? \nYou:        ").lower()
        if detailed_search == "yes":    
        
            # Capture job preferences without showing normalized input
            preferred_title = input("\nJobSeeker:  What is your preferred job title? \nYou:        ")
            preferred_title = normalize_input(preferred_title, "job title")
            print(f"            Normalized job title: {preferred_title}")
            
            preferred_location = input("\nJobSeeker:  Preferred job location (e.g., Remote, specific city)? \nYou:        ")
            preferred_location = normalize_location(preferred_location)
            print(f"            Normalized location: {preferred_location}")

            contract_type = input("\nJobSeeker:  What is your preferred contract? (Full-time or Part-time) \nYou:        ")
            contract_type = normalize_input(contract_type, "contract type")
            print(f"            Normalized contract: {contract_type}")

            remote_work = input("\nJobSeeker:  Do you want remote work (100% Remote, Hybrid, or No Remote)? \nYou:        ")
            remote_work_model = normalize_remote_work(remote_work)
            print(f"            Normalized remote work: {remote_work}")

            visa_sponsorship = input("\nJobSeeker:  Do you need visa sponsorship (Yes/No)? \nYou:        ")
            visa_sponsorship = normalize_visa_sponsorship(visa_sponsorship)
            print(f"            Normalized sponsorship: {visa_sponsorship}")
        

            # Filter jobs based on normalized inputs
            recommendations = filter_jobs(preferred_title, preferred_location, contract_type, remote_work_model, visa_sponsorship)
            
            if not recommendations.empty:
                index = 0
                batch_size = 5
                total_jobs = len(recommendations)

                while index < total_jobs:
                    # Get the next batch of 5 results
                    next_batch = recommendations.iloc[index:index+batch_size]  
                    print("\nJobSeeker: Here are some job recommendations for you:\n")
                    
                    # Display the batch of results
                    for _, row in next_batch.iterrows():
                        print(f"Job ID:{row['source_id']}\nTitle: {row['title']}\nCompany: {row['company']}\nLocation: {row['location']}\n"
                              f"Type: {row['types']}\nRemote Work: {row['remote_work_model']}\n")
                    
                    # Update the index for the next batch
                    index += batch_size  
                    
                    # Ask if the user wants to see more results
                    if index < total_jobs:
                        see_more = input("\nJobSeeker:  Do you want to see more results? (Yes/No): \nYou:        ").lower()
                        if see_more != "yes":
                            break

                # Ask if the user wants to search for more jobs
                continue_search = input("\nJobSeeker:  Do you want to search for more jobs? (Yes/No): \nYou:        ").lower()
                if continue_search != "yes":
                    anything_else = input("\nJobSeeker:  Anything else? \nYou:        ").lower()
                    if anything_else == "yes":
                        while True:
                            userinput = input("\nJobSeeker:  What else can I help you with? \nYou:       ")
                            if userinput.lower() in ["quit", "exit", "bye"]:
                                print("\nJobSeeker:  Happy Hunting! ")
                                break

                            response = chat_with_Seeker(userinput)
                            print("\nJobSeeker:  ", response)
                    else:
                        print("\nJobSeeker:  Happy Hunting!")
                        break
        else:
            anything_else = input("\nJobSeeker:  Anything else? \nYou:        ").lower()
            if anything_else == "yes":
                while True:
                    userinput = input("\nJobSeeker:  What else can I help you with? \nYou:        ")
                    if userinput.lower() in ["quit", "exit", "bye"]:
                        print("\nJobSeeker:  Happy Hunting! ")
                        break
                    
                    response = chat_with_Seeker(userinput)
                    print("\nJobSeeker:  ", response)
            else:
                print("\nJobSeeker:  Happy Hunting!")
                break

# Run the chatbot
if __name__ == "__main__":
    print("\nJobSeeker:  Hello! I am JobSeeker and I am here to help you find job recommendations.")
    job_chatbot()
