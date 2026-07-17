import ReactMarkdown from 'react-markdown';
import {
  CheckCircle, AlertTriangle, FileText, ExternalLink,
  Shield, BarChart3, Clock, Cpu
} from 'lucide-react';

export default function ResultView({ result }) {
  if (!result || result.status !== 'completed') return null;

  const guardrails = result.guardrail_results || {};
  const allPassed = Object.values(guardrails).every(g => g.passed);
  const traces = result.traces || [];
  const totalMs = traces.reduce((sum, t) => sum + (t.duration_ms || 0), 0);
  const totalInputTok = traces.reduce((sum, t) => sum + (t.token_usage?.input || 0), 0);
  const totalOutputTok = traces.reduce((sum, t) => sum + (t.token_usage?.output || 0), 0);

  return (
    <div className="result-view">
      {/* Metrics bar */}
      <div className="metrics-bar">
        <div className="metric">
          <Clock size={14} />
          <span>{(totalMs / 1000).toFixed(1)}s total</span>
        </div>
        <div className="metric">
          <Cpu size={14} />
          <span>{totalInputTok + totalOutputTok} tokens</span>
        </div>
        <div className="metric">
          <BarChart3 size={14} />
          <span>{(result.confidence_score * 100).toFixed(0)}% confidence</span>
        </div>
        <div className={`metric ${allPassed ? 'pass' : 'warn'}`}>
          <Shield size={14} />
          <span>{allPassed ? 'All guardrails passed' : 'Guardrail warnings'}</span>
        </div>
      </div>

      {/* Key points */}
      {result.key_points && result.key_points.length > 0 && (
        <div className="key-points">
          <h3>Key Findings</h3>
          <div className="key-points-grid">
            {result.key_points.map((point, i) => (
              <div key={i} className="key-point">
                <span className="kp-num">{i + 1}</span>
                <span>{point}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Full summary */}
      <div className="summary-content">
        <h3>Research Summary</h3>
        <div className="markdown-body">
          <ReactMarkdown>{result.summary}</ReactMarkdown>
        </div>
      </div>

      {/* Sources */}
      <div className="result-sources">
        <h3>Sources ({result.sources?.length || 0})</h3>
        <div className="sources-compact">
          {result.sources?.map((s, i) => (
            <div key={i} className="source-compact">
              <FileText size={12} />
              <span className="source-title-sm">{s.title}</span>
              <span className="relevance-sm">{(s.relevance_score * 100).toFixed(0)}%</span>
              {s.url && (
                <a href={s.url} target="_blank" rel="noopener noreferrer">
                  <ExternalLink size={10} />
                </a>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Guardrail details */}
      <details className="guardrails-section">
        <summary>
          <Shield size={14} />
          Guardrail Results
        </summary>
        <div className="guardrail-grid">
          {Object.entries(guardrails).map(([name, check]) => (
            <div key={name} className={`guardrail-card ${check.passed ? 'pass' : 'fail'}`}>
              {check.passed ? <CheckCircle size={14} /> : <AlertTriangle size={14} />}
              <span className="gr-name">{name.replace(/_/g, ' ')}</span>
              <span className="gr-detail">{check.detail}</span>
            </div>
          ))}
        </div>
      </details>

      {/* Agent trace log */}
      <details className="trace-section">
        <summary>
          <Cpu size={14} />
          Agent Trace Log ({traces.length} steps)
        </summary>
        <div className="trace-table">
          {traces.map((t, i) => (
            <div key={i} className="trace-row">
              <span className="tr-idx">{i + 1}</span>
              <span className={`tr-agent agent-${t.agent}`}>{t.agent}</span>
              <span className="tr-action">{t.action}</span>
              <span className="tr-time">{t.duration_ms?.toFixed(0)}ms</span>
              <span className="tr-tokens">
                {t.token_usage?.input || '—'}↗{t.token_usage?.output || '—'}
              </span>
              {t.output_summary && <span className="tr-out">{t.output_summary}</span>}
            </div>
          ))}
        </div>
      </details>
    </div>
  );
}
