#!/usr/bin/env python3
# print_db.py - Database inspection script

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from app.models.db_models import (
    DBUser, DBPaper, DBAuthor, DBCategory, DBFolder, DBUserFile,
    DBUserTopic, DBSession, DBMessage, PageViewDaily, DBFeedback,
    DBEmailList, DBSharedFolder, Base
)

# Database connection URL
DATABASE_URL = 'postgresql://postgres:yourpass@localhost:5432/dlmonitor'

def print_table_info():
    """Print all tables in the database"""
    engine = create_engine(DATABASE_URL, echo=False)
    inspector = inspect(engine)
    
    print("=== DATABASE TABLES ===")
    table_names = inspector.get_table_names()
    for i, table_name in enumerate(table_names, 1):
        print(f"{i:2d}. {table_name}")
    print(f"\nTotal tables: {len(table_names)}")
    print()

def print_table_columns(table_name):
    """Print column information for any table"""
    engine = create_engine(DATABASE_URL, echo=False)
    inspector = inspect(engine)
    
    print(f"=== {table_name.upper()} TABLE COLUMNS ===")
    try:
        columns = inspector.get_columns(table_name)
        for i, col in enumerate(columns, 1):
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            default = f" DEFAULT={col['default']}" if col['default'] is not None else ""
            print(f"{i:2d}. {col['name']} | {col['type']} | {nullable}{default}")
        print(f"\nTotal columns: {len(columns)}")
    except Exception as e:
        print(f"Error: Table '{table_name}' not found or inaccessible: {e}")
    print()

def print_papers_columns():
    """Print column information for the papers table"""
    print_table_columns('papers')

def print_all_table_columns():
    """Print column information for all tables"""
    engine = create_engine(DATABASE_URL, echo=False)
    inspector = inspect(engine)
    
    print("=== ALL TABLE COLUMNS ===")
    table_names = inspector.get_table_names()
    
    for table_name in sorted(table_names):
        print_table_columns(table_name)

def print_users():
    """Print all users"""
    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    print("=== USERS TABLE ===")
    users = session.query(DBUser).all()
    for u in users:
        print(f"id={u.id} | legacy_id={u.legacy_user_id} | name={u.name!r} | email={u.email!r}")
    print(f"Total users: {len(users)}\n")
    session.close()

def print_papers(limit=10):
    """Print papers with limit"""
    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    print(f"=== PAPERS TABLE (showing first {limit}) ===")
    print("COLUMNS: paper_id | title | published_date | click_count")
    print("-" * 80)
    papers = session.query(DBPaper).limit(limit).all()
    for p in papers:
        print(f"id={p.paper_id!r} | title={p.title[:80]!r}... | published={p.published_date.strftime('%Y-%m-%d')} | clicks={p.click_count}")
    
    total_count = session.query(DBPaper).count()
    print(f"Showing {len(papers)} of {total_count} total papers\n")
    session.close()

def print_authors(limit=20):
    """Print authors with limit"""
    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    print(f"=== AUTHORS TABLE (showing first {limit}) ===")
    authors = session.query(DBAuthor).limit(limit).all()
    for a in authors:
        print(f"id={a.id} | name={a.name!r}")
    
    total_count = session.query(DBAuthor).count()
    print(f"Showing {len(authors)} of {total_count} total authors\n")
    session.close()

def print_categories():
    """Print all categories"""
    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    print("=== CATEGORIES TABLE ===")
    categories = session.query(DBCategory).all()
    for c in categories:
        print(f"id={c.id} | name={c.name!r}")
    print(f"Total categories: {len(categories)}\n")
    session.close()

def print_folders(limit=20):
    """Print folders with limit"""
    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    print(f"=== FOLDERS TABLE (showing first {limit}) ===")
    folders = session.query(DBFolder).limit(limit).all()
    for f in folders:
        print(f"id={f.id} | user_id={f.user_id} | name={f.name!r} | created_at={f.created_at.strftime('%Y-%m-%d %H:%M')}")
    
    total_count = session.query(DBFolder).count()
    print(f"Showing {len(folders)} of {total_count} total folders\n")
    session.close()

def print_sessions(limit=20):
    """Print sessions with limit"""
    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    print(f"=== SESSIONS TABLE (showing first {limit}) ===")
    sessions = session.query(DBSession).limit(limit).all()
    for s in sessions:
        print(f"session_id={s.session_id!r} | user_id={s.user_id} | title={s.title!r} | created_at={s.created_at.strftime('%Y-%m-%d %H:%M')}")
    
    total_count = session.query(DBSession).count()
    print(f"Showing {len(sessions)} of {total_count} total sessions\n")
    session.close()

def print_messages(limit=20):
    """Print messages with limit"""
    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    print(f"=== MESSAGES TABLE (showing first {limit}) ===")
    messages = session.query(DBMessage).limit(limit).all()
    for m in messages:
        content_preview = m.content[:50] + "..." if len(m.content) > 50 else m.content
        print(f"id={m.message_id} | session_id={m.session_id!r} | role={m.role!r} | content={content_preview!r}")
    
    total_count = session.query(DBMessage).count()
    print(f"Showing {len(messages)} of {total_count} total messages\n")
    session.close()

def print_user_files(limit=20):
    """Print user files with limit"""
    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    print(f"=== USER_FILES TABLE (showing first {limit}) ===")
    user_files = session.query(DBUserFile).limit(limit).all()
    for uf in user_files:
        print(f"id={uf.id} | folder_id={uf.folder_id} | paper_id={uf.paper_id!r} | selected={uf.selected} | added_at={uf.added_at.strftime('%Y-%m-%d %H:%M')}")
    
    total_count = session.query(DBUserFile).count()
    print(f"Showing {len(user_files)} of {total_count} total user files\n")
    session.close()

def print_feedback():
    """Print all feedback"""
    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    print("=== FEEDBACK TABLE ===")
    feedbacks = session.query(DBFeedback).all()
    for f in feedbacks:
        question_preview = f.question[:50] + "..." if len(f.question) > 50 else f.question
        print(f"id={f.id} | email={f.email!r} | user_id={f.user_id} | question={question_preview!r} | created_at={f.created_at.strftime('%Y-%m-%d %H:%M')}")
    print(f"Total feedback entries: {len(feedbacks)}\n")
    session.close()

def print_email_list():
    """Print all emails in email list"""
    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    print("=== EMAIL_LIST TABLE ===")
    emails = session.query(DBEmailList).all()
    for e in emails:
        print(f"email={e.email!r}")
    print(f"Total emails: {len(emails)}\n")
    session.close()

def print_shared_folders():
    """Print all shared folders"""
    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    print("=== SHARED_FOLDERS TABLE ===")
    shared_folders = session.query(DBSharedFolder).all()
    for sf in shared_folders:
        print(f"id={sf.id} | folder_id={sf.folder_id} | owner_id={sf.owner_id} | is_public={sf.is_public} | created_at={sf.created_at.strftime('%Y-%m-%d %H:%M')}")
    print(f"Total shared folders: {len(shared_folders)}\n")
    session.close()

def print_page_views():
    """Print page view statistics"""
    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    print("=== PAGE_VIEW_DAILY TABLE ===")
    page_views = session.query(PageViewDaily).all()
    for pv in page_views:
        print(f"day={pv.day} | count={pv.cnt}")
    print(f"Total daily records: {len(page_views)}\n")
    session.close()

def main():
    """Main function to print database overview"""
    import sys
    
    print("DATABASE INSPECTION TOOL")
    print("=" * 50)
    print()
    
    # Print table structure
    print_table_info()
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--full':
            print("Showing detailed data for all tables...\n")
            # Print data from each table
            print_users()
            print_papers()
            print_authors()
            print_categories()
            print_folders()
            print_sessions()
            print_messages()
            print_user_files()
            print_feedback()
            print_email_list()
            print_shared_folders()
            print_page_views()
        elif sys.argv[1] == '--columns':
            print("Showing column information for all tables...\n")
            print_all_table_columns()
        elif sys.argv[1] == '--papers-columns':
            print("Showing column information for papers table...\n")
            print_papers_columns()
        elif sys.argv[1].startswith('--columns='):
            table_name = sys.argv[1].split('=')[1]
            print(f"Showing column information for {table_name} table...\n")
            print_table_columns(table_name)
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print_usage()
    else:
        print_usage()

def print_usage():
    """Print usage information"""
    print("Usage options:")
    print("  python print_db.py                    - Show table list only")
    print("  python print_db.py --full             - Show detailed data from all tables")
    print("  python print_db.py --columns          - Show column info for all tables")
    print("  python print_db.py --papers-columns   - Show column info for papers table")
    print("  python print_db.py --columns=<table>  - Show column info for specific table")

if __name__ == "__main__":
    main()
