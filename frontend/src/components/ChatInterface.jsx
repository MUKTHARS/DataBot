import React, { useState, useRef, useEffect } from 'react';
import { processChatQuery } from '../services/api';
import { Send, Bot, User, Database, Sparkles, TrendingUp, Clock, ChevronRight, Copy, Check } from 'lucide-react';
import ChartRenderer from './ChartRenderer';
const ChatInterface = ({ onDatabaseUpdate, currentDbConfig }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [copiedQueryId, setCopiedQueryId] = useState(null);
  const messagesEndRef = useRef(null);

  // Load session and messages
  useEffect(() => {
    const savedSessionId = localStorage.getItem('chatSessionId') || `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const savedMessages = localStorage.getItem('chatMessages');
    
    setSessionId(savedSessionId);
    localStorage.setItem('chatSessionId', savedSessionId);
    
    if (savedMessages) {
      try {
        setMessages(JSON.parse(savedMessages));
      } catch (e) {
        console.error('Failed to load saved messages:', e);
      }
    }
    
    loadSuggestions();
  }, []);

  // Save messages
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem('chatMessages', JSON.stringify(messages));
    }
  }, [messages]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadSuggestions = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/suggest-queries', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context: 'general' })
      });
      if (response.ok) {
        const data = await response.json();
        setSuggestions(data.suggestions || []);
      }
    } catch (error) {
      console.error('Failed to load suggestions:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;
    
    const userMessage = input.trim();
    setInput('');
    
    // Add user message
    setMessages(prev => [...prev, {
      id: Date.now(),
      type: 'user',
      content: userMessage,
      timestamp: new Date().toISOString()
    }]);
    
    setLoading(true);
    
    try {
      const response = await processChatQuery(userMessage, sessionId);
      // const response = await processChatQuery(userMessage, sessionId);

// Debug logging
console.log('Full API Response:', response);
console.log('Has chart property?', 'chart' in response);
console.log('Chart data:', response.chart);
console.log('Chart type:', response.chart?.type);
console.log('Chart labels:', response.chart?.labels);
console.log('Chart datasets:', response.chart?.datasets);
      // Add assistant response
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        type: 'assistant',
        content: response.response,
        data: response.data,
        insights: response.insights,
        suggestions: response.suggestions,
        queryUsed: response.query_used,
        chart: response.chart, 
        timestamp: new Date().toISOString()
      }]);
    } catch (error) {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        type: 'error',
        content: `Error: ${error.message}`,
        timestamp: new Date().toISOString()
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleSuggestionClick = (suggestion) => {
    setInput(suggestion);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedQueryId(id);
    setTimeout(() => setCopiedQueryId(null), 2000);
  };

  const clearChat = () => {
    setMessages([]);
    localStorage.removeItem('chatMessages');
  };

  const formatData = (data) => {
    if (!data || !Array.isArray(data) || data.length === 0) {
      return <div className="no-data">No data returned</div>;
    }
    
    const headers = Object.keys(data[0] || {});
    
    return (
      <div className="data-table-container">
        <div className="table-header">
          <span className="result-count">{data.length} results</span>
        </div>
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                {headers.map((header, index) => (
                  <th key={index} className="sticky-header">
                    {header}
                    <span className="column-type">text</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.slice(0, 20).map((row, rowIndex) => (
                <tr key={rowIndex} className={rowIndex % 2 === 0 ? 'even' : 'odd'}>
                  {headers.map((header, colIndex) => (
                    <td key={colIndex}>
                      <div className="cell-content">
                        {String(row[header] || '').substring(0, 100)}
                        {String(row[header] || '').length > 100 && '...'}
                      </div>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {data.length > 20 && (
          <div className="table-footer">
            Showing 20 of {data.length} rows
          </div>
        )}
      </div>
    );
  };

  const ChatHistorySidebar = () => (
    <div className={`chat-history-sidebar ${sidebarCollapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        <button className="collapse-btn" onClick={() => setSidebarCollapsed(!sidebarCollapsed)}>
          <ChevronRight className={`icon ${sidebarCollapsed ? 'rotated' : ''}`} />
        </button>
        {!sidebarCollapsed && (
          <>
            <h3>Chat History</h3>
            <button className="clear-btn" onClick={clearChat}>Clear</button>
          </>
        )}
      </div>
      
      {!sidebarCollapsed && (
        <div className="history-list">
          {messages.length === 0 ? (
            <div className="empty-history">
              <Clock size={24} />
              <p>No chat history</p>
            </div>
          ) : (
            messages
              .filter(msg => msg.type === 'user')
              .slice(-10)
              .reverse()
              .map((message, index) => (
                <div key={index} className="history-item" onClick={() => setInput(message.content)}>
                  <User size={14} />
                  <span className="history-text">{message.content.substring(0, 50)}...</span>
                </div>
              ))
          )}
        </div>
      )}
    </div>
  );

  return (
    <div className="chat-interface-pro">
      <ChatHistorySidebar />
      
      <div className="chat-main">
        <header className="chat-header">
          <div className="header-left">
            <div className="logo">
              <Bot size={28} className="bot-icon" />
              <div className="logo-text">
                <h1>Saple AI</h1>
                <span className="subtitle">Intelligent Database Analytics</span>
              </div>
            </div>
          </div>
          
          <div className="header-right">
            <div className="connection-status">
              <Database size={16} />
              <span className="status-text">
                {currentDbConfig?.database_type || 'mongodb'} • Connected
              </span>
            </div>
          </div>
        </header>

        <div className="chat-messages-container">
          {messages.length === 0 ? (
            <div className="welcome-screen">
              <div className="welcome-content">
                <div className="welcome-icon">
                  <Sparkles size={48} />
                </div>
                <h2>Welcome to Saple AI</h2>
                <p>Ask questions about your database in natural language</p>
                
                <div className="suggestions-grid">
                  {suggestions.slice(0, 6).map((suggestion, index) => (
                    <button
                      key={index}
                      className="suggestion-card"
                      onClick={() => handleSuggestionClick(suggestion)}
                    >
                      <TrendingUp size={16} />
                      <span>{suggestion}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="messages-list">
              {messages.map((message) => (
                <div key={message.id} className={`message-wrapper ${message.type}`}>
                  <div className="message-avatar">
                    {message.type === 'user' ? (
                      <div className="avatar user-avatar">
                        <User size={16} />
                      </div>
                    ) : message.type === 'assistant' ? (
                      <div className="avatar bot-avatar">
                        <Bot size={16} />
                      </div>
                    ) : (
                      <div className="avatar error-avatar">!</div>
                    )}
                  </div>
                  
                  <div className="message-content">
                    <div className="message-header">
                      <span className="sender">
                        {message.type === 'user' ? 'You' : 
                         message.type === 'assistant' ? 'Saple AI' : 'Error'}
                      </span>
                      <span className="timestamp">
                        {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    
                    <div className="message-body">
                      {message.content}
                    </div>
                    
                    {message.type === 'assistant' && message.queryUsed && (
                      <div className="query-section">
                        <div className="query-header">
                          <span className="query-label">Generated Query</span>
                          <button 
                            className="copy-btn"
                            onClick={() => copyToClipboard(message.queryUsed, message.id)}
                          >
                            {copiedQueryId === message.id ? <Check size={14} /> : <Copy size={14} />}
                            Copy
                          </button>
                        </div>
                        <pre className="query-code">
                          <code>{message.queryUsed}</code>
                        </pre>
                      </div>
                    )}
                    

                    {message.type === 'assistant' && message.chart && (
  <div className="chart-section">
    <div className="chart-section-header">
      <h4 className="chart-title">
        <TrendingUp size={16} />
        Data Visualization
      </h4>
    </div>
    <ChartRenderer chartConfig={message.chart} data={message.data} />
  </div>
)}

                    {message.type === 'assistant' && message.data && (
                      <div className="data-section">
                        <details>
                          <summary className="data-summary">
                            View Results ({Array.isArray(message.data) ? `${message.data.length} rows` : 'Object'})
                          </summary>
                          {formatData(message.data)}
                        </details>
                      </div>
                    )}
                    
                    {message.type === 'assistant' && message.insights && message.insights.length > 0 && (
                      <div className="insights-section">
                        <h4 className="insights-title">
                          <Sparkles size={16} />
                          Insights
                        </h4>
                        <ul className="insights-list">
                          {message.insights.slice(0, 3).map((insight, index) => (
                            <li key={index}>{insight}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    
                    {message.type === 'assistant' && message.suggestions && message.suggestions.length > 0 && (
                      <div className="followup-section">
                        <h4 className="followup-title">Follow-up Questions</h4>
                        <div className="followup-chips">
                          {message.suggestions.slice(0, 3).map((suggestion, index) => (
                            <button
                              key={index}
                              className="followup-chip"
                              onClick={() => handleSuggestionClick(suggestion)}
                            >
                              {suggestion}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              
              {loading && (
                <div className="message-wrapper assistant loading">
                  <div className="message-avatar">
                    <div className="avatar bot-avatar">
                      <Bot size={16} />
                    </div>
                  </div>
                  <div className="message-content">
                    <div className="message-header">
                      <span className="sender">Saple AI</span>
                    </div>
                    <div className="typing-indicator">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit} className="chat-input-area">
          <div className="input-container">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your data..."
              disabled={loading}
              rows={1}
              className="chat-input"
            />
            <button 
              type="submit" 
              disabled={!input.trim() || loading}
              className="send-button"
            >
              <Send size={20} />
            </button>
          </div>
          <div className="input-hint">
            Press Enter to send • Shift+Enter for new line
          </div>
        </form>
      </div>
    </div>
  );
};

export default ChatInterface;