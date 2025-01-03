#!/usr/bin/env python3

import json
import os
import sys
from hugchat import hugchat
from hugchat.login import Login
import subprocess

def run_gh_command(command):
    """Run a GitHub CLI command and return the output"""
    try:
        result = subprocess.run(command, shell=True, text=True, capture_output=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running GitHub CLI command: {e}")
        print(f"Command output: {e.output}")
        return None

def should_process_issue(issue_filter, issue_labels):
    """Check if the issue should be processed based on labels"""
    if not issue_filter:
        return True
    
    filter_labels = set(label.strip() for label in issue_filter.split(','))
    issue_label_names = set(label['name'] for label in json.loads(issue_labels))
    return bool(filter_labels & issue_label_names)

def add_labels_to_issue(issue_number, labels):
    """Add labels to the issue"""
    if not labels:
        return
    
    labels_list = [label.strip() for label in labels.split(',')]
    labels_arg = ','.join(labels_list)
    run_gh_command(f'gh issue edit {issue_number} --add-label "{labels_arg}"')

def generate_response(prompt):
    """Generate response using HugChat"""
    try:
        # Set up cookie directory
        cookie_dir = './cookies/'
        os.makedirs(cookie_dir, exist_ok=True)

        # Login to HugChat
        sign = Login(os.environ['HUGCHAT_EMAIL'], os.environ['HUGCHAT_PASSWORD'])
        cookies = sign.login(cookie_dir_path=cookie_dir, save_cookies=True)

        # Create ChatBot and generate response
        chatbot = hugchat.ChatBot(cookies=cookies.get_dict())
        chatbot.new_conversation(
            assistant=os.environ.get('ASSISTANT_ID', '673e290837ec25016921608f'),
            switch_to=True
        )
        
        web_search = os.environ.get('WEB_SEARCH', 'true').lower() == 'true'
        message_result = chatbot.chat(prompt, web_search=web_search)
        return message_result.wait_until_done()

    except Exception as e:
        print(f"Error generating response: {str(e)}")
        return None

def post_comment(issue_number, response):
    """Post comment to the issue"""
    if not response:
        return False

    template = os.environ.get('RESPONSE_TEMPLATE', '''
👋 Hello! Here's a response from HugChat:

---
{response}
---

*Note: I am a bot powered by HugChat. Please verify any information provided.*
''')

    comment = template.format(response=response)
    return run_gh_command(f'gh issue comment {issue_number} --body "{comment}"')

def main():
    # Get environment variables
    issue_number = os.environ.get('ISSUE_NUMBER')
    issue_body = os.environ.get('ISSUE_BODY')
    issue_labels = os.environ.get('ISSUE_LABELS', '[]')
    issue_filter = os.environ.get('ISSUE_FILTER', '')
    add_labels = os.environ.get('ADD_LABELS', '')

    if not issue_number or not issue_body:
        print("Error: Missing issue number or body")
        sys.exit(1)

    # Check if we should process this issue
    if not should_process_issue(issue_filter, issue_labels):
        print("Issue doesn't match label filters. Skipping.")
        sys.exit(0)

    # Generate and post response
    response = generate_response(issue_body)
    if post_comment(issue_number, response):
        add_labels_to_issue(issue_number, add_labels)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
