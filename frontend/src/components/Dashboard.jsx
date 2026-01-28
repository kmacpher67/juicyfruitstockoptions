import React, { useState, useEffect } from 'react';
import api from '../api/axios';
import { useAuth } from '../context/AuthContext';
import { RefreshCw, TrendingUp, TrendingDown, LogOut } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const Dashboard = () => {
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(false);
    const { logout, user } = useAuth();
    const navigate = useNavigate();

    const fetchData = async () => {
        setLoading(true);
        try {
            // In a real app, we might want to separate "Fetching" from "Triggering Run"
            // For now, we call the run endpoint which returns the fresh data
            // However, the backend currently returns {"status": "success", "file": ...} not the actual data list
            // We need to update the backend to return data, OR we need a new endpoint.
            // For now, let's assume we implement a GET /api/stocks endpoint in the backend.
            // But since I didn't implement that yet, I'll update this component to just show the status for now
            // or I can quickly add a GET endpoint in the backend. 
            // Let's stick to the plan: Phase 2 includes "Grid: Display stock data". 
            // The current backend doesn't serve the JSON data yet via GET.
            // I will implement a temporary fix: The run endpoint creates a JSON file. 
            // I should probably add a GET endpoint to the backend to read that JSON.

            // For now, let's try to hit the run endpoint and see if we can get data.
            // Actually, I'll add a 'refresh' button to trigger run.
            const response = await api.post('/run/stock-live-comparison');
            console.log(response.data);
            // TODO: We need a way to GET the data.
            // For the demo, I'll mock some data or handle this in the next step.
            alert("Report Generated: " + response.data.file);
        } catch (error) {
            console.error(error);
            alert("Failed to fetch data");
        } finally {
            setLoading(false);
        }
    };

    const handleLogout = () => {
        logout();
        navigate('/login');
    }

    return (
        <div className="min-h-screen bg-gray-900 text-white p-6">
            <header className="flex justify-between items-center mb-8">
                <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-green-400 to-blue-500">
                    Juicy Fruit Dashboard
                </h1>
                <div className="flex items-center gap-4">
                    <span className="text-gray-400">Welcome, {user?.username}</span>
                    <button onClick={handleLogout} className="p-2 hover:bg-gray-800 rounded">
                        <LogOut className="h-5 w-5 text-red-400" />
                    </button>
                </div>
            </header>

            <div className="mb-6 flex gap-4">
                <button
                    onClick={fetchData}
                    disabled={loading}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded disabled:opacity-50"
                >
                    <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                    {loading ? 'Running Analysis...' : 'Run Live Comparison'}
                </button>
            </div>

            <div className="bg-gray-800 rounded-lg p-6 shadow-lg">
                <div className="text-center text-gray-400 py-12">
                    <p>Metrics Dashboard coming soon...</p>
                    <p className="text-sm mt-2">Check 'report-results' folder for the generated Excel file.</p>
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
