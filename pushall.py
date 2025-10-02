#!/usr/bin/env python3
"""
统一推送脚本 - 自动检测并推送有新提交的项目到GitHub

使用方式:
python pushall.py

功能:
- 自动检测主项目和所有子项目中有新提交的项目
- 将这些项目的更改推送到GitHub远程仓库
- 提供详细的操作日志和摘要报告
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple


class PushAll:
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
    
    def run_git_command(self, command: List[str], cwd: Path) -> Tuple[bool, str]:
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
    
    def is_git_repository(self, project_path: Path) -> bool:
        """检查是否为Git仓库"""
        return (project_path / '.git').exists()
    
    def has_remote_origin(self, project_path: Path) -> Tuple[bool, str]:
        """检查是否配置了远程origin"""
        success, output = self.run_git_command(['git', 'remote', 'get-url', 'origin'], project_path)
        if success:
            return True, output
        return False, "未配置远程origin"
    
    def get_current_branch(self, project_path: Path) -> Tuple[bool, str]:
        """获取当前分支名"""
        success, branch = self.run_git_command(['git', 'branch', '--show-current'], project_path)
        if success and branch:
            return True, branch
        return False, "无法获取当前分支"
    
    def has_unpushed_commits(self, project_path: Path) -> Tuple[bool, str, int]:
        """检查是否有未推送的提交"""
        # 首先获取当前分支
        success, branch = self.get_current_branch(project_path)
        if not success:
            return False, branch, 0
        
        # 获取远程分支信息
        success, _ = self.run_git_command(['git', 'fetch', 'origin'], project_path)
        if not success:
            return False, "无法获取远程分支信息", 0
        
        # 检查本地分支是否领先于远程分支
        success, output = self.run_git_command(
            ['git', 'rev-list', '--count', f'origin/{branch}..HEAD'], 
            project_path
        )
        
        if not success:
            # 可能是新分支，检查是否有提交
            success, output = self.run_git_command(['git', 'rev-list', '--count', 'HEAD'], project_path)
            if success and output and int(output) > 0:
                return True, f"新分支 '{branch}' 有 {output} 个提交需要推送", int(output)
            return False, "无法检查提交状态", 0
        
        commit_count = int(output) if output else 0
        if commit_count > 0:
            return True, f"有 {commit_count} 个未推送的提交", commit_count
        
        return False, "没有未推送的提交", 0
    
    def push_to_remote(self, project_path: Path) -> Tuple[bool, str]:
        """推送到远程仓库"""
        # 获取当前分支
        success, branch = self.get_current_branch(project_path)
        if not success:
            return False, f"获取分支失败: {branch}"
        
        # 推送到远程
        success, output = self.run_git_command(['git', 'push', 'origin', branch], project_path)
        if not success:
            # 如果是新分支，尝试设置上游分支
            if "has no upstream branch" in output or "set-upstream" in output:
                success, output = self.run_git_command(
                    ['git', 'push', '--set-upstream', 'origin', branch], 
                    project_path
                )
                if success:
                    return True, f"成功推送新分支 '{branch}' 并设置上游"
        
        if success:
            return True, f"成功推送到 origin/{branch}"
        else:
            return False, f"推送失败: {output}"
    
    def check_and_push_project(self, project_key: str) -> Dict:
        """检查并推送单个项目"""
        if project_key not in self.project_configs:
            return {
                'success': False,
                'project': project_key,
                'message': f"未知项目: {project_key}",
                'skipped': True
            }
        
        config = self.project_configs[project_key]
        project_path = config['path']
        project_name = config['name']
        
        print(f"\n{'='*60}")
        print(f"检查项目: {project_name}")
        print(f"路径: {project_path}")
        print(f"{'='*60}")
        
        # 检查项目路径是否存在
        if not project_path.exists():
            message = f"项目路径不存在: {project_path}"
            print(f"❌ {message}")
            return {
                'success': False,
                'project': project_key,
                'message': message,
                'skipped': True
            }
        
        # 检查是否为Git仓库
        if not self.is_git_repository(project_path):
            message = "不是Git仓库"
            print(f"⏭️  {message}")
            return {
                'success': True,
                'project': project_key,
                'message': message,
                'skipped': True
            }
        
        # 检查是否配置了远程origin
        print("🔍 检查远程仓库配置...")
        has_origin, origin_info = self.has_remote_origin(project_path)
        if not has_origin:
            print(f"⏭️  {origin_info}")
            return {
                'success': True,
                'project': project_key,
                'message': origin_info,
                'skipped': True
            }
        
        print(f"✅ 远程仓库: {origin_info}")
        
        # 检查是否有未推送的提交
        print("🔍 检查未推送的提交...")
        has_commits, commit_info, commit_count = self.has_unpushed_commits(project_path)
        if not has_commits:
            print(f"ℹ️  {commit_info}")
            return {
                'success': True,
                'project': project_key,
                'message': commit_info,
                'skipped': True
            }
        
        print(f"📝 {commit_info}")
        
        # 推送到远程仓库
        print("🚀 推送到远程仓库...")
        success, push_result = self.push_to_remote(project_path)
        if not success:
            print(f"❌ {push_result}")
            return {
                'success': False,
                'project': project_key,
                'message': push_result
            }
        
        print(f"✅ {push_result}")
        return {
            'success': True,
            'project': project_key,
            'message': push_result,
            'pushed': True,
            'commit_count': commit_count
        }
    
    def get_available_projects(self) -> List[str]:
        """获取可用的项目列表"""
        available = []
        for key, config in self.project_configs.items():
            if config['path'].exists():
                available.append(key)
        return available
    
    def push_all_projects(self) -> List[Dict]:
        """检查并推送所有项目"""
        available_projects = self.get_available_projects()
        
        print(f"🚀 开始检查所有项目的推送状态")
        print(f"可用项目数量: {len(available_projects)}")
        
        results = []
        for project_key in available_projects:
            result = self.check_and_push_project(project_key)
            results.append(result)
        
        return results
    
    def print_summary(self, results: List[Dict]):
        """打印操作摘要"""
        print(f"\n{'='*60}")
        print("📊 推送操作摘要")
        print(f"{'='*60}")
        
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        skipped = [r for r in results if r.get('skipped', False)]
        pushed = [r for r in results if r.get('pushed', False)]
        
        total_commits = sum(r.get('commit_count', 0) for r in pushed)
        
        print(f"✅ 检查成功: {len(successful)}")
        print(f"❌ 操作失败: {len(failed)}")
        print(f"⏭️  跳过项目: {len(skipped)}")
        print(f"🚀 成功推送: {len(pushed)}")
        print(f"📝 推送提交数: {total_commits}")
        
        if pushed:
            print(f"\n🚀 成功推送的项目:")
            for result in pushed:
                config = self.project_configs.get(result['project'], {})
                project_name = config.get('name', result['project'])
                commit_count = result.get('commit_count', 0)
                print(f"  - {project_name}: {commit_count} 个提交")
        
        if failed:
            print(f"\n❌ 推送失败的项目:")
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
    
    def print_help(self):
        """打印帮助信息"""
        print("📚 统一推送脚本使用说明")
        print("="*60)
        print("使用方式:")
        print("  python pushall.py")
        print()
        print("功能:")
        print("  - 自动检测所有项目中有新提交的项目")
        print("  - 将这些项目的更改推送到GitHub远程仓库")
        print("  - 提供详细的操作日志和摘要报告")
        print()
        print("检查的项目:")
        
        available_projects = self.get_available_projects()
        
        for key, config in self.project_configs.items():
            status = "✅" if key in available_projects else "❌"
            print(f"  {status} {config['name']}")
            print(f"     路径: {config['path']}")
            print(f"     描述: {config['description']}")
            print()
        
        print("注意事项:")
        print("  - 只会推送已配置远程origin的Git仓库")
        print("  - 跳过没有未推送提交的项目")
        print("  - 自动处理新分支的上游设置")


def main():
    # 检查是否请求帮助
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
        push_tool = PushAll()
        push_tool.print_help()
        return
    
    push_tool = PushAll()
    
    # 执行推送操作
    results = push_tool.push_all_projects()
    
    # 打印摘要
    push_tool.print_summary(results)
    
    # 检查是否有失败的操作
    failed_count = len([r for r in results if not r['success']])
    if failed_count > 0:
        print(f"\n⚠️  有 {failed_count} 个项目推送失败")
        sys.exit(1)
    
    pushed_count = len([r for r in results if r.get('pushed', False)])
    if pushed_count == 0:
        print(f"\n✅ 所有项目都是最新状态，无需推送")
    else:
        print(f"\n✅ 成功推送 {pushed_count} 个项目")


if __name__ == '__main__':
    main()