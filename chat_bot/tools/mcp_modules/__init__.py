import importlib.util
import os

# daiso-mcp.py 처럼 하이픈이 들어간 파일명은 표준 import가 불가능하므로
# spec_from_file_location으로 직접 로드해 @register_tool 데코레이터가 실행되게 함
_mcp_dir = os.path.dirname(__file__)

for _fname in sorted(os.listdir(_mcp_dir)):
    if not _fname.endswith(".py") or _fname == "__init__.py":
        continue
    _fpath = os.path.join(_mcp_dir, _fname)
    _spec = importlib.util.spec_from_file_location(_fname[:-3], _fpath)
    _module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_module)
