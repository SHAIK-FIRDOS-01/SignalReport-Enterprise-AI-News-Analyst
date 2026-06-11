import React, { useState, useRef } from 'react';
import { ExternalLink, Sparkles, MessageCircle, X, BookOpen, Send, Activity } from 'lucide-react';

interface NewsCardProps {
  node: any;
  onSummarize: () => Promise<void>;
  onOpenDigest: () => void;
}

type FloatingState = 'summary' | 'qa' | 'glossary' | null;

const NewsCard: React.FC<NewsCardProps> = ({ node, onSummarize, onOpenDigest }) => {
  const [floating, setFloating] = useState<FloatingState>(null);
  
  // Q&A State
  const [question, setQuestion] = useState('');
  const [qaHistory, setQaHistory] = useState<{q: string, a: string}[]>([]);
  const [qaLoading, setQaLoading] = useState(false);
  
  // Glossary State
  const [selectionRange, setSelectionRange] = useState<{x: number, y: number, text: string} | null>(null);
  const [glossaryTerm, setGlossaryTerm] = useState('');
  const [glossaryDef, setGlossaryDef] = useState('');
  const [glossaryLoading, setGlossaryLoading] = useState(false);

  // Summarize state
  const [isSummarizing, setIsSummarizing] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);

  const handleMouseUp = () => {
    if (floating) return;

    const selection = window.getSelection();
    const text = selection?.toString().trim();

    if (text && text.length > 0 && text.split(' ').length <= 5) {
      const range = selection?.getRangeAt(0);
      const rect = range?.getBoundingClientRect();
      const cardRect = cardRef.current?.getBoundingClientRect();
      
      if (rect && cardRect) {
        setSelectionRange({
          x: rect.left - cardRect.left + (rect.width / 2),
          y: rect.top - cardRect.top,
          text: text
        });
      }
    } else {
      setSelectionRange(null);
    }
  };

  const clearSelection = () => {
    setSelectionRange(null);
    window.getSelection()?.removeAllRanges();
  };

  const handleCardClick = (e: React.MouseEvent) => {
    // If user is selecting text, don't open digest
    if (window.getSelection()?.toString().trim()) return;
    
    // Check if click was on a button or link
    const target = e.target as HTMLElement;
    if (target.closest('button') || target.closest('a')) return;

    onOpenDigest();
  };

  const handleDefine = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!selectionRange) return;
    
    const term = selectionRange.text;
    setGlossaryTerm(term);
    setFloating('glossary');
    setGlossaryLoading(true);
    clearSelection();

    try {
      const token = localStorage.getItem('token');
      const res = await fetch('http://localhost:8000/glossary/', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Bearer ${token}` })
        },
        body: JSON.stringify({ term, node_id: node.id })
      });
      const data = await res.json();
      setGlossaryDef(data.definition || 'No definition found.');
    } catch (err) {
      setGlossaryDef('Failed to load definition.');
    } finally {
      setGlossaryLoading(false);
    }
  };

  const handleSummarizeClick = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setFloating('summary');
    if (node.embedding_status !== 'COMPLETED') {
      setIsSummarizing(true);
      await onSummarize();
      setIsSummarizing(false);
    }
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

  const statusClass = `status-${node.embedding_status.toLowerCase()}`;
  const dateStr = node.published_at ? new Date(node.published_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : '';

  return (
    <div 
      className="glass-panel card" 
      ref={cardRef} 
      onMouseUp={handleMouseUp} 
      onMouseLeave={clearSelection}
      onClick={handleCardClick}
      style={{ cursor: 'pointer' }}
    >
      {/* Tooltip for Glossary */}
      {selectionRange && !floating && (
        <button 
          className="tooltip-btn"
          style={{ left: selectionRange.x, top: selectionRange.y }}
          onClick={handleDefine}
        >
          Define "{selectionRange.text}"
        </button>
      )}

      {/* Floating Modals (Summary, Q&A, Glossary) */}
      {floating && (
        <div className="floating-box">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '0.5rem' }}>
            <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0, fontSize: '1.1rem', color: 'var(--accent-primary)' }}>
              {floating === 'summary' && <Sparkles size={18} />}
              {floating === 'qa' && <MessageCircle size={18} />}
              {floating === 'glossary' && <BookOpen size={18} />}
              {floating === 'summary' ? 'AI Summary' : floating === 'qa' ? 'Q&A' : 'Glossary'}
            </h4>
            <button onClick={() => setFloating(null)} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
              <X size={20} />
            </button>
          </div>

          <div style={{ flexGrow: 1, overflowY: 'auto' }}>
            {floating === 'glossary' && (
              <div>
                <p style={{ fontSize: '1.2rem', fontWeight: 'bold', marginBottom: '0.5rem', color: 'var(--accent-secondary)' }}>{glossaryTerm}</p>
                {glossaryLoading ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)' }}><Activity size={16} className="spinner"/> Defining...</div>
                ) : (
                  <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>{glossaryDef}</p>
                )}
              </div>
            )}

            {floating === 'summary' && (
              <div>
                {isSummarizing ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)' }}><Activity size={16} className="spinner"/> Generating deep analysis...</div>
                ) : (
                  <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>{node.content_processed || 'Summary generation failed.'}</p>
                )}
              </div>
            )}

            {floating === 'qa' && (
              <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                <div style={{ flexGrow: 1, marginBottom: '1rem' }}>
                  {qaHistory.length === 0 && !qaLoading && <p style={{ color: 'var(--text-muted)', fontStyle: 'italic', fontSize: '0.9rem' }}>Ask anything about this article...</p>}
                  {qaHistory.map((item, idx) => (
                    <div key={idx} style={{ marginBottom: '1rem' }}>
                      <p style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.2rem' }}>Q: {item.q}</p>
                      <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', background: 'rgba(255,255,255,0.05)', padding: '0.5rem', borderRadius: '8px' }}>A: {item.a}</p>
                    </div>
                  ))}
                  {qaLoading && <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)' }}><Activity size={16} className="spinner"/> Thinking...</div>}
                </div>
                <form onSubmit={handleAskQuestion} style={{ display: 'flex', gap: '0.5rem', marginTop: 'auto' }}>
                  <input 
                    type="text" 
                    className="glass-input" 
                    style={{ padding: '0.5rem', fontSize: '0.9rem' }} 
                    placeholder="Type your question..." 
                    value={question}
                    onChange={e => setQuestion(e.target.value)}
                    disabled={qaLoading}
                  />
                  <button type="submit" className="glass-button" style={{ padding: '0.5rem' }} disabled={qaLoading || !question.trim()}>
                    <Send size={16} />
                  </button>
                </form>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Main Card Content */}
      <div style={{ opacity: floating ? 0.2 : 1, transition: 'opacity 0.3s ease', display: 'flex', flexDirection: 'column', height: '100%', pointerEvents: floating ? 'none' : 'auto' }}>
        {node.image_url && (
          <div className="card-image-container" style={{ width: 'calc(100% + 3rem)', height: '160px', margin: '-1.5rem -1.5rem 1rem -1.5rem', overflow: 'hidden', borderBottom: '1px solid var(--card-border)' }}>
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
        <div className="card-meta">
          <span className={`status-badge ${statusClass}`}>
            {node.embedding_status}
          </span>
          <span style={{ fontSize: '0.8rem', opacity: 0.8 }}>{dateStr}</span>
        </div>
        
        <h3 className="card-title" title={node.title}>{node.title}</h3>
        
        <div className="card-content">
          <p>{node.content_raw ? node.content_raw.substring(0, 160) + '...' : 'No content available.'}</p>
        </div>

        <div className="card-actions">
          {node.source_url && (
            <a href={node.source_url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.2rem', textDecoration: 'none', fontSize: '0.8rem', marginRight: 'auto' }}>
              <ExternalLink size={14} /> Source
            </a>
          )}
          
          <button className="icon-btn" title="Ask Question" onClick={(e) => { e.stopPropagation(); setFloating('qa'); }}>
            <MessageCircle size={18} />
          </button>
          <button className="icon-btn" title="AI Summary" onClick={handleSummarizeClick}>
            {isSummarizing ? <Activity size={18} className="spinner" /> : <Sparkles size={18} />}
          </button>
        </div>
      </div>
    </div>
  );
};

export default NewsCard;
