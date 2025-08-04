#!/usr/bin/env python3
import os
import sys
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text

# Add the parent directory to the path so we can import the app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import database connection
from app.db.database import SessionLocal
# Import extract_platform function
from app.services.extract_info import extract_platform
# Import models
from app.models.db_models import DBPaper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def update_platform_for_paper(paper_id: str, old_platform: str, new_platform: str) -> bool:
    """
    更新单个paper及其关联记录的platform
    使用原生SQL执行更新，暂时禁用外键约束
    """
    db = SessionLocal()
    try:
        # 开始事务
        db.begin()
        
        # 临时禁用外键约束
        db.execute(text("SET session_replication_role = 'replica';"))
        
        # 1. 更新papers表记录
        db.execute(
            text("""
            UPDATE papers
            SET platform = :new_platform
            WHERE paper_id = :paper_id AND platform = :old_platform
            """),
            {"paper_id": paper_id, "old_platform": old_platform, "new_platform": new_platform}
        )

        # 2. 更新paper_categories表
        db.execute(
            text("""
            UPDATE paper_categories
            SET platform = :new_platform
            WHERE paper_id = :paper_id AND platform = :old_platform
            """),
            {"paper_id": paper_id, "old_platform": old_platform, "new_platform": new_platform}
        )

        # 3. 更新paper_authors表
        db.execute(
            text("""
            UPDATE paper_authors
            SET platform = :new_platform
            WHERE paper_id = :paper_id AND platform = :old_platform
            """),
            {"paper_id": paper_id, "old_platform": old_platform, "new_platform": new_platform}
        )

        # 4. 更新user_files表
        db.execute(
            text("""
            UPDATE user_files
            SET platform = :new_platform
            WHERE paper_id = :paper_id AND platform = :old_platform
            """),
            {"paper_id": paper_id, "old_platform": old_platform, "new_platform": new_platform}
        )

        # 重新启用外键约束
        db.execute(text("SET session_replication_role = 'origin';"))
        
        # 提交事务
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating paper {paper_id}: {str(e)}")
        return False
    finally:
        # 确保在任何情况下都重新启用外键约束
        try:
            db.execute(text("SET session_replication_role = 'origin';"))
            db.commit()
        except:
            pass
        db.close()


def update_platforms():
    """
    Update platform values for all papers in the database based on paper_id.
    Also update related foreign key tables.
    """
    db = SessionLocal()
    try:
        # 获取所有papers的ID和当前platform
        papers_data = db.query(DBPaper.paper_id, DBPaper.platform).all()
        logger.info(f"Found {len(papers_data)} papers to process")

        # 关闭主会话，后面每个paper用独立事务处理
        db.close()

        # 统计
        total_checked = 0
        total_updated = 0
        total_errors = 0
        
        # 处理每个paper
        for paper_id, current_platform in papers_data:
            total_checked += 1
            
            try:
                # 提取正确的platform
                detected_platform = extract_platform(paper_id)
                
                # 如果platform需要更新
                if current_platform != detected_platform:
                    logger.info(f"Paper {paper_id}: Changing platform from '{current_platform}' to '{detected_platform}'")
                    
                    # 使用独立事务更新paper及其关联记录
                    if update_platform_for_paper(paper_id, current_platform, detected_platform):
                        total_updated += 1
                    else:
                        total_errors += 1
                
                # 每处理100个打印进度
                if total_checked % 100 == 0:
                    logger.info(f"Progress: {total_checked}/{len(papers_data)} papers processed")
                
            except Exception as e:
                logger.error(f"Error processing paper {paper_id}: {str(e)}")
                total_errors += 1
        
        logger.info(f"Summary: Checked {total_checked} papers, updated {total_updated} papers, encountered {total_errors} errors")
        
    except Exception as e:
        logger.error(f"Transaction failed: {str(e)}")


if __name__ == "__main__":
    logger.info("Starting platform update process...")
    update_platforms()
    logger.info("Platform update process completed") 