---
AIGC:
    ContentProducer: Minimax Agent AI
    ContentPropagator: Minimax Agent AI
    Label: AIGC
    ProduceID: "00000000000000000000000000000000"
    PropagateID: "00000000000000000000000000000000"
    ReservedCode1: 304402201727450cca7fec7e9f9eab9c8f9524bc1366d9f58fc31e934f47c33ffbd24abd02206b5eff23b0e7108cd02f35a4b169d078da51f02551eeae229c2833ef787a6375
    ReservedCode2: 3045022100b008de9782dfdc623f3a4888d9db4db987f61f0fce2d9433107b335f9bce37590220269b4c98cd364b51d9bcc36ba7f6add0ea10580b57518855ec84a0290777d625
---

# AgentBus Java用户系统扩展接口

本文档介绍如何使用AgentBus为Java用户系统提供的扩展接口，实现用户配置、记忆、技能偏好的持久化存储。

## 架构概览

```
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│   Java Application  │◄──►│   AgentBus Java API  │◄──►│   Storage Layer     │
│                     │    │                      │    │                     │
│ • REST API Client   │    │ • FastAPI Routes     │    │ • Database Storage  │
│ • User Management   │    │ • Request Validation │    │ • Memory Storage    │
│ • Preference Sync   │    │ • CORS Support       │    │ • Cache Management │
└─────────────────────┘    └──────────────────────┘    └─────────────────────┘
```

## 核心组件

### 1. 数据模型 (`agentbus/models/user.py`)

定义了完整的用户数据结构：

- **UserProfile**: 用户基本信息
- **UserPreferences**: 用户偏好设置
- **UserMemory**: 用户记忆存储
- **UserSkills**: 用户技能配置
- **UserContext**: 用户上下文信息
- **UserIntegration**: 外部系统集成配置
- **UserStats**: 用户统计数据

### 2. 存储抽象层 (`agentbus/storage/`)

提供统一的存储接口：

- **DatabaseStorage**: 基于SQLite的持久化存储
- **MemoryStorage**: 基于内存的高速缓存
- **StorageManager**: 存储管理器

### 3. Java客户端接口 (`agentbus/integrations/java_client.py`)

提供RESTful API：

- **JavaClient**: 主要的客户端接口
- **JavaClientAPI**: FastAPI路由定义
- **CORS支持**: 支持跨域请求

### 4. 用户偏好管理 (`agentbus/integrations/user_preferences.py`)

智能偏好管理：

- **UserPreferencesManager**: 偏好管理器
- **PreferenceValidator**: 偏好验证器
- **PreferenceMigrator**: 偏好迁移器

## 快速开始

### 1. 基本配置

```python
from agentbus.storage import StorageManager
from agentbus.integrations import JavaClient

# 配置存储
storage_config = {
    'type': 'database',  # 或 'memory'
    'db_path': 'agentbus.db',
    'max_memory_size': 10000
}

# 初始化存储
storage_manager = StorageManager(storage_config)
await storage_manager.initialize()

# 配置Java客户端
java_config = {
    'enabled': True,
    'cors_origins': ['*'],
    'max_connections': 1000,
    'timeout_seconds': 30
}

# 启动Java客户端
java_client = JavaClient(java_config)
await java_client.start()
```

### 2. 用户管理

#### 创建用户

```python
from agentbus.models.user import UserProfile, UserPreferences

user = UserProfile(
    username="java_developer",
    email="java@example.com",
    full_name="Java开发者",
    preferences=UserPreferences(
        java_version="17",
        ide_preference="IntelliJ IDEA",
        language="zh-CN",
        theme="dark"
    )
)

created_user = await storage_manager.user_storage.create_user(user)
```

#### 获取用户信息

```python
user = await storage_manager.user_storage.get_user(user_id)
preferences = await storage_manager.preferences_storage.get_preferences(user_id)
```

#### 更新用户偏好

```python
update_data = {
    'java_version': '21',
    'theme': 'light',
    'skill_level': SkillLevel.ADVANCED
}

updated_preferences = await storage_manager.preferences_storage.update_preferences(
    user_id, update_data
)
```

### 3. 记忆管理

#### 存储用户记忆

```python
from agentbus.models.user import UserMemory

memory = UserMemory(
    session_id="session_001",
    user_id=user_id,
    content="用户偏好使用Spring Boot开发微服务",
    memory_type="learning_progress",
    importance=8,
    tags=["spring", "microservices", "preference"]
)

memory_id = await storage_manager.memory_storage.store_memory(memory)
```

#### 搜索用户记忆

```python
# 按类型搜索
memories = await storage_manager.memory_storage.get_user_memories(
    user_id, memory_type="learning_progress"
)

# 关键词搜索
search_results = await storage_manager.memory_storage.search_memories(
    user_id, "Spring Boot", limit=10
)
```

### 4. 技能管理

#### 添加技能

```python
from agentbus.models.user import UserSkills, SkillLevel

skill = UserSkills(
    user_id=user_id,
    skill_name="Spring Framework",
    skill_level=SkillLevel.ADVANCED,
    experience_points=1500,
    custom_config={
        "preferred_version": "6.0",
        "modules_used": ["Spring MVC", "Spring Data", "Spring Security"]
    }
)

skill_id = await storage_manager.skills_storage.save_skill(skill)
```

### 5. 集成管理

#### 添加IDE集成

```python
from agentbus.models.user import UserIntegration

integration = UserIntegration(
    user_id=user_id,
    integration_type="java_ide",
    integration_name="IntelliJ IDEA Ultimate",
    config={
        "project_path": "/workspace/java-projects",
        "auto_save": True,
        "code_style": "Google Java Style",
        "java_version": "21"
    },
    credentials={
        "license_key": "xxx-xxx-xxx-xxx"
    }
)

integration_id = await storage_manager.integration_storage.save_integration(integration)
```

## Java API端点

### 用户管理

- `POST /java/api/users` - 创建用户
- `GET /java/api/users/{user_id}` - 获取用户信息
- `PUT /java/api/users/{user_id}` - 更新用户信息
- `DELETE /java/api/users/{user_id}` - 删除用户
- `GET /java/api/users` - 列出用户

### 用户偏好

- `GET /java/api/users/{user_id}/preferences` - 获取用户偏好
- `PUT /java/api/users/{user_id}/preferences` - 更新用户偏好

### 用户记忆

- `POST /java/api/users/{user_id}/memories` - 存储记忆
- `GET /java/api/users/{user_id}/memories` - 获取用户记忆
- `GET /java/api/users/{user_id}/memories/search` - 搜索记忆
- `DELETE /java/api/memories/{memory_id}` - 删除记忆

### 用户技能

- `POST /java/api/users/{user_id}/skills` - 添加技能
- `GET /java/api/users/{user_id}/skills` - 获取用户技能
- `PUT /java/api/users/{user_id}/skills/{skill_id}` - 更新技能
- `DELETE /java/api/users/{user_id}/skills/{skill_id}` - 删除技能

### 用户集成

- `POST /java/api/users/{user_id}/integrations` - 添加集成
- `GET /java/api/users/{user_id}/integrations` - 获取用户集成
- `PUT /java/api/integrations/{integration_id}` - 更新集成
- `DELETE /java/api/integrations/{integration_id}` - 删除集成

### 系统接口

- `GET /java/api/health` - 健康检查
- `GET /java/api/stats` - 系统统计

## Java客户端使用示例

### Maven依赖

```xml
<dependency>
    <groupId>com.squareup.okhttp3</groupId>
    <artifactId>okhttp</artifactId>
    <version>4.12.0</version>
</dependency>

<dependency>
    <groupId>com.google.code.gson</groupId>
    <artifactId>gson</artifactId>
    <version>2.10.1</version>
</dependency>
```

### Java客户端代码

```java
import okhttp3.*;
import com.google.gson.Gson;
import com.google.gson.JsonObject;

public class AgentBusJavaClient {
    private final String baseUrl;
    private final OkHttpClient client;
    private final Gson gson;
    
    public AgentBusJavaClient(String baseUrl) {
        this.baseUrl = baseUrl;
        this.client = new OkHttpClient();
        this.gson = new Gson();
    }
    
    // 创建用户
    public User createUser(String username, String email, String fullName) throws Exception {
        JsonObject requestBody = new JsonObject();
        requestBody.addProperty("username", username);
        requestBody.addProperty("email", email);
        requestBody.addProperty("full_name", fullName);
        
        Request request = new Request.Builder()
            .url(baseUrl + "/java/api/users")
            .post(RequestBody.create(
                gson.toJson(requestBody), 
                MediaType.parse("application/json")
            ))
            .build();
            
        try (Response response = client.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                throw new RuntimeException("Failed to create user: " + response.message());
            }
            
            JsonObject responseBody = gson.fromJson(
                response.body().string(), 
                JsonObject.class
            );
            
            return gson.fromJson(responseBody.get("data"), User.class);
        }
    }
    
    // 获取用户偏好
    public UserPreferences getUserPreferences(String userId) throws Exception {
        Request request = new Request.Builder()
            .url(baseUrl + "/java/api/users/" + userId + "/preferences")
            .get()
            .build();
            
        try (Response response = client.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                throw new RuntimeException("Failed to get preferences: " + response.message());
            }
            
            JsonObject responseBody = gson.fromJson(
                response.body().string(), 
                JsonObject.class
            );
            
            return gson.fromJson(responseBody.get("data"), UserPreferences.class);
        }
    }
    
    // 存储记忆
    public void storeMemory(String userId, String content, String memoryType) throws Exception {
        JsonObject requestBody = new JsonObject();
        requestBody.addProperty("content", content);
        requestBody.addProperty("memory_type", memoryType);
        requestBody.addProperty("importance", 5);
        
        Request request = new Request.Builder()
            .url(baseUrl + "/java/api/users/" + userId + "/memories")
            .post(RequestBody.create(
                gson.toJson(requestBody), 
                MediaType.parse("application/json")
            ))
            .build();
            
        try (Response response = client.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                throw new RuntimeException("Failed to store memory: " + response.message());
            }
        }
    }
}

// 数据模型
public class User {
    private String userId;
    private String username;
    private String email;
    private String fullName;
    private UserPreferences preferences;
    
    // getters and setters
}

public class UserPreferences {
    private String language;
    private String timezone;
    private String theme;
    private String javaVersion;
    private String idePreference;
    
    // getters and setters
}
```

### 使用示例

```java
public class Main {
    public static void main(String[] args) {
        try {
            // 初始化客户端
            AgentBusJavaClient client = new AgentBusJavaClient("http://localhost:8000");
            
            // 创建用户
            User user = client.createUser("java_dev", "dev@example.com", "Java开发者");
            System.out.println("创建用户成功: " + user.getUserId());
            
            // 获取偏好
            UserPreferences prefs = client.getUserPreferences(user.getUserId());
            System.out.println("用户偏好: " + prefs.getIdePreference());
            
            // 存储记忆
            client.storeMemory(
                user.getUserId(), 
                "用户已完成Spring Boot学习", 
                "learning_progress"
            );
            
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
```

## 高级功能

### 1. 智能推荐

```python
# 智能推荐IDE
suggested_ide = await preferences_manager.suggest_java_ide(user_id)

# 智能推荐Java版本
suggested_version = await preferences_manager.suggest_java_version(user_id)
```

### 2. 批量操作

```python
# 批量更新用户偏好
user_ids = ["user1", "user2", "user3"]
preferences_data = {"theme": "dark"}
results = await preferences_manager.bulk_update_preferences(user_ids, preferences_data)
```

### 3. 偏好验证

```python
from agentbus.integrations.user_preferences import PreferenceValidator

errors = PreferenceValidator.validate_java_preferences({
    'java_version': '17',
    'ide_preference': 'IntelliJ IDEA',
    'theme': 'dark'
})

if errors:
    print("验证错误:", errors)
```

### 4. 数据迁移

```python
from agentbus.integrations.user_preferences import PreferenceMigrator

old_format = {
    'java_prefs': {
        'java_version': '8',
        'ide': 'Eclipse'
    }
}

success = await migrator.migrate_preferences_format(user_id, old_format)
```

## 配置选项

### 存储配置

```python
storage_config = {
    'type': 'database',  # 'database' 或 'memory'
    'db_path': 'agentbus.db',  # 数据库路径
    'max_memory_size': 10000,  # 内存存储大小限制
    'connection_pool_size': 10,  # 连接池大小
    'timeout_seconds': 30  # 超时时间
}
```

### Java客户端配置

```python
java_config = {
    'enabled': True,
    'cors_origins': ['*'],  # CORS允许的来源
    'max_connections': 1000,  # 最大连接数
    'timeout_seconds': 30,  # 请求超时
    'storage_type': 'memory',  # 存储类型
    'health_check_interval': 60  # 健康检查间隔
}
```

## 错误处理

### 常见错误类型

- **StorageConnectionError**: 存储连接错误
- **StorageOperationError**: 存储操作错误
- **ValidationError**: 数据验证错误
- **AuthenticationError**: 认证错误

### 错误处理示例

```python
try:
    user = await storage_manager.user_storage.create_user(user_data)
except StorageConnectionError as e:
    logger.error(f"存储连接失败: {e}")
except StorageOperationError as e:
    logger.error(f"存储操作失败: {e}")
except Exception as e:
    logger.error(f"未知错误: {e}")
```

## 性能优化

### 1. 缓存策略

- 用户偏好自动缓存
- 缓存过期时间：5分钟
- 支持手动清除缓存

### 2. 批量操作

- 支持批量用户创建
- 支持批量偏好更新
- 优化数据库查询

### 3. 索引优化

- 用户邮箱索引
- 记忆类型索引
- 用户ID索引

## 部署和运维

### 1. 健康检查

```python
# 检查存储健康状态
health_status = await storage_manager.health_check()

# 检查API健康状态
response = await client.get("http://localhost:8000/java/api/health")
```

### 2. 监控和日志

```python
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
```

### 3. 备份和恢复

```python
# 导出用户偏好
exported_data = await preferences_manager.export_user_preferences(user_id)

# 导入用户偏好
await preferences_manager.import_user_preferences(user_id, imported_data)
```

## 故障排除

### 常见问题

1. **存储连接失败**
   - 检查数据库文件权限
   - 确认数据库路径正确
   - 检查磁盘空间

2. **CORS跨域问题**
   - 配置正确的CORS来源
   - 检查请求头设置

3. **性能问题**
   - 调整缓存大小
   - 优化数据库索引
   - 使用批量操作

## 示例项目

参考 `java_integration_example.py` 文件，该文件包含了完整的使用示例，展示了：

- 用户管理功能
- 记忆管理功能
- 技能管理功能
- 偏好管理功能
- 集成管理功能

运行示例：

```bash
cd /workspace/agentbus
python java_integration_example.py
```

## 扩展开发

### 自定义存储后端

```python
from agentbus.storage import BaseStorage

class CustomStorage(BaseStorage):
    async def initialize(self):
        # 自定义初始化逻辑
        pass
    
    async def create_user(self, user):
        # 自定义创建用户逻辑
        pass
```

### 自定义验证器

```python
from agentbus.integrations.user_preferences import PreferenceValidator

class CustomValidator(PreferenceValidator):
    @staticmethod
    def validate_custom_preferences(preferences_data):
        # 自定义验证逻辑
        return []
```

## 总结

AgentBus为Java用户系统提供了完整的扩展接口，包括：

✅ **用户数据管理** - 完整的用户档案管理  
✅ **偏好持久化** - 智能偏好管理和推荐  
✅ **记忆存储** - 灵活的记忆管理系统  
✅ **技能跟踪** - 技能水平管理和进度跟踪  
✅ **集成接口** - 外部系统集成支持  
✅ **RESTful API** - 完整的Java API接口  
✅ **高性能存储** - 数据库和内存存储支持  
✅ **智能推荐** - 基于用户行为的智能推荐  

这些接口为Java开发者提供了与AgentBus无缝集成的能力，实现了用户配置、记忆、技能偏好的持久化存储和管理。