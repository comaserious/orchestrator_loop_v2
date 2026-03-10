import importlib
import pkgutil
import os

# tool_modules/ 안의 모든 .py 파일을 자동으로 import해서 @register_tool 데코레이터가 실행되게 함
# 새 툴을 추가할 때 이 파일을 수정할 필요 없음
for _, module_name, _ in pkgutil.iter_modules([os.path.dirname(__file__)]):
    importlib.import_module(f"chat_bot.tools.tool_modules.{module_name}")
