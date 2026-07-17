import { useState } from 'react';
import { Search, Zap, BookOpen, Microscope } from 'lucide-react';

const DEPTHS = [
  { value: 'quick', label: 'Quick', icon: Zap, desc: '2-3 sources, fast' },
  { value: 'standard', label: 'Standard', icon: BookOpen, desc: '4-6 sources, balanced' },
  { value: 'deep', label: 'Deep', icon: Microscope, desc: '8-10 sources, thorough' },
];

export default function SearchForm({ onSubmit, loading }) {
  const [query, setQuery] = useState('');
  const [depth, setDepth] = useState('standard');
  const [maxSources, setMaxSources] = useState(5);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!query.trim() || loading) return;
    onSubmit({ query: query.trim(), depth, max_sources: maxSources });
  };

  return (
    <form onSubmit={handleSubmit} className="search-form">
      <div className="search-input-row">
        <Search size={20} className="search-icon" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="What would you like to research?"
          className="search-input"
          disabled={loading}
          minLength={5}
          maxLength={2000}
        />
      </div>

      <div className="search-options">
        <div className="depth-selector">
          {DEPTHS.map(({ value, label, icon: Icon, desc }) => (
            <button
              key={value}
              type="button"
              className={`depth-btn ${depth === value ? 'active' : ''}`}
              onClick={() => {
                setDepth(value);
                setMaxSources(value === 'quick' ? 3 : value === 'deep' ? 10 : 5);
              }}
              title={desc}
            >
              <Icon size={14} />
              <span>{label}</span>
            </button>
          ))}
        </div>

        <div className="sources-control">
          <label>Sources: {maxSources}</label>
          <input
            type="range"
            min={1}
            max={15}
            value={maxSources}
            onChange={(e) => setMaxSources(Number(e.target.value))}
          />
        </div>

        <button type="submit" className="submit-btn" disabled={!query.trim() || loading}>
          {loading ? 'Researching...' : 'Research'}
        </button>
      </div>
    </form>
  );
}
