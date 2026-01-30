"""
GitHub Skill for AgentBus

Migrated from Moltbot GitHub skill definition.
Provides GitHub CLI integration for repository management, issues, PRs, and CI.

Features:
- Pull request management (status, checks, reviews)
- Issue management (create, list, update)
- Repository operations (info, branches, tags)
- CI/CD workflow management
- GitHub API access for advanced queries
- JSON output formatting with jq support

Usage:
    # Check PR status
    skill.run_command("pr checks 55 --repo owner/repo")
    
    # List workflow runs
    skill.run_command("run list --repo owner/repo --limit 10")
    
    # API queries
    skill.run_command('api repos/owner/repo/pulls/55 --jq ".title, .state"')
"""

import subprocess
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..plugins.core import AgentBusPlugin, PluginContext


class GitHubSkill(AgentBusPlugin):
    """
    GitHub Skill - Provides GitHub CLI integration
    
    Implements Moltbot's GitHub skill functionality with gh CLI commands
    for repository management, issues, pull requests, and CI/CD workflows.
    """
    
    def __init__(self, plugin_id: str, context: PluginContext):
        super().__init__(plugin_id, context)
        self.command_history = []
        self._session_cache = {}
        
    def get_info(self) -> Dict[str, Any]:
        """Return plugin information"""
        return {
            'id': self.plugin_id,
            'name': 'GitHub Skill',
            'version': '1.0.0',
            'description': 'GitHub CLI integration for repository management, issues, PRs, and CI workflows',
            'author': 'AgentBus Team',
            'dependencies': ['gh'],
            'capabilities': [
                'pr_management',
                'issue_management', 
                'repo_operations',
                'ci_management',
                'api_queries'
            ]
        }
    
    async def activate(self):
        """Activate plugin and register tools"""
        await super().activate()
        
        # Register GitHub tools
        self.register_tool('check_pr_status', 'Check PR CI status', self.check_pr_status)
        self.register_tool('list_workflows', 'List workflow runs', self.list_workflows)
        self.register_tool('view_run', 'View workflow run details', self.view_run)
        self.register_tool('view_logs', 'View failed workflow logs', self.view_logs)
        self.register_tool('api_query', 'Execute GitHub API query', self.api_query)
        self.register_tool('list_issues', 'List repository issues', self.list_issues)
        self.register_tool('create_issue', 'Create new issue', self.create_issue)
        self.register_tool('get_pr_info', 'Get PR information', self.get_pr_info)
        self.register_tool('list_releases', 'List repository releases', self.list_releases)
        self.register_tool('create_release', 'Create new release', self.create_release)
        
        # Register commands
        self.register_command('/github_status', self.handle_status_command, 'Show GitHub CLI status')
        self.register_command('/github_repos', self.handle_repos_command, 'List accessible repositories')
        self.register_command('/github_prs', self.handle_prs_command, 'List pull requests')
        
        self.context.logger.info(f"GitHub skill {self.plugin_id} activated")
    
    def _run_gh_command(self, command: str, repo: str = None) -> Dict[str, Any]:
        """Execute gh CLI command"""
        try:
            # Build command
            if repo:
                cmd = f"gh {command} --repo {repo}"
            else:
                cmd = f"gh {command}"
            
            self.context.logger.debug(f"Executing: {cmd}")
            
            # Execute command
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True, 
                text=True,
                timeout=30
            )
            
            # Log command
            self.command_history.append({
                'command': cmd,
                'timestamp': datetime.now(),
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr
            })
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'output': result.stdout,
                    'command': cmd
                }
            else:
                return {
                    'success': False,
                    'error': result.stderr,
                    'command': cmd
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Command timed out',
                'command': cmd
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'command': cmd
            }
    
    def _parse_json_output(self, json_str: str) -> Any:
        """Parse JSON output safely"""
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return json_str
    
    async def check_pr_status(self, pr_number: str, repo: str) -> Dict[str, Any]:
        """Check CI status on a pull request"""
        try:
            result = self._run_gh_command(f"pr checks {pr_number}", repo)
            
            if result['success']:
                return {
                    'success': True,
                    'pr_number': pr_number,
                    'repo': repo,
                    'checks': result['output']
                }
            else:
                return {
                    'success': False,
                    'error': result['error']
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def list_workflows(self, repo: str, limit: int = 10) -> Dict[str, Any]:
        """List recent workflow runs"""
        try:
            result = self._run_gh_command(f"run list --limit {limit}", repo)
            
            if result['success']:
                return {
                    'success': True,
                    'repo': repo,
                    'runs': result['output'],
                    'limit': limit
                }
            else:
                return {
                    'success': False,
                    'error': result['error']
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def view_run(self, run_id: str, repo: str) -> Dict[str, Any]:
        """View workflow run details"""
        try:
            result = self._run_gh_command(f"run view {run_id}", repo)
            
            if result['success']:
                return {
                    'success': True,
                    'run_id': run_id,
                    'repo': repo,
                    'details': result['output']
                }
            else:
                return {
                    'success': False,
                    'error': result['error']
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def view_logs(self, run_id: str, repo: str, failed_only: bool = True) -> Dict[str, Any]:
        """View logs for failed steps"""
        try:
            cmd = f"run view {run_id}"
            if failed_only:
                cmd += " --log-failed"
            
            result = self._run_gh_command(cmd, repo)
            
            if result['success']:
                return {
                    'success': True,
                    'run_id': run_id,
                    'repo': repo,
                    'logs': result['output'],
                    'failed_only': failed_only
                }
            else:
                return {
                    'success': False,
                    'error': result['error']
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def api_query(self, endpoint: str, repo: str = None, jq_filter: str = None) -> Dict[str, Any]:
        """Execute GitHub API query"""
        try:
            cmd = f"api {endpoint}"
            if jq_filter:
                cmd += f" --jq '{jq_filter}'"
            
            result = self._run_gh_command(cmd, repo)
            
            if result['success']:
                parsed_output = self._parse_json_output(result['output'])
                return {
                    'success': True,
                    'endpoint': endpoint,
                    'repo': repo,
                    'jq_filter': jq_filter,
                    'data': parsed_output
                }
            else:
                return {
                    'success': False,
                    'error': result['error']
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def list_issues(self, repo: str, state: str = 'open', limit: int = 10) -> Dict[str, Any]:
        """List repository issues"""
        try:
            cmd = f"issue list --state {state} --limit {limit} --json number,title,state,author"
            result = self._run_gh_command(cmd, repo)
            
            if result['success']:
                issues = self._parse_json_output(result['output'])
                return {
                    'success': True,
                    'repo': repo,
                    'issues': issues,
                    'state': state,
                    'count': len(issues) if isinstance(issues, list) else 1
                }
            else:
                return {
                    'success': False,
                    'error': result['error']
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def create_issue(self, repo: str, title: str, body: str = None, labels: List[str] = None) -> Dict[str, Any]:
        """Create new issue"""
        try:
            cmd = f"issue create --title '{title}'"
            
            if body:
                cmd += f" --body '{body}'"
            
            if labels:
                cmd += f" --label {','.join(labels)}"
            
            result = self._run_gh_command(cmd, repo)
            
            if result['success']:
                return {
                    'success': True,
                    'repo': repo,
                    'title': title,
                    'issue_url': result['output'].strip()
                }
            else:
                return {
                    'success': False,
                    'error': result['error']
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def get_pr_info(self, pr_number: str, repo: str, fields: str = 'number,title,state,author') -> Dict[str, Any]:
        """Get PR information with specified fields"""
        try:
            cmd = f"pr view {pr_number} --json {fields}"
            result = self._run_gh_command(cmd, repo)
            
            if result['success']:
                pr_info = self._parse_json_output(result['output'])
                return {
                    'success': True,
                    'pr_number': pr_number,
                    'repo': repo,
                    'pr_info': pr_info
                }
            else:
                return {
                    'success': False,
                    'error': result['error']
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def list_releases(self, repo: str, limit: int = 10) -> Dict[str, Any]:
        """List repository releases"""
        try:
            cmd = f"release list --limit {limit} --json tag_name,name,published_at"
            result = self._run_gh_command(cmd, repo)
            
            if result['success']:
                releases = self._parse_json_output(result['output'])
                return {
                    'success': True,
                    'repo': repo,
                    'releases': releases,
                    'count': len(releases) if isinstance(releases, list) else 1
                }
            else:
                return {
                    'success': False,
                    'error': result['error']
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def create_release(self, repo: str, tag: str, name: str = None, body: str = None, draft: bool = False) -> Dict[str, Any]:
        """Create new release"""
        try:
            cmd = f"release create {tag}"
            
            if name:
                cmd += f" --title '{name}'"
            
            if body:
                cmd += f" --notes '{body}'"
            
            if draft:
                cmd += " --draft"
            
            result = self._run_gh_command(cmd, repo)
            
            if result['success']:
                return {
                    'success': True,
                    'repo': repo,
                    'tag': tag,
                    'release_url': result['output'].strip()
                }
            else:
                return {
                    'success': False,
                    'error': result['error']
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def run_command(self, command: str, repo: str = None) -> Dict[str, Any]:
        """Execute arbitrary GitHub CLI command"""
        try:
            result = self._run_gh_command(command, repo)
            
            return {
                'success': result['success'],
                'command': command,
                'repo': repo,
                'output': result.get('output'),
                'error': result.get('error')
            }
            
        except Exception as e:
            return {
                'success': False,
                'command': command,
                'error': str(e)
            }
    
    async def handle_status_command(self, args: str) -> str:
        """Handle GitHub status command"""
        try:
            # Check gh CLI availability
            gh_check = subprocess.run(['gh', '--version'], capture_output=True, text=True)
            gh_available = gh_check.returncode == 0
            
            # Get recent commands
            recent_commands = self.command_history[-5:] if self.command_history else []
            
            status_info = {
                'skill_id': self.plugin_id,
                'gh_available': gh_available,
                'command_count': len(self.command_history),
                'recent_commands': recent_commands
            }
            
            return f"GitHub Skill Status:\n{json.dumps(status_info, indent=2, ensure_ascii=False)}"
            
        except Exception as e:
            return f"获取GitHub状态失败: {str(e)}"
    
    async def handle_repos_command(self, args: str) -> str:
        """Handle repositories list command"""
        try:
            result = self._run_gh_command("repo list --json name,owner,url --limit 10")
            
            if result['success']:
                repos = self._parse_json_output(result['output'])
                repo_list = []
                for repo in repos:
                    repo_list.append(f"- {repo['owner']['login']}/{repo['name']}")
                
                return f"可访问的仓库:\n" + "\n".join(repo_list)
            else:
                return f"获取仓库列表失败: {result['error']}"
                
        except Exception as e:
            return f"获取仓库列表失败: {str(e)}"
    
    async def handle_prs_command(self, args: str) -> str:
        """Handle pull requests list command"""
        try:
            result = self._run_gh_command("pr list --json number,title,state,author --limit 5")
            
            if result['success']:
                prs = self._parse_json_output(result['output'])
                pr_list = []
                for pr in prs:
                    pr_list.append(f"#{pr['number']}: {pr['title']} ({pr['state']})")
                
                return f"最近的PR:\n" + "\n".join(pr_list)
            else:
                return f"获取PR列表失败: {result['error']}"
                
        except Exception as e:
            return f"获取PR列表失败: {str(e)}"
    
    async def deactivate(self):
        """Cleanup when deactivating"""
        try:
            self.command_history.clear()
            self._session_cache.clear()
            await super().deactivate()
        except Exception as e:
            self.context.logger.error(f"Error during GitHub skill cleanup: {e}")