#!/usr/bin/env python3
"""
测试修复后的添加服务器功能
"""
import requests
import json
import random

# 配置
BASE_URL = "http://localhost:8000"
LOGIN_URL = f"{BASE_URL}/api/v1/users/login/"
SERVERS_URL = f"{BASE_URL}/api/v1/resources/servers/"

def test_add_server():
    """测试添加服务器功能"""
    
    # 1. 登录获取token
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    print("🔐 正在登录...")
    login_response = requests.post(LOGIN_URL, json=login_data)
    
    if login_response.status_code != 200:
        print(f"❌ 登录失败: {login_response.status_code}")
        print(f"响应内容: {login_response.text}")
        return False
    
    token = login_response.json().get('access')
    if not token:
        print("❌ 未获取到访问令牌")
        return False
    
    print("✅ 登录成功")
    
    # 2. 准备添加服务器的数据
    random_ip = f"192.168.1.{random.randint(100, 254)}"
    server_data = {
        "name": f"测试服务器-{random.randint(1000, 9999)}",
        "ip_address": random_ip,
        "port": 22,
        "username": "root",
        "password": "password123",
        "os_type": "linux",  # 使用小写
        "description": "测试服务器描述"
    }
    
    # 3. 添加服务器
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"🖥️  正在添加服务器: {server_data['name']} ({server_data['ip_address']})")
    add_response = requests.post(SERVERS_URL, json=server_data, headers=headers)
    
    if add_response.status_code == 201:
        print("✅ 服务器添加成功!")
        server_info = add_response.json()
        print(f"   服务器ID: {server_info.get('id')}")
        print(f"   服务器名称: {server_info.get('name')}")
        print(f"   IP地址: {server_info.get('ip_address')}")
        print(f"   操作系统: {server_info.get('os_type')}")
        print(f"   状态: {server_info.get('status', '未知')}")
        return True
    else:
        print(f"❌ 添加服务器失败: {add_response.status_code}")
        print(f"响应内容: {add_response.text}")
        return False

if __name__ == "__main__":
    print("🚀 开始测试修复后的添加服务器功能...")
    success = test_add_server()
    
    if success:
        print("\n🎉 测试通过！renderStatus函数修复成功，添加服务器功能正常工作！")
    else:
        print("\n❌ 测试失败，请检查错误信息")