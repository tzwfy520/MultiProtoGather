#!/usr/bin/env python3
"""
测试前端添加服务器功能的脚本（使用唯一IP）
"""
import requests
import json
import time
import random

def test_add_server_functionality():
    """测试添加服务器功能"""
    base_url = "http://127.0.0.1:8000/api/v1"
    
    print("🔍 测试前端添加服务器功能...")
    
    # 1. 登录获取token
    print("1. 登录获取认证token...")
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = requests.post(f"{base_url}/users/login/", json=login_data)
        if response.status_code == 200:
            token = response.json()['access']
            print("✅ 登录成功")
        else:
            print(f"❌ 登录失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 登录请求失败: {e}")
        return False
    
    # 2. 测试添加服务器（使用随机IP确保唯一性）
    print("2. 测试添加服务器...")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 生成随机IP地址确保唯一性
    random_ip = f"192.168.{random.randint(2, 254)}.{random.randint(1, 254)}"
    
    server_data = {
        "name": "Frontend Test Server",
        "ip_address": random_ip,
        "ssh_port": 22,
        "username": "testuser",
        "password": "testpass123",
        "protocol": "ssh",
        "os_type": "linux",  # 使用小写值
        "os_version": "Ubuntu 20.04",
        "description": "前端功能测试服务器"
    }
    
    print(f"使用IP地址: {random_ip}")
    
    try:
        response = requests.post(f"{base_url}/resources/servers/", 
                               json=server_data, headers=headers)
        if response.status_code == 201:
            server = response.json()
            print(f"✅ 服务器添加成功: {server['name']} (ID: {server.get('id', 'N/A')})")
            print(f"服务器详情: IP={server.get('ip_address')}, OS={server.get('os_type')}")
            return True
        else:
            print(f"❌ 服务器添加失败: {response.status_code}")
            print(f"错误详情: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 添加服务器请求失败: {e}")
        return False

if __name__ == "__main__":
    success = test_add_server_functionality()
    if success:
        print("\n🎉 前端添加服务器功能测试通过！")
        print("✅ os_type字段修复成功，前端现在可以正常添加服务器")
    else:
        print("\n❌ 前端添加服务器功能测试失败！")
