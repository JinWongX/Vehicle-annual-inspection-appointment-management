# 车辆年检预约管理系统 - 前端

基于 Vite + React + Ant Design 的车辆年检预约管理系统前端工程。

## 前置条件

- Node.js >= 18
- 后端服务已运行在 http://127.0.0.1:8000

## 安装依赖

```bash
cd frontend
npm install
```

## 启动开发服务器

```bash
npm run dev
```

默认端口为 5173，浏览器访问 http://localhost:5173。

## 构建生产包

```bash
npm run build
```

## 主要功能

- 车主：车辆管理、年检提醒、预约检测站、查看预约、查看检测报告
- 检测站：今日预约、到站登记、检测结果录入
- 车管所：检测站 CRUD、统计看板、数据导出

## 登录说明

- 车主通过 `/register` 注册，角色固定为 `owner`。
- 检测站/车管所账号需由后端创建（角色为 `station` 或 `admin`）。
