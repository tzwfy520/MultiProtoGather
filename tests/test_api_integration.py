#!/usr/bin/env python3
"""
API集成测试脚本
测试前端与后端API的集成功能
"""

import requests
import json
import sys

# API配置
BASE_URL = "http://127.0.0.1:8000/api/v1"
FRONTEND_URL = "http://localhost:3000"

def test_login():
    """测试登录功能"""
    print("🔐 测试登录功能...")
    
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/users/login/", json=login_data)
        if response.status_code == 200:
            data = response.json()
            print("✅ 登录成功")
            return data.get('access')
        else:
            print(f"❌ 登录失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ 登录请求异常: {e}")
        return None

def test_server_resources_api(token):
    """测试服务器资源API"""
    print("\n🖥️  测试服务器资源API...")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 测试获取服务器列表
    try:
        response = requests.get(f"{BASE_URL}/resources/servers/", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 获取服务器列表成功，共 {data.get('count', 0)} 台服务器")
            return True
        else:
            print(f"❌ 获取服务器列表失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ 获取服务器列表异常: {e}")
        return False

def test_create_server(token):
    """测试创建服务器"""
    print("\n➕ 测试创建服务器...")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    server_data = {
        "name": "API测试服务器",
        "ip_address": "192.168.1.200",
        "port": 22,
        "username": "test",
        "password": "test123",
        "os_type": "linux",
        "description": "通过API创建的测试服务器"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/resources/servers/", headers=headers, json=server_data)
        if response.status_code == 201:
            data = response.json()
            print("✅ 创建服务器成功")
            print(f"   服务器ID: {data.get('id')}")
            print(f"   服务器名称: {data.get('name')}")
            return data.get('id')
        else:
            print(f"❌ 创建服务器失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ 创建服务器异常: {e}")
        return None

def test_frontend_accessibility():
    """测试前端可访问性"""
    print("\n🌐 测试前端可访问性...")
    
    try:
        response = requests.get(FRONTEND_URL, timeout=5)
        if response.status_code == 200:
            print("✅ 前端页面可正常访问")
            return True
        else:
            print(f"❌ 前端页面访问失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 前端页面访问异常: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始API集成测试...\n")
    
    # 测试前端可访问性
    frontend_ok = test_frontend_accessibility()
    
    # 测试登录
    token = test_login()
    if not token:
        print("\n❌ 登录失败，无法继续测试")
        sys.exit(1)
    
    # 测试服务器资源API
    api_ok = test_server_resources_api(token)
    
    # 测试创建服务器
    server_id = test_create_server(token)
    
    # 总结测试结果
    print("\n" + "="*50)
    print("📊 测试结果总结:")
    print(f"   前端可访问性: {'✅ 通过' if frontend_ok else '❌ 失败'}")
    print(f"   用户登录: {'✅ 通过' if token else '❌ 失败'}")
    print(f"   服务器API: {'✅ 通过' if api_ok else '❌ 失败'}")
    print(f"   创建服务器: {'✅ 通过' if server_id else '❌ 失败'}")
    
    if frontend_ok and token and api_ok and server_id:
        print("\n🎉 所有测试通过！前端与后端API集成正常")
        return True
    else:
        print("\n⚠️  部分测试失败，请检查相关配置")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)