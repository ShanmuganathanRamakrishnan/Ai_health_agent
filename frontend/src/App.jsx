import { useState } from 'react'

// Response Card Component
function ResponseCard({ response, isSelected, onClick }) {
    const { query, answer, confidence, evidence } = response
    const [evidenceOpen, setEvidenceOpen] = useState(confidence === 'Low')

    const confidenceColor = {
        'High': '#2e7d32',
        'Medium': '#f57c00',
        'Low': '#c62828'
    }

    return (
        <div
            className={`response-card ${isSelected ? 'selected' : ''} ${confidence?.toLowerCase()}`}
            onClick={onClick}
        >
            {query && <div className="card-query">{query}</div>}

            <div className="card-header">
                <span
                    className="confidence-badge"
                    style={{ backgroundColor: confidenceColor[confidence] || '#757575' }}
                >
                    {confidence}
                </span>
            </div>

            <div className="card-answer">{answer}</div>

            {evidence && evidence.length > 0 && (
                <div className="card-evidence">
                    <button
                        className="evidence-toggle"
                        onClick={(e) => { e.stopPropagation(); setEvidenceOpen(!evidenceOpen) }}
                    >
                        {evidenceOpen ? '▼' : '▶'} Evidence ({evidence.length})
                    </button>
                    {evidenceOpen && (
                        <ul className="evidence-list">
                            {evidence.map((item, idx) => (
                                <li key={idx}>{item}</li>
                            ))}
                        </ul>
                    )}
                </div>
            )}
        </div>
    )
}

// Right Inspector Panel
function InspectorPanel({ response, onClose }) {
    if (!response) return null

    const { answer, confidence, evidence } = response

    // Determine logic path based on evidence
    const getLogicPath = () => {
        if (!evidence || evidence.length === 0) return 'UNKNOWN'
        const evStr = evidence.join(' ').toLowerCase()
        if (evStr.includes('risk_level') && evStr.includes('history')) return 'SEVERITY'
        if (evStr.includes('cached')) return 'SUMMARY'
        if (evStr.includes('trend')) return 'COMPLEX'
        if (evStr.includes('patients.')) return 'FACTUAL'
        if (evStr.includes('mismatch') || evStr.includes('not found')) return 'REFUSAL'
        return 'COMPLEX'
    }

    const logicPath = getLogicPath()

    const pathColors = {
        'FACTUAL': '#2e7d32',
        'SUMMARY': '#1565c0',
        'COMPLEX': '#f57c00',
        'SEVERITY': '#7b1fa2',
        'REFUSAL': '#c62828'
    }

    return (
        <div className="inspector-panel">
            <div className="inspector-header">
                <h3>Response Details</h3>
                <button className="close-btn" onClick={onClose}>×</button>
            </div>

            <div className="inspector-section">
                <label>Logic Path</label>
                <div
                    className="logic-path-badge"
                    style={{ backgroundColor: pathColors[logicPath] }}
                >
                    {logicPath}
                </div>
            </div>

            <div className="inspector-section">
                <label>Confidence Level</label>
                <div className="confidence-meter">
                    <div className={`meter-fill ${confidence?.toLowerCase()}`}></div>
                    <span>{confidence}</span>
                </div>
            </div>

            <div className="inspector-section">
                <label>Evidence Sources</label>
                <ul className="inspector-evidence">
                    {evidence?.map((item, idx) => (
                        <li key={idx}>{item}</li>
                    ))}
                </ul>
            </div>

            <div className="inspector-section">
                <label>Full Response</label>
                <div className="inspector-answer">{answer}</div>
            </div>
        </div>
    )
}

function App() {
    const [responses, setResponses] = useState([])
    const [input, setInput] = useState('')
    const [loading, setLoading] = useState(false)
    const [selectedIdx, setSelectedIdx] = useState(null)

    const sendQuery = async () => {
        const query = input.trim()
        if (!query || loading) return

        setInput('')
        setLoading(true)

        try {
            const response = await fetch('http://localhost:8000/chat/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            })

            if (!response.ok) throw new Error('Request failed')

            const data = await response.json()
            setResponses(prev => [...prev, {
                query,
                answer: data.answer,
                confidence: data.confidence,
                evidence: data.evidence
            }])
        } catch (error) {
            setResponses(prev => [...prev, {
                query,
                answer: 'Unable to reach server.',
                confidence: 'Low',
                evidence: ['connection_error']
            }])
        } finally {
            setLoading(false)
        }
    }

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            sendQuery()
        }
    }

    const selectedResponse = selectedIdx !== null ? responses[selectedIdx] : null

    return (
        <div className="app">
            <header className="header">
                <h1>Clinical Information Assistant</h1>
                <p>Patient Health Record Query System</p>
            </header>

            <div className="main-layout">
                <main className="center-pane">
                    {responses.length === 0 && !loading && (
                        <div className="empty-state">
                            <h2>No queries yet</h2>
                            <p>Enter a patient query below to get started.</p>
                            <p className="hint">Examples: "What is John Brown diagnosed with?" or "Is Sarah Wilson's condition serious?"</p>
                        </div>
                    )}

                    <div className="responses-list">
                        {responses.map((resp, idx) => (
                            <ResponseCard
                                key={idx}
                                response={resp}
                                isSelected={selectedIdx === idx}
                                onClick={() => setSelectedIdx(selectedIdx === idx ? null : idx)}
                            />
                        ))}
                    </div>

                    {loading && (
                        <div className="loading-card">
                            <div className="loading-spinner"></div>
                            <span>Analyzing query...</span>
                        </div>
                    )}

                    <div className="input-area">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Enter patient query..."
                            disabled={loading}
                        />
                        <button onClick={sendQuery} disabled={loading || !input.trim()}>
                            Submit
                        </button>
                    </div>
                </main>

                {selectedResponse && (
                    <InspectorPanel
                        response={selectedResponse}
                        onClose={() => setSelectedIdx(null)}
                    />
                )}
            </div>
        </div>
    )
}

export default App
