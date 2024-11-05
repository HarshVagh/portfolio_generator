import React, { useContext, useEffect } from 'react';
import { Navigate } from 'react-router-dom';
import { UserContext } from './UserContext';
import AxiosInstance from './AxiosInstance';

const AuthRoute = ({ children }) => {
  const { user, setUser } = useContext(UserContext);
  const token = localStorage.getItem('authToken');

  useEffect(() => {
    const fetchUser = async () => {
      if (token && !user) {
        try {
          const response = await AxiosInstance.get('/api/auth/user', {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          });
          setUser(response.data);
          
        } catch (error) {
          console.error('Failed to fetch user:', error);
          localStorage.removeItem('authToken');
        }
      }
    };
    fetchUser();
  }, [token, user, setUser]);

  return token ? children : <Navigate to="/login" />;
};

export default AuthRoute;
