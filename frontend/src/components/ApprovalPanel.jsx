import { useState } from 'react';
import { ThumbsUp, ThumbsDown, FileText, ExternalLink } from 'lucide-react';

export default function ApprovalPanel({ result, onApprove }) {
  const [feedback, setFeedback] = useState('');

  if (!result) return null;

  return (
    <div className="approval-panel">
      <div className="approval-header">
        <h3>Review Research Findings</h3>
        <p>The researcher gathered {result.sources?.length || 0} sources. Review before generating the final summary.</p>
      </div>

      {result.plan && (
        <div className="approval-section">
          <h4>Research Plan</h4>
          <p className="plan-approach">{result.plan.approach}</p>
          <div className="sub-questions">
            {result.plan.sub_questions?.map((q, i) => (
              <div key={i} className="sub-q">
                <span className="sub-q-num">{i + 1}</span>
                <span>{q}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {result.sources && result.sources.length > 0 && (
        <div className="approval-section">
          <h4>Sources Found</h4>
          <div className="sources-list">
            {result.sources.map((s, i) => (
              <div key={i} className="source-card">
                <div className="source-header">
                  <FileText size={14} />
                  <span className="source-title">{s.title}</span>
                  <span className="relevance-badge">{(s.relevance_score * 100).toFixed(0)}%</span>
                </div>
                <p className="source-snippet">{s.snippet}</p>
                {s.url && (
                  <a href={s.url} target="_blank" rel="noopener noreferrer" className="source-url">
                    <ExternalLink size={12} /> {s.url}
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="approval-actions">
        <textarea
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          placeholder="Optional feedback for the summarizer..."
          className="approval-feedback"
          rows={2}
        />
        <div className="approval-buttons">
          <button className="approve-btn" onClick={() => onApprove(true, feedback)}>
            <ThumbsUp size={16} /> Approve & Summarize
          </button>
          <button className="reject-btn" onClick={() => onApprove(false, feedback)}>
            <ThumbsDown size={16} /> Reject
          </button>
        </div>
      </div>
    </div>
  );
}
