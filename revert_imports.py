import os
import re

# 要还原的模块列表
MODULES = [
    "core", "plugins", "channels", "services", "gateway", 
    "media_understanding", "auto_reply", "infrastructure", 
    "agentbus_logging", "agents", "api", "cli", "config", 
    "daemon", "extensions", "hooks", "integrations", "memory", 
    "models", "preferences", "scheduler", "security", "sessions", 
    "skills", "storage"
]

# 编译正则表达式，匹配以 agentbus. 开头的导入语句
REVERT_PATTERN = re.compile(r'^from agentbus\.(%s)(?=[ .])' % "|".join(MODULES), re.MULTILINE)

def revert_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 还原导入，去掉 agentbus. 前缀
    new_content = REVERT_PATTERN.sub(r'from \1', content)
    
    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False

def main():
    base_dir = r"d:\gitAgentBus\AgentBus"
    count = 0
    for root, dirs, files in os.walk(base_dir):
        if any(exc in root for exc in [".git", "__pycache__", ".pytest_cache", "venv"]):
            continue
            
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                if revert_file(file_path):
                    print(f"Reverted: {file_path}")
                    count += 1
    
    print(f"Total files reverted: {count}")

if __name__ == "__main__":
    main()
