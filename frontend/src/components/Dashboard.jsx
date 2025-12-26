import React, { useState, useEffect } from 'react';
import ChatInterface from './ChatInterface';
import DatabaseConfig from './DatabaseConfig';
import { Bot, Database, Cpu, Zap, BarChart3, Settings, MessageSquare, Shield } from 'lucide-react';

const Dashboard = ({ activeTab, onTabChange }) => {
  const [health, setHealth] = useState(null);
  const [stats, setStats] = useState(null);
  const [currentDbConfig, setCurrentDbConfig] = useState(() => {
    const savedConfig = localStorage.getItem('dbConfig');
    return savedConfig ? JSON.parse(savedConfig) : null;
  });

  useEffect(() => {
    loadHealthStatus();
    loadStats();
    
    const interval = setInterval(() => {
      loadHealthStatus();
    }, 30000);
    
    return () => clearInterval(interval);
  }, []);

  const loadHealthStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/health');
      if (response.ok) {
        const data = await response.json();
        setHealth(data);
      }
    } catch (error) {
      console.error('Health check failed:', error);
    }
  };

  const loadStats = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/status');
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      // Stats endpoint might not exist
    }
  };

  const handleConfigUpdate = (config) => {
    if (config) {
      localStorage.setItem('dbConfig', JSON.stringify(config));
      setCurrentDbConfig(config);
    }
    loadHealthStatus();
    loadStats();
  };

  const Sidebar = () => (
    <div className="dashboard-sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <Bot size={32} className="logo-icon" />
          <div className="logo-text">
            <h2>Saple AI</h2>
            <span className="version">v2.0</span>
          </div>
        </div>
      </div>
      
      <nav className="sidebar-nav">
        <button
          className={`nav-item ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => onTabChange('chat')}
        >
          <MessageSquare size={20} />
          <span>Chat Interface</span>
        </button>
        
        <button
          className={`nav-item ${activeTab === 'config' ? 'active' : ''}`}
          onClick={() => onTabChange('config')}
        >
          <Settings size={20} />
          <span>Database Config</span>
        </button>
        
        <button
          className={`nav-item ${activeTab === 'analytics' ? 'active' : ''}`}
          onClick={() => onTabChange('analytics')}
        >
          <BarChart3 size={20} />
          <span>Analytics</span>
        </button>
      </nav>
      
      <div className="sidebar-footer">
        <div className="connection-status">
          <div className={`status-dot ${health?.status === 'healthy' ? 'online' : 'offline'}`} />
          <span>{health?.status || 'Unknown'}</span>
        </div>
        <div className="database-info">
          <Database size={14} />
          <span>{health?.database_type || 'Not connected'}</span>
        </div>
      </div>
    </div>
  );

  return (
    <div className="dashboard-pro">
      <Sidebar />
      
      <main className="dashboard-main">
        <header className="main-header">
          <div className="header-title">
            <h1>
              {activeTab === 'chat' && 'Chat Interface'}
              {activeTab === 'config' && 'Database Configuration'}
              {activeTab === 'analytics' && 'System Analytics'}
            </h1>
            <p className="header-subtitle">
              {activeTab === 'chat' && 'Ask questions about your data in natural language'}
              {activeTab === 'config' && 'Configure and manage database connections'}
              {activeTab === 'analytics' && 'Monitor system performance and statistics'}
            </p>
          </div>
          
          <div className="header-stats">
            <div className="stat-card">
              <div className="stat-icon">
                <Zap size={18} />
              </div>
              <div className="stat-content">
                <div className="stat-value">{stats?.active_sessions || 0}</div>
                <div className="stat-label">Active Sessions</div>
              </div>
            </div>
            
            <div className="stat-card">
              <div className="stat-icon">
                <Cpu size={18} />
              </div>
              <div className="stat-content">
                <div className="stat-value">{stats?.queries_processed || 0}</div>
                <div className="stat-label">Queries</div>
              </div>
            </div>
            
            <div className="stat-card">
              <div className="stat-icon">
                <Shield size={18} />
              </div>
              <div className="stat-content">
                <div className="stat-value">100%</div>
                <div className="stat-label">Secure</div>
              </div>
            </div>
          </div>
        </header>

        <div className="main-content">
          {activeTab === 'chat' && (
            <ChatInterface 
              onDatabaseUpdate={handleConfigUpdate}
              currentDbConfig={currentDbConfig}
            />
          )}
          
          {activeTab === 'config' && (
            <DatabaseConfig 
              onConfigUpdate={handleConfigUpdate}
              initialConfig={currentDbConfig}
            />
          )}
          
          {activeTab === 'analytics' && (
            <div className="analytics-dashboard">
              <div className="analytics-grid">
                <div className="analytics-card">
                  <h3>Performance Metrics</h3>
                  <div className="metric-grid">
                    <div className="metric-item">
                      <div className="metric-value">{stats?.avg_response_time ? `${stats.avg_response_time.toFixed(2)}s` : 'N/A'}</div>
                      <div className="metric-label">Avg Response Time</div>
                    </div>
                    <div className="metric-item">
                      <div className="metric-value">{stats?.cache_hits || 0}</div>
                      <div className="metric-label">Cache Hits</div>
                    </div>
                    <div className="metric-item">
                      <div className="metric-value">{stats?.errors || 0}</div>
                      <div className="metric-label">Errors</div>
                    </div>
                  </div>
                </div>
                
                <div className="analytics-card">
                  <h3>Database Health</h3>
                  <div className="health-status">
                    <div className={`health-indicator ${health?.status === 'healthy' ? 'healthy' : 'unhealthy'}`}>
                      {health?.status === 'healthy' ? '✅ Healthy' : '❌ Unhealthy'}
                    </div>
                    <div className="health-details">
                      <div className="detail-item">
                        <span>Type:</span>
                        <strong>{health?.database_type || 'Unknown'}</strong>
                      </div>
                      <div className="detail-item">
                        <span>Agent:</span>
                        <strong>{health?.agent ? 'Active' : 'Inactive'}</strong>
                      </div>
                      <div className="detail-item">
                        <span>Connected:</span>
                        <strong>{health?.database ? 'Yes' : 'No'}</strong>
                      </div>
                    </div>
                  </div>
                </div>
                
                <div className="analytics-card full-width">
                  <h3>Query Statistics</h3>
                  <div className="query-stats">
                    <div className="stat-bar">
                      <div className="stat-label">Processed Queries</div>
                      <div className="stat-value">{stats?.queries_processed || 0}</div>
                    </div>
                    <div className="stat-bar">
                      <div className="stat-label">Successful</div>
                      <div className="stat-value">{stats?.queries_processed - (stats?.errors || 0) || 0}</div>
                    </div>
                    <div className="stat-bar">
                      <div className="stat-label">Cache Efficiency</div>
                      <div className="stat-value">
                        {stats?.queries_processed ? 
                          `${Math.round(((stats?.cache_hits || 0) / stats.queries_processed) * 100)}%` : '0%'}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="analytics-tips">
                <h3>Best Practices</h3>
                <div className="tips-grid">
                  <div className="tip-card">
                    <h4>📊 Data Analysis</h4>
                    <ul>
                      <li>Use specific date ranges</li>
                      <li>Compare metrics over time</li>
                      <li>Ask for trends and patterns</li>
                    </ul>
                  </div>
                  <div className="tip-card">
                    <h4>🔍 Query Optimization</h4>
                    <ul>
                      <li>Be specific in your questions</li>
                      <li>Use natural language</li>
                      <li>Ask follow-up questions</li>
                    </ul>
                  </div>
                  <div className="tip-card">
                    <h4>⚡ Performance</h4>
                    <ul>
                      <li>Start with broad questions</li>
                      <li>Drill down with specifics</li>
                      <li>Use the suggestions</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
        
        <footer className="main-footer">
          <div className="footer-content">
            <span>© 2024 Saple AI • Powered by OpenAI & FastAPI</span>
            <span className="footer-links">
              <a href="#" target="_blank" rel="noopener noreferrer">Documentation</a>
              <span>•</span>
              <a href="#" target="_blank" rel="noopener noreferrer">API Reference</a>
              <span>•</span>
              <a href="#" target="_blank" rel="noopener noreferrer">Support</a>
            </span>
          </div>
        </footer>
      </main>
    </div>
  );
};

export default Dashboard;