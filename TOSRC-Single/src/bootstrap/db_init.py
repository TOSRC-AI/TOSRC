"""
数据库初始化模块化方法，单独拆分，便于维护和扩展
"""
from src.adapter.dal.sqlite_dal import SQLiteDAL
from src.utils.logger import logger

def init_db(sqlite_path: str) -> SQLiteDAL:
    """初始化SQLite数据库"""
    try:
        db = SQLiteDAL(db_path=sqlite_path)
        # 测试数据库连接
        conn = db.get_connection()
        conn.execute("SELECT 1")
        conn.close()
        logger.info(f"✅ 数据库初始化成功，路径：{sqlite_path}")
        return db
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败：{str(e)}", exc_info=True)
        raise Exception(f"数据库初始化失败：{str(e)}") from e