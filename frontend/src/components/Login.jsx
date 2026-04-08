import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, useLocation } from 'react-router-dom';
import { Lock, User } from 'lucide-react';

const Login = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const { login } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        try {
            const loggedInUser = await login(username, password);
            
            let redirectUrl = '/';
            
            const routerFrom = location.state?.from;
            const routerStateUrl = routerFrom ? routerFrom.pathname + (routerFrom.search || '') : null;
            
            const storedContextStr = localStorage.getItem('redirect_context');
            if (storedContextStr) {
                try {
                    const storedContext = JSON.parse(storedContextStr);
                    if (storedContext.username === loggedInUser.username) {
                        redirectUrl = storedContext.url;
                    }
                } catch (err) {
                    console.error("Invalid redirect context");
                }
                localStorage.removeItem('redirect_context');
            } else if (routerStateUrl) {
                redirectUrl = routerStateUrl;
            }

            navigate(redirectUrl, { replace: true });
        } catch (err) {
            setError('Invalid credentials');
        }
    };

    return (
        <div className="flex items-center justify-center min-h-screen bg-gray-900 text-white">
            <div className="w-full max-w-md p-8 bg-gray-800 rounded-lg shadow-lg">
                <h2 className="text-3xl font-bold text-center mb-8 text-green-400">Juicy Fruit Portal</h2>
                {error && <div className="p-3 mb-4 bg-red-900/50 text-red-200 rounded">{error}</div>}
                <form onSubmit={handleSubmit} className="space-y-6">
                    <div>
                        <label className="block text-sm font-medium mb-1">Username</label>
                        <div className="relative">
                            <User className="absolute left-3 top-2.5 h-5 w-5 text-gray-400" />
                            <input
                                type="text"
                                className="w-full pl-10 pr-4 py-2 bg-gray-700 rounded focus:outline-none focus:ring-2 focus:ring-green-500"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                            />
                        </div>
                    </div>
                    <div>
                        <label className="block text-sm font-medium mb-1">Password</label>
                        <div className="relative">
                            <Lock className="absolute left-3 top-2.5 h-5 w-5 text-gray-400" />
                            <input
                                type="password"
                                className="w-full pl-10 pr-4 py-2 bg-gray-700 rounded focus:outline-none focus:ring-2 focus:ring-green-500"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                            />
                        </div>
                    </div>
                    <button
                        type="submit"
                        className="w-full py-2 bg-green-600 hover:bg-green-700 rounded font-bold transition-colors"
                    >
                        Login
                    </button>
                </form>
            </div>
        </div>
    );
};

export default Login;
