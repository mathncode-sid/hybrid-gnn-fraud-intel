import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Transactions from './pages/Transaction';
import FraudNetwork from './pages/FraudNetwork'; 

// Placeholders for remaining pages
const Dashboard = () => <div><h1 className="text-2xl font-bold mb-4">Dashboard Overview</h1><p>KPIs and Charts will go here.</p></div>;
const Alerts = () => <div><h1 className="text-2xl font-bold mb-4">Review Queue</h1></div>;

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/transactions" element={<Transactions />} />
          <Route path="/network" element={<FraudNetwork />} /> {/*  NEW ROUTE */}
          <Route path="/alerts" element={<Alerts />} />
          <Route path="*" element={<div>Page under construction</div>} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;