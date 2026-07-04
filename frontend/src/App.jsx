import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { 
  Activity, RefreshCw, Settings, Terminal, Briefcase, 
  Upload, BookOpen, Sparkles, LineChart, CheckCircle,
  Bookmark, ChevronRight, TrendingUp, Award, Clock, 
  User, Check, Phone, Mail, MapPin, AlertCircle
} from 'lucide-react';

const API_BASE = 'http://localhost:8000/api';
const WS_BASE = 'ws://localhost:8000/api/ws/stream';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  
  // Analytics and profile state
  const [analytics, setAnalytics] = useState({
    totalJobs: 0, matchedCount: 0, savedCount: 0, appliedCount: 0,
    interviewCount: 0, rejectedCount: 0, successRate: 0,
    resumeScore: 0, profileStrength: 0, marketDemandScore: 0
  });
  const [profile, setProfile] = useState(null);
  const [marketInsights, setMarketInsights] = useState(null);
  const [upskillPlan, setUpskillPlan] = useState([]);
  const [resumeSuggestions, setResumeSuggestions] = useState(null);
  
  // Search parameters & inputs
  const [keywords, setKeywords] = useState('');
  const [locations, setLocations] = useState('');
  const [jobType, setJobType] = useState('All');
  const [expLevel, setExpLevel] = useState('All');
  
  // UI feedback
  const [uploading, setUploading] = useState(false);
  const [savingPrefs, setSavingPrefs] = useState(false);
  const [message, setMessage] = useState('');
  const [isError, setIsError] = useState(false);
  
  // WebSocket console logs
  const [logs, setLogs] = useState([]);
  const logEndRef = useRef(null);

  // Modal and paste state
  const [showPasteModal, setShowPasteModal] = useState(false);
  const [pastedResumeText, setPastedResumeText] = useState('');
  const [pasting, setPasting] = useState(false);

  // Filters for job feed
  const [filterKeyword, setFilterKeyword] = useState('');
  const [filterRemote, setFilterRemote] = useState('All');
  const [filterSource, setFilterSource] = useState('All');
  const [filterMinScore, setFilterMinScore] = useState(0);

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

  const fetchAnalytics = async () => {
    try {
      const response = await axios.get(`${API_BASE}/analytics`);
      setAnalytics(response.data);
    } catch (error) {
      console.error('Error fetching analytics:', error);
    }
  };

  const fetchProfile = async () => {
    try {
      const response = await axios.get(`${API_BASE}/profile`);
      setProfile(response.data);
    } catch (error) {
      console.error('Error fetching profile:', error);
    }
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

  const fetchInsights = async () => {
    try {
      const response = await axios.get(`${API_BASE}/market-insights`);
      setMarketInsights(response.data);
    } catch (error) {
      console.error('Error fetching market insights:', error);
    }
  };

  const fetchUpskillPlan = async () => {
    try {
      const response = await axios.get(`${API_BASE}/up-skill`);
      setUpskillPlan(response.data);
    } catch (error) {
      console.error('Error fetching upskill plan:', error);
    }
  };

  const fetchResumeSuggestions = async () => {
    try {
      const response = await axios.get(`${API_BASE}/resume-suggestions`);
      setResumeSuggestions(response.data);
    } catch (error) {
      console.error('Error fetching resume suggestions:', error);
    }
  };

  const loadAllData = () => {
    fetchJobs();
    fetchAnalytics();
    fetchProfile();
    fetchPreferences();
    fetchInsights();
    fetchUpskillPlan();
    fetchResumeSuggestions();
  };

  useEffect(() => {
    loadAllData();
    
    const ws = new WebSocket(WS_BASE);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'log') {
        setLogs(prev => [...prev.slice(-49), data.message]);
      } else if (data.type === 'new_job') {
        setJobs(prev => [data.data, ...prev]);
        fetchAnalytics(); // Refresh counters
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
    setMessage('Uploading and analyzing resume...');
    setIsError(false);
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await axios.post(`${API_BASE}/resume/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      if (response.data.status === 'success') {
        setMessage(response.data.message);
        loadAllData(); // Reload parsed values
      } else {
        setMessage(response.data.message);
        setIsError(true);
      }
    } catch (error) {
      console.error('Upload error details:', error);
      setMessage('Failed to upload resume.');
      setIsError(true);
    }
    setUploading(false);
    e.target.value = ''; // Reset input to allow selecting same file again
    setTimeout(() => setMessage(''), 5000);
  };

  const handleResumePaste = async () => {
    if (!pastedResumeText.trim()) return;
    setPasting(true);
    setMessage('Analyzing pasted resume...');
    setIsError(false);
    try {
      const response = await axios.post(`${API_BASE}/resume/paste`, { text: pastedResumeText });
      if (response.data.status === 'success') {
        setMessage(response.data.message);
        setPastedResumeText('');
        setShowPasteModal(false);
        loadAllData(); // Reload parsed values
      } else {
        setMessage(response.data.message);
        setIsError(true);
      }
    } catch (error) {
      setMessage('Failed to connect to API server.');
      setIsError(true);
    }
    setPasting(false);
    setTimeout(() => setMessage(''), 5000);
  };

  const handleDeleteResume = async () => {
    if (!window.confirm("Are you sure you want to delete your parsed resume profile? This cannot be undone.")) return;
    setMessage('Removing resume...');
    setIsError(false);
    try {
      const response = await axios.delete(`${API_BASE}/resume`);
      if (response.data.status === 'success') {
        setMessage(response.data.message);
        loadAllData(); // Reload parsed values (will clear the profile)
      } else {
        setMessage(response.data.message);
        setIsError(true);
      }
    } catch (error) {
      setMessage('Failed to delete resume profile.');
      setIsError(true);
    }
    setTimeout(() => setMessage(''), 5000);
  };

  const savePreferences = async () => {
    setSavingPrefs(true);
    try {
      const response = await axios.post(`${API_BASE}/preferences`, {
        keywords, locations, job_type: jobType, experience_level: expLevel
      });
      setMessage(response.data.message);
      setIsError(false);
      loadAllData();
    } catch (error) {
      setMessage('Failed to save preferences');
      setIsError(true);
    }
    setSavingPrefs(false);
    setTimeout(() => setMessage(''), 3000);
  };

  const updateJobStatus = async (jobId, newStatus) => {
    try {
      await axios.post(`${API_BASE}/jobs/${jobId}/status`, { status: newStatus });
      setJobs(prev => prev.map(j => j.job_id === jobId ? { ...j, status: newStatus } : j));
      fetchAnalytics();
    } catch (error) {
      console.error('Error updating job status:', error);
    }
  };

  const filteredJobs = jobs.filter(job => {
    const matchesKeyword = !filterKeyword || 
      job.title.toLowerCase().includes(filterKeyword.toLowerCase()) || 
      job.company.toLowerCase().includes(filterKeyword.toLowerCase()) ||
      (job.skills && job.skills.toLowerCase().includes(filterKeyword.toLowerCase()));
      
    const matchesRemote = filterRemote === 'All' || 
      (filterRemote === 'Remote' && job.remote_status?.toLowerCase() === 'remote') ||
      (filterRemote === 'Onsite' && job.remote_status?.toLowerCase() === 'onsite') ||
      (filterRemote === 'Hybrid' && job.remote_status?.toLowerCase() === 'hybrid');
      
    const matchesSource = filterSource === 'All' || job.source === filterSource;
    const matchesScore = job.matchScore >= filterMinScore;
    
    return matchesKeyword && matchesRemote && matchesSource && matchesScore;
  });

  return (
    <div className="min-h-screen text-slate-100 flex flex-col lg:flex-row antialiased select-none font-sans">
      
      {/* LEFT COLUMN: Sidebar Navigation & Identity (Sleek minimalist 00 format) */}
      <aside className="w-full lg:w-[400px] border-r border-carbon bg-black/70 p-10 flex flex-col justify-between shrink-0 relative z-10">
        <div className="space-y-12">
          {/* Logo / Concept Name */}
          <div className="space-y-1">
            <h1 className="text-2xl font-bold tracking-[0.15em] text-white uppercase font-sans">
              JobSentinel
            </h1>
            <p className="text-[10px] font-medium tracking-[0.3em] uppercase text-carbon-muted">
              Autonomous Intelligence Agent
            </p>
          </div>

          {/* Blink scanner status */}
          <div className="flex items-center gap-3 bg-white/[0.02] border border-white/5 py-3 px-5 rounded-none">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-[9px] font-bold tracking-[0.2em] uppercase text-slate-400">
              Active Scanning Loop
            </span>
          </div>

          {/* Minimalist Tab Navigation matching "01." concept layout */}
          <nav className="flex flex-col gap-6">
            {[
              { id: 'dashboard', num: '00', label: 'Overview' },
              { id: 'jobs', num: '01', label: 'Discoveries' },
              { id: 'upskill', num: '02', label: 'Skills Path' },
              { id: 'critique', num: '03', label: 'ATS Optimize' },
              { id: 'profile', num: '04', label: 'Profile' }
            ].map(tab => (
              <button 
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className="flex items-center text-left group outline-none"
              >
                <span className={`text-[10px] font-bold font-mono tracking-widest mr-4 transition-all duration-300 ${
                  activeTab === tab.id ? 'text-white' : 'text-carbon-muted group-hover:text-slate-300'
                }`}>
                  {tab.num}.
                </span>
                <span className={`text-xs font-bold uppercase tracking-[0.25em] transition-all duration-300 ${
                  activeTab === tab.id ? 'text-white border-b border-white pb-1' : 'text-slate-500 group-hover:text-white'
                }`}>
                  {tab.label}
                </span>
              </button>
            ))}
          </nav>
        </div>

        {/* Brand/User Details Card at bottom */}
        <div className="space-y-6 pt-10">
          <div className="thin-accent-line" />
          <div className="space-y-2 text-xs">
            <div className="text-[9px] uppercase tracking-widest text-carbon-muted font-bold">Active Candidate</div>
            <div className="font-bold text-white tracking-wide">{profile?.name || 'Guest User'}</div>
            <div className="text-[10px] text-slate-500 leading-relaxed font-light">
              {profile?.current_role || 'No active profile loaded. Upload your resume to start semantic scoring.'}
            </div>
          </div>

          {/* Quick upload options */}
          <div className="flex gap-2.5">
            <input type="file" id="resume-upload" className="hidden" accept=".pdf,.txt,.md" onChange={handleFileUpload} disabled={uploading} />
            <label htmlFor="resume-upload" className="flex-1 text-center py-3 bg-white text-black font-bold text-[9px] uppercase tracking-widest cursor-pointer hover:bg-slate-200 transition-all">
              {uploading ? 'Processing...' : 'Upload Resume'}
            </label>
            <button 
              onClick={() => setShowPasteModal(true)} 
              className="flex-1 text-center py-3 bg-zinc-900 border border-zinc-800 text-white font-bold text-[9px] uppercase tracking-widest hover:bg-zinc-800 transition-all"
            >
              Paste Resume
            </button>
            <button 
              onClick={loadAllData} 
              className="p-3 bg-zinc-900 border border-zinc-800 text-slate-400 hover:text-white transition-all"
            >
              <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>
          
          {/* Global Message Banner */}
          {message && (
            <div className={`p-3 text-[10px] uppercase font-bold tracking-wider text-center ${
              isError ? 'bg-red-950/40 border border-red-900/50 text-red-400' : 'bg-zinc-900 border border-zinc-800 text-slate-300'
            }`}>
              {message}
            </div>
          )}
        </div>
      </aside>

      {/* RIGHT COLUMN: Tab Panel Contents */}
      <main className="flex-grow p-10 lg:p-14 overflow-y-auto max-h-screen relative z-10">
        
        {/* Tab 00: Overview / Dashboard */}
        {activeTab === 'dashboard' && (
          <div className="space-y-12">
            
            {/* Top Concept Header */}
            <div className="flex justify-between items-end border-b border-carbon pb-8">
              <div>
                <span className="text-[10px] font-bold font-mono tracking-widest text-carbon-muted uppercase block mb-1">00. Overview</span>
                <h2 className="text-xl font-bold uppercase tracking-[0.2em] text-white">System Telemetry</h2>
              </div>
              <div className="text-[10px] text-carbon-muted font-bold uppercase tracking-widest">
                Local Time: {new Date().toLocaleTimeString()}
              </div>
            </div>

            {/* Grid layout containing Metrics, Config, Logs */}
            <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">
              
              {/* Metric panel */}
              <div className="xl:col-span-4 carbon-panel p-8 space-y-8">
                <div>
                  <span className="text-[10px] font-bold text-carbon-muted font-mono uppercase block mb-1">01. Stats</span>
                  <h3 className="text-xs font-bold uppercase tracking-widest text-white">Semantic Metrics</h3>
                </div>

                <div className="space-y-6">
                  <div>
                    <div className="flex justify-between text-[10px] uppercase font-bold tracking-wider mb-2">
                      <span className="text-slate-500">Profile Strength</span>
                      <span className="text-white">{analytics.profileStrength}%</span>
                    </div>
                    <div className="w-full bg-zinc-900 h-1 rounded-none overflow-hidden">
                      <div className="bg-white h-full" style={{ width: `${analytics.profileStrength}%` }} />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-[10px] uppercase font-bold tracking-wider mb-2">
                      <span className="text-slate-500">Resume ATS Score</span>
                      <span className="text-white">{analytics.resumeScore}%</span>
                    </div>
                    <div className="w-full bg-zinc-900 h-1 rounded-none overflow-hidden">
                      <div className="bg-white h-full" style={{ width: `${analytics.resumeScore}%` }} />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-[10px] uppercase font-bold tracking-wider mb-2">
                      <span className="text-slate-500">Market Demand Index</span>
                      <span className="text-white">{analytics.marketDemandScore}%</span>
                    </div>
                    <div className="w-full bg-zinc-900 h-1 rounded-none overflow-hidden">
                      <div className="bg-white h-full" style={{ width: `${analytics.marketDemandScore}%` }} />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-[10px] uppercase font-bold tracking-wider mb-2">
                      <span className="text-slate-500">Success rate</span>
                      <span className="text-white">{analytics.successRate}%</span>
                    </div>
                    <div className="w-full bg-zinc-900 h-1 rounded-none overflow-hidden">
                      <div className="bg-white h-full" style={{ width: `${analytics.successRate}%` }} />
                    </div>
                  </div>
                </div>
              </div>

              {/* Preferences panel */}
              <div className="xl:col-span-4 carbon-panel p-8 space-y-8">
                <div>
                  <span className="text-[10px] font-bold text-carbon-muted font-mono uppercase block mb-1">02. Config</span>
                  <h3 className="text-xs font-bold uppercase tracking-widest text-white">Hunt Parameters</h3>
                </div>

                <div className="space-y-4 text-xs">
                  <div className="space-y-1">
                    <label className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Job Keywords</label>
                    <input type="text" value={keywords} onChange={(e) => setKeywords(e.target.value)} placeholder="e.g. Frontend Engineer, Golang" className="w-full bg-black/60 border border-zinc-800 p-2.5 focus:border-white outline-none text-white text-xs rounded-none" />
                  </div>
                  
                  <div className="space-y-1">
                    <label className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Cities</label>
                    <input type="text" value={locations} onChange={(e) => setLocations(e.target.value)} placeholder="e.g. Remote, Bangalore" className="w-full bg-black/60 border border-zinc-800 p-2.5 focus:border-white outline-none text-white text-xs rounded-none" />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1">
                      <label className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Type</label>
                      <select value={jobType} onChange={(e) => setJobType(e.target.value)} className="w-full bg-black/60 border border-zinc-800 p-2.5 focus:border-white outline-none text-slate-300 text-xs rounded-none">
                        <option value="All">All Types</option>
                        <option value="F">Full-time</option>
                        <option value="P">Part-time</option>
                        <option value="I">Internship</option>
                      </select>
                    </div>
                    <div className="space-y-1">
                      <label className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Seniority</label>
                      <select value={expLevel} onChange={(e) => setExpLevel(e.target.value)} className="w-full bg-black/60 border border-zinc-800 p-2.5 focus:border-white outline-none text-slate-300 text-xs rounded-none">
                        <option value="All">All Levels</option>
                        <option value="2">Fresher / Intern</option>
                        <option value="4">Experienced</option>
                      </select>
                    </div>
                  </div>

                  <button onClick={savePreferences} disabled={savingPrefs} className="w-full bg-white text-black py-3 font-bold text-[9px] uppercase tracking-widest hover:bg-slate-200 transition-all mt-2">
                    {savingPrefs ? 'Updating...' : 'Save Config'}
                  </button>
                </div>
              </div>

              {/* Logs Stream panel */}
              <div className="xl:col-span-4 carbon-panel p-8 flex flex-col h-[380px]">
                <div className="mb-4">
                  <span className="text-[10px] font-bold text-carbon-muted font-mono uppercase block mb-1">03. Logs</span>
                  <h3 className="text-xs font-bold uppercase tracking-widest text-white">System Logs</h3>
                </div>

                <div className="flex-1 bg-black/60 border border-zinc-850 p-4 font-mono text-[9px] overflow-y-auto space-y-2 leading-relaxed">
                  {logs.map((log, i) => (
                    <div key={i} className="text-slate-400 break-all">
                      <span className="text-zinc-600 mr-2">[{new Date().toLocaleTimeString()}]</span>
                      {log}
                    </div>
                  ))}
                  {logs.length === 0 && <div className="text-zinc-700">Awaiting scanning loops...</div>}
                  <div ref={logEndRef} />
                </div>
              </div>
            </div>

            {/* Bottom Market Intelligence */}
            <div className="carbon-panel p-8 space-y-6">
              <div>
                <span className="text-[10px] font-bold text-carbon-muted font-mono uppercase block mb-1">04. Market Demands</span>
                <h3 className="text-xs font-bold uppercase tracking-widest text-white">Career Intelligence Analytics</h3>
              </div>

              {marketInsights ? (
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 text-xs leading-relaxed">
                  <div className="lg:col-span-6 space-y-3">
                    <div className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Active Demands Summary</div>
                    <p className="text-slate-300 font-light border-l border-zinc-800 pl-4 py-1">
                      {marketInsights.insightsSummary}
                    </p>
                  </div>
                  
                  <div className="lg:col-span-3 space-y-3">
                    <div className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Trending Tech Gaps</div>
                    <div className="flex flex-wrap gap-1.5">
                      {marketInsights.trendingSkills?.map((skill, idx) => (
                        <span key={idx} className="px-2 py-0.5 bg-zinc-900 border border-zinc-800 text-slate-300 text-[10px] font-mono">
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="lg:col-span-3 space-y-3">
                    <div className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Stats Summary</div>
                    <div className="space-y-1.5 font-light">
                      <div className="flex justify-between"><span className="text-slate-500">Average Band:</span> <span className="font-bold text-white font-mono">{marketInsights.averageSalary}</span></div>
                      <div className="flex justify-between"><span className="text-slate-500">Top Hirers:</span> <span className="font-bold text-white text-right truncate max-w-[120px]">{marketInsights.mostHiringCompanies?.join(', ')}</span></div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-zinc-600 text-xs py-4">
                  Aggregating market trends. Real-time intelligence will populate as scanning proceeds.
                </div>
              )}
            </div>

            {/* Pipeline Tracker */}
            <div className="carbon-panel p-8 space-y-6">
              <div>
                <span className="text-[10px] font-bold text-carbon-muted font-mono uppercase block mb-1">05. Pipeline</span>
                <h3 className="text-xs font-bold uppercase tracking-widest text-white">Application Pipeline</h3>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-5 gap-6 text-center">
                <div className="border border-zinc-850 p-4">
                  <div className="text-slate-500 text-[9px] uppercase tracking-wider mb-1">Crawled</div>
                  <div className="text-xl font-bold font-mono text-white">{analytics.totalJobs}</div>
                </div>
                <div className="border border-zinc-850 p-4">
                  <div className="text-slate-500 text-[9px] uppercase tracking-wider mb-1">Match &ge; 80%</div>
                  <div className="text-xl font-bold font-mono text-white">{analytics.matchedCount}</div>
                </div>
                <div className="border border-zinc-850 p-4">
                  <div className="text-slate-500 text-[9px] uppercase tracking-wider mb-1">Saved</div>
                  <div className="text-xl font-bold font-mono text-white">{analytics.savedCount}</div>
                </div>
                <div className="border border-zinc-850 p-4">
                  <div className="text-slate-500 text-[9px] uppercase tracking-wider mb-1">Applied</div>
                  <div className="text-xl font-bold font-mono text-white">{analytics.appliedCount}</div>
                </div>
                <div className="border border-zinc-850 p-4 col-span-2 md:col-span-1">
                  <div className="text-slate-500 text-[9px] uppercase tracking-wider mb-1">Interviews</div>
                  <div className="text-xl font-bold font-mono text-white">{analytics.interviewCount}</div>
                </div>
              </div>
            </div>

          </div>
        )}

        {/* Tab 01: Discoveries / Jobs Feed */}
        {activeTab === 'jobs' && (
          <div className="space-y-12">
            <div className="flex justify-between items-end border-b border-carbon pb-8">
              <div>
                <span className="text-[10px] font-bold font-mono tracking-widest text-carbon-muted uppercase block mb-1">01. Discoveries</span>
                <h2 className="text-xl font-bold uppercase tracking-[0.2em] text-white">Active Postings</h2>
              </div>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-12 gap-10">
              {/* Filters sidebar */}
              <div className="xl:col-span-3 space-y-6">
                <div className="carbon-panel p-6 space-y-6 sticky top-6">
                  <h3 className="text-xs font-bold uppercase tracking-widest text-white">Filter Results</h3>
                  
                  <div className="space-y-4 text-xs">
                    <div className="space-y-1">
                      <label className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Query</label>
                      <input 
                        type="text" 
                        value={filterKeyword} 
                        onChange={(e) => setFilterKeyword(e.target.value)} 
                        placeholder="Title, Company, Skills..."
                        className="w-full bg-black/60 border border-zinc-800 p-2 focus:border-white outline-none text-white text-xs rounded-none" 
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Location Mode</label>
                      <select value={filterRemote} onChange={(e) => setFilterRemote(e.target.value)} className="w-full bg-black/60 border border-zinc-800 p-2 focus:border-white outline-none text-slate-300 text-xs rounded-none">
                        <option value="All">All Locations</option>
                        <option value="Remote">Remote Only</option>
                        <option value="Onsite">Onsite Only</option>
                        <option value="Hybrid">Hybrid Only</option>
                      </select>
                    </div>
                    <div className="space-y-1">
                      <label className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Source</label>
                      <select value={filterSource} onChange={(e) => setFilterSource(e.target.value)} className="w-full bg-black/60 border border-zinc-800 p-2 focus:border-white outline-none text-slate-300 text-xs rounded-none">
                        <option value="All">All Sources</option>
                        <option value="LinkedIn">LinkedIn</option>
                        <option value="Naukri">Naukri</option>
                        <option value="Wellfound">Wellfound</option>
                        <option value="YC Jobs">YC Jobs</option>
                      </select>
                    </div>
                    <div className="space-y-1">
                      <div className="flex justify-between items-center mb-1">
                        <label className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Min Match Score</label>
                        <span className="font-mono text-white">{filterMinScore}%</span>
                      </div>
                      <input 
                        type="range" 
                        min="0" 
                        max="100" 
                        value={filterMinScore} 
                        onChange={(e) => setFilterMinScore(Number(e.target.value))} 
                        className="w-full accent-white" 
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Opportunities Feed */}
              <div className="xl:col-span-9 space-y-6">
                <div className="flex justify-between items-center mb-2">
                  <div className="text-[10px] uppercase tracking-widest font-bold text-slate-500">
                    Showing {filteredJobs.length} opportunities matched
                  </div>
                </div>

                <div className="space-y-6">
                  {filteredJobs.map((job) => (
                    <div 
                      key={job.job_id} 
                      className={`carbon-panel p-6 border-l-2 transition-all duration-300 hover:border-slate-400 ${
                        job.matchScore >= 80 ? 'border-l-white' : 'border-l-transparent'
                      }`}
                    >
                      <div className="flex flex-col md:flex-row gap-6 justify-between">
                        {/* Job Details */}
                        <div className="space-y-4 flex-1">
                          <div className="flex flex-wrap gap-2 items-center text-[9px] font-mono">
                            <span className="px-2 py-0.5 bg-zinc-900 border border-zinc-850 text-slate-400">
                              {job.source}
                            </span>
                            {job.remote_status && (
                              <span className="px-2 py-0.5 bg-zinc-900 border border-zinc-850 text-slate-400">
                                {job.remote_status}
                              </span>
                            )}
                            {job.experience && (
                              <span className="px-2 py-0.5 bg-zinc-900 border border-zinc-850 text-slate-400">
                                {job.experience}
                              </span>
                            )}
                          </div>
                          
                          <div>
                            <h4 className="text-md font-bold text-white tracking-wide">{job.title}</h4>
                            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">{job.company} &bull; <span className="font-normal normal-case">{job.location}</span></p>
                          </div>
                          
                          <p className="text-xs text-slate-400 leading-relaxed font-light line-clamp-2">
                            {job.summary || job.description}
                          </p>

                          {/* Skill alignment tag arrays */}
                          <div className="space-y-2">
                            {job.matchedSkills && job.matchedSkills.length > 0 && (
                              <div className="flex flex-wrap items-center gap-1.5">
                                <span className="text-[8px] font-bold text-slate-500 uppercase tracking-wider mr-2">Matched:</span>
                                {job.matchedSkills.map((s, idx) => (
                                  <span key={idx} className="px-1.5 py-0.5 bg-zinc-900 border border-zinc-850 text-slate-300 text-[9px] font-mono">
                                    {s}
                                  </span>
                                ))}
                              </div>
                            )}
                            {job.missingSkills && job.missingSkills.length > 0 && (
                              <div className="flex flex-wrap items-center gap-1.5">
                                <span className="text-[8px] font-bold text-slate-500 uppercase tracking-wider mr-2">Missing:</span>
                                {job.missingSkills.map((s, idx) => (
                                  <span key={idx} className="px-1.5 py-0.5 bg-zinc-900 border border-red-950/20 text-red-400/80 text-[9px] font-mono">
                                    {s}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Analysis Scores & Actions */}
                        <div className="flex flex-row md:flex-col justify-between items-center md:items-end w-full md:w-auto border-t md:border-t-0 border-zinc-850 pt-4 md:pt-0 gap-4 shrink-0">
                          <div className="text-right">
                            <span className="text-[9px] text-slate-500 font-bold uppercase tracking-wider block mb-0.5">Match score</span>
                            <span className="text-2xl font-bold font-mono text-white">
                              {job.matchScore || 0}%
                            </span>
                          </div>

                          {job.recommendationReason && (
                            <div className="hidden lg:block max-w-[200px] text-right text-[9px] text-slate-500 leading-snug font-light italic">
                              "{job.recommendationReason.slice(0, 75)}..."
                            </div>
                          )}

                          <div className="flex gap-2">
                            {job.status !== 'applied' ? (
                              <button 
                                onClick={() => updateJobStatus(job.job_id, 'applied')}
                                className="px-4 py-2 bg-white text-black hover:bg-slate-200 text-[10px] font-bold uppercase tracking-widest transition-all"
                              >
                                Applied
                              </button>
                            ) : (
                              <span className="px-3 py-2 bg-zinc-900 border border-zinc-800 text-slate-400 text-[10px] font-bold uppercase tracking-widest flex items-center gap-1.5">
                                <Check size={10} /> Applied
                              </span>
                            )}
                            {job.status !== 'saved' && job.status !== 'applied' && (
                              <button 
                                onClick={() => updateJobStatus(job.job_id, 'saved')}
                                className="p-2 bg-zinc-900 border border-zinc-800 text-slate-400 hover:text-white transition-all"
                              >
                                <Bookmark size={12} />
                              </button>
                            )}
                            <a 
                              href={job.url} 
                              target="_blank" 
                              rel="noopener noreferrer" 
                              className="px-4 py-2 bg-zinc-900 border border-zinc-800 text-slate-300 hover:bg-zinc-800 text-[10px] font-bold uppercase tracking-widest text-center transition-all"
                            >
                              JD Link
                            </a>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}

                  {filteredJobs.length === 0 && (
                    <div className="carbon-panel p-12 text-center text-slate-500 text-xs">
                      No matching discoveries found. Update configuration filters.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 02: Skills Gap / Up-skill Plan */}
        {activeTab === 'upskill' && (
          <div className="space-y-12 max-w-4xl">
            <div className="flex justify-between items-end border-b border-carbon pb-8">
              <div>
                <span className="text-[10px] font-bold font-mono tracking-widest text-carbon-muted uppercase block mb-1">02. Up-skilling Plan</span>
                <h2 className="text-xl font-bold uppercase tracking-[0.2em] text-white">Skills Gap Analysis</h2>
              </div>
            </div>

            <p className="text-xs text-slate-500 leading-relaxed font-light max-w-2xl">
              Based on active search requirements across postings, your profile indicates specific technology gaps. 
              Adopt these tools to optimize your compatibility ratios.
            </p>

            {upskillPlan.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {upskillPlan.map((plan, idx) => (
                  <div key={idx} className="carbon-panel p-8 space-y-6">
                    <div className="flex justify-between items-start">
                      <h4 className="text-md font-bold text-white tracking-wide">{plan.skill}</h4>
                      <div className="flex gap-2 text-[9px] uppercase font-bold tracking-wider font-mono">
                        <span className="px-2 py-0.5 bg-zinc-900 border border-zinc-850 text-slate-400">{plan.learningTime}</span>
                        <span className="px-2 py-0.5 bg-zinc-900 border border-zinc-850 text-white">{plan.roi}</span>
                      </div>
                    </div>
                    
                    <div className="space-y-4 text-xs leading-relaxed font-light">
                      <div>
                        <span className="text-[9px] text-slate-500 font-bold uppercase tracking-widest block mb-0.5">Recommended Course</span>
                        <span className="text-slate-300">{plan.course}</span>
                      </div>
                      <div>
                        <span className="text-[9px] text-slate-500 font-bold uppercase tracking-widest block mb-0.5">Practical Portfolio Project</span>
                        <span className="text-slate-300">{plan.project}</span>
                      </div>
                      {plan.certification && (
                        <div>
                          <span className="text-[9px] text-slate-500 font-bold uppercase tracking-widest block mb-0.5">Certification Goal</span>
                          <span className="text-slate-300">{plan.certification}</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="carbon-panel p-12 text-center text-slate-500 text-xs">
                Upload your resume to formulate a personalized learning roadmap.
              </div>
            )}
          </div>
        )}

        {/* Tab 03: Resume ATS Optimization Critique */}
        {activeTab === 'critique' && (
          <div className="space-y-12 max-w-4xl">
            <div className="flex justify-between items-end border-b border-carbon pb-8">
              <div>
                <span className="text-[10px] font-bold font-mono tracking-widest text-carbon-muted uppercase block mb-1">03. ATS Optimize</span>
                <h2 className="text-xl font-bold uppercase tracking-[0.2em] text-white">Resume Critique Suggestions</h2>
              </div>
            </div>

            <p className="text-xs text-slate-500 leading-relaxed font-light max-w-2xl">
              AI-driven optimization critique matching your parsed profile structure against high-priority market demands.
            </p>

            {resumeSuggestions ? (
              <div className="space-y-8 text-xs font-light">
                <div className="carbon-panel p-8 space-y-4">
                  <h4 className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">High Impact Keywords to Add</h4>
                  <div className="flex flex-wrap gap-2">
                    {resumeSuggestions.missingKeywords?.map((kw, idx) => (
                      <span key={idx} className="px-2 py-0.5 bg-zinc-900 border border-zinc-850 text-white font-mono">
                        + {kw}
                      </span>
                    ))}
                  </div>
                </div>
                
                <div className="carbon-panel p-8 space-y-3">
                  <h4 className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Formatting & Parsing Improvements</h4>
                  <p className="text-slate-300 leading-relaxed text-sm">{resumeSuggestions.atsImprovements}</p>
                </div>
                
                <div className="carbon-panel p-8 space-y-3">
                  <h4 className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Recommended Project Enhancements</h4>
                  <p className="text-slate-300 leading-relaxed text-sm">{resumeSuggestions.projectImprovements}</p>
                </div>
                
                {resumeSuggestions.grammarFixes && (
                  <div className="carbon-panel p-8 space-y-3">
                    <h4 className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Action Verbs & Impact Metrics</h4>
                    <p className="text-slate-300 leading-relaxed text-sm">{resumeSuggestions.grammarFixes}</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="carbon-panel p-12 text-center text-slate-500 text-xs">
                Upload your resume to analyze keyword gaps and ATS layout feedback.
              </div>
            )}
          </div>
        )}

        {/* Tab 04: Recruiter / Candidate Profile metadata details */}
        {activeTab === 'profile' && (
          <div className="space-y-12 max-w-5xl">
            <div className="flex justify-between items-end border-b border-carbon pb-8">
              <div>
                <span className="text-[10px] font-bold font-mono tracking-widest text-carbon-muted uppercase block mb-1">04. Candidate Profile</span>
                <h2 className="text-xl font-bold uppercase tracking-[0.2em] text-white">Parsed Profile Parameters</h2>
              </div>
            </div>

            {profile ? (
              <div className="grid grid-cols-1 md:grid-cols-12 gap-8 text-xs leading-relaxed font-light">
                {/* Left side details */}
                <div className="md:col-span-4 carbon-panel p-8 space-y-6">
                  <div className="text-center space-y-3">
                    <div className="w-16 h-16 bg-white text-black flex items-center justify-center text-xl font-black mx-auto uppercase">
                      {profile.name?.slice(0, 2)}
                    </div>
                    <div>
                      <h4 className="text-md font-bold text-white">{profile.name}</h4>
                      <span className="text-[9px] text-slate-500 font-bold uppercase tracking-widest block mt-1">{profile.current_role}</span>
                    </div>
                  </div>

                  <div className="thin-accent-line" />

                  <div className="space-y-4">
                    <div className="flex items-center gap-2.5 text-slate-400">
                      <Mail size={12} className="text-slate-500" /> <span>{profile.email || "No email parsed"}</span>
                    </div>
                    <div className="flex items-center gap-2.5 text-slate-400">
                      <Phone size={12} className="text-slate-500" /> <span>{profile.phone || "No phone parsed"}</span>
                    </div>
                    <div className="flex items-center gap-2.5 text-slate-400">
                      <MapPin size={12} className="text-slate-500" /> <span>{profile.location}</span>
                    </div>
                    
                    <div className="thin-accent-line" />
                    
                    <div className="flex justify-between text-slate-400">
                      <span>Experience YOE:</span> <span className="font-bold text-white font-mono">{profile.yoe} Years</span>
                    </div>
                    <div className="flex justify-between text-slate-400">
                      <span>Work Visa status:</span> <span className="font-bold text-white text-right">{profile.work_authorization || "Not Specified"}</span>
                    </div>

                    <button 
                      onClick={handleDeleteResume}
                      className="w-full text-center py-2.5 bg-red-950/40 border border-red-900/50 hover:bg-red-900/20 text-red-400 font-bold text-[9px] uppercase tracking-widest transition-all mt-6"
                    >
                      Remove Resume
                    </button>
                  </div>
                </div>

                {/* Right side details */}
                <div className="md:col-span-8 carbon-panel p-8 space-y-8">
                  <div className="space-y-3">
                    <h4 className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Extracted Technology Stack</h4>
                    <div className="flex flex-wrap gap-2">
                      {profile.skills?.map((s, idx) => (
                        <span key={idx} className="px-2 py-0.5 bg-zinc-900 border border-zinc-850 text-slate-300 font-mono">
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>
                  
                  {profile.projects && profile.projects.length > 0 && (
                    <div className="space-y-3">
                      <h4 className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Key Project Summaries</h4>
                      <ul className="list-disc pl-4 space-y-1.5 text-slate-400">
                        {profile.projects.map((p, idx) => (
                          <li key={idx} className="font-light">{p}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  
                  {profile.previous_roles && profile.previous_roles.length > 0 && (
                    <div className="space-y-3">
                      <h4 className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Previous Roles</h4>
                      <div className="flex flex-wrap gap-2">
                        {profile.previous_roles.map((r, idx) => (
                          <span key={idx} className="px-2 py-0.5 bg-zinc-950 border border-zinc-850 text-slate-400">
                            {r}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                      <h4 className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Education Background</h4>
                      <ul className="list-disc pl-4 space-y-1 text-slate-400">
                        {profile.education?.map((e, idx) => (
                          <li key={idx}>{e}</li>
                        ))}
                      </ul>
                    </div>
                    <div className="space-y-2">
                      <h4 className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Candidate Target Settings</h4>
                      <div className="space-y-1 text-slate-400">
                        <div>Preference commitment: <span className="text-white font-bold">{profile.internship_or_fulltime}</span></div>
                        <div>Target mode: <span className="text-white font-bold">{profile.remote_preference}</span></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="carbon-panel p-12 text-center space-y-6">
                <div className="text-slate-500 text-xs">
                  Resume details empty. Upload your resume (PDF, TXT, MD) in the sidebar toolbar, or paste it below to trigger AI profiling.
                </div>
                <div className="max-w-2xl mx-auto space-y-4">
                  <textarea 
                    placeholder="Paste your raw resume text here..." 
                    className="w-full h-48 bg-black/60 border border-zinc-850 p-4 focus:border-white outline-none text-xs text-white font-mono resize-none rounded-none"
                    value={pastedResumeText}
                    onChange={(e) => setPastedResumeText(e.target.value)}
                  />
                  <button 
                    onClick={handleResumePaste}
                    disabled={pasting || !pastedResumeText.trim()}
                    className="px-6 py-3 bg-white text-black font-bold text-[9px] uppercase tracking-widest hover:bg-slate-200 transition-all disabled:opacity-50"
                  >
                    {pasting ? 'Analyzing...' : 'Analyze Pasted Resume'}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Paste Resume Modal (Glassmorphic Overlay) */}
      {showPasteModal && (
        <div className="fixed inset-0 bg-black/90 backdrop-blur-sm z-[100] flex items-center justify-center p-4">
          <div className="bg-zinc-950 border border-zinc-800 max-w-2xl w-full p-8 space-y-6 shadow-2xl relative rounded-none">
            <button 
              onClick={() => setShowPasteModal(false)}
              className="absolute top-6 right-6 text-slate-500 hover:text-white transition-all text-xl font-bold outline-none"
            >
              &times;
            </button>
            <div className="space-y-1">
              <h3 className="text-lg font-bold text-white uppercase tracking-widest flex items-center gap-2">
                Paste Resume Text
              </h3>
              <p className="text-xs text-slate-500">
                Paste your resume raw details directly below. The system will parse them and update metrics.
              </p>
            </div>
            
            <textarea 
              placeholder="Paste experiences, skills, and portfolio descriptions here..." 
              className="w-full h-64 bg-black/60 border border-zinc-850 p-4 focus:border-white outline-none text-xs text-white font-mono resize-none rounded-none"
              value={pastedResumeText}
              onChange={(e) => setPastedResumeText(e.target.value)}
            />
            
            <div className="flex gap-4 justify-end text-xs">
              <button 
                onClick={() => setShowPasteModal(false)}
                className="px-5 py-3 border border-zinc-800 text-slate-400 hover:text-white uppercase tracking-widest font-bold transition-all"
              >
                Cancel
              </button>
              <button 
                onClick={handleResumePaste}
                disabled={pasting || !pastedResumeText.trim()}
                className="px-6 py-3 bg-white text-black uppercase tracking-widest font-bold hover:bg-slate-200 transition-all disabled:opacity-50"
              >
                {pasting ? 'Analyzing...' : 'Analyze Resume'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
