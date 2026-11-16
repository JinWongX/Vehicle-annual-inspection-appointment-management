# 车辆年检预约管理系统后端

车辆年检预约管理系统的 FastAPI 后端，使用 SQLite + SQLAlchemy。

## 环境要求

- Python 3.10+

## 安装依赖

在项目根目录下创建并激活虚拟环境：

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r backend\requirements.txt
```

## 初始化数据库

运行初始化脚本创建所有表，并插入默认车管所管理员账号：

```powershell
.\venv\Scripts\python.exe backend\init_db.py
```

默认管理员账号：

- 用户名：`admin`
- 密码：`admin123`
- 角色：`admin`

## 启动服务

从项目根目录启动：

```powershell
.\venv\Scripts\uvicorn.exe backend.app.main:app --reload
```

或进入 backend 目录：

```powershell
cd backend
..\venv\Scripts\uvicorn.exe app.main:app --reload
```

服务默认运行在 `http://127.0.0.1:8000`。

API 文档地址：

- Swagger UI：`http://127.0.0.1:8000/docs`
- ReDoc：`http://127.0.0.1:8000/redoc`

## 运行测试

```powershell
.\venv\Scripts\pytest.exe backend
```
