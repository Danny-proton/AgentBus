"""
PageAnalysis Skill - 页面分析技能

使用LLM分析页面并生成探索任务
"""

import json
import logging
from typing import Dict, Any, List

from skills.base import BaseSkill
from skills.types import SkillType


logger = logging.getLogger(__name__)


# System Prompt for Page Analysis
SYSTEM_PROMPT = """你是一个网页探索军师,负责分析页面并规划探索策略。

## 你的角色
你需要像一个经验丰富的测试工程师一样思考:
1. **立即执行的导航任务** (frontier_tasks) - 用于建图
2. **延后执行的测试想法** (test_ideas) - 用于深度测试

## 输入
- 页面截图路径
- 精简DOM树(仅包含可交互元素)
- 当前URL

## 输出格式
```json
{
    "summary": "页面的业务含义,一句话",
    "frontier_tasks": [
        {
            "id": "task_001",
            "selector": "#login-btn",
            "action": "click",
            "reason": "进入登录页,探索认证流程",
            "priority": 8,
            "is_destructive": false,
            "parameters": {}
        }
    ],
    "test_ideas": [
        {
            "id": "idea_001",
            "name": "暴力破解测试",
            "description": "测试登录页是否有防暴力破解机制",
            "type": "security",
            "target_selector": "#login-form",
            "priority": 7
        }
    ]
}
```

## frontier_tasks 规则

**这些是立即要做的导航任务,用于探索网站结构:**

1. **优先级排序** (priority: 1-10):
   - 10分: 核心业务流程入口(登录、购物车、结算)
   - 8-9分: 详情页链接(产品详情、用户详情)
   - 6-7分: 列表页链接(产品列表、订单列表)
   - 4-5分: 导航链接(关于我们、帮助中心)
   - 1-3分: 次要链接(社交媒体、外部链接)

2. **动作类型**:
   - `click`: 点击链接或按钮
   - `type`: 填写表单字段
   - `submit`: 提交表单
   - `navigate`: 直接导航到URL

3. **破坏性标记**:
   - `is_destructive: true`: 删除、修改、支付等操作
   - `is_destructive: false`: 查看、搜索、导航等操作
   - **原则**: 先探索非破坏性操作,破坏性操作优先级降低

4. **表单处理**:
   - 先生成填写任务(type),后生成提交任务(submit)
   - 填写任务的priority应该高于提交任务

## test_ideas 规则

**这些是测试想法,不立即执行,保存到文件供Phase 2使用:**

1. **测试类型**:
   - `boundary`: 边界值测试(长度限制、数值范围)
   - `injection`: 注入攻击测试(SQL、XSS、命令注入)
   - `security`: 安全测试(暴力破解、权限绕过)
   - `permission`: 权限测试(未授权访问、越权操作)
   - `performance`: 性能测试(并发、大数据)

2. **何时生成test_ideas**:
   - 发现登录表单 → 生成"暴力破解测试"
   - 发现搜索框 → 生成"SQL注入测试"、"XSS测试"
   - 发现文件上传 → 生成"恶意文件上传测试"
   - 发现删除按钮 → 生成"未授权删除测试"
   - 发现支付流程 → 生成"金额篡改测试"

3. **优先级**:
   - 高优先级(8-10): 安全漏洞、权限问题
   - 中优先级(5-7): 边界值、性能问题
   - 低优先级(1-4): UI问题、兼容性问题

## 示例

### 示例1: 首页
```json
{
    "summary": "电商网站首页,包含导航和产品推荐",
    "frontier_tasks": [
        {
            "id": "task_001",
            "selector": "#login-link",
            "action": "click",
            "reason": "进入登录页,探索认证流程",
            "priority": 9,
            "is_destructive": false
        },
        {
            "id": "task_002",
            "selector": "#products-link",
            "action": "click",
            "reason": "进入产品列表,可能有详情页链接",
            "priority": 8,
            "is_destructive": false
        },
        {
            "id": "task_003",
            "selector": "#about-link",
            "action": "click",
            "reason": "查看关于页面",
            "priority": 4,
            "is_destructive": false
        }
    ],
    "test_ideas": []
}
```

### 示例2: 登录页
```json
{
    "summary": "用户登录页面,包含用户名和密码输入框",
    "frontier_tasks": [
        {
            "id": "task_001",
            "selector": "#username",
            "action": "type",
            "reason": "填写用户名",
            "priority": 8,
            "is_destructive": false,
            "parameters": {"value": "testuser"}
        },
        {
            "id": "task_002",
            "selector": "#password",
            "action": "type",
            "reason": "填写密码",
            "priority": 8,
            "is_destructive": false,
            "parameters": {"value": "testpass"}
        },
        {
            "id": "task_003",
            "selector": "#login-btn",
            "action": "click",
            "reason": "提交登录表单",
            "priority": 7,
            "is_destructive": false
        }
    ],
    "test_ideas": [
        {
            "id": "idea_001",
            "name": "暴力破解防护测试",
            "description": "测试连续失败登录是否有锁定机制",
            "type": "security",
            "target_selector": "#login-form",
            "priority": 9
        },
        {
            "id": "idea_002",
            "name": "SQL注入测试",
            "description": "在用户名和密码字段测试SQL注入",
            "type": "injection",
            "target_selector": "#username",
            "priority": 8
        },
        {
            "id": "idea_003",
            "name": "密码长度边界测试",
            "description": "测试超长密码和空密码的处理",
            "type": "boundary",
            "target_selector": "#password",
            "priority": 6
        }
    ]
}
```

## 重要提醒

1. **frontier_tasks是立即执行的** - 这些任务会被马上执行,用于探索网站
2. **test_ideas是延后执行的** - 这些想法会被保存到文件,Phase 2时再执行
3. **每个任务必须有唯一的id** - 格式: task_001, task_002...
4. **每个想法必须有唯一的id** - 格式: idea_001, idea_002...
5. **selector必须是有效的CSS选择器** - 可以是id、class、属性选择器等
6. **优先推荐能深入的链接** - 详情页 > 列表页 > 导航页
"""


class PageAnalysisSkill(BaseSkill):
    """页面分析技能"""
    
    NAME = "page_analysis"
    TYPE = SkillType.CUSTOM
    DESCRIPTION = "分析页面并生成探索任务"
    VERSION = "1.0.0"
    
    def __init__(self):
        super().__init__()
        self.system_prompt = SYSTEM_PROMPT
    
    async def execute(
        self,
        action: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行页面分析
        
        Args:
            action: 动作类型(这里固定为"analyze")
            parameters: {
                "screenshot_path": str,
                "dom_tree": dict,
                "url": str
            }
        
        Returns:
            {
                "summary": str,
                "frontier_tasks": List[Dict],
                "test_ideas": List[Dict]
            }
        """
        try:
            screenshot_path = parameters.get("screenshot_path", "")
            dom_tree = parameters.get("dom_tree", {})
            url = parameters.get("url", "")
            
            # 构建用户提示
            user_prompt = self._build_user_prompt(url, dom_tree, screenshot_path)
            
            # 调用LLM
            # TODO: 实际调用LLM服务
            # 这里先返回模拟数据
            result = await self._call_llm(user_prompt)
            
            # 验证输出格式
            validated_result = self._validate_output(result)
            
            return validated_result
            
        except Exception as e:
            logger.error(f"PageAnalysis执行失败: {e}", exc_info=True)
            return {
                "summary": "页面分析失败",
                "frontier_tasks": [],
                "test_ideas": []
            }
    
    def _build_user_prompt(
        self,
        url: str,
        dom_tree: Dict[str, Any],
        screenshot_path: str
    ) -> str:
        """构建用户提示"""
        # 简化DOM树,只保留可交互元素
        interactive_elements = self._extract_interactive_elements(dom_tree)
        
        prompt = f"""请分析以下页面:

URL: {url}

可交互元素:
{json.dumps(interactive_elements, indent=2, ensure_ascii=False)}

截图路径: {screenshot_path}

请按照要求的JSON格式输出分析结果。
"""
        return prompt
    
    def _extract_interactive_elements(self, dom_tree: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取可交互元素"""
        # TODO: 实现DOM树解析,提取链接、按钮、输入框等
        # 这里返回示例数据
        return [
            {"tag": "a", "id": "login-link", "text": "登录", "href": "/login"},
            {"tag": "a", "id": "products-link", "text": "产品", "href": "/products"},
            {"tag": "button", "id": "search-btn", "text": "搜索"}
        ]
    
    async def _call_llm(self, user_prompt: str) -> Dict[str, Any]:
        """
        调用LLM
        
        TODO: 实际调用LLM服务
        这里先返回模拟数据
        """
        # 模拟LLM响应
        mock_response = {
            "summary": "网站首页,包含导航链接和搜索功能",
            "frontier_tasks": [
                {
                    "selector": "#products-link",
                    "action": "click",
                    "reason": "进入产品列表页,可能包含详情页链接",
                    "priority": 8,
                    "is_destructive": False
                },
                {
                    "selector": "#login-link",
                    "action": "click",
                    "reason": "进入登录页,测试认证流程",
                    "priority": 7,
                    "is_destructive": False
                },
                {
                    "selector": "#search-btn",
                    "action": "click",
                    "reason": "测试搜索功能",
                    "priority": 5,
                    "is_destructive": False
                }
            ],
            "test_ideas": [
                {
                    "name": "搜索框边界测试",
                    "description": "测试搜索框的输入长度限制和特殊字符处理",
                    "type": "boundary"
                },
                {
                    "name": "SQL注入测试",
                    "description": "在搜索框中测试SQL注入攻击",
                    "type": "injection"
                }
            ]
        }
        
        return mock_response
    
    def _validate_output(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """验证输出格式"""
        # 确保必需字段存在
        validated = {
            "summary": result.get("summary", ""),
            "frontier_tasks": result.get("frontier_tasks", []),
            "test_ideas": result.get("test_ideas", [])
        }
        
        # 验证frontier_tasks格式
        valid_tasks = []
        for task in validated["frontier_tasks"]:
            if all(k in task for k in ["selector", "action", "priority"]):
                valid_tasks.append(task)
            else:
                logger.warning(f"无效的任务格式: {task}")
        
        validated["frontier_tasks"] = valid_tasks
        
        return validated
