#!/usr/bin/env python3
"""
MultiProtGather 最终集成测试脚本
验证前后端集成和所有核心功能
"""

import requests
import json
import time
import sys
from datetime import datetime

# 配置
BACKEND_URL = "http://127.0.0.1:8000/api/v1"
FRONTEND_URL = "http://localhost:3000"
TEST_USER = {"username": "admin", "password": "admin123"}

class IntegrationTester:
    def __init__(self):
        self.access_token = None
        self.test_results = []
        
    def log_test(self, test_name, success, message=""):
        """记录测试结果"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            "test": test_name,
            "status": status,
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        print(f"{status} {test_name}: {message}")
        
    def test_frontend_accessibility(self):
        """测试前端可访问性"""
        try:
            response = requests.get(FRONTEND_URL, timeout=5)
            if response.status_code == 200 and "React App" in response.text:
                self.log_test("前端服务访问", True, "React应用正常运行")
                return True
            else:
                self.log_test("前端服务访问", False, f"状态码: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("前端服务访问", False, f"连接失败: {str(e)}")
            return False
            
    def test_backend_accessibility(self):
        """测试后端可访问性"""
        try:
            response = requests.get(f"{BACKEND_URL}/users/login/", timeout=5)
            # 405 Method Not Allowed 是正常的，说明服务在运行
            if response.status_code in [405, 200]:
                self.log_test("后端服务访问", True, f"Django API正常运行 (状态码: {response.status_code})")
                return True
            else:
                self.log_test("后端服务访问", False, f"异常状态码: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("后端服务访问", False, f"连接失败: {str(e)}")
            return False
            
    def test_user_authentication(self):
        """测试用户认证"""
        try:
            response = requests.post(
                f"{BACKEND_URL}/users/login/",
                json=TEST_USER,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if "access" in data and "user" in data:
                    self.access_token = data["access"]
                    username = data["user"].get("username", "unknown")
                    self.log_test("用户认证", True, f"成功登录用户: {username}")
                    return True
                else:
                    self.log_test("用户认证", False, "响应格式错误")
                    return False
            else:
                self.log_test("用户认证", False, f"登录失败，状态码: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("用户认证", False, f"认证请求失败: {str(e)}")
            return False
            
    def test_server_resource_api(self):
        """测试服务器资源API"""
        if not self.access_token:
            self.log_test("服务器资源API", False, "缺少访问令牌")
            return False
            
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            # 测试获取服务器列表
            response = requests.get(f"{BACKEND_URL}/resources/servers/", headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                server_count = data.get("count", 0)
                self.log_test("获取服务器列表", True, f"当前服务器数量: {server_count}")
                
                # 测试创建服务器资源
                test_server = {
                    "name": "集成测试服务器",
                    "ip_address": "192.168.1.201",  # 使用不同的IP避免冲突
                    "port": 2222,  # 使用不同的端口避免冲突
                    "username": "testuser",
                    "password": "testpass123",  # 添加密码字段
                    "os_type": "linux",
                    "is_active": True,
                    "description": "自动化集成测试创建的服务器"
                }
                
                create_response = requests.post(
                    f"{BACKEND_URL}/resources/servers/",
                    json=test_server,
                    headers=headers,
                    timeout=10
                )
                
                if create_response.status_code == 201:
                    created_server = create_response.json()
                    server_id = created_server.get("id")
                    self.log_test("创建服务器资源", True, f"成功创建服务器 ID: {server_id}")
                    return True
                else:
                    self.log_test("创建服务器资源", False, f"创建失败，状态码: {create_response.status_code}")
                    return False
            else:
                self.log_test("获取服务器列表", False, f"请求失败，状态码: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("服务器资源API", False, f"API请求失败: {str(e)}")
            return False
            
    def test_database_operations(self):
        """测试数据库操作"""
        if not self.access_token:
            self.log_test("数据库操作", False, "缺少访问令牌")
            return False
            
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        try:
            # 获取最新的服务器列表，验证数据持久化
            response = requests.get(f"{BACKEND_URL}/resources/servers/", headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                
                # 查找我们刚创建的测试服务器
                test_server_found = any(
                    server.get("name") == "集成测试服务器" 
                    for server in results
                )
                
                if test_server_found:
                    self.log_test("数据库持久化", True, "测试数据成功保存到数据库")
                    return True
                else:
                    self.log_test("数据库持久化", False, "未找到测试数据")
                    return False
            else:
                self.log_test("数据库操作", False, f"查询失败，状态码: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("数据库操作", False, f"数据库查询失败: {str(e)}")
            return False
            
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始 MultiProtGather 集成测试")
        print("=" * 50)
        
        # 按顺序执行测试
        tests = [
            self.test_frontend_accessibility,
            self.test_backend_accessibility,
            self.test_user_authentication,
            self.test_server_resource_api,
            self.test_database_operations
        ]
        
        for test in tests:
            test()
            time.sleep(1)  # 测试间隔
            
        # 生成测试报告
        self.generate_report()
        
    def generate_report(self):
        """生成测试报告"""
        print("\n" + "=" * 50)
        print("📊 测试报告")
        print("=" * 50)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"总测试数: {total}")
        print(f"通过数: {passed}")
        print(f"失败数: {total - passed}")
        print(f"成功率: {success_rate:.1f}%")
        
        print("\n详细结果:")
        for result in self.test_results:
            print(f"  {result['status']} {result['test']}")
            if result['message']:
                print(f"    └─ {result['message']}")
                
        # 保存结果到文件
        with open("integration_test_results.json", "w", encoding="utf-8") as f:
            json.dump({
                "summary": {
                    "total": total,
                    "passed": passed,
                    "failed": total - passed,
                    "success_rate": success_rate,
                    "timestamp": datetime.now().isoformat()
                },
                "results": self.test_results
            }, f, ensure_ascii=False, indent=2)
            
        print(f"\n📄 详细结果已保存到: integration_test_results.json")
        
        if success_rate == 100:
            print("\n🎉 所有测试通过！系统集成成功！")
            return True
        else:
            print(f"\n⚠️  有 {total - passed} 个测试失败，请检查系统配置")
            return False

if __name__ == "__main__":
    tester = IntegrationTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)