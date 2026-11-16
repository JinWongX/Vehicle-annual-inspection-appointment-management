import axios from 'axios';

const request = axios.create({
  baseURL: 'http://127.0.0.1:8000/api/v1',
  timeout: 30000,
});

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('inspection_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

request.interceptors.response.use(
  (response) => response,
  (error) => {
    // 登录/注册接口自身的 401（账号或密码错误）不应触发全局跳转，
    // 否则会整页刷新到 /login 清空表单，导致错误提示无法展示。
    const url = error.config?.url || '';
    const isAuthEndpoint = url.includes('/auth/login') || url.includes('/auth/register');
    if (error.response?.status === 401 && !isAuthEndpoint) {
      localStorage.removeItem('inspection_token');
      localStorage.removeItem('inspection_user');
      // 通知 AuthProvider 同步清空本地登录态，避免整页跳转前顶栏仍渲染旧用户
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new Event('auth:expired'));
      }
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default request;
