import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { UserProvider } from './auth/UserContext';
import AuthRoute from './auth/AuthRoute';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Chat from './pages/Chat';

const App = () => {
  return (
    <UserProvider>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/dashboard" element={<AuthRoute><Chat /></AuthRoute>} />
        <Route path="*" element={<div>404 Not Found</div>} />
      </Routes>
    </UserProvider>
  );
};

export default App;
