import React, { useState } from 'react';

const Recommender: React.FC = () => {
    const [itemId, setItemId] = useState('');
    const [results, setResults] = useState<{
        collaborative: string[];
        content: string[];
        azure: string[];
    }>({
        collaborative: [],
        content: [],
        azure: [],
    });

    const validItemIds = [
        "-9222795471790223670",
        "-9216926795620865886",
        "-9194572880052200111",
        "-9192549002213406534",
        "-9190737901804729417",
        "-9189659052158407108",
        "-9184137057748005562",
        "-9176143510534135851",
        "-9172673334835262304",
        "-9171475473795142532"
    ];

    const handleRecommend = async () => {
        try {
            const [collabRes, contentRes] = await Promise.all([
                fetch("http://localhost:8000/recommend/collaborative", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ itemId })
                }),
                fetch("http://localhost:8000/recommend/content", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ itemId })
                })
            ]);

            const collabData = await collabRes.json();
            const contentData = await contentRes.json();
            console.log("Content-Based Response:", contentData); // 🧪 log what we got


            setResults({
                collaborative: (collabData?.recommendations || []).map(String),
                content: (contentData?.recommendations || []).map(String),
                azure: [] // Future model
            });
        } catch (error) {
            console.error("Error fetching recommendations:", error);
        }
    };

    const renderResultList = (title: string, items: string[]) => (
        <div className="card mb-3">
            <div className="card-header">{title}</div>
            <div className="card-body">
                {items.length > 0 ? (
                    <ul className="list-group list-group-flush">
                        {items.map((item, idx) => (
                            <li key={idx} className="list-group-item">{item}</li>
                        ))}
                    </ul>
                ) : (
                    <p className="text-muted">No recommendations yet.</p>
                )}
            </div>
        </div>
    );

    return (
        <div className="container mt-4">
            <h1>Recommender</h1>
            <div className="mb-4">
                <label htmlFor="itemId" className="form-label">Select an Item ID:</label>
                <select
                    id="itemId"
                    className="form-select"
                    value={itemId}
                    onChange={(e) => setItemId(e.target.value)}
                >
                    <option value="">-- Choose an item --</option>
                    {validItemIds.map((id) => (
                        <option key={id} value={id}>{id}</option>
                    ))}
                </select>

                <button
                    className="btn btn-primary mt-2"
                    onClick={handleRecommend}
                    disabled={!itemId}
                >
                    Get Recommendations
                </button>
            </div>

            {renderResultList('Collaborative Filtering', results.collaborative)}
            {renderResultList('Content-Based Filtering', results.content)}
            {renderResultList('Azure ML Model', results.azure)}
        </div>
    );

};
export default Recommender;
