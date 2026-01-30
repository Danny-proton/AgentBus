"""
用户偏好管理 - 专门处理Java用户的偏好设置
支持个性化配置和智能推荐
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import json

from ..models.user import UserPreferences, SkillLevel
from ..storage import StorageManager

logger = logging.getLogger(__name__)


class UserPreferencesManager:
    """用户偏好管理器"""
    
    def __init__(self, storage_manager: StorageManager):
        self.storage_manager = storage_manager
        self._preference_cache = {}  # 偏好缓存
        self._cache_timeout = 300  # 缓存超时时间(秒)
    
    async def initialize(self):
        """初始化偏好管理器"""
        logger.info("User preferences manager initialized")
    
    async def get_user_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """获取用户偏好"""
        try:
            # 尝试从缓存获取
            if user_id in self._preference_cache:
                cache_entry = self._preference_cache[user_id]
                if datetime.now().timestamp() - cache_entry['timestamp'] < self._cache_timeout:
                    return cache_entry['preferences']
            
            # 从存储获取
            preferences = await self.storage_manager.preferences_storage.get_preferences(user_id)
            
            if preferences:
                # 更新缓存
                self._preference_cache[user_id] = {
                    'preferences': preferences,
                    'timestamp': datetime.now().timestamp()
                }
            
            return preferences
            
        except Exception as e:
            logger.error(f"Failed to get user preferences for {user_id}: {e}")
            return None
    
    async def update_user_preferences(self, user_id: str, preferences_data: Dict[str, Any]) -> Optional[UserPreferences]:
        """更新用户偏好"""
        try:
            # 获取当前偏好
            current_preferences = await self.get_user_preferences(user_id)
            if not current_preferences:
                # 如果没有偏好，创建默认偏好
                current_preferences = UserPreferences()
            
            # 更新偏好字段
            for key, value in preferences_data.items():
                if hasattr(current_preferences, key):
                    setattr(current_preferences, key, value)
            
            current_preferences.updated_at = datetime.now()
            
            # 保存到存储
            await self.storage_manager.preferences_storage.save_preferences(user_id, current_preferences)
            
            # 更新缓存
            self._preference_cache[user_id] = {
                'preferences': current_preferences,
                'timestamp': datetime.now().timestamp()
            }
            
            logger.info(f"Updated preferences for user {user_id}")
            return current_preferences
            
        except Exception as e:
            logger.error(f"Failed to update user preferences for {user_id}: {e}")
            return None
    
    async def set_java_preferences(self, user_id: str, java_version: str, ide_preference: str, 
                                 coding_style: Optional[Dict[str, Any]] = None) -> bool:
        """设置Java特定偏好"""
        try:
            java_preferences = {
                'java_version': java_version,
                'ide_preference': ide_preference,
            }
            
            if coding_style:
                java_preferences['coding_style'] = coding_style
            
            result = await self.update_user_preferences(user_id, java_preferences)
            return result is not None
            
        except Exception as e:
            logger.error(f"Failed to set Java preferences for {user_id}: {e}")
            return False
    
    async def get_java_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取Java特定偏好"""
        try:
            preferences = await self.get_user_preferences(user_id)
            if not preferences:
                return None
            
            return {
                'java_version': preferences.java_version,
                'ide_preference': preferences.ide_preference,
                'coding_style': preferences.coding_style
            }
            
        except Exception as e:
            logger.error(f"Failed to get Java preferences for {user_id}: {e}")
            return None
    
    async def set_ui_preferences(self, user_id: str, theme: str, language: str = 'zh-CN') -> bool:
        """设置界面偏好"""
        try:
            ui_preferences = {
                'theme': theme,
                'language': language
            }
            
            result = await self.update_user_preferences(user_id, ui_preferences)
            return result is not None
            
        except Exception as e:
            logger.error(f"Failed to set UI preferences for {user_id}: {e}")
            return False
    
    async def set_notification_preferences(self, user_id: str, notifications: bool, auto_save: bool = True) -> bool:
        """设置通知偏好"""
        try:
            notification_preferences = {
                'notifications': notifications,
                'auto_save': auto_save
            }
            
            result = await self.update_user_preferences(user_id, notification_preferences)
            return result is not None
            
        except Exception as e:
            logger.error(f"Failed to set notification preferences for {user_id}: {e}")
            return False
    
    async def set_skill_level(self, user_id: str, skill_level: SkillLevel) -> bool:
        """设置技能水平"""
        try:
            skill_preferences = {
                'skill_level': skill_level
            }
            
            result = await self.update_user_preferences(user_id, skill_preferences)
            return result is not None
            
        except Exception as e:
            logger.error(f"Failed to set skill level for {user_id}: {e}")
            return False
    
    async def get_skill_level(self, user_id: str) -> Optional[SkillLevel]:
        """获取技能水平"""
        try:
            preferences = await self.get_user_preferences(user_id)
            return preferences.skill_level if preferences else None
            
        except Exception as e:
            logger.error(f"Failed to get skill level for {user_id}: {e}")
            return None
    
    async def suggest_java_ide(self, user_id: str) -> Optional[str]:
        """智能推荐Java IDE"""
        try:
            preferences = await self.get_user_preferences(user_id)
            if not preferences:
                return "IntelliJ IDEA"  # 默认推荐
            
            # 根据技能水平推荐
            if preferences.skill_level == SkillLevel.BEGINNER:
                return "IntelliJ IDEA Community"  # 对初学者友好
            elif preferences.skill_level == SkillLevel.INTERMEDIATE:
                return "IntelliJ IDEA"  # 功能完整
            elif preferences.skill_level == SkillLevel.ADVANCED:
                return "IntelliJ IDEA Ultimate"  # 高级功能
            elif preferences.skill_level == SkillLevel.EXPERT:
                return "VS Code"  # 高度可定制
            
            return preferences.ide_preference or "IntelliJ IDEA"
            
        except Exception as e:
            logger.error(f"Failed to suggest Java IDE for {user_id}: {e}")
            return "IntelliJ IDEA"
    
    async def suggest_java_version(self, user_id: str) -> Optional[str]:
        """智能推荐Java版本"""
        try:
            preferences = await self.get_user_preferences(user_id)
            if not preferences:
                return "17"  # 默认LTS版本
            
            # 根据技能水平推荐版本
            if preferences.skill_level == SkillLevel.BEGINNER:
                return "17"  # 稳定的LTS版本
            elif preferences.skill_level == SkillLevel.INTERMEDIATE:
                return "17"  # 平衡稳定性和新特性
            elif preferences.skill_level == SkillLevel.ADVANCED:
                return "21"  # 最新LTS版本
            elif preferences.skill_level == SkillLevel.EXPERT:
                return "21"  # 尝试最新特性
            
            return preferences.java_version or "17"
            
        except Exception as e:
            logger.error(f"Failed to suggest Java version for {user_id}: {e}")
            return "17"
    
    async def apply_learning_progress(self, user_id: str, progress_data: Dict[str, Any]) -> bool:
        """应用学习进度到偏好"""
        try:
            preferences = await self.get_user_preferences(user_id)
            if not preferences:
                preferences = UserPreferences()
            
            # 根据学习进度调整技能水平
            if 'skill_progression' in progress_data:
                skill_progression = progress_data['skill_progression']
                
                # 自动调整技能水平
                if skill_progression >= 90:
                    preferences.skill_level = SkillLevel.EXPERT
                elif skill_progression >= 70:
                    preferences.skill_level = SkillLevel.ADVANCED
                elif skill_progression >= 40:
                    preferences.skill_level = SkillLevel.INTERMEDIATE
                else:
                    preferences.skill_level = SkillLevel.BEGINNER
            
            # 更新编码风格偏好
            if 'coding_style' in progress_data:
                preferences.coding_style.update(progress_data['coding_style'])
            
            preferences.updated_at = datetime.now()
            
            # 保存更新后的偏好
            await self.storage_manager.preferences_storage.save_preferences(user_id, preferences)
            
            # 更新缓存
            self._preference_cache[user_id] = {
                'preferences': preferences,
                'timestamp': datetime.now().timestamp()
            }
            
            logger.info(f"Applied learning progress for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply learning progress for {user_id}: {e}")
            return False
    
    async def export_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """导出用户偏好"""
        try:
            preferences = await self.get_user_preferences(user_id)
            if not preferences:
                return None
            
            return {
                'user_id': user_id,
                'preferences': preferences.dict(),
                'exported_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to export user preferences for {user_id}: {e}")
            return None
    
    async def import_user_preferences(self, user_id: str, preferences_data: Dict[str, Any]) -> bool:
        """导入用户偏好"""
        try:
            if 'preferences' not in preferences_data:
                return False
            
            preferences_dict = preferences_data['preferences']
            
            # 验证和更新偏好
            result = await self.update_user_preferences(user_id, preferences_dict)
            return result is not None
            
        except Exception as e:
            logger.error(f"Failed to import user preferences for {user_id}: {e}")
            return False
    
    async def reset_user_preferences(self, user_id: str) -> bool:
        """重置用户偏好为默认值"""
        try:
            default_preferences = UserPreferences()
            
            # 保存默认偏好
            await self.storage_manager.preferences_storage.save_preferences(user_id, default_preferences)
            
            # 清除缓存
            if user_id in self._preference_cache:
                del self._preference_cache[user_id]
            
            logger.info(f"Reset preferences for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset user preferences for {user_id}: {e}")
            return False
    
    async def bulk_update_preferences(self, user_ids: List[str], preferences_data: Dict[str, Any]) -> Dict[str, bool]:
        """批量更新用户偏好"""
        results = {}
        
        for user_id in user_ids:
            try:
                result = await self.update_user_preferences(user_id, preferences_data)
                results[user_id] = result is not None
            except Exception as e:
                logger.error(f"Failed to bulk update preferences for user {user_id}: {e}")
                results[user_id] = False
        
        return results
    
    async def get_preference_statistics(self) -> Dict[str, Any]:
        """获取偏好统计信息"""
        try:
            # 这是一个简化实现，实际中可能需要更复杂的统计逻辑
            total_users = 0
            theme_distribution = {}
            skill_level_distribution = {}
            
            # 模拟统计数据
            total_users = len(self._preference_cache)
            
            for user_id, cache_entry in self._preference_cache.items():
                preferences = cache_entry['preferences']
                
                # 主题分布
                theme = preferences.theme
                theme_distribution[theme] = theme_distribution.get(theme, 0) + 1
                
                # 技能水平分布
                skill_level = preferences.skill_level.value
                skill_level_distribution[skill_level] = skill_level_distribution.get(skill_level, 0) + 1
            
            return {
                'total_users': total_users,
                'theme_distribution': theme_distribution,
                'skill_level_distribution': skill_level_distribution,
                'cached_entries': len(self._preference_cache),
                'statistics_generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get preference statistics: {e}")
            return {}
    
    async def cleanup_cache(self):
        """清理过期的缓存"""
        try:
            current_time = datetime.now().timestamp()
            expired_users = []
            
            for user_id, cache_entry in self._preference_cache.items():
                if current_time - cache_entry['timestamp'] > self._cache_timeout:
                    expired_users.append(user_id)
            
            for user_id in expired_users:
                del self._preference_cache[user_id]
            
            logger.info(f"Cleaned up {len(expired_users)} expired cache entries")
            
        except Exception as e:
            logger.error(f"Failed to cleanup cache: {e}")


class PreferenceValidator:
    """偏好验证器"""
    
    @staticmethod
    def validate_java_preferences(preferences_data: Dict[str, Any]) -> List[str]:
        """验证Java偏好设置"""
        errors = []
        
        # 验证Java版本
        if 'java_version' in preferences_data:
            java_version = preferences_data['java_version']
            valid_versions = ['8', '11', '17', '21']
            if java_version not in valid_versions:
                errors.append(f"Invalid Java version: {java_version}. Valid versions: {valid_versions}")
        
        # 验证IDE偏好
        if 'ide_preference' in preferences_data:
            ide_preference = preferences_data['ide_preference']
            valid_ides = ['IntelliJ IDEA', 'Eclipse', 'VS Code', 'NetBeans']
            if ide_preference not in valid_ides:
                errors.append(f"IDE preference not recognized: {ide_preference}")
        
        # 验证主题
        if 'theme' in preferences_data:
            theme = preferences_data['theme']
            valid_themes = ['light', 'dark', 'auto']
            if theme not in valid_themes:
                errors.append(f"Invalid theme: {theme}. Valid themes: {valid_themes}")
        
        # 验证语言
        if 'language' in preferences_data:
            language = preferences_data['language']
            valid_languages = ['zh-CN', 'en-US', 'ja-JP']
            if language not in valid_languages:
                errors.append(f"Unsupported language: {language}")
        
        return errors
    
    @staticmethod
    def validate_skill_level(skill_level: str) -> bool:
        """验证技能水平"""
        valid_levels = ['beginner', 'intermediate', 'advanced', 'expert']
        return skill_level.lower() in valid_levels


class PreferenceMigrator:
    """偏好迁移器"""
    
    def __init__(self, storage_manager: StorageManager):
        self.storage_manager = storage_manager
    
    async def migrate_preferences_format(self, user_id: str, old_format: Dict[str, Any]) -> bool:
        """迁移偏好格式"""
        try:
            new_format = {}
            
            # 映射旧格式到新格式
            if 'java_prefs' in old_format:
                java_prefs = old_format['java_prefs']
                if 'java_version' in java_prefs:
                    new_format['java_version'] = java_prefs['java_version']
                if 'ide' in java_prefs:
                    new_format['ide_preference'] = java_prefs['ide']
            
            if 'ui_prefs' in old_format:
                ui_prefs = old_format['ui_prefs']
                if 'theme' in ui_prefs:
                    new_format['theme'] = ui_prefs['theme']
                if 'lang' in ui_prefs:
                    new_format['language'] = ui_prefs['lang']
            
            # 应用迁移后的偏好
            preferences_manager = UserPreferencesManager(self.storage_manager)
            result = await preferences_manager.update_user_preferences(user_id, new_format)
            
            return result is not None
            
        except Exception as e:
            logger.error(f"Failed to migrate preferences format for user {user_id}: {e}")
            return False