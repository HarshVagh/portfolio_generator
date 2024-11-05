import axios from 'axios';

const apiUrl = process.env.REACT_APP_API_URL;

console.log("API URL:", apiUrl);

const AxiosInstance = axios.create({
  baseURL: apiUrl,
});

AxiosInstance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export default AxiosInstance;