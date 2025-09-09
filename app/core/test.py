import os, sys

def resource_path(relative_path):
    """Trả về đường dẫn tuyệt đối, tương thích khi chạy script .py và file .exe"""
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)