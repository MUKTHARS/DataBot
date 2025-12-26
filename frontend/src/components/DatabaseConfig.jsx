import React, { useState, useEffect } from 'react';

const DatabaseConfig = ({ onConfigUpdate, initialConfig }) => {
  const [config, setConfig] = useState(initialConfig || {
    database_type: 'postgres',
    connection_url: '',
    database_name: ''
  });
  
  const [status, setStatus] = useState({
    loading: false,
    message: '',
    success: null
  });
  
  const [connectionTest, setConnectionTest] = useState({
    testing: false,
    result: null,
    message: ''
  });
  
  const [health, setHealth] = useState(null);
  const [schema, setSchema] = useState(null);

  useEffect(() => {
    loadCurrentConfig();
  }, []);
  useEffect(() => {
    if (initialConfig) {
      setConfig(initialConfig);
    }
  }, [initialConfig]);

const loadCurrentConfig = async () => {
  try {
    // First try to get the actual config from backend
    const configResponse = await fetch('http://localhost:8000/api/v1/current-db-config');
    if (configResponse.ok) {
      const configData = await configResponse.json();
      
      // Update local config state
      setConfig({
        database_type: configData.database_type,
        connection_url: configData.connection_url || '',
        database_name: ''
      });
      
      // Save to localStorage
      localStorage.setItem('dbConfig', JSON.stringify({
        database_type: configData.database_type,
        connection_url: configData.connection_url || ''
      }));
    }
    
    // Get health status
    const healthResponse = await fetch('http://localhost:8000/api/v1/status');
    if (healthResponse.ok) {
      const healthData = await healthResponse.json();
      setHealth(healthData);
    }
  } catch (error) {
    console.error('Failed to load config:', error);
  }
};

  const loadSchema = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/schema');
      if (response.ok) {
        const data = await response.json();
        setSchema(data);
      }
    } catch (error) {
      console.error('Failed to load schema:', error);
    }
  };

  const handleTestConnection = async () => {
    setConnectionTest({ testing: true, result: null, message: '' });
    
    try {
      const response = await fetch('http://localhost:8000/api/v1/test-connection', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          database_type: config.database_type,
          connection_url: config.connection_url
        })
      });
      
      const result = await response.json();
      
      setConnectionTest({
        testing: false,
        result: result.success,
        message: result.message
      });
      
    } catch (error) {
      setConnectionTest({
        testing: false,
        result: false,
        message: `Test failed: ${error.message}`
      });
    }
  };

  const handleSwitchDatabase = async () => {
    setStatus({ loading: true, message: 'Switching database...', success: null });
    
    try {
      const response = await fetch('http://localhost:8000/api/v1/switch-database', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config)
      });
      
      const result = await response.json();
      
      if (response.ok) {
        setStatus({
          loading: false,
          message: result.message,
          success: true
        });
        
        // Reload configuration
        setTimeout(() => {
          loadCurrentConfig();
          loadSchema();
          onConfigUpdate();
        }, 1000);
      } else {
        setStatus({
          loading: false,
          message: result.detail || 'Switch failed',
          success: false
        });
      }
      
    } catch (error) {
      setStatus({
        loading: false,
        message: `Error: ${error.message}`,
        success: false
      });
    }
  };

  const getExampleUrl = () => {
    switch(config.database_type) {
      case 'postgres':
        return 'postgresql://username:password@localhost:5432/database_name';
      case 'mysql':
        return 'mysql://username:password@localhost:3306/database_name';
      case 'mongodb':
        return 'mongodb://localhost:27017/database_name';
      default:
        return '';
    }
  };

  return (
    <div className="database-config">
      <div className="config-header">
        <h2>⚙️ Database Configuration</h2>
        {health && (
          <div className="current-status">
            <div className={`status-indicator ${health.database_connected ? 'connected' : 'disconnected'}`}>
              ● {health.database_connected ? 'Connected' : 'Disconnected'}
            </div>
            <div className="status-details">
              <span>Type: <strong>{health.database_type}</strong></span>
              <span>Agent: <strong>{health.agent_ready ? 'Ready' : 'Not Ready'}</strong></span>
              <span>ChatGPT: <strong>{health.chatgpt_available ? 'Available' : 'Unavailable'}</strong></span>
            </div>
          </div>
        )}
      </div>

      <div className="config-form">
        <div className="form-group">
          <label htmlFor="database_type">Database Type</label>
          <select
            id="database_type"
            value={config.database_type}
            onChange={(e) => setConfig({
              ...config, 
              database_type: e.target.value,
              connection_url: getExampleUrl()
            })}
          >
            <option value="postgres">PostgreSQL</option>
            <option value="mysql">MySQL</option>
            <option value="mongodb">MongoDB</option>
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="connection_url">Connection URL</label>
          <input
            type="text"
            id="connection_url"
            value={config.connection_url}
            onChange={(e) => setConfig({...config, connection_url: e.target.value})}
            placeholder={getExampleUrl()}
          />
          <small className="form-help">
            Format: {getExampleUrl()}
          </small>
        </div>

        <div className="form-group">
          <label htmlFor="database_name">Database Name (Optional)</label>
          <input
            type="text"
            id="database_name"
            value={config.database_name}
            onChange={(e) => setConfig({...config, database_name: e.target.value})}
            placeholder="analytics_db"
          />
        </div>

        <div className="form-actions">
          <button
            type="button"
            onClick={handleTestConnection}
            disabled={connectionTest.testing || !config.connection_url}
            className="btn-test"
          >
            {connectionTest.testing ? 'Testing...' : 'Test Connection'}
          </button>
          
          <button
            type="button"
            onClick={handleSwitchDatabase}
            disabled={status.loading || !config.connection_url}
            className="btn-switch"
          >
            {status.loading ? 'Switching...' : 'Switch Database'}
          </button>
        </div>

        {connectionTest.result !== null && (
          <div className={`test-result ${connectionTest.result ? 'success' : 'error'}`}>
            <strong>{connectionTest.result ? '✅' : '❌'}</strong>
            {connectionTest.message}
          </div>
        )}

        {status.message && (
          <div className={`switch-result ${status.success ? 'success' : 'error'}`}>
            <strong>{status.success ? '✅' : '❌'}</strong>
            {status.message}
          </div>
        )}
      </div>

      {health?.database_connected && (
        <div className="database-info">
          <div className="info-header">
            <h3>📊 Database Information</h3>
            <button onClick={loadSchema} className="btn-refresh">
              Refresh Schema
            </button>
          </div>
          
          {schema && (
            <div className="schema-info">
              {schema.tables && schema.tables.length > 0 && (
                <div className="tables-section">
                  <h4>Tables ({schema.tables.length})</h4>
                  <div className="tables-grid">
                    {schema.tables.slice(0, 10).map((table, index) => (
                      <div key={index} className="table-card">
                        <div className="table-header">
                          <strong>{table.name}</strong>
                          <span className="table-type">{table.type}</span>
                        </div>
                        <div className="table-stats">
                          {table.row_count !== undefined && (
                            <span>📊 {table.row_count.toLocaleString()} rows</span>
                          )}
                          <span>📋 {table.columns?.length || 0} columns</span>
                        </div>
                        {table.columns && (
                          <div className="table-columns">
                            {table.columns.slice(0, 5).map((col, idx) => (
                              <div key={idx} className="column-item">
                                <code>{col.name}</code>
                                <small>{col.type}</small>
                              </div>
                            ))}
                            {table.columns.length > 5 && (
                              <div className="column-more">
                                +{table.columns.length - 5} more columns
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {schema.collections && schema.collections.length > 0 && (
                <div className="collections-section">
                  <h4>Collections ({schema.collections.length})</h4>
                  <div className="collections-grid">
                    {schema.collections.slice(0, 10).map((collection, index) => (
                      <div key={index} className="collection-card">
                        <div className="collection-header">
                          <strong>{collection.name}</strong>
                        </div>
                        <div className="collection-stats">
                          <span>📄 {collection.document_count?.toLocaleString() || 0} documents</span>
                          <span>🏷️ {collection.fields?.length || 0} fields</span>
                        </div>
                        {collection.fields && (
                          <div className="collection-fields">
                            {collection.fields.slice(0, 5).map((field, idx) => (
                              <div key={idx} className="field-item">
                                <code>{field.name}</code>
                                <small>{field.type}</small>
                              </div>
                            ))}
                            {collection.fields.length > 5 && (
                              <div className="field-more">
                                +{collection.fields.length - 5} more fields
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {schema.relationships && schema.relationships.length > 0 && (
                <div className="relationships-section">
                  <h4>Relationships ({schema.relationships.length})</h4>
                  <div className="relationships-list">
                    {schema.relationships.slice(0, 10).map((rel, index) => (
                      <div key={index} className="relationship-item">
                        <code>{rel.from_table}.{rel.from_column}</code>
                        <span>→</span>
                        <code>{rel.to_table}.{rel.to_column}</code>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <div className="config-help">
        <h4>📖 Help & Examples</h4>
        <div className="help-content">
          <div className="help-section">
            <h5>PostgreSQL Examples:</h5>
            <ul>
              <li><code>postgresql://user:pass@localhost:5432/mydb</code></li>
              <li><code>postgresql://user:pass@host:5432/db?sslmode=require</code></li>
            </ul>
          </div>
          
          <div className="help-section">
            <h5>MongoDB Examples:</h5>
            <ul>
              <li><code>mongodb://localhost:27017/mydb</code></li>
              <li><code>mongodb+srv://user:pass@cluster.mongodb.net/db</code></li>
            </ul>
          </div>
          
          <div className="help-section">
            <h5>MySQL Examples:</h5>
            <ul>
              <li><code>mysql://user:pass@localhost:3306/mydb</code></li>
              <li><code>mysql+aiomysql://user:pass@host:3306/db</code></li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DatabaseConfig;