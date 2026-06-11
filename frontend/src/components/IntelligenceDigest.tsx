import React, { useState } from 'react';
import { X, Sparkles, MessageCircle, BookOpen, Send, Activity, ExternalLink, ShieldCheck } from 'lucide-react';

interface IntelligenceDigestProps {
  node: any;
  onClose: () => void;
  onSummarize: () => Promise<void>;
}

const IntelligenceDigest: React.FC<IntelligenceDigestProps> = ({ node, onClose, onSummarize }) => {
  const [question, setQuestion] = useState('');
  const [qaHistory, setQaHistory] = useState<{q: string, a: string}[]>([]);
  const [qaLoading, setQaLoading] = useState(false);
  const [summarizing, setSummarizing] = useState(false);

  const handleSummarizeRequest = async () => {
    setSummarizing(true);
    await onSummarize();
    setSummarizing(false);
  };

  const handleAskQuestion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    const currentQ = question;
    setQuestion('');
    setQaLoading(true);

    try {
      const token = localStorage.getItem('token');
      const res = await fetch('http://localhost:8000/ask/', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Bearer ${token}` })
        },
        body: JSON.stringify({ question: currentQ, node_id: node.id })
      });
      const data = await res.json();
      setQaHistory(prev => [...prev, { q: currentQ, a: data.answer || 'No answer found.' }]);
    } catch (err) {
      setQaHistory(prev => [...prev, { q: currentQ, a: 'Failed to process question.' }]);
    } finally {
      setQaLoading(false);
    }
  };

  return (
    <div className="digest-overlay">
      <div className="digest-container glass-panel">
        {/* Header */}
        <header className="digest-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <span className={`status-badge status-${node.embedding_status.toLowerCase()}`}>
              {node.embedding_status}
            </span>
            <h2 className="digest-title">{node.title}</h2>
          </div>
          <button className="close-btn" onClick={onClose}><X size={24} /></button>
        </header>

        <div className="digest-content-layout">
          {/* Main Content Area */}
          <main className="digest-main">
            {node.image_url && (
              <div className="digest-image-container" style={{ width: '100%', maxHeight: '320px', overflow: 'hidden', borderRadius: '12px', marginBottom: '2rem' }}>
                <img 
                  src={node.image_url} 
                  alt={node.title} 
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }} 
                  onError={(e) => { 
                    const parent = (e.target as HTMLElement).parentElement;
                    if (parent) parent.style.display = 'none';
                  }}
                />
              </div>
            )}
            {/* Top Section: AI Summary */}
            <section className="digest-section summary-section">
              <h3 className="section-title"><Sparkles size={18} /> AI Intelligence Summary</h3>
              <div className="summary-box">
                {node.content_processed ? (
                  <p>{node.content_processed}</p>
                ) : (
                  <div style={{ textAlign: 'center', padding: '1rem' }}>
                    <p className="placeholder-text" style={{ marginBottom: '1rem' }}>Deep analysis pending.</p>
                    <button 
                      className="glass-button primary" 
                      onClick={handleSummarizeRequest}
                      disabled={summarizing}
                    >
                      {summarizing ? <Activity size={16} className="spinner" /> : <Sparkles size={16} />}
                      {summarizing ? 'Analyzing Article...' : 'Generate AI Summary'}
                    </button>
                  </div>
                )}
              </div>
            </section>

            {/* Middle Section: Full Scraped Text */}
            <section className="digest-section full-text-section">
              <h3 className="section-title"><BookOpen size={18} /> Full Article Content</h3>
              <div className="article-body">
                {node.full_text_scraped ? (
                  node.full_text_scraped.split('\n').map((para: string, i: number) => (
                    <p key={i}>{para}</p>
                  ))
                ) : (
                  <p className="placeholder-text">
                    {node.content_raw || "No content available for this article."}
                    <br/><br/>
                    <span style={{ fontSize: '0.8rem', opacity: 0.6 }}>Note: Full-text scraping may have been restricted by the source.</span>
                  </p>
                )}
              </div>
            </section>

            {/* Bottom Section: Source Link */}
            <footer className="digest-footer">
               <a href={node.source_url} target="_blank" rel="noopener noreferrer" className="source-link">
                 <ExternalLink size={16} /> View Original Source
               </a>
               <div className="credibility-badge">
                 <ShieldCheck size={16} /> Credibility Score: {(node.source_credibility_score * 100).toFixed(0)}%
               </div>
            </footer>
          </main>

          {/* Side Panel: Q&A */}
          <aside className="digest-sidebar">
            <h3 className="section-title"><MessageCircle size={18} /> Interactive Q&A</h3>
            <div className="qa-container">
              <div className="qa-history">
                {qaHistory.length === 0 && (
                  <div className="qa-empty">
                    <p>Ask anything about this intelligence report...</p>
                  </div>
                )}
                {qaHistory.map((item, idx) => (
                  <div key={idx} className="qa-item">
                    <p className="qa-q">Q: {item.q}</p>
                    <p className="qa-a">A: {item.a}</p>
                  </div>
                ))}
                {qaLoading && (
                  <div className="qa-loading">
                    <Activity size={16} className="spinner" /> Analyzing context...
                  </div>
                )}
              </div>
              <form onSubmit={handleAskQuestion} className="qa-form">
                <input 
                  type="text" 
                  className="glass-input" 
                  placeholder="Type your question..." 
                  value={question}
                  onChange={e => setQuestion(e.target.value)}
                  disabled={qaLoading}
                />
                <button type="submit" className="glass-button" disabled={qaLoading || !question.trim()}>
                  <Send size={16} />
                </button>
              </form>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
};

export default IntelligenceDigest;
