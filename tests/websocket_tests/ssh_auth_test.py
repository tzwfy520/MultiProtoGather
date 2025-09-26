#!/usr/bin/env python3
"""
SSH认证测试脚本
测试不同的SSH认证方法和参数
"""

import paramiko
import socket
import time
import logging
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SSHAuthTester:
    def __init__(self):
        self.host = "115.190.80.219"
        self.port = 22
        self.username = "Eccom123"
        self.password = "Ff@123qwe"
        
    def test_auth_methods(self):
        """测试可用的认证方法"""
        logger.info("=== 测试SSH认证方法 ===")
        
        try:
            transport = paramiko.Transport((self.host, self.port))
            transport.start_client()
            
            # 获取支持的认证方法
            auth_methods = transport.auth_none(self.username)
            logger.info(f"服务器支持的认证方法: {auth_methods}")
            
            transport.close()
            return auth_methods
            
        except Exception as e:
            logger.error(f"获取认证方法失败: {e}")
            return None
    
    def test_password_auth_variations(self):
        """测试不同的密码认证变体"""
        logger.info("=== 测试密码认证变体 ===")
        
        # 测试不同的密码变体
        password_variations = [
            self.password,  # 原始密码
            self.password.strip(),  # 去除空格
            self.password.encode('utf-8').decode('utf-8'),  # 编码解码
        ]
        
        for i, pwd in enumerate(password_variations, 1):
            logger.info(f"--- 测试密码变体 {i}: '{pwd}' ---")
            
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                client.connect(
                    hostname=self.host,
                    port=self.port,
                    username=self.username,
                    password=pwd,
                    timeout=30,
                    banner_timeout=30,
                    auth_timeout=30,
                    look_for_keys=False,
                    allow_agent=False
                )
                
                logger.info(f"✅ 密码变体 {i} 认证成功")
                client.close()
                return True
                
            except paramiko.AuthenticationException as e:
                logger.error(f"❌ 密码变体 {i} 认证失败: {e}")
            except Exception as e:
                logger.error(f"❌ 密码变体 {i} 连接异常: {e}")
        
        return False
    
    def test_username_variations(self):
        """测试不同的用户名变体"""
        logger.info("=== 测试用户名变体 ===")
        
        # 测试不同的用户名变体
        username_variations = [
            self.username,  # 原始用户名
            self.username.lower(),  # 小写
            self.username.upper(),  # 大写
            self.username.strip(),  # 去除空格
        ]
        
        for i, user in enumerate(username_variations, 1):
            logger.info(f"--- 测试用户名变体 {i}: '{user}' ---")
            
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                client.connect(
                    hostname=self.host,
                    port=self.port,
                    username=user,
                    password=self.password,
                    timeout=30,
                    banner_timeout=30,
                    auth_timeout=30,
                    look_for_keys=False,
                    allow_agent=False
                )
                
                logger.info(f"✅ 用户名变体 {i} 认证成功")
                client.close()
                return True
                
            except paramiko.AuthenticationException as e:
                logger.error(f"❌ 用户名变体 {i} 认证失败: {e}")
            except Exception as e:
                logger.error(f"❌ 用户名变体 {i} 连接异常: {e}")
        
        return False
    
    def test_keyboard_interactive(self):
        """测试键盘交互认证"""
        logger.info("=== 测试键盘交互认证 ===")
        
        def auth_handler(title, instructions, prompt_list):
            logger.info(f"键盘交互认证 - 标题: {title}")
            logger.info(f"说明: {instructions}")
            
            responses = []
            for prompt, echo in prompt_list:
                logger.info(f"提示: {prompt} (echo: {echo})")
                if 'password' in prompt.lower():
                    responses.append(self.password)
                else:
                    responses.append('')
            
            return responses
        
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            transport = paramiko.Transport((self.host, self.port))
            transport.start_client()
            
            # 尝试键盘交互认证
            result = transport.auth_interactive(self.username, auth_handler)
            
            if result == paramiko.AUTH_SUCCESSFUL:
                logger.info("✅ 键盘交互认证成功")
                transport.close()
                return True
            else:
                logger.error(f"❌ 键盘交互认证失败: {result}")
                transport.close()
                return False
                
        except Exception as e:
            logger.error(f"❌ 键盘交互认证异常: {e}")
            return False
    
    def test_manual_ssh_command(self):
        """提示手动测试SSH命令"""
        logger.info("=== 手动SSH测试建议 ===")
        
        ssh_command = f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {self.username}@{self.host}"
        
        logger.info("请手动执行以下SSH命令进行测试:")
        logger.info(f"命令: {ssh_command}")
        logger.info(f"密码: {self.password}")
        logger.info("如果手动连接成功，说明凭据正确，问题可能在于paramiko的配置")
        logger.info("如果手动连接失败，说明凭据或服务器配置有问题")
    
    def run_all_tests(self):
        """运行所有认证测试"""
        logger.info("开始SSH认证测试")
        logger.info(f"目标: {self.username}@{self.host}:{self.port}")
        logger.info("=" * 60)
        
        results = {}
        
        # 1. 测试认证方法
        auth_methods = self.test_auth_methods()
        results['auth_methods'] = auth_methods is not None
        
        # 2. 测试密码认证变体
        results['password_variations'] = self.test_password_auth_variations()
        
        # 3. 测试用户名变体
        results['username_variations'] = self.test_username_variations()
        
        # 4. 测试键盘交互认证
        results['keyboard_interactive'] = self.test_keyboard_interactive()
        
        # 5. 手动测试建议
        self.test_manual_ssh_command()
        
        # 总结
        logger.info("=" * 60)
        logger.info("认证测试结果总结:")
        for test_name, result in results.items():
            status = "✅ 成功" if result else "❌ 失败"
            logger.info(f"{test_name}: {status}")
        
        success_count = sum(results.values())
        total_count = len(results)
        
        logger.info(f"总体结果: {success_count}/{total_count} 项测试成功")
        
        if success_count > 0:
            logger.info("🎉 至少有一种认证方法成功")
        else:
            logger.info("🚨 所有认证方法都失败，请检查凭据或服务器配置")
        
        return results

if __name__ == "__main__":
    tester = SSHAuthTester()
    results = tester.run_all_tests()