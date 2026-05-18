import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Upload, Briefcase, CheckCircle, XCircle, RefreshCw, ExternalLink, FileText, Settings, Save, AlertCircle } from 'lucide-react';

const API_BASE = 'http://localhost:8000/api';

function App() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');
  const [isError, setIsError] = useState(false);
  
  // Search Preferences
  const [keywords, setKeywords] = useState('');
  const [locations, setLocations] = useState('');
  const [jobType, setJobType] = useState('All');
  const [expLevel, setExpLevel] = useState('All');
  const [savingPrefs, setSavingPrefs] = useState(false);

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE}/jobs`);
      setJobs(response.data);
    } catch (error) {
      console.error('Error fetching jobs:', error);
    }
    setLoading(false);
  };

  const fetchPreferences = async () => {
    try {
      const response = await axios.get(`${API_BASE}/preferences`);
      setKeywords(response.data.keywords);
      setLocations(response.data.locations);
      setJobType(response.data.job_type || 'All');
      setExpLevel(response.data.experience_level || 'All');
    } catch (error) {
      console.error('Error fetching preferences:', error);
    }
  };

  useEffect(() => {
    fetchJobs();
    fetchPreferences();
    const interval = setInterval(fetchJobs, 30000); // Poll every 30s
    return () => clearInterval(interval);
  }, []);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    setIsError(false);
    setMessage('Uploading and parsing resume...');
    
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API_BASE}/resume/upload`, formData);
      if (response.data.status === 'success') {
        setMessage(response.data.message);
        setIsError(false);
      } else {
        setMessage(response.data.message);
        setIsError(true);
      }
    } catch (error) {
      setMessage('Server connection failed. Is the backend running?');
      setIsError(true);
    }
    setUploading(false);
    setTimeout(() => setMessage(''), 8000);
  };

  const savePreferences = async () => {
    setSavingPrefs(true);
    try {
      const response = await axios.post(`${API_BASE}/preferences`, {
        keywords,
        locations,
        job_type: jobType,
        experience_level: expLevel
      });
      setMessage(response.data.message);
      setIsError(false);
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      setMessage('Failed to save preferences');
      setIsError(true);
    }
    setSavingPrefs(false);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-sans selection:bg-blue-500/30">
      {/* Top Banner */}
      <header className="bg-slate-900/50 border-b border-slate-800 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="bg-blue-600 p-2 rounded-xl shadow-lg shadow-blue-900/20">
              <Briefcase className="text-white" size={28} />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white">JobSentinel</h1>
              <p className="text-xs text-slate-500 font-medium uppercase tracking-widest">Auto-Hunt Active</p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="relative group">
              <input type="file" id="resume-upload" className="hidden" accept=".pdf" onChange={handleFileUpload} disabled={uploading} />
              <label htmlFor="resume-upload" className={`flex items-center gap-2 px-4 py-2 rounded-lg font-bold text-sm cursor-pointer transition-all border ${
                uploading ? 'bg-slate-800 border-slate-700 text-slate-500' : 'bg-slate-800 border-slate-700 hover:border-blue-500 text-slate-300 hover:text-white'
              }`}>
                {uploading ? <RefreshCw className="animate-spin" size={18} /> : <Upload size={18} />}
                {uploading ? 'Parsing...' : 'Update Resume'}
              </label>
            </div>
            <button onClick={fetchJobs} className="p-2 rounded-lg bg-slate-800 border border-slate-700 hover:border-blue-500 text-slate-400 hover:text-white transition-all">
              <RefreshCw size={20} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Simple Notification Toast */}
        {message && (
          <div className={`mb-8 p-4 rounded-xl border flex items-center gap-3 animate-in fade-in slide-in-from-top-2 ${
            isError ? 'bg-red-500/10 border-red-500/20 text-red-400' : 'bg-green-500/10 border-green-500/20 text-green-400'
          }`}>
            {isError ? <AlertCircle size={20} /> : <CheckCircle size={20} />}
            <span className="font-medium text-sm">{message}</span>
          </div>
        )}

        {/* Configuration Section */}
        <section className="bg-slate-900 rounded-2xl border border-slate-800 p-8 mb-12 shadow-sm">
          <h2 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
            <Settings size={20} className="text-blue-500" /> Hunt Preferences
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Job Keywords</label>
              <input
                type="text"
                value={keywords}
                onChange={(e) => setKeywords(e.target.value)}
                placeholder="e.g. Frontend, React"
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 focus:border-blue-500 outline-none transition-all text-sm"
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Location</label>
              <input
                type="text"
                value={locations}
                onChange={(e) => setLocations(e.target.value)}
                placeholder="e.g. Remote, NY"
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 focus:border-blue-500 outline-none transition-all text-sm"
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Job Type</label>
              <select
                value={jobType}
                onChange={(e) => setJobType(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 focus:border-blue-500 outline-none transition-all text-sm appearance-none"
              >
                <option value="All">All Types</option>
                <option value="F">Full-time</option>
                <option value="P">Part-time</option>
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Exp. Level</label>
              <select
                value={expLevel}
                onChange={(e) => setExpLevel(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 focus:border-blue-500 outline-none transition-all text-sm appearance-none"
              >
                <option value="All">All Levels</option>
                <option value="2">Fresher (Entry)</option>
                <option value="4">Experienced (Mid-Senior)</option>
              </select>
            </div>
          </div>
          <div className="mt-8 flex justify-end">
            <button
              onClick={savePreferences}
              disabled={savingPrefs}
              className="bg-blue-600 hover:bg-blue-500 text-white px-8 py-2.5 rounded-xl font-bold transition-all disabled:opacity-50 shadow-lg shadow-blue-600/20 flex items-center gap-2"
            >
              {savingPrefs ? <RefreshCw className="animate-spin" size={20} /> : <Save size={20} />}
              {savingPrefs ? 'Saving...' : 'Apply & Restart Search'}
            </button>
          </div>
        </section>

        {/* Jobs Grid */}
        <section>
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              Discovered Opportunities
              <span className="bg-slate-800 text-slate-400 px-2 py-0.5 rounded-md text-xs">{jobs.length}</span>
            </h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {jobs.map((job) => (
              <div key={job.job_id} className="bg-slate-900 rounded-2xl p-6 border border-slate-800 hover:border-blue-500/50 transition-all group relative overflow-hidden">
                <div className="flex justify-between items-start mb-4 relative z-10">
                  <div className="space-y-1">
                    <h3 className="font-bold text-white leading-tight group-hover:text-blue-400 transition-colors line-clamp-2">{job.title}</h3>
                    <p className="text-sm text-slate-400 font-medium">{job.company}</p>
                  </div>
                  <div className={`px-2 py-1 rounded-md text-[10px] font-black uppercase tracking-tighter border ${
                    job.status === 'tailored' ? 'bg-green-500/10 border-green-500/20 text-green-500' : 'bg-slate-800 border-slate-700 text-slate-500'
                  }`}>
                    {job.status}
                  </div>
                </div>

                <div className="space-y-3 mb-6 relative z-10">
                  <div className="flex justify-between items-end mb-1">
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Match Score</span>
                    <span className="text-lg font-mono font-black text-white">{job.ats_score || 0}%</span>
                  </div>
                  <div className="bg-slate-950 h-1.5 rounded-full overflow-hidden border border-slate-800">
                    <div 
                      className={`h-full transition-all duration-1000 ${
                        job.ats_score >= 80 ? 'bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.5)]' : job.ats_score >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${job.ats_score || 0}%` }}
                    />
                  </div>
                </div>

                <div className="flex gap-3 relative z-10">
                  <a
                    href={job.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 flex items-center justify-center gap-2 bg-slate-800 hover:bg-slate-700 text-white py-2 rounded-xl transition-all text-xs font-bold border border-slate-700"
                  >
                    <ExternalLink size={14} /> View
                  </a>
                  {job.status === 'tailored' && (
                    <button className="flex-1 flex items-center justify-center gap-2 bg-blue-600/10 hover:bg-blue-600/20 text-blue-400 py-2 rounded-xl transition-all text-xs font-bold border border-blue-400/20">
                      <FileText size={14} /> Resume
                    </button>
                  )}
                </div>
                
                <div className="mt-5 pt-4 border-t border-slate-800 text-[10px] text-slate-600 font-bold uppercase flex justify-between">
                  <span>LinkedIn</span>
                  <span>{new Date(job.processed_at).toLocaleDateString()}</span>
                </div>
              </div>
            ))}
          </div>
          
          {jobs.length === 0 && !loading && (
            <div className="text-center py-32 bg-slate-900/50 rounded-3xl border border-dashed border-slate-800">
              <div className="bg-slate-800 w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <Briefcase size={32} className="text-slate-600" />
              </div>
              <p className="text-slate-400 font-medium text-lg">No matches found yet.</p>
              <p className="text-slate-600 text-sm mt-1">Refine your preferences above to broaden the search.</p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;
