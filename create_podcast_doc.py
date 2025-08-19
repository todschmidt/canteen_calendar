#!/usr/bin/env python3
"""
Script to create a Google Doc from the current podcast script.
The document will be created in the 'Shared with me/Newscast/July 30, 2025' 
folder.
"""

import os
from datetime import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle

# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive'
]


def authenticate_google():
    """Authenticate with Google APIs."""
    creds = None
    # The file token.pickle stores the user's access and refresh tokens.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return creds


def find_shared_folder(service, folder_name):
    """Find a folder that's been shared with the user."""
    print(f"Looking for shared folder: '{folder_name}'")
    
    # Search for folders with the exact name that are accessible to the user
    query = (
        f"name='{folder_name}' and "
        f"mimeType='application/vnd.google-apps.folder' and "
        f"trashed=false"
    )
    
    results = service.files().list(q=query, spaces='drive').execute()
    
    if results['files']:
        folder_id = results['files'][0]['id']
        print(f"Found shared folder: {folder_name} with ID: {folder_id}")
        return folder_id
    else:
        print(f"Shared folder '{folder_name}' not found!")
        return None


def find_or_create_date_folder(service, date_folder_name, parent_folder_id):
    """Find or create a date folder within the specified parent folder."""
    print(f"Looking for date folder: '{date_folder_name}' in parent: {parent_folder_id}")
    
    # Look for the date folder within the parent
    query = (
        f"name='{date_folder_name}' and "
        f"mimeType='application/vnd.google-apps.folder' and "
        f"'{parent_folder_id}' in parents and trashed=false"
    )
    
    results = service.files().list(q=query, spaces='drive').execute()
    
    if results['files']:
        folder_id = results['files'][0]['id']
        print(f"Found existing date folder: {date_folder_name}")
        return folder_id
    else:
        # Create the date folder
        print(f"Creating date folder: {date_folder_name}")
        folder_metadata = {
            'name': date_folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_folder_id]
        }
        
        folder = service.files().create(
            body=folder_metadata, fields='id').execute()
        folder_id = folder['id']
        print(f"Created date folder: {date_folder_name}")
        return folder_id


def create_document(service, title, folder_id):
    """Create a new Google Doc in the specified folder."""
    print(f"Attempting to create Google Doc: {title}")
    print(f"In folder ID: {folder_id}")
    
    document_metadata = {
        'name': title,
        'parents': [folder_id],
        'mimeType': 'application/vnd.google-apps.document'  # This makes it a Google Doc
    }
    
    try:
        document = service.files().create(body=document_metadata, fields='id').execute()
        document_id = document['id']
        print(f"Google Doc created successfully with ID: {document_id}")
        
        # Verify the document was created by trying to get it
        try:
            doc_info = service.files().get(fileId=document_id, fields='id,name,parents,mimeType').execute()
            print(f"Document verification successful:")
            print(f"  ID: {doc_info.get('id')}")
            print(f"  Name: {doc_info.get('name')}")
            print(f"  Parents: {doc_info.get('parents')}")
            print(f"  MIME Type: {doc_info.get('mimeType')}")
        except Exception as e:
            print(f"Warning: Could not verify document after creation: {e}")
        
        return document_id
    except Exception as e:
        print(f"Error creating Google Doc: {e}")
        print(f"Error type: {type(e)}")
        return None


def find_existing_document(service, title, folder_id):
    """Find an existing document with the same title in the specified folder."""
    print(f"Looking for existing document: '{title}' in folder: {folder_id}")
    
    query = (
        f"name='{title}' and "
        f"mimeType='application/vnd.google-apps.document' and "
        f"'{folder_id}' in parents and trashed=false"
    )
    
    results = service.files().list(q=query, spaces='drive').execute()
    
    if results['files']:
        document_id = results['files'][0]['id']
        print(f"Found existing document: {title} with ID: {document_id}")
        return document_id
    else:
        print(f"No existing document found with title: {title}")
        return None


def clear_document_content(docs_service, document_id):
    """Clear all content from an existing document."""
    print(f"Clearing existing content from document: {document_id}")
    
    try:
        # Get the document to see its current content
        doc = docs_service.documents().get(documentId=document_id).execute()
        content_length = len(doc.get('body', {}).get('content', []))
        
        if content_length > 1:  # Document has content beyond the initial newline
            # Delete all content except the initial newline
            requests = [{
                'deleteContentRange': {
                    'range': {
                        'startIndex': 1,
                        'endIndex': content_length
                    }
                }
            }]
            
            docs_service.documents().batchUpdate(
                documentId=document_id,
                body={'requests': requests}
            ).execute()
            
            print("Document content cleared successfully")
        else:
            print("Document is already empty")
            
    except Exception as e:
        print(f"Error clearing document content: {e}")
        print(f"Error type: {type(e)}")


def format_script_for_docs(script_content):
    """Format the script content for Google Docs API."""
    # Return the script content as a simple insert request
    return [{
        'insertText': {
            'location': {
                'index': 1
            },
            'text': script_content
        }
    }]

def update_document_content(docs_service, document_id, requests):
    """Update the document content with the formatted script."""
    print(f"Updating document {document_id}...")
    
    try:
        # First, let's try to get the document to see if it exists
        doc = docs_service.documents().get(documentId=document_id).execute()
        print(f"Document retrieved successfully: {doc.get('title', 'No title')}")
        
        # Now try to insert the actual script content
        if requests and len(requests) > 0:
            script_content = requests[0]['insertText']['text']
            print(f"Inserting script content ({len(script_content)} characters)")
            
            result = docs_service.documents().batchUpdate(
                documentId=document_id,
                body={'requests': requests}
            ).execute()
            
            print("Document content updated successfully")
        else:
            print("No script content to insert!")
        
    except HttpError as error:
        print(f"An error occurred: {error}")
        print(f"Error details: {error.error_details if hasattr(error, 'error_details') else 'No details'}")
        print(f"Error reason: {error.reason if hasattr(error, 'reason') else 'No reason'}")
        
        # Try to get more specific error info
        try:
            error_content = error.content.decode('utf-8') if hasattr(error, 'content') else 'No content'
            print(f"Error content: {error_content}")
        except:
            print("Could not decode error content")
            
    except Exception as e:
        print(f"Unexpected error: {e}")
        print(f"Error type: {type(e)}")


def main():
    """Main function to create the podcast script document."""
    creds = authenticate_google()
    
    # Build the services
    docs_service = build('docs', 'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    
    # Get today's date for folder and document naming
    today = datetime.now()
    # e.g., "August 14, 2025"
    folder_date = today.strftime("%B %d, %Y")
    
    # Define folder path and document title
    shared_folder_name = "Newscast"  # The folder shared with you
    target_folder = folder_date       # The date folder to create
    document_title = f"Cedar Mountain Community Podcast Script - {folder_date}"
    
    print(f"Creating document for: {folder_date}")
    print(f"Looking for shared folder: {shared_folder_name}")
    print(f"Will create date folder: {target_folder}")
    
    # Find the shared Newscast folder
    print(f"\n=== STEP 1: Finding Shared Newscast Folder ===")
    newscast_folder_id = find_shared_folder(drive_service, shared_folder_name)
    
    if not newscast_folder_id:
        print("ERROR: Could not find the shared 'Newscast' folder!")
        print("Make sure the folder is shared with you and has the exact name 'Newscast'")
        return
    
    # Find or create the date folder within Newscast
    print(f"\n=== STEP 2: Creating Date Folder ===")
    folder_id = find_or_create_date_folder(drive_service, target_folder, newscast_folder_id)
    
    if not folder_id:
        print("ERROR: Could not create or find the date folder!")
        return
    
    print(f"Date folder ID obtained: {folder_id}")
    
    # Find existing document
    print(f"\n=== STEP 3: Finding Existing Document ===")
    existing_document_id = find_existing_document(drive_service, document_title, folder_id)
    
    if existing_document_id:
        print(f"Found existing document: {document_title}. Clearing content.")
        clear_document_content(docs_service, existing_document_id)
        document_id = existing_document_id # Use the existing document ID
    else:
        print(f"No existing document found for: {document_title}. Creating new document.")
        document_id = create_document(drive_service, document_title, folder_id)
    
    if not document_id:
        print("ERROR: Could not create or update the document!")
        return
    
    print(f"Document ID obtained: {document_id}")
    
    # Read the current news script
    print(f"\n=== STEP 4: Reading Script File ===")
    script_path = 'podcast/current_news_script.md'
    if not os.path.exists(script_path):
        print(f"Error: Script file not found at {script_path}")
        return
    
    with open(script_path, 'r', encoding='utf-8') as file:
        script_content = file.read()
    
    print(f"Script content loaded: {len(script_content)} characters")
    print(f"First 200 characters: {script_content[:200]}")
    
    # Format the script for Google Docs
    print(f"\n=== STEP 5: Formatting Script ===")
    requests = format_script_for_docs(script_content)
    
    print(f"Generated {len(requests)} formatting requests")
    
    # Update the document content
    print(f"\n=== STEP 6: Updating Document Content ===")
    update_document_content(docs_service, document_id, requests)
    
    print("\nPodcast script document created successfully!")
    print(f"Document ID: {document_id}")
    print(f"Document title: {document_title}")
    print(f"Location: {shared_folder_name}/{target_folder}")


if __name__ == '__main__':
    main() 