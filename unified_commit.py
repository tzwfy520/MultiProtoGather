#!/usr/bin/env python3
"""
统一提交脚本 - 支持主项目和子项目的Git提交管理

使用方式:
python unified_commit.py -m "commit message" mode

支持的模式:
- all: 主项目和所有子项目均提交
- gather: 只提交主项目
- sshcollector: 只提交SSHCollector项目
- sshcollectorpro: 只提交SSHCollectorPro项目
- snmp: 只提交SNMP项目（暂未实现）
- api: 只提交API项目（暂未实现）
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Optional


class UnifiedCommit:
    def __init__(self):
        self.root_dir = Path(__file__).parent.absolute()
        self.project_configs = {
            'gather': {
                'path': self.root_dir,
                'name': '主项目 (MultiProtGather)',
                'description': '多协议采集控制器主项目'
            },
            'sshcollector': {
                'path': self.root_dir / 'collector-projects' / 'SSHCollector',
                'name': 'SSH采集器 (Python版)',
                'description': '基于Python开发的SSH采集器'
            },
            'sshcollectorpro': {
                'path': self.root_dir / 'collector-projects' / 'SSHCollectorPro',
                'name': 'SSH采集器Pro (Go版)',
                'description': '基于Go开发的SSH采集器'
            },
            'snmp': {
                'path': self.root_dir / 'collector-projects' / 'SNMPCollector',
                'name': 'SNMP采集器',
                'description': 'SNMP协议采集器（规划中）'
            },
            'api': {
                'path': self.root_dir / 'collector-projects' / 'APICollector',
                'name': 'API采集器',
                'description': 'API接口采集器（规划中）'
            }
        }
    
    def run_git_command(self, command: List[str], cwd: Path) -> tuple[bool, str]:
        """执行Git命令"""
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True
            )
            return True, result.stdout.strip()
        except subprocess.CalledProcessError as e:
            return False, e.stderr.strip()
        except Exception as e:
            return False, str(e)
    
    def check_git_status(self, project_path: Path) -> tuple[bool, str]:
        """检查Git状态"""
        if not (project_path / '.git').exists():
            return False, "不是Git仓库"
        
        success, output = self.run_git_command(['git', 'status', '--porcelain'], project_path)
        if not success:
            return False, f"检查状态失败: {output}"
        
        if not output.strip():
            return False, "没有需要提交的更改"
        
        return True, "有更改需要提交"
    
    def add_and_commit(self, project_path: Path, commit_message: str) -> tuple[bool, str]:
        """添加并提交更改"""
        # 添加所有更改
        success, output = self.run_git_command(['git', 'add', '.'], project_path)
        if not success:
            return False, f"添加文件失败: {output}"
        
        # 提交更改
        success, output = self.run_git_command(['git', 'commit', '-m', commit_message], project_path)
        if not success:
            return False, f"提交失败: {output}"
        
        return True, "提交成功"
    
    def push_changes(self, project_path: Path) -> tuple[bool, str]:
        """推送更改到远程仓库"""
        # 获取当前分支
        success, branch = self.run_git_command(['git', 'branch', '--show-current'], project_path)
        if not success:
            return False, f"获取分支失败: {branch}"
        
        # 推送到远程
        success, output = self.run_git_command(['git', 'push', 'origin', branch], project_path)
        if not success:
            return False, f"推送失败: {output}"
        
        return True, "推送成功"
    
    def commit_project(self, project_key: str, commit_message: str, push: bool = False) -> Dict:
        """提交单个项目"""
        if project_key not in self.project_configs:
            return {
                'success': False,
                'project': project_key,
                'message': f"未知项目: {project_key}"
            }
        
        config = self.project_configs[project_key]
        project_path = config['path']
        project_name = config['name']
        
        print(f"\n{'='*60}")
        print(f"处理项目: {project_name}")
        print(f"路径: {project_path}")
        print(f"{'='*60}")
        
        # 检查项目路径是否存在
        if not project_path.exists():
            message = f"项目路径不存在: {project_path}"
            print(f"❌ {message}")
            return {
                'success': False,
                'project': project_key,
                'message': message
            }
        
        # 检查Git状态
        print("🔍 检查Git状态...")
        has_changes, status_msg = self.check_git_status(project_path)
        if not has_changes:
            print(f"ℹ️  {status_msg}")
            return {
                'success': True,
                'project': project_key,
                'message': status_msg,
                'skipped': True
            }
        
        print(f"✅ {status_msg}")
        
        # 添加并提交
        print("📝 添加并提交更改...")
        success, commit_result = self.add_and_commit(project_path, commit_message)
        if not success:
            print(f"❌ {commit_result}")
            return {
                'success': False,
                'project': project_key,
                'message': commit_result
            }
        
        print(f"✅ {commit_result}")
        
        result = {
            'success': True,
            'project': project_key,
            'message': commit_result
        }
        
        # 推送更改（如果需要）
        if push:
            print("🚀 推送到远程仓库...")
            success, push_result = self.push_changes(project_path)
            if not success:
                print(f"⚠️  {push_result}")
                result['push_warning'] = push_result
            else:
                print(f"✅ {push_result}")
                result['pushed'] = True
        
        return result
    
    def commit_multiple_projects(self, project_keys: List[str], commit_message: str, push: bool = False) -> List[Dict]:
        """提交多个项目"""
        results = []
        
        print(f"\n🚀 开始批量提交操作")
        print(f"提交信息: {commit_message}")
        print(f"项目数量: {len(project_keys)}")
        print(f"推送到远程: {'是' if push else '否'}")
        
        for project_key in project_keys:
            result = self.commit_project(project_key, commit_message, push)
            results.append(result)
        
        return results
    
    def print_summary(self, results: List[Dict]):
        """打印操作摘要"""
        print(f"\n{'='*60}")
        print("📊 操作摘要")
        print(f"{'='*60}")
        
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        skipped = [r for r in results if r.get('skipped', False)]
        pushed = [r for r in results if r.get('pushed', False)]
        
        print(f"✅ 成功: {len(successful)}")
        print(f"❌ 失败: {len(failed)}")
        print(f"⏭️  跳过: {len(skipped)}")
        print(f"🚀 已推送: {len(pushed)}")
        
        if failed:
            print(f"\n❌ 失败的项目:")
            for result in failed:
                config = self.project_configs.get(result['project'], {})
                project_name = config.get('name', result['project'])
                print(f"  - {project_name}: {result['message']}")
        
        if skipped:
            print(f"\n⏭️  跳过的项目:")
            for result in skipped:
                config = self.project_configs.get(result['project'], {})
                project_name = config.get('name', result['project'])
                print(f"  - {project_name}: {result['message']}")
        
        warnings = [r for r in results if 'push_warning' in r]
        if warnings:
            print(f"\n⚠️  推送警告:")
            for result in warnings:
                config = self.project_configs.get(result['project'], {})
                project_name = config.get('name', result['project'])
                print(f"  - {project_name}: {result['push_warning']}")
    
    def get_available_projects(self) -> List[str]:
        """获取可用的项目列表"""
        available = []
        for key, config in self.project_configs.items():
            if config['path'].exists():
                available.append(key)
        return available
    
    def print_help(self):
        """打印帮助信息"""
        print("📚 统一提交脚本使用说明")
        print("="*60)
        print("使用方式:")
        print("  python unified_commit.py -m \"提交信息\" [模式] [选项]")
        print()
        print("支持的模式:")
        
        available_projects = self.get_available_projects()
        
        for key, config in self.project_configs.items():
            status = "✅" if key in available_projects else "❌"
            print(f"  {status} {key:<15} - {config['name']}")
            print(f"     {'':15}   {config['description']}")
        
        print(f"  ✅ {'all':<15} - 所有可用项目")
        print(f"     {'':15}   提交所有存在的项目")
        print()
        print("选项:")
        print("  -m, --message    提交信息（必需）")
        print("  -p, --push       提交后推送到远程仓库")
        print("  -h, --help       显示帮助信息")
        print()
        print("示例:")
        print("  python unified_commit.py -m \"修复SSH连接问题\" gather")
        print("  python unified_commit.py -m \"添加新功能\" all -p")
        print("  python unified_commit.py -m \"更新文档\" sshcollector sshcollectorpro")


def main():
    parser = argparse.ArgumentParser(
        description="统一提交脚本 - 支持主项目和子项目的Git提交管理",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '-m', '--message',
        required=True,
        help='提交信息'
    )
    
    parser.add_argument(
        'modes',
        nargs='+',
        help='提交模式: all, gather, sshcollector, sshcollectorpro, snmp, api'
    )
    
    parser.add_argument(
        '-p', '--push',
        action='store_true',
        help='提交后推送到远程仓库'
    )
    
    args = parser.parse_args()
    
    commit_tool = UnifiedCommit()
    
    # 处理模式
    project_keys = []
    for mode in args.modes:
        if mode == 'all':
            project_keys.extend(commit_tool.get_available_projects())
        elif mode in commit_tool.project_configs:
            project_keys.append(mode)
        else:
            print(f"❌ 未知模式: {mode}")
            commit_tool.print_help()
            sys.exit(1)
    
    # 去重并保持顺序
    project_keys = list(dict.fromkeys(project_keys))
    
    if not project_keys:
        print("❌ 没有找到可用的项目")
        commit_tool.print_help()
        sys.exit(1)
    
    # 执行提交操作
    results = commit_tool.commit_multiple_projects(
        project_keys,
        args.message,
        args.push
    )
    
    # 打印摘要
    commit_tool.print_summary(results)
    
    # 检查是否有失败的操作
    failed_count = len([r for r in results if not r['success']])
    if failed_count > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()