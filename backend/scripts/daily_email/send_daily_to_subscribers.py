#!/usr/bin/env python3
"""
Send daily summary emails to all subscribed users in the database.
This script retrieves all users with subscribed=True and sends them 
the daily feed email with personalized greetings.
"""

import asyncio
import sys
import os
import logging
import argparse
from typing import List

# Add the backend directory to the Python path
backend_dir = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, backend_dir)

from app.services.db_service import db_service
from send_email import send_daily_summary

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def send_to_all_subscribers(test_mode=False):
    """
    Get all subscription emails from the database and send daily summary emails to them.
    
    参数：
    test_mode: 如果为True，则只显示将要发送的邮件信息，不实际发送
    
    Returns the number of emails successfully sent.
    """
    try:
        # Get all subscription emails from database
        logger.info("Fetching subscription emails from database...")
        subscription_emails = await db_service.get_all_subscription_emails()
        
        if not subscription_emails:
            logger.info("No subscription emails found in database")
            return 0
        
        logger.info(f"Found {len(subscription_emails)} subscription emails")
        
        if test_mode:
            logger.info("🧪 TEST MODE: Will simulate sending emails")
        
        # Send emails to all subscribers
        successful_sends = 0
        failed_sends = 0
        print(f"\nSending daily summary emails to {subscription_emails} subscribers...\n")
        for email in subscription_emails:
            logger.info(f"Sending daily summary to {email}")
            
            try:
                # Send email (no personalized name since we only have email addresses)
                result = send_daily_summary(
                    recipient_email=email,
                    recipient_name=None,
                    test_mode=test_mode
                )
                
                if result["success"]:
                    successful_sends += 1
                    logger.info(f"✅ Successfully sent email to {email}")
                    logger.debug(f"   Details: {result.get('message', 'No details')}")
                else:
                    failed_sends += 1
                    error_msg = result.get('message', 'Unknown error')
                    logger.error(f"❌ Failed to send email to {email}: {error_msg}")
                    
            except Exception as e:
                failed_sends += 1
                logger.error(f"❌ Error sending email to {email}: {str(e)}")
        
        # Log summary
        logger.info(f"Email sending completed:")
        logger.info(f"  ✅ Successful: {successful_sends}")
        logger.info(f"  ❌ Failed: {failed_sends}")
        logger.info(f"  📊 Total attempted: {len(subscription_emails)}")
        
        return successful_sends
        
    except Exception as e:
        logger.error(f"Critical error in send_to_all_subscribers: {str(e)}", exc_info=True)
        return 0

async def main(test_mode=False):
    """
    Main function to run the subscriber email sending process.
    """
    mode_str = "TEST MODE" if test_mode else "PRODUCTION MODE"
    logger.info(f"=== Starting Daily Email to Subscribers ({mode_str}) ===")
    
    try:
        successful_count = await send_to_all_subscribers(test_mode=test_mode)
        
        if successful_count > 0:
            if test_mode:
                logger.info(f"🧪 TEST COMPLETE: Would send daily summaries to {successful_count} subscribers")
            else:
                logger.info(f"🎉 Successfully sent daily summaries to {successful_count} subscribers")
            return 0  # Success exit code
        else:
            if test_mode:
                logger.warning("⚠️ TEST: No emails would be sent")
            else:
                logger.warning("⚠️ No emails were sent successfully")
            return 1  # Error exit code
            
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}", exc_info=True)
        return 1

def sync_main():
    """
    Synchronous wrapper for the main async function with command line argument parsing.
    """
    parser = argparse.ArgumentParser(
        description="Send daily summary emails to all subscribed users",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python send_daily_to_subscribers.py                # Send emails to all subscribers
  python send_daily_to_subscribers.py --test         # Test mode (no emails sent)
  python send_daily_to_subscribers.py --verbose      # Verbose logging
        """
    )
    
    parser.add_argument(
        '--test', 
        action='store_true',
        help='Run in test mode (simulate sending but don\'t actually send emails)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging (DEBUG level)'
    )
    
    args = parser.parse_args()
    
    # Set logging level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Verbose logging enabled")
    
    if args.test:
        logger.info("Test mode enabled - no emails will be sent")
    
    return asyncio.run(main(test_mode=args.test))

if __name__ == "__main__":
    exit_code = sync_main()
    sys.exit(exit_code) 