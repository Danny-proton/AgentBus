"""
沟通地图 (Communication Map) 服务
Communication Map service for AgentBus

本模块实现沟通地图系统，管理本地联系人信息，
并基于上下文智能匹配合适的联系人作为HITL的求助对象。
"""

import json
import yaml
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from pathlib import Path
from loguru import logger

from core.settings import settings


@dataclass
class Contact:
    """联系人数据结构"""
    id: str
    name: str
    role: str
    expertise: Set[str]
    availability: str  # "always", "work_hours", "on_call", "weekends"
    contact_methods: List[Dict[str, Any]]
    timezone: str = "Asia/Shanghai"
    language: str = "zh-CN"
    priority_score: float = 1.0
    active: bool = True
    tags: Set[str] = None
    last_active: Optional[datetime] = None
    response_time_estimate: int = 30  # 预估响应时间（分钟）
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = set()


@dataclass
class ContactMatch:
    """联系人匹配结果"""
    contact: Contact
    match_score: float
    match_reasons: List[str]
    recommended: bool = False


class CommunicationMap:
    """沟通地图核心类"""
    
    def __init__(self, map_file: str = None):
        self.map_file = map_file or settings.communication_map_file
        self.contacts: Dict[str, Contact] = {}
        self.expertise_index: Dict[str, List[str]] = {}  # 专业技能 -> 联系人ID列表
        self.role_index: Dict[str, List[str]] = {}       # 角色 -> 联系人ID列表
        
        logger.info("沟通地图初始化完成")
    
    async def load(self):
        """加载沟通地图数据"""
        try:
            map_path = Path(self.map_file)
            
            if not map_path.exists():
                logger.warning(f"沟通地图文件不存在: {self.map_file}")
                await self._create_default_map()
                return
            
            with open(map_path, 'r', encoding='utf-8') as f:
                if self.map_file.endswith('.yaml') or self.map_file.endswith('.yml'):
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            
            # 加载联系人
            contacts_data = data.get('contacts', [])
            for contact_data in contacts_data:
                contact = self._dict_to_contact(contact_data)
                self.contacts[contact.id] = contact
                await self._index_contact(contact)
            
            logger.info(f"沟通地图加载完成，共{len(self.contacts)}个联系人")
            
        except Exception as e:
            logger.error(f"加载沟通地图失败: {e}")
            await self._create_default_map()
    
    async def save(self):
        """保存沟通地图数据"""
        try:
            map_path = Path(self.map_file)
            map_path.parent.mkdir(parents=True, exist_ok=True)
            
            contacts_data = [self._contact_to_dict(contact) for contact in self.contacts.values()]
            
            data = {
                'contacts': contacts_data,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(map_path, 'w', encoding='utf-8') as f:
                if self.map_file.endswith('.yaml') or self.map_file.endswith('.yml'):
                    yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
                else:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"沟通地图已保存: {self.map_file}")
            
        except Exception as e:
            logger.error(f"保存沟通地图失败: {e}")
    
    async def add_contact(self, contact: Contact) -> bool:
        """添加联系人"""
        try:
            self.contacts[contact.id] = contact
            await self._index_contact(contact)
            await self.save()
            logger.info(f"联系人添加成功: {contact.name}")
            return True
        except Exception as e:
            logger.error(f"添加联系人失败: {e}")
            return False
    
    async def update_contact(self, contact_id: str, updates: Dict[str, Any]) -> bool:
        """更新联系人信息"""
        try:
            if contact_id not in self.contacts:
                return False
            
            contact = self.contacts[contact_id]
            
            # 应用更新
            for key, value in updates.items():
                if hasattr(contact, key):
                    setattr(contact, key, value)
            
            # 重新索引
            await self._reindex_contact(contact_id)
            await self.save()
            
            logger.info(f"联系人更新成功: {contact.name}")
            return True
            
        except Exception as e:
            logger.error(f"更新联系人失败: {e}")
            return False
    
    async def remove_contact(self, contact_id: str) -> bool:
        """删除联系人"""
        try:
            if contact_id not in self.contacts:
                return False
            
            contact = self.contacts[contact_id]
            
            # 从索引中移除
            await self._remove_from_index(contact)
            
            # 删除联系人
            del self.contacts[contact_id]
            await self.save()
            
            logger.info(f"联系人删除成功: {contact.name}")
            return True
            
        except Exception as e:
            logger.error(f"删除联系人失败: {e}")
            return False
    
    async def find_contacts_by_context(
        self, 
        context: Dict[str, Any], 
        priority: str = "medium",
        max_results: int = 5
    ) -> List[str]:
        """根据上下文智能匹配联系人"""
        
        # 提取关键信息
        required_expertise = self._extract_expertise_from_context(context)
        task_type = context.get('task_type', '')
        domain = context.get('domain', '')
        urgency = self._calculate_urgency(priority, context)
        
        # 获取所有活跃联系人
        active_contacts = [
            contact for contact in self.contacts.values()
            if contact.active
        ]
        
        # 计算匹配分数
        matches = []
        for contact in active_contacts:
            match_score, match_reasons = self._calculate_match_score(
                contact, required_expertise, task_type, domain, urgency
            )
            
            if match_score > 0.3:  # 最低匹配阈值
                matches.append(ContactMatch(
                    contact=contact,
                    match_score=match_score,
                    match_reasons=match_reasons
                ))
        
        # 排序并返回结果
        matches.sort(key=lambda x: x.match_score, reverse=True)
        
        # 标记推荐联系人
        if matches:
            top_matches = matches[:min(3, len(matches))]
            for match in top_matches:
                match.recommended = True
        
        # 返回联系人ID列表
        return [match.contact.id for match in matches[:max_results]]
    
    async def get_contact(self, contact_id: str) -> Optional[Contact]:
        """获取指定联系人信息"""
        return self.contacts.get(contact_id)
    
    async def list_contacts(
        self, 
        role: str = None, 
        expertise: str = None, 
        active_only: bool = True
    ) -> List[Contact]:
        """列出联系人"""
        contacts = list(self.contacts.values())
        
        if active_only:
            contacts = [c for c in contacts if c.active]
        
        if role:
            contacts = [c for c in contacts if c.role == role]
        
        if expertise:
            contacts = [c for c in contacts if expertise in c.expertise]
        
        return contacts
    
    async def get_contact_stats(self) -> Dict[str, Any]:
        """获取联系人统计信息"""
        total_contacts = len(self.contacts)
        active_contacts = len([c for c in self.contacts.values() if c.active])
        
        role_distribution = {}
        expertise_distribution = {}
        
        for contact in self.contacts.values():
            # 角色分布
            role_distribution[contact.role] = role_distribution.get(contact.role, 0) + 1
            
            # 专业技能分布
            for skill in contact.expertise:
                expertise_distribution[skill] = expertise_distribution.get(skill, 0) + 1
        
        return {
            "total_contacts": total_contacts,
            "active_contacts": active_contacts,
            "role_distribution": role_distribution,
            "top_expertise": sorted(expertise_distribution.items(), key=lambda x: x[1], reverse=True)[:10]
        }
    
    def _extract_expertise_from_context(self, context: Dict[str, Any]) -> Set[str]:
        """从上下文中提取所需专业技能"""
        expertise_set = set()
        
        # 直接指定的专业技能
        if 'required_expertise' in context:
            if isinstance(context['required_expertise'], list):
                expertise_set.update(context['required_expertise'])
            else:
                expertise_set.add(context['required_expertise'])
        
        # 从任务类型推断
        task_type = context.get('task_type', '')
        if task_type:
            expertise_set.add(task_type)
        
        # 从域推断
        domain = context.get('domain', '')
        if domain:
            expertise_set.add(domain)
        
        # 从关键词推断
        keywords = context.get('keywords', [])
        for keyword in keywords:
            if isinstance(keyword, str):
                expertise_set.add(keyword)
        
        return expertise_set
    
    def _calculate_urgency(self, priority: str, context: Dict[str, Any]) -> float:
        """计算紧急程度"""
        base_urgency = {
            'low': 0.3,
            'medium': 0.6,
            'high': 0.8,
            'urgent': 1.0
        }.get(priority.lower(), 0.5)
        
        # 根据上下文调整紧急程度
        if context.get('deadline_soon', False):
            base_urgency += 0.2
        
        if context.get('business_critical', False):
            base_urgency += 0.3
        
        return min(base_urgency, 1.0)
    
    def _calculate_match_score(
        self,
        contact: Contact,
        required_expertise: Set[str],
        task_type: str,
        domain: str,
        urgency: float
    ) -> tuple[float, List[str]]:
        """计算联系人匹配分数"""
        
        match_score = 0.0
        match_reasons = []
        
        # 专业技能匹配 (40%)
        expertise_overlap = contact.expertise.intersection(required_expertise)
        if expertise_overlap:
            expertise_score = len(expertise_overlap) / max(len(required_expertise), 1)
            match_score += expertise_score * 0.4
            match_reasons.append(f"专业技能匹配: {', '.join(expertise_overlap)}")
        
        # 角色匹配 (20%)
        if task_type and task_type in contact.role:
            match_score += 0.2
            match_reasons.append(f"角色匹配: {contact.role}")
        
        # 可用性匹配 (20%)
        availability_score = self._calculate_availability_score(contact, urgency)
        match_score += availability_score * 0.2
        if availability_score > 0.7:
            match_reasons.append(f"可用性良好: {contact.availability}")
        
        # 优先级评分 (10%)
        match_score += contact.priority_score * 0.1
        
        # 响应时间评估 (10%)
        if contact.response_time_estimate <= 30:
            match_score += 0.1
            match_reasons.append(f"快速响应: {contact.response_time_estimate}分钟")
        
        return min(match_score, 1.0), match_reasons
    
    def _calculate_availability_score(self, contact: Contact, urgency: float) -> float:
        """计算联系人可用性分数"""
        
        availability_map = {
            'always': 1.0,
            'work_hours': 0.7,
            'on_call': 0.9,
            'weekends': 0.5
        }
        
        base_score = availability_map.get(contact.availability, 0.5)
        
        # 紧急情况下提升可用性要求
        if urgency > 0.8 and contact.availability == 'weekends':
            base_score *= 0.5
        
        return base_score
    
    async def _index_contact(self, contact: Contact):
        """索引联系人信息"""
        # 专业技能索引
        for expertise in contact.expertise:
            if expertise not in self.expertise_index:
                self.expertise_index[expertise] = []
            self.expertise_index[expertise].append(contact.id)
        
        # 角色索引
        if contact.role not in self.role_index:
            self.role_index[contact.role] = []
        self.role_index[contact.role].append(contact.id)
    
    async def _reindex_contact(self, contact_id: str):
        """重新索引联系人"""
        contact = self.contacts[contact_id]
        
        # 先移除旧索引
        await self._remove_from_index(contact)
        
        # 添加新索引
        await self._index_contact(contact)
    
    async def _remove_from_index(self, contact: Contact):
        """从索引中移除联系人"""
        # 移除专业技能索引
        for expertise in contact.expertise:
            if expertise in self.expertise_index:
                self.expertise_index[expertise] = [
                    cid for cid in self.expertise_index[expertise]
                    if cid != contact.id
                ]
                if not self.expertise_index[expertise]:
                    del self.expertise_index[expertise]
        
        # 移除角色索引
        if contact.role in self.role_index:
            self.role_index[contact.role] = [
                cid for cid in self.role_index[contact.role]
                if cid != contact.id
            ]
            if not self.role_index[contact.role]:
                del self.role_index[contact.role]
    
    def _dict_to_contact(self, data: Dict[str, Any]) -> Contact:
        """将字典转换为Contact对象"""
        # 处理集合字段
        if 'expertise' in data and isinstance(data['expertise'], list):
            data['expertise'] = set(data['expertise'])
        
        if 'tags' in data and isinstance(data['tags'], list):
            data['tags'] = set(data['tags'])
        
        # 处理时间字段
        if 'last_active' in data and data['last_active']:
            if isinstance(data['last_active'], str):
                data['last_active'] = datetime.fromisoformat(data['last_active'])
        
        return Contact(**data)
    
    def _contact_to_dict(self, contact: Contact) -> Dict[str, Any]:
        """将Contact对象转换为字典"""
        data = asdict(contact)
        
        # 处理集合字段
        data['expertise'] = list(data['expertise'])
        data['tags'] = list(data['tags'])
        
        # 处理时间字段
        if data['last_active']:
            data['last_active'] = data['last_active'].isoformat()
        
        return data
    
    async def _create_default_map(self):
        """创建默认沟通地图"""
        logger.info("创建默认沟通地图")
        
        # 创建默认联系人
        default_contacts = [
            Contact(
                id="admin",
                name="系统管理员",
                role="administrator",
                expertise={"system", "infrastructure", "troubleshooting"},
                availability="always",
                contact_methods=[
                    {"type": "email", "value": "admin@company.com"},
                    {"type": "phone", "value": "+86-138-0000-0000"}
                ],
                priority_score=1.0,
                response_time_estimate=15
            ),
            Contact(
                id="tech_lead",
                name="技术负责人",
                role="technical_lead",
                expertise={"development", "architecture", "review", "code_quality"},
                availability="work_hours",
                contact_methods=[
                    {"type": "email", "value": "tech.lead@company.com"},
                    {"type": "slack", "value": "@tech_lead"}
                ],
                priority_score=0.9,
                response_time_estimate=30
            ),
            Contact(
                id="data_scientist",
                name="数据科学家",
                role="data_scientist",
                expertise={"data_analysis", "machine_learning", "statistics", "python"},
                availability="work_hours",
                contact_methods=[
                    {"type": "email", "value": "data.science@company.com"},
                    {"type": "teams", "value": "data.scientist"}
                ],
                priority_score=0.8,
                response_time_estimate=45
            )
        ]
        
        for contact in default_contacts:
            self.contacts[contact.id] = contact
            await self._index_contact(contact)
        
        await self.save()
        logger.info(f"默认沟通地图创建完成，共{len(default_contacts)}个联系人")
