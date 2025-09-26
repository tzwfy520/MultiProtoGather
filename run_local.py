#!/usr/bin/env python3
"""
本地运行 MultiProtGather 系统的脚本
绕过 Docker 网络问题，直接在本地环境运行
"""

import os
import sys
import subprocess
import time
import signal
from pathlib import Path

def check_python_version():
    """检查 Python 版本"""
    if sys.version_info < (3, 8):
        print("错误: 需要 Python 3.8 或更高版本")
        sys.exit(1)
    print(f"✓ Python 版本: {sys.version}")

def check_dependencies():
    """检查依赖是否安装"""
    try:
        import django
        print(f"✓ Django 版本: {django.get_version()}")
    except ImportError:
        print("错误: Django 未安装，请运行: pip install -r requirements.txt")
        sys.exit(1)

def setup_environment():
    """设置环境变量"""
    env_vars = {
        'DJANGO_SETTINGS_MODULE': 'multiprotgather_backend.settings',
        'DEBUG': 'True',
        'SECRET_KEY': 'dev-secret-key-for-local-testing',
        'DATABASE_URL': 'sqlite:///db.sqlite3',
        'REDIS_URL': 'redis://localhost:6379/0',
        'ALLOWED_HOSTS': 'localhost,127.0.0.1',
        'CORS_ALLOWED_ORIGINS': 'http://localhost:3000,http://127.0.0.1:3000',
        'DB_ENGINE': 'django.db.backends.sqlite3',
        'DB_NAME': 'db.sqlite3',
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"✓ 设置环境变量: {key}")

def run_migrations():
    """运行数据库迁移"""
    print("\n🔄 运行数据库迁移...")
    try:
        subprocess.run([sys.executable, 'manage.py', 'migrate'], check=True)
        print("✓ 数据库迁移完成")
    except subprocess.CalledProcessError as e:
        print(f"错误: 数据库迁移失败: {e}")
        return False
    return True

def create_superuser():
    """创建超级用户"""
    print("\n👤 创建超级用户...")
    try:
        # 检查是否已存在超级用户
        result = subprocess.run([
            sys.executable, 'manage.py', 'shell', '-c',
            'from django.contrib.auth.models import User; print(User.objects.filter(is_superuser=True).exists())'
        ], capture_output=True, text=True)
        
        if 'True' in result.stdout:
            print("✓ 超级用户已存在")
            return True
            
        # 创建默认超级用户
        subprocess.run([
            sys.executable, 'manage.py', 'shell', '-c',
            '''
from django.contrib.auth.models import User
if not User.objects.filter(username="admin").exists():
    User.objects.create_superuser("admin", "admin@example.com", "admin123")
    print("创建默认超级用户: admin/admin123")
'''
        ], check=True)
        print("✓ 超级用户创建完成")
    except subprocess.CalledProcessError as e:
        print(f"警告: 超级用户创建失败: {e}")
    return True

def start_django_server():
    """启动 Django 开发服务器"""
    print("\n🚀 启动 Django 开发服务器...")
    try:
        process = subprocess.Popen([
            sys.executable, 'manage.py', 'runserver', '0.0.0.0:8000'
        ])
        return process
    except Exception as e:
        print(f"错误: Django 服务器启动失败: {e}")
        return None

def start_frontend_server():
    """启动前端开发服务器"""
    frontend_dir = Path('multiprotgather-frontend')
    if not frontend_dir.exists():
        print("警告: 前端目录不存在，跳过前端服务器启动")
        return None
        
    print("\n🌐 启动前端开发服务器...")
    try:
        # 检查是否安装了依赖
        if not (frontend_dir / 'node_modules').exists():
            print("安装前端依赖...")
            subprocess.run(['npm', 'install'], cwd=frontend_dir, check=True)
        
        process = subprocess.Popen(['npm', 'start'], cwd=frontend_dir)
        return process
    except Exception as e:
        print(f"警告: 前端服务器启动失败: {e}")
        return None

def main():
    """主函数"""
    print("🔧 MultiProtGather 本地运行脚本")
    print("=" * 50)
    
    # 检查环境
    check_python_version()
    check_dependencies()
    setup_environment()
    
    # 数据库设置
    if not run_migrations():
        sys.exit(1)
    create_superuser()
    
    # 启动服务
    django_process = start_django_server()
    if not django_process:
        sys.exit(1)
    
    frontend_process = start_frontend_server()
    
    print("\n" + "=" * 50)
    print("🎉 系统启动完成!")
    print("📍 后端 API: http://localhost:8000")
    print("📍 API 文档: http://localhost:8000/api/docs/")
    print("📍 管理后台: http://localhost:8000/admin/")
    print("📍 默认管理员: admin / admin123")
    
    if frontend_process:
        print("📍 前端界面: http://localhost:3000")
    
    print("\n按 Ctrl+C 停止服务")
    print("=" * 50)
    
    # 等待中断信号
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 正在停止服务...")
        
        if django_process:
            django_process.terminate()
            django_process.wait()
            print("✓ Django 服务器已停止")
        
        if frontend_process:
            frontend_process.terminate()
            frontend_process.wait()
            print("✓ 前端服务器已停止")
        
        print("👋 再见!")

if __name__ == '__main__':
    main()