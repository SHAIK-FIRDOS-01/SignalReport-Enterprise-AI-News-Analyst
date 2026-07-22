import React, { useState, useEffect } from 'react';
import { 
  Newspaper, 
  Search, 
  ExternalLink, 
  AlertTriangle,
  RefreshCw,
  Sparkles,
  MessageCircle,
  Send,
  ShieldCheck,
  BookMarked,
  LogOut,
  ChevronRight,
  X,
  CheckSquare,
  Square,
  Bell
} from 'lucide-react';
import { useNewsWebsocket } from './hooks/useNewsWebsocket';

const API_BASE = 'http://localhost:8000';

interface ArticleNode {
  id: number;
  title: string;
  category: string;
  geography: string;
  content_raw: string;
  full_text_scraped: string | null;
  content_processed: string | null;
  embedding_status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  source_credibility_score: number;
  published_at: string | null;
  source_url: string;
  image_url: string | null;
  sentiment_score?: number;
  entities?: string[];
}

interface GlossaryItem {
  word: string;
  definition: string;
  context?: string;
}

function App() {
  // Auth State
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [userProfile, setUserProfile] = useState<any>(null);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  
  // Auth Inputs
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [authError, setAuthError] = useState('');
  const [authLoading, setAuthLoading] = useState(false);


  // Dashboard state
  const [nodes, setNodes] = useState<ArticleNode[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isIngesting, setIsIngesting] = useState(false);

  // Detail Drawer state
  const [selectedNode, setSelectedNode] = useState<ArticleNode | null>(null);
  const [drawerTab, setDrawerTab] = useState<'analysis' | 'chat' | 'glossary'>('analysis');
  
  // Pipeline processing animation
  const [pipelineStep, setPipelineStep] = useState<number>(-1);
  const [pipelineLoading, setPipelineLoading] = useState(false);

  // Q&A chat state
  const [chatQuestion, setChatQuestion] = useState('');
  const [chatHistory, setChatHistory] = useState<{q: string, a: string}[]>([]);
  const [chatLoading, setChatLoading] = useState(false);

  // In-drawer glossary definitions
  const [drawerGlossary, setDrawerGlossary] = useState<GlossaryItem[]>([]);

  // Multi-Article Synthesis Briefing
  const [selectedNodeIds, setSelectedNodeIds] = useState<number[]>([]);
  const [briefingMarkdown, setBriefingMarkdown] = useState<string | null>(null);
  const [briefingLoading, setBriefingLoading] = useState(false);

  // Websocket Alert
  const { alert: wsAlert } = useNewsWebsocket();

  // Helper fetch method
  const fetchWithAuth = async (endpoint: string, options: RequestInit = {}) => {
    const headers = new Headers(options.headers || {});
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
    const response = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
    if (response.status === 401) {
      handleLogout();
      throw new Error('Unauthorized session. Please log in again.');
    }
    return response;
  };

  // Auth Action Handlers
  const handleAuthSuccess = (newToken: string, user: any) => {
    localStorage.setItem('token', newToken);
    setToken(newToken);
    setUserProfile(user);
    setAuthError('');
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUserProfile(null);
    setNodes([]);
    setSelectedNode(null);
    setAuthMode('login');
    setEmail('');
    setPassword('');
    setFirstName('');
    setAuthError('');
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError('');
    try {
      const res = await fetch(`${API_BASE}/auth/login/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      const data = await res.json();
      if (data.status === 'success') {
        handleAuthSuccess(data.token, data.user);
      } else {
        setAuthError(data.message || 'Authentication failed. Please verify credentials.');
      }
    } catch (err) {
      setAuthError('Connection failed. Please check that backend server is active.');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError('');
    try {
      const res = await fetch(`${API_BASE}/auth/register/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, first_name: firstName })
      });
      const data = await res.json();
      if (data.status === 'success') {
        handleAuthSuccess(data.token, data.user);
      } else {
        setAuthError(data.message || 'Registration failed. Please check information.');
      }
    } catch (err) {
      setAuthError('Connection failed. Please check that backend server is active.');
    } finally {
      setAuthLoading(false);
    }
  };

  // Fetch Dashboard Nodes
  const fetchNodes = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.append('category', selectedCategory);
      
      const res = await fetchWithAuth(`/?${params.toString()}`);
      const data = await res.json();
      setNodes(data.nodes || []);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch dashboard intelligence feed.');
    } finally {
      setIsLoading(false);
    }
  };

  // Ingest Trigger
  const triggerIngestion = async () => {
    setIsIngesting(true);
    try {
      const res = await fetchWithAuth('/ingest/', { method: 'POST' });
      const data = await res.json();
      if (data.status === 'success') {
        setTimeout(() => {
          fetchNodes();
          setIsIngesting(false);
        }, 1500);
      } else {
        setIsIngesting(false);
      }
    } catch (err) {
      setIsIngesting(false);
    }
  };

  // Run AI Enrichment pipeline
  const runAIPipeline = async (nodeId: number) => {
    setPipelineLoading(true);
    setPipelineStep(0);
    
    const timer1 = setTimeout(() => setPipelineStep(1), 1200);
    const timer2 = setTimeout(() => setPipelineStep(2), 2400);
    const timer3 = setTimeout(() => setPipelineStep(3), 4000);

    try {
      const res = await fetchWithAuth(`/summarize/${nodeId}/`, { method: 'POST' });
      const data = await res.json();
      
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      setPipelineStep(4);
      
      if (data.status === 'success' && data.node) {
        const nodesRes = await fetchWithAuth(`/?category=${selectedCategory}`);
        const nodesData = await nodesRes.json();
        const updatedNodes = nodesData.nodes || [];
        setNodes(updatedNodes);
        
        const freshSelected = updatedNodes.find((n: ArticleNode) => n.id === nodeId);
        if (freshSelected) {
          setSelectedNode(freshSelected);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setTimeout(() => {
        setPipelineLoading(false);
        setPipelineStep(-1);
      }, 800);
    }
  };

  // Contextual Q&A Chat
  const handleAskQuestion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatQuestion.trim() || !selectedNode) return;

    const query = chatQuestion;
    setChatQuestion('');
    setChatLoading(true);

    try {
      const res = await fetchWithAuth('/ask/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: query, node_id: selectedNode.id })
      });
      const data = await res.json();
      setChatHistory(prev => [...prev, { q: query, a: data.answer || 'Answer not generated.' }]);
    } catch (err) {
      setChatHistory(prev => [...prev, { q: query, a: 'Backend failed to respond to the prompt.' }]);
    } finally {
      setChatLoading(false);
    }
  };

  // Double Click Glossary trigger
  const handleSummaryTextSelection = async () => {
    const selection = window.getSelection();
    if (!selection) return;
    const selectedText = selection.toString().trim();
    if (selectedText.length < 2 || selectedText.length > 50 || !selectedNode) return;

    try {
      const res = await fetchWithAuth('/glossary/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ term: selectedText, node_id: selectedNode.id })
      });
      const data = await res.json();
      if (data.status === 'success' && data.definition) {
        setDrawerTab('glossary');
        if (!drawerGlossary.some(item => item.word.toLowerCase() === selectedText.toLowerCase())) {
          const newGlossaryItem: GlossaryItem = { word: selectedText, definition: data.definition, context: selectedNode.title };
          setDrawerGlossary(prev => [newGlossaryItem, ...prev]);
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Multi-article briefing synthesis trigger
  const handleGenerateBriefing = async () => {
    if (selectedNodeIds.length === 0) return;
    setBriefingLoading(true);
    setBriefingMarkdown(null);
    try {
      const res = await fetchWithAuth('/briefings/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ node_ids: selectedNodeIds })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setBriefingMarkdown(data.briefing);
      } else {
        alert(data.message || 'Briefing synthesis failed.');
      }
    } catch (err) {
      alert('Network request failed for multi-article synthesis briefing.');
    } finally {
      setBriefingLoading(false);
    }
  };

  // Toggle single node selected ID
  const toggleNodeSelection = (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    setSelectedNodeIds(prev => 
      prev.includes(id) ? prev.filter(nid => nid !== id) : [...prev, id]
    );
  };

  // Profile and Initial Data Fetch on load
  useEffect(() => {
    if (token) {
      fetchNodes();
      fetchWithAuth('/auth/me/')
        .then(res => res.json())
        .then(data => {
          if (data.status === 'success') setUserProfile(data.user);
        })
        .catch(console.error);
    }
  }, [token, selectedCategory]);

  // Auto-refresh feed periodically
  useEffect(() => {
    if (!token) return;

    const interval = setInterval(() => {
      const fetchNodesSilently = async () => {
        try {
          const params = new URLSearchParams();
          params.append('category', selectedCategory);
          const res = await fetchWithAuth(`/?${params.toString()}`);
          const data = await res.json();
          const updatedNodes = data.nodes || [];
          setNodes(updatedNodes);
          
          if (selectedNode) {
            const freshSelected = updatedNodes.find((n: ArticleNode) => n.id === selectedNode.id);
            if (freshSelected && (
              freshSelected.embedding_status !== selectedNode.embedding_status ||
              freshSelected.content_processed !== selectedNode.content_processed ||
              freshSelected.full_text_scraped !== selectedNode.full_text_scraped
            )) {
              setSelectedNode(freshSelected);
            }
          }
        } catch (err) {
          console.error('Silent auto-refresh failed:', err);
        }
      };
      fetchNodesSilently();
    }, 12000);

    return () => clearInterval(interval);
  }, [token, selectedCategory, selectedNode]);

  // Handle drawer selection reset
  useEffect(() => {
    if (selectedNode) {
      setChatHistory([]);
      setDrawerGlossary([]);
      setDrawerTab('analysis');
      
      if (selectedNode.embedding_status === 'PENDING' && !pipelineLoading) {
        runAIPipeline(selectedNode.id);
      }
    }
  }, [selectedNode]);

  // Helper date formatter
  const formatDate = (isoStr: string | null) => {
    if (!isoStr) return 'Unknown Date';
    try {
      const date = new Date(isoStr);
      return date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (e) {
      return isoStr;
    }
  };

  // Local card filtering on query
  const filteredNodes = nodes.filter(node => {
    const q = searchQuery.toLowerCase();
    return (
      node.title.toLowerCase().includes(q) ||
      (node.content_processed && node.content_processed.toLowerCase().includes(q)) ||
      node.content_raw.toLowerCase().includes(q)
    );
  });

  if (!token) {
    // Render Authentication UI
    return (
      <div className="auth-page">
        <div className="auth-brand">
          <div className="auth-brand-logo">
            <Newspaper size={18} />
          </div>
          <div className="auth-brand-text">SignalReport</div>
        </div>

        <div className="auth-card">
          <div className="auth-header">
            <h2>{authMode === 'login' ? 'Clearance Access' : 'Register Access Node'}</h2>
            <p>{authMode === 'login' ? 'Provide security credentials to enter.' : 'Establish a new analyst profile.'}</p>
          </div>

          {authError && <div className="auth-error">{authError}</div>}

          {authMode === 'login' ? (
            <form onSubmit={handleLoginSubmit} className="auth-form">
              <div className="form-group">
                <label>Email Address</label>
                <input 
                  type="email" 
                  required 
                  className="auth-input" 
                  value={email}
                  onChange={e => setEmail(e.target.value)} 
                  placeholder="analyst@signalreport.ai"
                />
              </div>
              <div className="form-group">
                <label>Clearance Key (Password)</label>
                <input 
                  type="password" 
                  required 
                  className="auth-input" 
                  value={password}
                  onChange={e => setPassword(e.target.value)} 
                  placeholder="••••••••"
                />
              </div>
              <button type="submit" disabled={authLoading} className="auth-submit-btn">
                {authLoading ? <RefreshCw size={16} className="animate-spin" /> : 'Enter Platform'}
              </button>
            </form>
          ) : (
            <form onSubmit={handleRegisterSubmit} className="auth-form">
              <div className="form-group">
                <label>First Name</label>
                <input 
                  type="text" 
                  required 
                  className="auth-input" 
                  value={firstName}
                  onChange={e => setFirstName(e.target.value)} 
                  placeholder="John"
                />
              </div>
              <div className="form-group">
                <label>Email Address</label>
                <input 
                  type="email" 
                  required 
                  className="auth-input" 
                  value={email}
                  onChange={e => setEmail(e.target.value)} 
                  placeholder="analyst@signalreport.ai"
                />
              </div>
              <div className="form-group">
                <label>Create Clearance Key</label>
                <input 
                  type="password" 
                  required 
                  className="auth-input" 
                  value={password}
                  onChange={e => setPassword(e.target.value)} 
                  placeholder="Minimum 8 characters"
                />
              </div>
              <button type="submit" disabled={authLoading} className="auth-submit-btn">
                {authLoading ? <RefreshCw size={16} className="animate-spin" /> : 'Create Account'}
              </button>
            </form>
          )}

          <div className="auth-footer">
            {authMode === 'login' ? (
              <span>Need access clearance? <button className="auth-link" onClick={() => setAuthMode('register')}>Request Registration</button></span>
            ) : (
              <span>Already registered? <button className="auth-link" onClick={() => setAuthMode('login')}>Sign In</button></span>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      {/* WS Alert Toast */}
      {wsAlert && (
        <div style={{
          position: 'fixed',
          bottom: '20px',
          right: '20px',
          backgroundColor: '#3b82f6',
          color: 'white',
          padding: '16px',
          borderRadius: '8px',
          boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          zIndex: 50,
          animation: 'bounce 1s infinite'
        }}>
          <Bell size={24} />
          <div>
            <p style={{ fontWeight: 'bold', margin: 0 }}>Real-time Alert</p>
            <p style={{ fontSize: '14px', margin: 0 }}>{wsAlert.message}</p>
          </div>
        </div>
      )}

      {/* Main Content Pane */}
      <div className="content-area">
        <header className="top-bar">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div className="sidebar-logo" style={{ width: '36px', height: '36px', boxShadow: 'none' }}>
              <Newspaper size={18} />
            </div>
            <div className="sidebar-brand">
              <h1 style={{ fontSize: '19px' }}>SignalReport</h1>
              <p style={{ fontSize: '11px' }}>Intelligence Center</p>
            </div>
          </div>
          <div className="top-bar-actions">
            {userProfile && (
              <div className="user-profile" style={{ marginRight: '10px' }}>
                <div className="user-avatar" style={{ width: '34px', height: '34px', fontSize: '14px' }}>
                  {userProfile.first_name ? userProfile.first_name[0].toUpperCase() : 'A'}
                </div>
                <div className="user-details">
                  <span className="user-name" style={{ fontSize: '14px' }}>{userProfile.first_name || 'AI Analyst'}</span>
                </div>
              </div>
            )}
            <button className="logout-btn" onClick={handleLogout} style={{ width: 'auto', padding: '8px 16px' }}>
              <LogOut size={13} />
              Exit Platform
            </button>
          </div>
        </header>

        <main className="main-inner">
          {/* Filter and Ingest actions bar */}
          <div className="dashboard-controls" style={{ marginTop: '0px' }}>
            <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
              <div className="category-pills">
                {['All', 'General', 'Business', 'Technology', 'Science', 'Sports'].map(cat => (
                  <button
                    key={cat}
                    className={`category-pill-btn ${selectedCategory === cat ? 'active' : ''}`}
                    onClick={() => setSelectedCategory(cat)}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>

            <div className="dashboard-actions">
              <div className="search-container">
                <input 
                  type="text" 
                  className="search-input" 
                  placeholder="Search news keyword..."
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                />
                <Search size={14} className="search-icon-inside" />
              </div>

              <button 
                onClick={triggerIngestion} 
                disabled={isIngesting}
                className="refresh-trigger-btn"
              >
                <RefreshCw size={13} className={isIngesting ? 'animate-spin' : ''} />
                {isIngesting ? 'Ingesting...' : 'Ingest News'}
              </button>
            </div>
          </div>

          {/* Grid Layout of Cards */}
          <div className="cards-layout-header">
            <h2 className="cards-layout-title">Latest Stream Intelligence</h2>
            <span className="cards-count">{filteredNodes.length} nodes indexed</span>
          </div>

          {error && (
            <div className="error-state">
              <AlertTriangle className="error-icon" />
              <div className="error-details">
                <h4>Communication Error</h4>
                <p>{error}</p>
              </div>
            </div>
          )}

          {isLoading ? (
            <div className="skeleton-grid">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="skeleton-card"></div>
              ))}
            </div>
          ) : filteredNodes.length > 0 ? (
            <div className="cards-grid">
              {filteredNodes.map((node) => {
                const isSelected = selectedNodeIds.includes(node.id);
                return (
                  <article 
                    key={node.id} 
                    className={`article-card ${isSelected ? 'selected' : ''}`}
                    onClick={() => setSelectedNode(node)}
                  >
                    {/* Checkbox overlay for briefing synthesis */}
                    <div 
                      className="card-selection-wrapper"
                      onClick={(e) => toggleNodeSelection(e, node.id)}
                    >
                      <div className={`card-checkbox ${isSelected ? 'selected' : ''}`}>
                        {isSelected ? <CheckSquare size={14} /> : <Square size={14} />}
                      </div>
                    </div>

                    <div className="article-card-image-wrapper">
                      {node.image_url ? (
                        <img 
                          src={node.image_url} 
                          alt={node.title} 
                          className="article-card-image"
                          onError={(e) => {
                            (e.target as HTMLImageElement).src = 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?q=80&w=600&auto=format&fit=crop';
                          }}
                        />
                      ) : (
                        <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#0e172a', color: 'var(--text-muted)' }}>
                          <Newspaper size={36} style={{ opacity: 0.2 }} />
                        </div>
                      )}

                      <span className={`article-card-ai-badge ${
                        node.embedding_status === 'COMPLETED' ? 'ai-completed' :
                        node.embedding_status === 'PROCESSING' ? 'ai-processing' :
                        node.embedding_status === 'FAILED' ? 'ai-failed' : 'ai-pending'
                      }`}>
                        {node.embedding_status === 'COMPLETED' && <ShieldCheck size={10} />}
                        {node.embedding_status === 'PROCESSING' && <RefreshCw size={10} className="animate-spin" />}
                        {node.embedding_status === 'COMPLETED' ? `Analyzed (${(node.source_credibility_score * 100).toFixed(0)}%)` : 
                         node.embedding_status === 'PROCESSING' ? 'Enriching...' : 
                         node.embedding_status === 'FAILED' ? 'Fail' : 'AI Pending'}
                      </span>
                    </div>

                    <div className="article-card-content">
                      <div className="article-card-meta">
                        <span className="meta-source">{node.category}</span>
                        <span>•</span>
                        <span>{formatDate(node.published_at)}</span>
                      </div>

                      <h3 className="article-card-title" title={node.title}>
                        {node.title}
                      </h3>

                      <p className="article-card-snippet">
                        {node.content_processed ? node.content_processed : node.content_raw}
                      </p>

                      <div className="article-card-footer">
                        <span className="card-category-tag" style={{ visibility: 'hidden' }}>Dummy</span>
                        <span className="card-read-link">
                          Investigate <ChevronRight size={12} />
                        </span>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          ) : (
            <div className="empty-state">
              <Newspaper className="empty-state-icon" />
              <h3>No Intelligence Files Located</h3>
              <p>Execute "Ingest News" to sync reports.</p>
            </div>
          )}

          {/* Floating Multi-Article Briefing Synthesis Action Bar */}
          {selectedNodeIds.length > 0 && (
            <div className="briefing-floating-bar">
              <span>Selected {selectedNodeIds.length} article{selectedNodeIds.length > 1 ? 's' : ''} for synthesis</span>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button 
                  className="briefing-generate-btn"
                  onClick={handleGenerateBriefing}
                  disabled={briefingLoading}
                >
                  {briefingLoading ? <RefreshCw size={14} className="animate-spin" /> : <Sparkles size={14} />}
                  {briefingLoading ? 'Synthesizing Briefing...' : 'Generate Executive Briefing'}
                </button>
                <button 
                  className="briefing-clear-btn"
                  onClick={() => setSelectedNodeIds([])}
                >
                  Deselect All
                </button>
              </div>
            </div>
          )}

          {/* Generated Briefing Modal Dialog */}
          {(briefingMarkdown || briefingLoading) && (
            <div className="modal-overlay" onClick={() => setBriefingMarkdown(null)}>
              <div className="briefing-modal" onClick={e => e.stopPropagation()}>
                <header className="briefing-modal-header">
                  <h3>Executive Synthesis Briefing</h3>
                  <button className="briefing-close-btn" onClick={() => setBriefingMarkdown(null)}>
                    <X size={20} />
                  </button>
                </header>
                <div className="briefing-modal-body">
                  {briefingLoading ? (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '60px 0', gap: '16px' }}>
                      <RefreshCw size={36} className="animate-spin" style={{ color: 'var(--primary)' }} />
                      <p style={{ fontWeight: 600 }}>Assembling cross-article consensus and anomalies...</p>
                    </div>
                  ) : (
                    <div className="briefing-markdown-content">
                      {briefingMarkdown?.split('\n').map((line, idx) => {
                        if (line.startsWith('# ')) {
                          return <h1 key={idx}>{line.slice(2)}</h1>;
                        } else if (line.startsWith('## ')) {
                          return <h2 key={idx}>{line.slice(3)}</h2>;
                        } else if (line.startsWith('### ')) {
                          return <h3 key={idx}>{line.slice(4)}</h3>;
                        } else if (line.startsWith('- ') || line.startsWith('* ')) {
                          return <li key={idx} style={{ marginLeft: '12px', listStyleType: 'disc' }}>{line.slice(2)}</li>;
                        } else if (line.trim() === '') {
                          return <br key={idx} />;
                        }
                        return <p key={idx}>{line}</p>;
                      })}
                    </div>
                  )}
                </div>
                {!briefingLoading && (
                  <footer className="briefing-modal-footer">
                    <button 
                      className="briefing-copy-btn"
                      onClick={() => {
                        if (briefingMarkdown) {
                          navigator.clipboard.writeText(briefingMarkdown);
                          alert('Briefing markdown copied to clipboard.');
                        }
                      }}
                    >
                      Copy Markdown
                    </button>
                    <button 
                      className="briefing-generate-btn"
                      onClick={() => setBriefingMarkdown(null)}
                    >
                      Close Report
                    </button>
                  </footer>
                )}
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Slide-over Right Intelligence Drawer */}
      {selectedNode && (
        <div className="drawer-overlay" onClick={() => setSelectedNode(null)}>
          <div className="drawer-container" onClick={e => e.stopPropagation()}>
            
            {/* Header */}
            <header className="drawer-header">
              <div className="drawer-title-section">
                <div className="drawer-meta-tags">
                  <span className="card-category-tag">{selectedNode.category}</span>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>
                    {formatDate(selectedNode.published_at)}
                  </span>
                </div>
                <h2 className="drawer-title">{selectedNode.title}</h2>
              </div>
              <button className="drawer-close-btn" onClick={() => setSelectedNode(null)}>
                <X size={20} />
              </button>
            </header>

            {/* Tab switchers */}
            <div className="drawer-tabs">
              <button 
                className={`drawer-tab-btn ${drawerTab === 'analysis' ? 'active' : ''}`}
                onClick={() => setDrawerTab('analysis')}
              >
                <Sparkles size={14} />
                AI Analysis
              </button>
              <button 
                className={`drawer-tab-btn ${drawerTab === 'glossary' ? 'active' : ''}`}
                onClick={() => setDrawerTab('glossary')}
              >
                <BookMarked size={14} />
                Glossary ({drawerGlossary.length})
              </button>
              <button 
                className={`drawer-tab-btn ${drawerTab === 'chat' ? 'active' : ''}`}
                onClick={() => setDrawerTab('chat')}
              >
                <MessageCircle size={14} />
                Context Q&A
              </button>
            </div>

            {/* Drawer Content Body */}
            <div className="drawer-body">
              {drawerTab === 'analysis' && (
                <div className="synthesis-section">
                  {pipelineLoading ? (
                    <div className="pipeline-loader-panel">
                      <div className="pulse-spinner"></div>
                      <h4>Executing AI Enrichment Pipeline</h4>
                      
                      <div className="pipeline-steps-list">
                        <div className={`pipeline-step-item ${pipelineStep >= 0 ? (pipelineStep === 0 ? 'active' : 'completed') : ''}`}>
                          <div className="step-indicator-dot"></div>
                          <span>Scraping full article content...</span>
                        </div>
                        <div className={`pipeline-step-item ${pipelineStep >= 1 ? (pipelineStep === 1 ? 'active' : 'completed') : ''}`}>
                          <div className="step-indicator-dot"></div>
                          <span>Extracting NLP entities & sentiment...</span>
                        </div>
                        <div className={`pipeline-step-item ${pipelineStep >= 2 ? (pipelineStep === 2 ? 'active' : 'completed') : ''}`}>
                          <div className="step-indicator-dot"></div>
                          <span>Generating LLM synthesized analysis...</span>
                        </div>
                        <div className={`pipeline-step-item ${pipelineStep >= 3 ? (pipelineStep === 3 ? 'active' : 'completed') : ''}`}>
                          <div className="step-indicator-dot"></div>
                          <span>Calculating trust credibility score...</span>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <>
                      {/* Run pipeline prompt */}
                      {selectedNode.embedding_status !== 'COMPLETED' && (
                        <div className="pipeline-run-prompt" style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '16px', borderRadius: '12px', border: '1px dashed var(--border-color)', background: 'rgba(99,102,241,0.05)', marginBottom: '16px' }}>
                          <h4 style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, color: 'white', fontSize: '13px' }}>
                            <Sparkles size={14} style={{ color: 'var(--primary)' }} />
                            AI Analysis Pending
                          </h4>
                          <p style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                            Generate summaries, credibility ratings, and deeper context by executing our pipeline.
                          </p>
                          <button 
                            className="pipeline-btn"
                            onClick={() => runAIPipeline(selectedNode.id)}
                            style={{ alignSelf: 'flex-start', marginTop: '6px', padding: '6px 12px', fontSize: '12px' }}
                          >
                            <Sparkles size={12} />
                            Run Intelligence Pipeline
                          </button>
                        </div>
                      )}

                      {/* Credibility and Sentiment metrics */}
                      {selectedNode.embedding_status === 'COMPLETED' && (
                        <div className="analysis-dashboard-row">
                          <div className="metric-panel">
                            <span className="metric-panel-title">Credibility Rating</span>
                            <div className="credibility-gauge-container">
                              <svg className="credibility-svg">
                                <circle className="credibility-circle-bg" cx="40" cy="40" r="34"></circle>
                                <circle 
                                  className="credibility-circle-fill" 
                                  cx="40" 
                                  cy="40" 
                                  r="34"
                                  style={{
                                    strokeDasharray: 213.6,
                                    strokeDashoffset: 213.6 - (213.6 * selectedNode.source_credibility_score)
                                  }}
                                ></circle>
                              </svg>
                              <span className="credibility-percentage">
                                {(selectedNode.source_credibility_score * 100).toFixed(0)}%
                              </span>
                            </div>
                          </div>

                          <div className="metric-panel">
                            <span className="metric-panel-title">NLP Sentiment Indicator</span>
                            <div className="sentiment-indicator-wrapper">
                              <div className="sentiment-bar-track">
                                <div 
                                  className="sentiment-bar-indicator"
                                  style={{ 
                                    left: selectedNode.sentiment_score !== undefined 
                                      ? `${((selectedNode.sentiment_score + 1) / 2) * 100}%`
                                      : '50%'
                                  }}
                                ></div>
                              </div>
                              <div className="sentiment-bar-labels">
                                <span>NEGATIVE</span>
                                <span>NEUTRAL</span>
                                <span>POSITIVE</span>
                              </div>
                            </div>
                            <span className="sentiment-score-badge">
                              {selectedNode.sentiment_score !== undefined ? (
                                selectedNode.sentiment_score > 0.35 ? `Positive (${selectedNode.sentiment_score})` :
                                selectedNode.sentiment_score < -0.35 ? `Negative (${selectedNode.sentiment_score})` :
                                `Neutral (${selectedNode.sentiment_score})`
                              ) : 'Neutral'}
                            </span>
                          </div>
                        </div>
                      )}

                      {/* Summary container */}
                      <div className="summary-block">
                        <span className="summary-heading">
                          {selectedNode.embedding_status === 'COMPLETED' && selectedNode.content_processed 
                            ? 'AI Synthesis Summary' 
                            : 'Raw Article Content'}
                        </span>
                        <p style={{ fontSize: '10px', color: 'var(--text-muted)', marginBottom: '8px', fontStyle: 'italic' }}>
                          *Tip: Double-click any phrase or term in the block below to request an inline AI Glossary definition.*
                        </p>
                        <div 
                          className="summary-text-container" 
                          onMouseUp={handleSummaryTextSelection}
                          style={{ cursor: 'text' }}
                        >
                          {(selectedNode.content_processed || selectedNode.full_text_scraped || selectedNode.content_raw || '').split('\n').map((para, i) => (
                            <p key={i} style={{ marginBottom: '14px' }}>{para}</p>
                          ))}
                        </div>
                      </div>

                      {/* Key Entities */}
                      {selectedNode.embedding_status === 'COMPLETED' && selectedNode.entities && selectedNode.entities.length > 0 && (
                        <div className="summary-block">
                          <span className="summary-heading">Identified Entities</span>
                          <div className="entity-tags-container">
                            {selectedNode.entities.map((item, idx) => (
                              <span key={idx} className="entity-pill">{item}</span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Full Scraped Text */}
                      {selectedNode.embedding_status === 'COMPLETED' && (
                        <div className="summary-block">
                          <span className="summary-heading">Full Scraped Content (RAG Raw Data)</span>
                          <div className="article-scraped-block">
                            {selectedNode.full_text_scraped ? (
                              selectedNode.full_text_scraped.split('\n').map((para, i) => (
                                <p key={i}>{para}</p>
                              ))
                            ) : (
                              <p>{selectedNode.content_raw || 'No raw scraped content available.'}</p>
                            )}
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}

              {/* Contextual Q&A Chat */}
              {drawerTab === 'chat' && (
                <div className="chat-container">
                  <div className="chat-history">
                    {chatHistory.length === 0 && (
                      <div className="chat-empty">
                        <MessageCircle size={32} style={{ opacity: 0.3, marginBottom: '12px' }} />
                        <p>Ask our AI model any question regarding this article's contents or credibility framework.</p>
                      </div>
                    )}
                    
                    {chatHistory.map((msg, idx) => (
                      <React.Fragment key={idx}>
                        <div className="chat-bubble chat-bubble-user">{msg.q}</div>
                        <div className="chat-bubble chat-bubble-ai">{msg.a}</div>
                      </React.Fragment>
                    ))}
                    
                    {chatLoading && (
                      <div className="chat-loading">
                        <RefreshCw size={12} className="animate-spin" />
                        Analyst is thinking...
                      </div>
                    )}
                  </div>
                  
                  <form onSubmit={handleAskQuestion} className="chat-form">
                    <input 
                      type="text" 
                      className="chat-input"
                      placeholder="Type your question about this news..."
                      value={chatQuestion}
                      onChange={e => setChatQuestion(e.target.value)}
                      disabled={chatLoading}
                    />
                    <button type="submit" className="chat-send-btn" disabled={chatLoading || !chatQuestion.trim()}>
                      <Send size={14} />
                    </button>
                  </form>
                </div>
              )}

              {/* Glossary tab (no card pop-ups, double click jumps here directly) */}
              {drawerTab === 'glossary' && (
                <div className="glossary-section">
                  <div className="glossary-info-card">
                    <BookMarked size={16} style={{ color: 'var(--primary)' }} />
                    <span>To define new words, select/double-click text in the AI Synthesis Summary tab!</span>
                  </div>

                  {drawerGlossary.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                      {drawerGlossary.map((item, idx) => (
                        <div key={idx} className="glossary-item">
                          <div className="glossary-word">{item.word}</div>
                          <div className="glossary-definition">{item.definition}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="chat-empty" style={{ height: '260px' }}>
                      <BookMarked size={32} style={{ opacity: 0.3, marginBottom: '12px' }} />
                      <p>No words defined for this file yet. Highlight phrases in the summary to request definitions.</p>
                    </div>
                  )}
                </div>
              )}
            </div>

            <footer className="drawer-footer">
              <a 
                href={selectedNode.source_url} 
                target="_blank" 
                rel="noopener noreferrer" 
                className="drawer-source-link"
              >
                <ExternalLink size={14} />
                Open Original Article Link
              </a>
            </footer>

          </div>
        </div>
      )}
    </div>
  );
}

export default App;
