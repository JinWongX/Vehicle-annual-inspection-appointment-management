import React, { createContext, useContext, useEffect, useState } from 'react';
import request from '../utils/request';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('inspection_token');
    if (!token) {
      localStorage.removeItem('inspection_user');
      setLoading(false);
      return;
    }
    // 有 token 时向后端校验并刷新用户信息，避免信任已过期/失效的本地产物态
    request
      .get('/auth/me')
      .then((res) => {
        localStorage.setItem('inspection_user', JSON.stringify(res.data));
        setUser(res.data);
      })
      .catch(() => {
        localStorage.removeItem('inspection_token');
        localStorage.removeItem('inspection_user');
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  // 监听全局 401 登出事件（由 request 拦截器触发），同步清空登录态
  useEffect(() => {
    const onAuthExpired = () => {
      localStorage.removeItem('inspection_token');
      localStorage.removeItem('inspection_user');
      setUser(null);
    };
    window.addEventListener('auth:expired', onAuthExpired);
    return () => window.removeEventListener('auth:expired', onAuthExpired);
  }, []);

  const login = async (username, password) => {
    const form = new URLSearchParams();
    form.append('username', username);
    form.append('password', password);
    const res = await request.post('/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    const { access_token } = res.data;
    localStorage.setItem('inspection_token', access_token);
    const me = await request.get('/auth/me');
    localStorage.setItem('inspection_user', JSON.stringify(me.data));
    setUser(me.data);
    return me.data;
  };

  const registerAndLogin = async (values) => {
    await request.post('/auth/register', values);
    return login(values.username, values.password);
  };

  const logout = () => {
    localStorage.removeItem('inspection_token');
    localStorage.removeItem('inspection_user');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, registerAndLogin, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
