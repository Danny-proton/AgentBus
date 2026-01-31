import os
import re

# 要标准化的模块列表
MODULES = [
    "core", "plugins", "channels", "services", "gateway", 
    "media_understanding", "auto_reply", "infrastructure", 
    "agentbus_logging", "agents", "api", "cli", "config", 
    "daemon", "extensions", "hooks", "integrations", "memory", 
    "models", "preferences", "scheduler", "security", "sessions", 
    "skills", "storage"
]

# 编译正则表达式，匹配以这些模块开头的导入语句
IMPORT_PATTERN = re.compile(f'^from ({"|".join(MODULES)})(?=[ .])', re.MULTILINE)

def standardize_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换不带 agentbus. 前缀的导入
    new_content = IMPORT_PATTERN.sub(r'from agentbus.\1', content)
    
    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False

def main():
    base_dir = r"d:\gitAgentBus\AgentBus"
    count = 0
    for root, dirs, files in os.walk(base_dir):
        # 排除不需要处理的目录
        if any(exc in root for exc in [".git", "__pycache__", ".pytest_cache", "venv"]):
            continue
            
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                if standardize_file(file_path):
                    print(f"Standardized: {file_path}")
                    count += 1
    
    print(f"Total files updated: {count}")

if __name__ == "__main__":
    main()
