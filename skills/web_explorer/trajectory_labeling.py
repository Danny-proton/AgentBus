"""
TrajectoryLabeling Skill - 轨迹标注技能

使用LLM判断动作是否有意义并生成语义标签
"""

import json
import logging
from typing import Dict, Any

from skills.base import BaseSkill
from skills.types import SkillType


logger = logging.getLogger(__name__)


# System Prompt for Trajectory Labeling
SYSTEM_PROMPT = """你是一个行为分析史官,负责判断操作是否产生了有意义的状态变化。

## 你的角色
你像一个严谨的历史记录员,需要判断:
1. 这个动作是否真的改变了系统状态?
2. 如果改变了,这个状态值得记录吗?
3. 应该如何描述这个状态转换?

## 输入
- `screenshot_before`: 操作前的截图路径
- `action_description`: 操作描述(如"点击登录按钮")
- `screenshot_after`: 操作后的截图路径
- `dom_before`: 操作前的DOM信息(URL、title等)
- `dom_after`: 操作后的DOM信息

## 输出格式
```json
{
    "is_meaningful": true,
    "semantic_label": "用户成功进入了登录页",
    "script_name": "nav_to_login.py",
    "confidence": 0.95
}
```

## 判断标准

### ✅ 有意义的状态变化 (is_meaningful: true)

1. **URL变化**:
   - 从 `/` 跳转到 `/login`
   - 从 `/products` 跳转到 `/products/123`
   - **即使页面内容相似,URL变化也算有意义**

2. **页面结构变化**:
   - 出现了新的表单
   - 出现了新的列表
   - 页面主体内容完全不同

3. **模态框/弹窗**:
   - 弹出了登录框
   - 弹出了确认对话框
   - 出现了侧边栏

4. **内容加载**:
   - 列表加载了新数据
   - 详情页显示了具体信息
   - 搜索结果出现

### ❌ 无意义的状态变化 (is_meaningful: false)

1. **页面无变化**:
   - 点击后什么都没发生
   - 只是按钮颜色变了一下
   - 页面完全一样

2. **临时状态**:
   - 只是Loading动画闪了一下
   - 只是Hover效果
   - 只是焦点变化

3. **错误提示**:
   - 弹出了"请先登录"的提示
   - 显示了"权限不足"
   - 页面结构没变,只是多了错误信息

4. **同页面刷新**:
   - URL没变
   - 内容没变
   - 只是重新加载了一次

## semantic_label 规则

**格式**: "验证: [主语] [动作] [结果]"

**示例**:
- ✅ "验证: 用户成功进入了登录页"
- ✅ "验证: 点击产品链接成功打开产品详情页"
- ✅ "验证: 提交登录表单后进入了用户仪表板"
- ❌ "点击了登录按钮" (太简单)
- ❌ "页面跳转了" (不够具体)

**要点**:
- 必须包含业务含义
- 必须说明结果
- 使用过去时态
- 简洁明了

## script_name 规则

**格式**: `nav_to_<目标页面>.py` 或 `action_<动作>.py`

**示例**:
- `nav_to_login.py` - 导航到登录页
- `nav_to_product_detail.py` - 导航到产品详情
- `nav_to_cart.py` - 导航到购物车
- `action_submit_login.py` - 提交登录表单
- `action_add_to_cart.py` - 添加到购物车

**要点**:
- 全小写
- 使用下划线分隔
- 必须以 `.py` 结尾
- 简洁但有意义
- 避免使用特殊字符

## confidence 规则

**置信度评分** (0.0 - 1.0):

- **0.9-1.0**: 非常确定
  - URL明显变化
  - 页面结构完全不同
  - 有明确的业务含义

- **0.7-0.9**: 比较确定
  - URL变化或页面内容变化
  - 能识别出业务含义
  - 可能有一些不确定因素

- **0.5-0.7**: 不太确定
  - 变化很微小
  - 难以判断是否有意义
  - 可能需要更多信息

- **0.0-0.5**: 很不确定
  - 几乎看不出变化
  - 可能是错误或异常
  - 建议标记为无意义

## 示例

### 示例1: 成功导航
```json
{
    "is_meaningful": true,
    "semantic_label": "验证: 点击登录链接成功进入登录页",
    "script_name": "nav_to_login.py",
    "confidence": 0.95
}
```
**理由**: URL从 `/` 变为 `/login`,页面出现了登录表单

### 示例2: 表单提交成功
```json
{
    "is_meaningful": true,
    "semantic_label": "验证: 提交登录表单后成功进入用户仪表板",
    "script_name": "action_submit_login.py",
    "confidence": 0.92
}
```
**理由**: URL从 `/login` 变为 `/dashboard`,页面显示用户信息

### 示例3: 点击无效
```json
{
    "is_meaningful": false,
    "semantic_label": "点击无效,页面未发生变化",
    "script_name": "unknown.py",
    "confidence": 0.85
}
```
**理由**: URL没变,页面内容也没变

### 示例4: 错误提示
```json
{
    "is_meaningful": false,
    "semantic_label": "登录失败,显示错误提示",
    "script_name": "unknown.py",
    "confidence": 0.80
}
```
**理由**: 虽然出现了错误提示,但页面结构没变,仍在登录页

## 重要提醒

1. **URL变化优先** - 即使页面看起来相似,URL变化也算有意义
2. **业务含义优先** - 描述要包含业务含义,不只是技术动作
3. **保守判断** - 不确定时,宁可标记为无意义
4. **置信度诚实** - 如实反映你的判断确定程度
"""


class TrajectoryLabelingSkill(BaseSkill):
    """轨迹标注技能"""
    
    NAME = "trajectory_labeling"
    TYPE = SkillType.CUSTOM
    DESCRIPTION = "判断动作意义并生成语义标签"
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
        执行轨迹标注
        
        Args:
            action: 动作类型(这里固定为"label")
            parameters: {
                "screenshot_before": str,
                "action_description": str,
                "screenshot_after": str,
                "dom_before": dict,
                "dom_after": dict
            }
        
        Returns:
            {
                "is_meaningful": bool,
                "semantic_label": str,
                "script_name": str,
                "confidence": float
            }
        """
        try:
            screenshot_before = parameters.get("screenshot_before", "")
            action_description = parameters.get("action_description", "")
            screenshot_after = parameters.get("screenshot_after", "")
            dom_before = parameters.get("dom_before", {})
            dom_after = parameters.get("dom_after", {})
            
            # 构建用户提示
            user_prompt = self._build_user_prompt(
                screenshot_before,
                action_description,
                screenshot_after,
                dom_before,
                dom_after
            )
            
            # 调用LLM
            # TODO: 实际调用LLM服务
            result = await self._call_llm(user_prompt, action_description)
            
            # 验证输出格式
            validated_result = self._validate_output(result)
            
            return validated_result
            
        except Exception as e:
            logger.error(f"TrajectoryLabeling执行失败: {e}", exc_info=True)
            return {
                "is_meaningful": False,
                "semantic_label": "标注失败",
                "script_name": "unknown.py",
                "confidence": 0.0
            }
    
    def _build_user_prompt(
        self,
        screenshot_before: str,
        action_description: str,
        screenshot_after: str,
        dom_before: Dict[str, Any],
        dom_after: Dict[str, Any]
    ) -> str:
        """构建用户提示"""
        # 计算DOM差异
        dom_diff = self._calculate_dom_diff(dom_before, dom_after)
        
        prompt = f"""请分析以下操作:

操作描述: {action_description}

操作前截图: {screenshot_before}
操作后截图: {screenshot_after}

DOM变化:
{json.dumps(dom_diff, indent=2, ensure_ascii=False)}

请判断这个操作是否有意义,并按照要求的JSON格式输出结果。
"""
        return prompt
    
    def _calculate_dom_diff(
        self,
        dom_before: Dict[str, Any],
        dom_after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """计算DOM差异"""
        # TODO: 实现DOM差异计算
        # 这里返回简化的差异信息
        url_changed = dom_before.get("url") != dom_after.get("url")
        title_changed = dom_before.get("title") != dom_after.get("title")
        
        return {
            "url_changed": url_changed,
            "title_changed": title_changed,
            "url_before": dom_before.get("url", ""),
            "url_after": dom_after.get("url", ""),
            "title_before": dom_before.get("title", ""),
            "title_after": dom_after.get("title", "")
        }
    
    async def _call_llm(
        self,
        user_prompt: str,
        action_description: str
    ) -> Dict[str, Any]:
        """
        调用LLM
        
        TODO: 实际调用LLM服务
        这里先返回模拟数据
        """
        # 简单的启发式判断(模拟LLM)
        if "点击" in action_description or "click" in action_description.lower():
            # 假设点击操作通常是有意义的
            mock_response = {
                "is_meaningful": True,
                "semantic_label": f"验证: {action_description}成功执行",
                "script_name": "click_action.py",
                "confidence": 0.85
            }
        else:
            mock_response = {
                "is_meaningful": True,
                "semantic_label": f"验证: {action_description}",
                "script_name": "action.py",
                "confidence": 0.75
            }
        
        return mock_response
    
    def _validate_output(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """验证输出格式"""
        validated = {
            "is_meaningful": result.get("is_meaningful", False),
            "semantic_label": result.get("semantic_label", ""),
            "script_name": result.get("script_name", "unknown.py"),
            "confidence": result.get("confidence", 0.5)
        }
        
        # 确保confidence在0-1之间
        validated["confidence"] = max(0.0, min(1.0, validated["confidence"]))
        
        # 确保script_name有.py后缀
        if not validated["script_name"].endswith(".py"):
            validated["script_name"] += ".py"
        
        return validated
