import base64
import json
import os
import shutil
import time

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def get_gmail_service():
    """Authenticates and returns the Gmail service."""
    creds = None

    script_dir = os.path.dirname(os.path.abspath(__file__))
    api_dir = os.path.dirname(script_dir)
    token_path = os.path.join(api_dir, "token.json")
    credentials_path = os.path.join(api_dir, "credentials.json")

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_path):
                raise FileNotFoundError(f"Credentials file not found at: {credentials_path}")

            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            print("Starting local server for authentication...")
            creds = flow.run_local_server(
                port=8088, prompt="select_account", login_hint="macon.phillips@gmail.com"
            )
            print("Authentication successful.")

        with open(token_path, "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def extract_body_recursive(payload, mime_type="text/html"):
    """Recursively search for body content of specified mime type."""
    if payload.get("mimeType") == mime_type:
        data = payload.get("body", {}).get("data")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8")

    parts = payload.get("parts", [])
    for part in parts:
        result = extract_body_recursive(part, mime_type)
        if result:
            return result
    return None


def get_message_details(service, msg_id):
    """Retrieves the details of a specific message."""
    message = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    payload = message.get("payload", {})
    headers = payload.get("headers", [])

    subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
    sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown")
    date = next((h["value"] for h in headers if h["name"] == "Date"), "Unknown")

    # Extract HTML body (preferred) and plain text
    body_html = extract_body_recursive(payload, "text/html")
    body_text = extract_body_recursive(payload, "text/plain")

    return {
        "id": msg_id,
        "threadId": message.get("threadId"),
        "subject": subject,
        "from": sender,
        "date": date,
        "snippet": message.get("snippet"),
        "body_html": body_html,
        "body_text": body_text,
    }


def get_all_message_ids(service, query):
    """Fetches ALL message IDs matching the query using pagination."""
    all_messages = []
    page_token = None
    page_num = 1

    while True:
        print(f"Fetching message IDs page {page_num}...")
        results = (
            service.users()
            .messages()
            .list(
                userId="me",
                q=query,
                pageToken=page_token,
                maxResults=500,
            )
            .execute()
        )

        messages = results.get("messages", [])
        all_messages.extend(messages)
        print(f"  Found {len(messages)} messages on this page (total so far: {len(all_messages)})")

        page_token = results.get("nextPageToken")
        if not page_token:
            break
        page_num += 1

    return all_messages


def main():
    """Main entry point."""
    service = get_gmail_service()

    # Set up output directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    output_dir = os.path.join(project_root, "data", "fpf_emails")
    os.makedirs(output_dir, exist_ok=True)

    # Check what we already have (for resuming)
    existing_ids = set()
    for filename in os.listdir(output_dir):
        if filename.endswith(".json") and filename != "_index.json":
            existing_ids.add(filename.replace(".json", ""))

    if existing_ids:
        print(f"Found {len(existing_ids)} already downloaded emails (will skip these)")

    # Search for messages with the specific label
    query = 'label:"Front Porch Forum"'
    print(f"Searching for emails with query: {query}")

    messages = get_all_message_ids(service, query)

    if not messages:
        print("No messages found.")
        return

    # Filter out already downloaded
    to_download = [m for m in messages if m["id"] not in existing_ids]
    print(f"\nFound {len(messages)} total messages, {len(to_download)} need downloading...")

    # Fetch messages one at a time with rate limiting
    all_emails = []
    errors = 0

    for i, msg in enumerate(to_download, 1):
        msg_id = msg["id"]
        try:
            details = get_message_details(service, msg_id)

            # Save individual email
            email_file = os.path.join(output_dir, f"{msg_id}.json")
            with open(email_file, "w") as f:
                json.dump(details, f, indent=2)

            subject_preview = (details["subject"] or "No Subject")[:50]
            print(f"[{i}/{len(to_download)}] Saved: {subject_preview}...")
            all_emails.append(details)

            # Rate limit: 0.1s between requests (10 req/sec max)
            time.sleep(0.1)

        except HttpError as e:
            if e.resp.status == 429:  # Rate limited
                print(f"Rate limited! Waiting 60 seconds...")
                time.sleep(60)
                # Retry this one
                try:
                    details = get_message_details(service, msg_id)
                    email_file = os.path.join(output_dir, f"{msg_id}.json")
                    with open(email_file, "w") as f:
                        json.dump(details, f, indent=2)
                    all_emails.append(details)
                    print(f"[{i}/{len(to_download)}] Retry succeeded")
                except Exception as retry_e:
                    print(f"[{i}/{len(to_download)}] Retry failed: {retry_e}")
                    errors += 1
            else:
                print(f"[{i}/{len(to_download)}] Error: {e}")
                errors += 1
        except Exception as e:
            print(f"[{i}/{len(to_download)}] Error: {e}")
            errors += 1

    # Build full index from all files
    print("\nBuilding index from all downloaded files...")
    all_downloaded = []
    for filename in os.listdir(output_dir):
        if filename.endswith(".json") and filename != "_index.json":
            filepath = os.path.join(output_dir, filename)
            with open(filepath) as f:
                all_downloaded.append(json.load(f))

    # Save combined index file
    index_file = os.path.join(output_dir, "_index.json")
    with open(index_file, "w") as f:
        json.dump(all_downloaded, f, indent=2)

    print(f"\nDone! {len(all_downloaded)} total emails in {output_dir}/")
    print(f"Downloaded {len(all_emails)} new emails this run, {errors} errors")
    print(f"Index saved to {index_file}")


if __name__ == "__main__":
    main()
