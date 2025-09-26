#!/usr/bin/env python3
"""
SSH连接诊断脚本
用于诊断SSH连接到115.190.80.219的具体问题
"""

import paramiko
import socket
import time
import logging
import sys
import os

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('ssh_diagnosis.log')
    ]
)
logger = logging.getLogger(__name__)

class SSHConnectionDiagnosis:
    def __init__(self):
        self.host = "115.190.80.219"
        self.port = 22
        self.username = "Eccom123"
        self.password = "Ff@123qwe"
        
    def test_network_connectivity(self):
        """测试网络连通性"""
        logger.info("=== 网络连通性测试 ===")
        
        try:
            # 测试TCP连接
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            result = sock.connect_ex((self.host, self.port))
            sock.close()
            
            if result == 0:
                logger.info(f"✅ TCP连接到 {self.host}:{self.port} 成功")
                return True
            else:
                logger.error(f"❌ TCP连接到 {self.host}:{self.port} 失败，错误代码: {result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 网络连接测试异常: {e}")
            return False
    
    def test_ssh_banner(self):
        """测试SSH banner"""
        logger.info("=== SSH Banner测试 ===")
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(15)
            sock.connect((self.host, self.port))
            
            # 接收SSH banner
            banner = sock.recv(1024).decode('utf-8').strip()
            logger.info(f"✅ SSH Banner: {banner}")
            sock.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ SSH Banner测试失败: {e}")
            return False
    
    def test_ssh_connection_basic(self):
        """基础SSH连接测试"""
        logger.info("=== 基础SSH连接测试 ===")
        
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # 基本连接参数
            connect_params = {
                'hostname': self.host,
                'port': self.port,
                'username': self.username,
                'password': self.password,
                'timeout': 15,
                'banner_timeout': 20,
                'auth_timeout': 15,
                'look_for_keys': False,
                'allow_agent': False
            }
            
            logger.info(f"尝试连接到 {self.host}:{self.port}")
            logger.info(f"用户名: {self.username}")
            
            client.connect(**connect_params)
            logger.info("✅ SSH连接成功建立")
            
            # 测试执行简单命令
            stdin, stdout, stderr = client.exec_command('whoami')
            output = stdout.read().decode().strip()
            error = stderr.read().decode().strip()
            
            if output:
                logger.info(f"✅ 命令执行成功，输出: {output}")
            if error:
                logger.warning(f"⚠️ 命令执行有错误输出: {error}")
            
            client.close()
            return True
            
        except paramiko.AuthenticationException as e:
            logger.error(f"❌ SSH认证失败: {e}")
            return False
        except paramiko.SSHException as e:
            logger.error(f"❌ SSH协议错误: {e}")
            return False
        except socket.timeout as e:
            logger.error(f"❌ SSH连接超时: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ SSH连接异常: {e}")
            return False
    
    def test_ssh_interactive_shell(self):
        """测试交互式Shell"""
        logger.info("=== 交互式Shell测试 ===")
        
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            connect_params = {
                'hostname': self.host,
                'port': self.port,
                'username': self.username,
                'password': self.password,
                'timeout': 15,
                'banner_timeout': 20,
                'auth_timeout': 15,
                'look_for_keys': False,
                'allow_agent': False
            }
            
            client.connect(**connect_params)
            logger.info("✅ SSH连接已建立")
            
            # 创建交互式shell
            channel = client.invoke_shell(
                term='xterm-256color',
                width=80,
                height=24
            )
            
            logger.info("✅ 交互式Shell已创建")
            
            # 设置通道参数
            channel.settimeout(0.5)
            
            # 等待初始输出
            time.sleep(2)
            
            # 读取初始输出
            if channel.recv_ready():
                initial_output = channel.recv(4096).decode('utf-8', errors='ignore')
                logger.info(f"初始输出: {repr(initial_output)}")
            
            # 发送测试命令
            test_commands = [
                'whoami\n',
                'pwd\n',
                'echo "SSH Shell Test"\n',
                'date\n'
            ]
            
            for cmd in test_commands:
                logger.info(f"发送命令: {repr(cmd)}")
                channel.send(cmd)
                time.sleep(1)
                
                # 读取输出
                output = ""
                start_time = time.time()
                while time.time() - start_time < 3:
                    if channel.recv_ready():
                        data = channel.recv(4096).decode('utf-8', errors='ignore')
                        output += data
                    else:
                        time.sleep(0.1)
                
                if output:
                    logger.info(f"命令输出: {repr(output)}")
                else:
                    logger.warning("没有收到命令输出")
            
            channel.close()
            client.close()
            logger.info("✅ 交互式Shell测试完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 交互式Shell测试失败: {e}")
            return False
    
    def test_connection_with_different_params(self):
        """使用不同参数测试连接"""
        logger.info("=== 不同参数连接测试 ===")
        
        # 测试不同的超时设置
        timeout_configs = [
            {'timeout': 30, 'banner_timeout': 30, 'auth_timeout': 30},
            {'timeout': 60, 'banner_timeout': 60, 'auth_timeout': 60},
            {'timeout': 10, 'banner_timeout': 15, 'auth_timeout': 10}
        ]
        
        for i, config in enumerate(timeout_configs, 1):
            logger.info(f"--- 测试配置 {i}: {config} ---")
            
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                connect_params = {
                    'hostname': self.host,
                    'port': self.port,
                    'username': self.username,
                    'password': self.password,
                    'look_for_keys': False,
                    'allow_agent': False,
                    **config
                }
                
                start_time = time.time()
                client.connect(**connect_params)
                connect_time = time.time() - start_time
                
                logger.info(f"✅ 配置 {i} 连接成功，耗时: {connect_time:.2f}秒")
                client.close()
                return True
                
            except Exception as e:
                logger.error(f"❌ 配置 {i} 连接失败: {e}")
        
        return False
    
    def run_full_diagnosis(self):
        """运行完整诊断"""
        logger.info("开始SSH连接完整诊断")
        logger.info(f"目标服务器: {self.host}:{self.port}")
        logger.info(f"用户名: {self.username}")
        logger.info("=" * 60)
        
        results = {}
        
        # 1. 网络连通性测试
        results['network'] = self.test_network_connectivity()
        
        # 2. SSH Banner测试
        results['banner'] = self.test_ssh_banner()
        
        # 3. 基础SSH连接测试
        results['basic_ssh'] = self.test_ssh_connection_basic()
        
        # 4. 交互式Shell测试
        results['interactive_shell'] = self.test_ssh_interactive_shell()
        
        # 5. 不同参数连接测试
        results['different_params'] = self.test_connection_with_different_params()
        
        # 总结结果
        logger.info("=" * 60)
        logger.info("诊断结果总结:")
        for test_name, result in results.items():
            status = "✅ 通过" if result else "❌ 失败"
            logger.info(f"{test_name}: {status}")
        
        # 总体评估
        passed_tests = sum(results.values())
        total_tests = len(results)
        
        logger.info(f"总体结果: {passed_tests}/{total_tests} 项测试通过")
        
        if passed_tests == total_tests:
            logger.info("🎉 所有测试通过，SSH连接正常")
        elif results['network'] and results['banner']:
            logger.info("🔧 网络连接正常，但SSH连接有问题，需要检查认证或配置")
        else:
            logger.info("🚨 网络连接或SSH服务有问题")
        
        return results

if __name__ == "__main__":
    diagnosis = SSHConnectionDiagnosis()
    results = diagnosis.run_full_diagnosis()