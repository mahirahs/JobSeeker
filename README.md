**JobSeeker: Easy Job Hunting**

Overview

JobSeeker is a Python-based job recommendation chatbot that helps users find suitable jobs by filtering job listings based on their preferences. The chatbot uses OpenAI's GPT-3.5-turbo for natural language processing, allowing users to specify their job preferences, such as job title, location, contract type, remote work preferences, and visa sponsorship requirements.

The chatbot interacts with users through a conversational flow, gathers job preferences, and provides job recommendations from a dataset of U.S. software engineering jobs.
Features

    Natural Language Input Normalization: 
    
    User inputs like job title, location, and remote work preferences are normalized using GPT-3.5-turbo to ensure consistent and relevant filtering.
    
    Job Recommendations: 
    
    Jobs are filtered based on user preferences like location, contract type, remote work options, and visa sponsorship.
    
    Interactive Conversation: 
    
    Users can interact with the chatbot in a friendly, conversational manner, and they can continue the search or refine their preferences.
    
    Batch Display of Jobs: 
    
    Recommendations are shown in batches of five to avoid overwhelming the user, with the option to display more results if desired.

Prerequisites

    Python 3.7+
    
    OpenAI Python SDK: Install using pip install openai
    
    Pandas: Install using pip install pandas
    
    Job Dataset: A CSV file (us-software-engineer-jobs-updated.csv) containing job listings is required for filtering.

Setup and Installation

    Clone or download the repository.
    
    Install required Python libraries:
        
        pip install openai pandas

    Set your OpenAI API key in the code:

        openai.api_key = "your-api-key-here"

    Ensure the dataset (us-software-engineer-jobs-updated.csv) is in the same directory as the script.

How to Run

To run the chatbot:

    Open a terminal or command prompt.
   
    Run the script using Python:

        python MainFile.py

    Interact with the chatbot by answering its prompts. You can input job preferences, and the chatbot will return job recommendations based on your inputs.

Usage

When prompted, provide the following details:

    Job Title: Your preferred job title (e.g., "Software Engineer").

    Location: The preferred job location (e.g., "Remote" or a specific city).
    
    Contract Type: Full-time or part-time.
    
    Remote Work Preferences: 100% Remote, Hybrid, or No Remote.
    
    Visa Sponsorship: Whether visa sponsorship is required (Yes/No).

The chatbot will return a list of job recommendations based on your inputs. You can ask for more recommendations or adjust your search preferences.

OpenAI key:

Replace "enter_your_openai_key" with your OpenAI key. Get your OpenAI key from "https://platform.openai.com/docs/api-reference/authentication"

Example Interaction:

Seeker: Do you want a detailed job search?
You: Yes
Seeker: What is your preferred job title?
You: Software Engineer
Seeker: Preferred job location (e.g., Remote, specific city)?
You: Remote
Seeker: What is your preferred contract? (Full-time or Part-time)
You: Full-time
Seeker: Do you want remote work (100% Remote, Hybrid, or No Remote)?
You: 100% Remote
Seeker: Do you need visa sponsorship (Yes/No)?
You: No

Seeker: Here are some job recommendations for you:
Title: Software Engineer
Company: TechCorp
Location: Remote
Type: Full-time
Remote Work: 100% Remote

License

This project is licensed under the MIT License - see the LICENSE file for details.

Contact

For any questions or issues, feel free to reach out at [amalesh.unoffical@gmail.com, ].
