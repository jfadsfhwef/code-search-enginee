# logger_config.py
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List
import sys


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # Basic log info
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage()
        }

        # Add extra fields if they exist
        if hasattr(record, 'query'):
            log_data['query'] = record.query
        if hasattr(record, 'results'):
            log_data['results'] = record.results

        return json.dumps(log_data)

def get_absolute_log_dir(log_dir: str = 'logs') -> str:
    """Get absolute path to log directory"""
    # If LOGS_DIR environment variable is set, use it
    if 'LOGS_DIR' in os.environ:
        abs_log_dir = os.environ['LOGS_DIR']
    # If log_dir is already absolute, use it
    elif os.path.isabs(log_dir):
        abs_log_dir = log_dir
    # Otherwise, make it absolute relative to the project root
    else:
        # Get the project root directory (3 levels up from this file)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        abs_log_dir = os.path.join(project_root, log_dir)
    
    # Ensure the directory exists
    os.makedirs(abs_log_dir, exist_ok=True)
    return abs_log_dir

class HSCodeLogger:
    _instance = None  # prevent duplicated: Singleton instance
    
    @classmethod
    def get_instance(cls, log_dir: str = 'logs') -> 'HSCodeLogger':
        if cls._instance is None:
            cls._instance = cls(log_dir)
        return cls._instance
    
    def __init__(self, log_dir: str = 'logs'):
        # prevent re-initialization if instance exists
        if HSCodeLogger._instance is not None:
            return
        
        self.log_dir = get_absolute_log_dir(log_dir)
        self._setup_logger()

    def _setup_logger(self):
        # Create logger
        self.logger = logging.getLogger('HSCodeMatcher')
        
        # Only set up handler if it doesn't exist
        if not self.logger.handlers:
            self.logger.setLevel(logging.INFO)
            
            # Console handler only
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # Formatter
            formatter = logging.Formatter('%(message)s')  # Simplified format
            console_handler.setFormatter(formatter)
            
            # Add handler
            self.logger.addHandler(console_handler)

    def log_search(self, query: str, results: List[Dict[str, Any]]):
        """Log search query and results to console"""
        self.logger.info(f"Search performed - Query: {query}")
        self.logger.info(f"Found {len(results)} results")

    def log_error(self, error_msg: str, details: Dict[str, Any] = None):
        """Log error messages to console"""
        if details:
            self.logger.error(f"{error_msg}\nDetails: {json.dumps(details, indent=2)}")
        else:
            self.logger.error(error_msg)
        
    def info(self, msg: str, *args, **kwargs):
        """Log info level message"""
        self.logger.info(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        """Log error level message"""
        self.logger.error(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        """Log warning level message"""
        self.logger.warning(msg, *args, **kwargs)

    def debug(self, msg: str, *args, **kwargs):
        """Log debug level message"""
        self.logger.debug(msg, *args, **kwargs)


def get_logger(log_dir: str = 'logs') -> HSCodeLogger:
    """Factory function to get logger instance"""
    return HSCodeLogger.get_instance(log_dir)

class JSONFileHandler:
    def __init__(self, filename: str):
        # Convert to absolute path if it's not already
        if not os.path.isabs(filename):
            log_dir = get_absolute_log_dir()
            self.filename = os.path.join(log_dir, os.path.basename(filename))
        else:
            self.filename = filename
            
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.filename), exist_ok=True)
        
        # Create the file with empty array if it doesn't exist
        if not os.path.exists(self.filename):
            with open(self.filename, 'w', encoding='utf-8') as f:
                f.write('[]')
        
    def write(self, data: Dict[str, Any]):
        """Write data to JSON file, overwriting any existing content"""
        try:
            # For results.json, we want to overwrite with a single entry
            if os.path.basename(self.filename) == 'results.json':
                # Wrap the data in a list since we expect JSON array format
                data_to_write = [data]
            else:
                # For other files like errors.json, we still want to append
                existing_data = []
                try:
                    with open(self.filename, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:
                            existing_data = json.loads(content)
                        if not isinstance(existing_data, list):
                            existing_data = []
                except (json.JSONDecodeError, FileNotFoundError):
                    existing_data = []
                
                # Add new data
                existing_data.append(data)
                data_to_write = existing_data
            
            # Write to file
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(data_to_write, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Error writing to JSON file {self.filename}: {str(e)}")

class CustomLogger:
    def __init__(self):
        # Set up regular logging
        self.logger = logging.getLogger('hscode_search')
        self.logger.setLevel(logging.INFO)
        
        # Get absolute log directory
        self.log_dir = get_absolute_log_dir()
        
        # Create handlers if they don't exist
        if not self.logger.handlers:
            # Console handler only
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # Formatter
            formatter = logging.Formatter('%(message)s')  # Simplified format
            console_handler.setFormatter(formatter)
            
            # Add handler
            self.logger.addHandler(console_handler)
        
        # JSON file handler for results only
        self.results_handler = JSONFileHandler(os.path.join(self.log_dir, 'results.json'))
    
    def log_search_result(self, query: str, results: List[Dict[str, Any]]):
        """Log search results to results.json, overwriting previous results"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'query': query,
                'results': results,
                'result_count': len(results)
            }
            self.results_handler.write(log_entry)
            self.logger.info(f"Search results logged for query: {query}")
        except Exception as e:
            self.logger.error(f"Error logging search result: {str(e)}")
    
    def log_error(self, error_type: str, error_message: str, details: Dict[str, Any] = None):
        """Log errors to console only"""
        error_msg = f"Error: {error_type} - {error_message}"
        if details:
            error_msg += f"\nDetails: {json.dumps(details, indent=2)}"
        self.logger.error(error_msg)

    def info(self, message: str):
        """Log info level message to console"""
        self.logger.info(message)

    def error(self, message: str):
        """Log error level message to console"""
        self.logger.error(message)

    def warning(self, message: str):
        """Log warning level message to console"""
        self.logger.warning(message)

    def debug(self, message: str):
        """Log debug level message to console"""
        self.logger.debug(message)

_logger = None

def get_logger() -> CustomLogger:
    global _logger
    if _logger is None:
        _logger = CustomLogger()
    return _logger