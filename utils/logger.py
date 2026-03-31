"""
简单的日志模块
提供统一的日志记录功能
"""

import logging
import os
from datetime import datetime
from typing import Optional


class TokenLensLogger:
    """Token Lens 日志记录器"""

    def __init__(self, name: str = "token_lens", log_dir: Optional[str] = None):
        """
        初始化日志记录器

        Args:
            name: 日志记录器名称
            log_dir: 日志文件目录（默认为项目根目录下的 logs 文件夹）
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # 避免重复添加处理器
        if not self.logger.handlers:
            # 控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_format = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(console_format)
            self.logger.addHandler(console_handler)

            # 文件处理器
            if log_dir is None:
                # 默认日志目录为项目根目录下的 logs 文件夹
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                log_dir = os.path.join(project_root, "logs")

            # 确保 logs 目录存在
            os.makedirs(log_dir, exist_ok=True)

            # 按日期创建日志文件
            log_file = os.path.join(log_dir, f"token_lens_{datetime.now().strftime('%Y%m%d')}.log")
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_format = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_format)
            self.logger.addHandler(file_handler)

    def info(self, message: str):
        """记录信息级别日志"""
        self.logger.info(message)

    def warning(self, message: str):
        """记录警告级别日志"""
        self.logger.warning(message)

    def error(self, message: str, exc_info: bool = False):
        """记录错误级别日志"""
        self.logger.error(message, exc_info=exc_info)

    def debug(self, message: str):
        """记录调试级别日志"""
        self.logger.debug(message)

    def api_call(self, api_name: str, endpoint: str, params: Optional[dict] = None):
        """记录 API 调用"""
        params_str = f" with params {params}" if params else ""
        self.info(f"API Call: {api_name} - {endpoint}{params_str}")

    def api_success(self, api_name: str, duration: float):
        """记录 API 调用成功"""
        self.info(f"API Success: {api_name} - Completed in {duration:.2f}s")

    def api_error(self, api_name: str, error: Exception, duration: float = 0):
        """记录 API 调用失败"""
        self.error(f"API Error: {api_name} - {str(error)} (took {duration:.2f}s)", exc_info=False)


# 全局日志实例
_logger_instance = None


def get_logger(name: str = "token_lens") -> TokenLensLogger:
    """获取全局日志实例"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = TokenLensLogger(name)
    return _logger_instance


def log_function_call(func):
    """装饰器：记录函数调用"""
    def wrapper(*args, **kwargs):
        logger = get_logger()
        func_name = func.__name__
        logger.debug(f"Calling function: {func_name}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"Function {func_name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Function {func_name} failed: {str(e)}", exc_info=True)
            raise
    return wrapper