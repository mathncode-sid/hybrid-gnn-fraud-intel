import { useState } from 'react';
import axios from 'axios';
import { ShieldAlert, ShieldCheck, Activity, Search } from 'lucide-react';

export default function Transactions() {
  // State to hold the form data
  const [formData, setFormData] = useState({
    transaction_id: 'TXN_' + Math.floor(Math.random() * 1000000),
    sender_id: 'USER_123',
    receiver_id: 'USER_999',
    amount: 500,
    transactions_last_24hr: 1,
    hour: 14
  });

  // State to hold the AI response
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Handle form input changes
  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  // Send the transaction to FastAPI
  const handlePredict = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setPrediction(null);
    
    try {
      // Hit your local FastAPI server
      const response = await axios.post('http://127.0.0.1:8000/predict', {
        ...formData,
        amount: parseFloat(formData.amount),
        transactions_last_24hr: parseInt(formData.transactions_last_24hr),
        hour: parseInt(formData.hour)
      });
      setPrediction(response.data);
    } catch (err) {
      console.error(err);
      setError('Failed to connect to the AI Engine. Is FastAPI running on port 8000?');
    }
    setLoading(false);
  };

  // Helper function to style the badge based on the AI's decision
  const getBadgeStyle = (decision) => {
    if (decision === 'AUTO_CLEARED_SAFE') return 'bg-green-100 text-green-800 border-green-200';
    if (decision === 'REQUIRE_HUMAN') return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    return 'bg-red-100 text-red-800 border-red-200';
  };

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Live Transaction Monitor</h1>
        <p className="text-gray-500">Tier 2 AI Analyst Console</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        
        {/* LEFT COLUMN: The Simulator Form */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <h2 className="text-lg font-semibold flex items-center gap-2 mb-6 border-b pb-4">
            <Activity className="text-brandPrimary" size={20} /> 
            Simulate Transaction
          </h2>
          
          <form onSubmit={handlePredict} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Amount (Ksh)</label>
                <input type="number" name="amount" value={formData.amount} onChange={handleChange} required 
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brandPrimary outline-none" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Velocity (Last 24h)</label>
                <input type="number" name="transactions_last_24hr" value={formData.transactions_last_24hr} onChange={handleChange} required 
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brandPrimary outline-none" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Sender ID</label>
                <input type="text" name="sender_id" value={formData.sender_id} onChange={handleChange} required 
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brandPrimary outline-none" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Receiver ID</label>
                <input type="text" name="receiver_id" value={formData.receiver_id} onChange={handleChange} required 
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brandPrimary outline-none" />
              </div>
            </div>
            
            <button type="submit" disabled={loading} 
              className="w-full mt-6 bg-brandPrimary hover:bg-indigo-700 text-white font-bold py-3 px-4 rounded-lg transition-colors disabled:bg-indigo-300">
              {loading ? 'Analyzing Graph & Running Models...' : 'Process Transaction'}
            </button>
          </form>
          {error && <p className="text-red-500 text-sm mt-4 font-medium">{error}</p>}
        </div>

        {/* RIGHT COLUMN: The AI Results */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex flex-col">
          <h2 className="text-lg font-semibold flex items-center gap-2 mb-6 border-b pb-4">
            <Search className="text-brandPrimary" size={20} /> 
            AI Analysis Results
          </h2>
          
          {!prediction && !loading && (
             <div className="flex-1 flex items-center justify-center text-gray-400 border-2 border-dashed border-gray-200 rounded-lg p-8">
               Waiting for transaction input...
             </div>
          )}

          {loading && (
            <div className="flex-1 flex flex-col items-center justify-center text-brandPrimary animate-pulse">
              <Activity size={48} className="mb-4" />
              <p className="font-medium">Querying Neo4j & Running XGBoost...</p>
            </div>
          )}

          {prediction && (
            <div className={`p-6 rounded-lg border-l-4 shadow-sm bg-gray-50 ${
              prediction.decision === 'AUTO_CLEARED_SAFE' ? 'border-l-green-500' : 
              prediction.decision === 'REQUIRE_HUMAN' ? 'border-l-yellow-500' : 'border-l-red-500'
            }`}>
              <div className="flex justify-between items-center border-b border-gray-200 pb-4 mb-4">
                <div>
                  <p className="text-sm text-gray-500 font-medium uppercase tracking-wider mb-1">Fraud Risk Score</p>
                  <h3 className="text-3xl font-bold text-gray-900">{(prediction.risk_score * 100).toFixed(1)}%</h3>
                </div>
                {prediction.decision === 'AUTO_CLEARED_SAFE' ? (
                  <ShieldCheck className="text-green-500" size={48} />
                ) : (
                  <ShieldAlert className={prediction.decision === 'AUTO_FREEZE' ? 'text-red-500' : 'text-yellow-500'} size={48} />
                )}
              </div>
              
              <div className="space-y-3">
                <p className="flex items-center gap-2">
                  <strong className="text-gray-700">System Action:</strong> 
                  <span className={`px-3 py-1 rounded-full text-xs font-bold border ${getBadgeStyle(prediction.decision)}`}>
                    {prediction.decision.replace(/_/g, ' ')}
                  </span>
                </p>
                <p><strong className="text-gray-700">AI Reasoning:</strong> <span className="text-gray-600">{prediction.reason}</span></p>
                <p><strong className="text-gray-700">Transaction ID:</strong> <span className="text-gray-600 font-mono text-sm">{prediction.transaction_id}</span></p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}