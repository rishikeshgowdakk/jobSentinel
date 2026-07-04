import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Upload, Briefcase, CheckCircle, XCircle, RefreshCw, ExternalLink, FileText, Settings, Save, AlertCircle, Activity, Terminal, ShieldAlert } from 'lucide-react';

const API_BASE = 'http://localhost:8000/api';
const WS_BASE = 'ws://localhost:8000/api/ws/stream';

function App() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');
  const [isError, setIsError] = useState(false);
  
  // Real-time Logs
  const [logs, setLogs] = useState([]);
  const logEndRef = useRef(null);
  
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
    const ws = new WebSocket(WS_BASE);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'log') {
        setLogs(prev => [...prev.slice(-49), data.message]);
      } else if (data.type === 'new_job') {
        setJobs(prev => [data.data, ...prev]);
      }
    };
    return () => ws.close();
  }, []);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const response = await axios.post(`${API_BASE}/resume/upload`, formData);
      setMessage(response.data.message);
      setIsError(response.data.status !== 'success');
    } catch (error) {
      setMessage('Server connection failed.');
      setIsError(true);
    }
    setUploading(false);
    setTimeout(() => setMessage(''), 5000);
  };

  const savePreferences = async () => {
    setSavingPrefs(true);
    try {
      const response = await axios.post(`${API_BASE}/preferences`, {
        keywords, locations, job_type: jobType, experience_level: expLevel
      });
      setMessage(response.data.message);
    } catch (error) {
      setMessage('Failed to save preferences');
    }
    setSavingPrefs(false);
    setTimeout(() => setMessage(''), 3000);
  };

  return (
    <div className="min-h-screen bg-black text-slate-300 font-sans selection:bg-blue-500/30 overflow-x-hidden">
      <header className="bg-slate-900/40 border-b border-white/5 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-[1600px] mx-auto px-8 py-5 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <div className="bg-blue-600 p-2.5 rounded-2xl shadow-2xl shadow-blue-500/20">
              <Activity className="text-white animate-pulse" size={24} />
            </div>
            <div>
              <h1 className="text-xl font-black tracking-tight text-white uppercase italic">JobSentinel <span className="text-blue-500 not-italic font-normal">Live</span></h1>
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-ping" />
                <span className="text-[10px] text-slate-500 font-black uppercase tracking-[0.2em]">Active Hunt</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <input type="file" id="resume-upload" className="hidden" accept=".pdf" onChange={handleFileUpload} />
            <label htmlFor="resume-upload" className="px-5 py-2.5 rounded-xl font-black text-[11px] uppercase tracking-widest cursor-pointer bg-white/5 border border-white/10 hover:border-blue-500 hover:text-white transition-all">
              {uploading ? 'Parsing...' : 'Update Context'}
            </label>
            <button onClick={fetchJobs} className="p-2.5 rounded-xl bg-white/5 border border-white/10 hover:border-blue-500 text-slate-400 hover:text-white transition-all">
              <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-[1600px] mx-auto px-8 py-10 grid grid-cols-1 xl:grid-cols-12 gap-10">
        <div className="xl:col-span-4 space-y-10">
          <section className="bg-slate-900/50 rounded-3xl border border-white/5 p-8 shadow-2xl">
            <h2 className="text-xs font-black text-slate-500 uppercase tracking-[0.3em] mb-8 flex items-center gap-3">
              <Settings size={16} className="text-blue-500" /> Hunt Parameters
            </h2>
            <div className="space-y-6">
              <div className="space-y-2">
                <label className="text-[10px] font-black text-slate-600 uppercase tracking-widest">Target Keywords</label>
                <input type="text" value={keywords} onChange={(e) => setKeywords(e.target.value)} placeholder="e.g. SDE, Frontend" className="w-full bg-black/40 border border-white/5 rounded-2xl px-5 py-3.5 focus:border-blue-500 outline-none transition-all text-sm font-medium" />
              </div>
              <div className="space-y-2">
                <label className="text-[10px] font-black text-slate-600 uppercase tracking-widest">Geofence (Strict)</label>
                <input type="text" value={locations} onChange={(e) => setLocations(e.target.value)} placeholder="e.g. Remote, London" className="w-full bg-black/40 border border-white/5 rounded-2xl px-5 py-3.5 focus:border-blue-500 outline-none transition-all text-sm font-medium" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-600 uppercase tracking-widest">Commitment</label>
                  <select value={jobType} onChange={(e) => setJobType(e.target.value)} className="w-full bg-black/40 border border-white/5 rounded-2xl px-5 py-3.5 focus:border-blue-500 outline-none text-sm appearance-none">
                    <option value="All">All Types</option>
                    <option value="F">Full-time</option>
                    <option value="P">Part-time</option>
                    <option value="I">Internship</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-600 uppercase tracking-widest">Seniority</label>
                  <select value={expLevel} onChange={(e) => setExpLevel(e.target.value)} className="w-full bg-black/40 border border-white/5 rounded-2xl px-5 py-3.5 focus:border-blue-500 outline-none text-sm appearance-none">
                    <option value="All">All Levels</option>
                    <option value="2">Fresher</option>
                    <option value="4">Experienced</option>
                  </select>
                </div>
              </div>
              <button onClick={savePreferences} disabled={savingPrefs} className="w-full bg-blue-600 hover:bg-blue-500 text-white py-4 rounded-2xl font-black text-xs uppercase tracking-[0.2em] transition-all shadow-xl shadow-blue-600/20">
                {savingPrefs ? 'Pushing Config...' : 'Apply Strict Parameters'}
              </button>
            </div>
          </section>

          <section className="bg-slate-900/80 rounded-3xl border border-white/5 p-8 shadow-2xl h-[400px] flex flex-col">
            <h2 className="text-xs font-black text-slate-500 uppercase tracking-[0.3em] mb-6 flex items-center gap-3">
              <Terminal size={16} className="text-green-500" /> Activity Stream
            </h2>
            <div className="flex-1 bg-black/60 rounded-2xl p-5 font-mono text-[11px] overflow-y-auto space-y-2 border border-white/5">
              {logs.map((log, i) => (
                <div key={i} className="text-green-500/80 leading-relaxed break-all">
                  <span className="text-slate-700 mr-2">[{new Date().toLocaleTimeString()}]</span>
                  {log}
                </div>
              ))}
              <div ref={logEndRef} />
            </div>
          </section>
        </div>

        <div className="xl:col-span-8">
          <h2 className="text-xl font-black text-white uppercase italic tracking-widest flex items-center gap-4 mb-10">
            Real-time Discoveries
            <span className="bg-blue-600 text-[10px] font-black not-italic px-3 py-1 rounded-full text-white">{jobs.length} Hits</span>
          </h2>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {jobs.map((job) => (
              <div key={job.job_id} className={`group bg-slate-900/40 rounded-[2rem] p-8 border transition-all duration-500 relative overflow-hidden ${
                job.status === 'tailored' ? 'border-blue-500/30 bg-blue-500/[0.02]' : 'border-white/5'
              }`}>
                <div className="relative z-10">
                  <div className="flex justify-between items-start mb-6">
                    <div className="space-y-2 max-w-[70%]">
                      <h3 className="text-lg font-black text-white leading-tight line-clamp-2 group-hover:text-blue-400 transition-colors">{job.title}</h3>
                      <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">{job.company}</p>
                    </div>
                    <div className={`px-4 py-1.5 rounded-full text-[9px] font-black uppercase tracking-widest border ${
                      job.status === 'tailored' ? 'bg-blue-500/10 border-blue-500/20 text-blue-400' : 'bg-slate-800/50 border-white/5 text-slate-600'
                    }`}>
                      {job.source}
                    </div>
                  </div>

                  {job.ats_score === 0 && job.rejection_reason && (
                    <div className="mb-6 p-4 bg-red-500/5 border border-red-500/10 rounded-2xl flex items-center gap-3 text-red-400">
                      <ShieldAlert size={16} />
                      <span className="text-[10px] font-black uppercase tracking-widest">{job.rejection_reason}</span>
                    </div>
                  )}

                  <div className="mb-8">
                    <div className="flex justify-between items-center mb-3">
                      <span className="text-[10px] font-black text-slate-600 uppercase tracking-widest">Compatibility</span>
                      <span className={`text-xl font-mono font-black ${
                        job.ats_score >= 80 ? 'text-blue-400' : 'text-slate-500'
                      }`}>{job.ats_score || 0}%</span>
                    </div>
                    <div className="h-1 bg-white/5 rounded-full overflow-hidden">
                      <div className={`h-full transition-all duration-[2s] ${
                        job.ats_score >= 80 ? 'bg-blue-500' : 'bg-slate-700'
                      }`} style={{ width: `${job.ats_score || 0}%` }} />
                    </div>
                  </div>

                  <div className="flex gap-4">
                    <a href={job.url} target="_blank" className="flex-1 bg-white/5 hover:bg-white/10 text-white py-3 rounded-2xl text-[10px] font-black uppercase tracking-widest text-center transition-all border border-white/5">
                      Explore JD
                    </a>
                    {job.status === 'tailored' && (
                      <button className="flex-1 bg-blue-600/10 hover:bg-blue-600/20 text-blue-400 py-3 rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all border border-blue-500/20">
                        Tailored PDF
                      </button>
                    )}
                  </div>
                </div>
                <div className="absolute -right-10 -top-10 w-40 h-40 bg-blue-500/5 rounded-full blur-[80px]" />
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
