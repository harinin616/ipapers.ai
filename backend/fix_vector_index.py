 #!/usr/bin/env python3
"""
脚本用于修复FAISS索引中的paper_ids，添加平台信息。
将现有的paper_ids列表转换为包含(paper_id, platform)元组的列表。
"""

import os
import sys
import pickle
import logging
from pathlib import Path
from typing import List, Tuple

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# 导入需要的模块
from app.services.extract_info import extract_platform

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def fix_paper_ids():
    """
    修复paper_ids列表，将其转换为(paper_id, platform)元组的列表
    """
    # 定义文件路径
    data_dir = project_root / "data"
    paper_ids_path = data_dir / "paper_ids.pkl"
    paper_platforms_path = data_dir / "paper_platforms.pkl"
    
    # 检查文件是否存在
    if not paper_ids_path.exists():
        logger.error(f"无法找到paper_ids文件: {paper_ids_path}")
        return False
    
    try:
        # 加载现有的paper_ids
        logger.info(f"加载paper_ids文件: {paper_ids_path}")
        with open(paper_ids_path, 'rb') as f:
            paper_ids = pickle.load(f)
        
        logger.info(f"加载了 {len(paper_ids)} 个paper_ids")
        
        # 创建新的(paper_id, platform)元组列表
        paper_id_platforms = []
        paper_platforms = []
        
        # 处理每个paper_id
        for paper_id in paper_ids:
            # 使用extract_platform获取平台信息
            platform = extract_platform(paper_id)
            paper_id_platforms.append((paper_id, platform))
            paper_platforms.append(platform)
        
        # 保存新的数据
        with open(paper_ids_path, 'wb') as f:
            pickle.dump(paper_id_platforms, f)
        
        # 单独保存platforms列表，以便兼容旧代码
        with open(paper_platforms_path, 'wb') as f:
            pickle.dump(paper_platforms, f)
        
        logger.info(f"成功更新 {len(paper_id_platforms)} 个paper_ids，添加了platform信息")
        logger.info(f"新文件已保存到: {paper_ids_path}")
        logger.info(f"platforms文件已保存到: {paper_platforms_path}")
        
        # 打印前5个元素作为示例
        sample = paper_id_platforms[:5]
        logger.info(f"样本数据: {sample}")
        
        return True
    
    except Exception as e:
        logger.error(f"处理过程中出错: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    logger.info("开始修复vector_search_service的paper_ids")
    success = fix_paper_ids()
    if success:
        logger.info("修复完成")
    else:
        logger.error("修复失败") 