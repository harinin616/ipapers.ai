#!/usr/bin/env python3
"""
Simple test script to send daily summary email to yourself.
Just change the EMAIL and NAME variables below and run the script.
"""

import sys
import os

# Add the backend directory to the Python path
backend_dir = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, backend_dir)

from send_email import send_daily_summary

# ==========================================
# CHANGE THESE VALUES FOR YOUR EMAIL TEST
# ==========================================
EMAIL = "hl1097@scarletmail.rutgers.edu"  # 👈 Change this to your email
EMAIL = "xiazhiqiuyarle@gmail.com"
TEST_MODE = False                  # 👈 Set to False to actually send email

def main():
    """
    Send a test email to the configured email address.
    """
    print("=" * 50)
    print("📧 Single Email Test Script")
    print("=" * 50)
    print(f"Email: {EMAIL}")
    
    try:
        # Send the email
        result = send_daily_summary(
            recipient_email=EMAIL,
            test_mode=TEST_MODE
        )
        
        # Display the result
        if result["success"]:
            if result.get("skipped", False):
                print("⏭️ SKIPPED!")
                print(f"   {result['message']}")
                
                # Show additional details if available
                if 'date' in result:
                    print(f"   📅 Date: {result['date']}")
                if 'total_papers' in result:
                    print(f"   📄 Total papers: {result['total_papers']}")
                if 'reason' in result:
                    print(f"   🚫 Reason: {result['reason']}")
            else:
                print("✅ SUCCESS!")
                print(f"   {result['message']}")
                
                # Show additional details if available
                if 'date' in result:
                    print(f"   📅 Date: {result['date']}")
                if 'total_papers' in result:
                    print(f"   📄 Total papers: {result['total_papers']}")
                if 'categories_count' in result:
                    print(f"   🏷️  Categories: {result['categories_count']}")
                if 'images_embedded' in result:
                    print(f"   🖼️  Images embedded: {result['images_embedded']}")
                
        else:
            print("❌ FAILED!")
            print(f"   Error: {result['message']}")
            if 'error_type' in result:
                print(f"   Error type: {result['error_type']}")
        
        print()
        print("=" * 50)
        return 0 if result["success"] else 1
        
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {str(e)}")
        print()
        print("=" * 50)
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 