import re
import ipaddress
from django.http import HttpRequest
from django.conf import settings
from cryptography.fernet import Fernet
from typing import Optional
import base64
import os


def get_client_ip(request: HttpRequest) -> Optional[str]:
    """
    获取客户端真实IP地址
    
    Args:
        request: Django HttpRequest对象
        
    Returns:
        客户端IP地址字符串，如果无法获取则返回None
    """
    # 尝试从各种HTTP头获取真实IP
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # X-Forwarded-For可能包含多个IP，取第一个
        ip = x_forwarded_for.split(',')[0].strip()
        if is_valid_ip(ip):
            return ip
    
    # 尝试从X-Real-IP头获取
    x_real_ip = request.META.get('HTTP_X_REAL_IP')
    if x_real_ip and is_valid_ip(x_real_ip):
        return x_real_ip
    
    # 尝试从CF-Connecting-IP头获取（Cloudflare）
    cf_connecting_ip = request.META.get('HTTP_CF_CONNECTING_IP')
    if cf_connecting_ip and is_valid_ip(cf_connecting_ip):
        return cf_connecting_ip
    
    # 最后使用REMOTE_ADDR
    remote_addr = request.META.get('REMOTE_ADDR')
    if remote_addr and is_valid_ip(remote_addr):
        return remote_addr
    
    return None


def get_user_agent(request: HttpRequest) -> Optional[str]:
    """
    获取用户代理字符串
    
    Args:
        request: Django HttpRequest对象
        
    Returns:
        用户代理字符串，如果无法获取则返回None
    """
    return request.META.get('HTTP_USER_AGENT')


def is_valid_ip(ip_str: str) -> bool:
    """
    验证IP地址是否有效
    
    Args:
        ip_str: IP地址字符串
        
    Returns:
        如果是有效的IP地址返回True，否则返回False
    """
    try:
        ipaddress.ip_address(ip_str)
        return True
    except ValueError:
        return False


def is_private_ip(ip_str: str) -> bool:
    """
    判断IP地址是否为私有地址
    
    Args:
        ip_str: IP地址字符串
        
    Returns:
        如果是私有IP地址返回True，否则返回False
    """
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip.is_private
    except ValueError:
        return False


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除不安全字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        清理后的安全文件名
    """
    # 移除或替换不安全字符
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # 移除控制字符
    filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)
    # 限制长度
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        max_name_len = 255 - len(ext) - 1 if ext else 255
        filename = name[:max_name_len] + ('.' + ext if ext else '')
    
    return filename.strip()


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小为人类可读格式
    
    Args:
        size_bytes: 文件大小（字节）
        
    Returns:
        格式化后的文件大小字符串
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    return f"{size:.1f} {size_names[i]}"


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    截断字符串到指定长度
    
    Args:
        text: 原始字符串
        max_length: 最大长度
        suffix: 截断后的后缀
        
    Returns:
        截断后的字符串
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def parse_duration(duration_str: str) -> Optional[int]:
    """
    解析持续时间字符串为秒数
    
    Args:
        duration_str: 持续时间字符串，如 "1h30m", "90s", "2d"
        
    Returns:
        持续时间的秒数，解析失败返回None
    """
    if not duration_str:
        return None
    
    # 定义时间单位转换
    units = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400,
        'w': 604800,
    }
    
    total_seconds = 0
    current_number = ""
    
    for char in duration_str.lower():
        if char.isdigit():
            current_number += char
        elif char in units:
            if current_number:
                total_seconds += int(current_number) * units[char]
                current_number = ""
            else:
                return None
        else:
            return None
    
    # 如果最后还有数字但没有单位，默认为秒
    if current_number:
        total_seconds += int(current_number)
    
    return total_seconds if total_seconds > 0 else None


def get_encryption_key():
    """获取加密密钥"""
    key = getattr(settings, 'ENCRYPTION_KEY', None)
    if not key:
        # 如果没有设置密钥，从环境变量获取
        key = os.environ.get('ENCRYPTION_KEY')
    
    if not key:
        raise ValueError("未设置加密密钥，请在settings中设置ENCRYPTION_KEY或环境变量ENCRYPTION_KEY")
    
    # 如果密钥是字符串，转换为bytes
    if isinstance(key, str):
        key = key.encode()
    
    return key


def encrypt_password(password: str) -> str:
    """
    加密密码
    
    Args:
        password: 明文密码
        
    Returns:
        加密后的密码（base64编码）
    """
    if not password:
        return ""
    
    try:
        key = get_encryption_key()
        fernet = Fernet(key)
        encrypted = fernet.encrypt(password.encode())
        return base64.b64encode(encrypted).decode()
    except Exception as e:
        raise ValueError(f"密码加密失败: {str(e)}")


def decrypt_password(encrypted_password: str) -> str:
    """
    解密密码
    
    Args:
        encrypted_password: 加密的密码（base64编码）
        
    Returns:
        明文密码
    """
    if not encrypted_password:
        return ""
    
    try:
        key = get_encryption_key()
        fernet = Fernet(key)
        encrypted_bytes = base64.b64decode(encrypted_password.encode())
        decrypted = fernet.decrypt(encrypted_bytes)
        return decrypted.decode()
    except Exception as e:
        raise ValueError(f"密码解密失败: {str(e)}")


def generate_encryption_key() -> str:
    """
    生成新的加密密钥
    
    Returns:
        base64编码的密钥字符串
    """
    key = Fernet.generate_key()
    return base64.b64encode(key).decode()