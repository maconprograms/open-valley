"""Parse FPF email digests and import into database."""

import json
import os
import re
from datetime import datetime
from email.utils import parsedate_to_datetime

from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import engine, Base
from src.models import FPFIssue, FPFPerson, FPFPost


def parse_issue_info(subject: str, date_str: str) -> tuple[int | None, datetime, bool]:
    """Extract issue number and date from email. Returns (issue_number, published_at, is_forward)."""
    # Check if this is a forward
    is_forward = subject.lower().startswith("fwd:") if subject else False

    # Subject format: "Mad River Valley Front Porch Forum No. 4230"
    issue_match = re.search(r"No\.\s*(\d+)", subject or "")
    issue_number = int(issue_match.group(1)) if issue_match else None

    # Parse email date (convert to naive UTC for database compatibility)
    try:
        published_at = parsedate_to_datetime(date_str)
        # Convert to naive datetime (remove timezone info) for database compatibility
        if published_at.tzinfo is not None:
            published_at = published_at.replace(tzinfo=None)
    except Exception:
        published_at = datetime.utcnow()

    return issue_number, published_at, is_forward


def parse_location(location_text: str) -> tuple[str | None, str | None]:
    """Parse location into road and town."""
    if not location_text:
        return None, None

    location_text = location_text.strip()

    # Known towns in Mad River Valley
    towns = [
        "Warren", "Waitsfield", "Fayston", "Moretown",
        "North Fayston", "Duxbury", "Granville"
    ]

    town = None
    road = location_text

    for t in towns:
        if location_text.endswith(t):
            town = t
            road = location_text[: -len(t)].rstrip(", ")
            break

    return road if road else None, town


def extract_email_from_mailto(mailto_href: str) -> str | None:
    """Extract email address from mailto: link."""
    if not mailto_href or not mailto_href.startswith("mailto:"):
        return None
    email = mailto_href[7:].split("?")[0]
    return email if email else None


def parse_posts_from_html(html: str) -> list[dict]:
    """Parse individual posts from FPF email HTML."""
    soup = BeautifulSoup(html, "html.parser")
    posts = []

    # Find all post containers (boxes with h3 titles)
    for box in soup.find_all("td", class_="box"):
        # Skip if this is a "Paid Ad"
        paid_ad = box.find("a", string=re.compile(r"Paid\s*Ad", re.I))
        if paid_ad:
            continue

        # Look for post structure: h3 title, author info, category, content
        h3 = box.find("h3")
        if not h3:
            continue

        title = h3.get_text(strip=True)
        if not title:
            continue

        # Skip the "In This Issue" section (which is a table of contents)
        if "In This Issue" in title:
            continue

        # Skip "And X more postings!" entries
        if "more posting" in title.lower():
            continue

        # Find author info: <b>Name</b> • Location
        author_b = box.find("b")
        if not author_b:
            continue

        author_name = author_b.get_text(strip=True)

        # Get location from the paragraph containing the author
        author_p = author_b.find_parent("p")
        if author_p:
            # Extract text after the bullet
            full_text = author_p.get_text(strip=True)
            if "•" in full_text:
                location_text = full_text.split("•", 1)[1].strip()
            else:
                location_text = ""
        else:
            location_text = ""

        road, town = parse_location(location_text)

        # Find category from the link with e7eef1 background
        category = None
        category_link = box.find("a", style=re.compile(r"#e7eef1|e7eef1"))
        if category_link:
            category = category_link.get_text(strip=True)

        # Find content - look for the main content paragraph (font-size: 16px)
        # The content is in a nested div, with p having font-size: 16px
        content = ""
        for div in box.find_all("div"):
            content_p = div.find("p", style=re.compile(r"font-size:\s*16px"))
            if content_p:
                content = content_p.get_text(separator="\n", strip=True)
                break

        # Find author email from mailto link
        email = None
        email_link = box.find("a", href=re.compile(r"^mailto:"))
        if email_link:
            email = extract_email_from_mailto(email_link.get("href", ""))

        # Check if this is a reply
        is_reply = title.lower().startswith("re:")

        if author_name and (title or content):
            posts.append({
                "title": title,
                "content": content,
                "author_name": author_name,
                "author_email": email,
                "road": road,
                "town": town,
                "category": category,
                "is_reply": is_reply,
            })

    return posts


def get_or_create_person(
    session: Session,
    name: str,
    email: str | None,
    road: str | None,
    town: str | None,
    published_at: datetime,
) -> FPFPerson:
    """Get existing person or create new one."""
    # Try to match by email first (most reliable)
    if email:
        person = session.execute(
            select(FPFPerson).where(FPFPerson.email == email)
        ).scalar_one_or_none()
        if person:
            # Update last seen
            if published_at > person.last_seen_at:
                person.last_seen_at = published_at
            return person

    # Try to match by name + road + town
    query = select(FPFPerson).where(FPFPerson.name == name)
    if road:
        query = query.where(FPFPerson.road == road)
    if town:
        query = query.where(FPFPerson.town == town)

    person = session.execute(query).scalar_one_or_none()

    if person:
        # Update email if we have it now and didn't before
        if email and not person.email:
            person.email = email
        if published_at > person.last_seen_at:
            person.last_seen_at = published_at
        return person

    # Create new person
    person = FPFPerson(
        name=name,
        email=email,
        road=road,
        town=town,
        first_seen_at=published_at,
        last_seen_at=published_at,
    )
    session.add(person)
    session.flush()
    return person


def import_email(session: Session, email_data: dict) -> tuple[int, int]:
    """Import a single email. Returns (issues_created, posts_created)."""
    gmail_id = email_data["id"]

    # Check if already imported
    existing = session.execute(
        select(FPFIssue).where(FPFIssue.gmail_id == gmail_id)
    ).scalar_one_or_none()
    if existing:
        return 0, 0

    # Parse issue info
    subject = email_data.get("subject", "")
    date_str = email_data.get("date", "")
    issue_number, published_at, is_forward = parse_issue_info(subject, date_str)

    # Skip forwards - they're duplicates of the original issue
    if is_forward:
        return 0, 0

    # Check if issue number already exists (might be re-sent)
    if issue_number:
        existing_issue = session.execute(
            select(FPFIssue).where(FPFIssue.issue_number == issue_number)
        ).scalar_one_or_none()
        if existing_issue:
            return 0, 0

    # Create issue
    issue = FPFIssue(
        issue_number=issue_number,
        published_at=published_at,
        gmail_id=gmail_id,
        subject=subject,
    )
    session.add(issue)
    session.flush()

    # Parse and create posts
    html = email_data.get("body_html", "")
    if not html:
        return 1, 0

    posts_data = parse_posts_from_html(html)
    posts_created = 0

    for post_data in posts_data:
        person = get_or_create_person(
            session,
            name=post_data["author_name"],
            email=post_data.get("author_email"),
            road=post_data.get("road"),
            town=post_data.get("town"),
            published_at=published_at,
        )

        post = FPFPost(
            issue_id=issue.id,
            person_id=person.id,
            title=post_data["title"],
            content=post_data.get("content", ""),
            category=post_data.get("category"),
            is_reply=post_data.get("is_reply", False),
            published_at=published_at,
        )
        session.add(post)
        posts_created += 1

    return 1, posts_created


def main():
    """Main entry point."""
    # Create tables if they don't exist
    Base.metadata.create_all(engine)

    # Find email files
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    email_dir = os.path.join(project_root, "data", "fpf_emails")

    if not os.path.exists(email_dir):
        print(f"Email directory not found: {email_dir}")
        return

    email_files = [
        f for f in os.listdir(email_dir)
        if f.endswith(".json") and f != "_index.json"
    ]
    print(f"Found {len(email_files)} email files")

    # Import emails
    total_issues = 0
    total_posts = 0
    errors = 0

    from sqlalchemy.orm import Session as SessionClass

    with SessionClass(engine) as session:
        for i, filename in enumerate(email_files, 1):
            filepath = os.path.join(email_dir, filename)
            try:
                with open(filepath) as f:
                    email_data = json.load(f)

                issues_created, posts_created = import_email(session, email_data)
                total_issues += issues_created
                total_posts += posts_created

                if i % 100 == 0:
                    session.commit()
                    print(f"[{i}/{len(email_files)}] {total_issues} issues, {total_posts} posts")

            except Exception as e:
                print(f"Error processing {filename}: {e}")
                session.rollback()
                errors += 1

        session.commit()

    # Print summary
    print(f"\nDone!")
    print(f"  Issues imported: {total_issues}")
    print(f"  Posts imported: {total_posts}")
    print(f"  Errors: {errors}")

    # Print person stats
    with SessionClass(engine) as session:
        person_count = session.execute(
            select(FPFPerson)
        ).all()
        print(f"  Unique people: {len(person_count)}")


if __name__ == "__main__":
    main()
