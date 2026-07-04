import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { 
  Activity, RefreshCw, Settings, Terminal, Briefcase, ShieldAlert, 
  Upload, BookOpen, Sparkles, LineChart, CheckCircle, XCircle, 
  Bookmark, ChevronRight, TrendingUp, FolderGit2, Award, Clock, 
  User, Check, AlertCircle, HelpCircle, Phone, Mail, MapPin
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
        fetchAnalytics(); // Refresh counters on new findings
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
    setMessage('Uploading and analyzing resume PDF...');
    setIsError(false);
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await axios.post(`${API_BASE}/resume/upload`, formData);
      if (response.data.status === 'success') {
        setMessage(response.data.message);
        loadAllData(); // Reload parsed values
      } else {
        setMessage(response.data.message);
        setIsError(true);
      }
    } catch (error) {
      setMessage('Failed to connect to API server.');
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

  // Filtering job listings locally
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
    <div className="min-h-screen bg-black text-slate-300 font-sans selection:bg-blue-500/30 overflow-x-hidden">
      {/* Header bar */}
      <header className="bg-slate-900/40 border-b border-white/5 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-[1600px] mx-auto px-8 py-5 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <div className="bg-blue-600 p-2.5 rounded-2xl shadow-lg shadow-blue-500/20">
              <Activity className="text-white animate-pulse" size={24} />
            </div>
            <div>
              <h1 className="text-xl font-black tracking-tight text-white uppercase italic">JobSentinel <span className="text-blue-500 not-italic font-normal">Agent</span></h1>
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-ping" />
                <span className="text-[10px] text-slate-500 font-black uppercase tracking-[0.2em]">Active scanning</span>
              </div>
            </div>
          </div>
          
          {/* Global message banner */}
          {message && (
            <div className={`px-4 py-2 rounded-xl text-xs font-bold border transition-all ${
              isError ? 'bg-red-500/10 border-red-500/20 text-red-400' : 'bg-blue-500/10 border-blue-500/20 text-blue-400'
            }`}>
              {message}
            </div>
          )}

          <div className="flex items-center gap-4">
            {/* Quick action: Resume upload */}
            <input type="file" id="resume-upload" className="hidden" accept=".pdf" onChange={handleFileUpload} disabled={uploading} />
            <label htmlFor="resume-upload" className="px-5 py-2.5 rounded-xl font-black text-[11px] uppercase tracking-widest cursor-pointer bg-blue-600 hover:bg-blue-500 text-white shadow-xl shadow-blue-600/10 transition-all">
              {uploading ? 'Processing PDF...' : 'Upload Resume'}
            </label>
            <button onClick={loadAllData} className="p-2.5 rounded-xl bg-white/5 border border-white/10 hover:border-blue-500 text-slate-400 hover:text-white transition-all">
              <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>
      </header>

      {/* Tabs navigation */}
      <nav className="bg-slate-900/20 border-b border-white/5 backdrop-blur-md sticky top-[77px] z-40">
        <div className="max-w-[1600px] mx-auto px-8 py-2.5 flex gap-8">
          {[
            { id: 'dashboard', label: 'Overview', icon: TrendingUp },
            { id: 'jobs', label: 'Job Discoveries', icon: Briefcase },
            { id: 'upskill', label: 'Skills Pathing', icon: BookOpen },
            { id: 'critique', label: 'Resume Critique', icon: Sparkles },
            { id: 'profile', label: 'Recruiter Profile', icon: User }
          ].map(tab => {
            const Icon = tab.icon;
            return (
              <button 
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 py-2 px-4 rounded-xl font-bold text-xs uppercase tracking-wider transition-all ${
                  activeTab === tab.id 
                    ? 'bg-blue-600 text-white' 
                    : 'text-slate-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <Icon size={14} />
                {tab.label}
              </button>
            )
          })}
        </div>
      </nav>

      {/* Main interface layout */}
      <main className="max-w-[1600px] mx-auto px-8 py-8">
        
        {/* Tab 1: Dashboard / Overview */}
        {activeTab === 'dashboard' && (
          <div className="space-y-8">
            {/* Top Metrics Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="bg-slate-900/50 border border-white/5 rounded-3xl p-6 relative overflow-hidden">
                <div className="flex justify-between items-center mb-4">
                  <span className="text-[10px] font-black uppercase text-slate-500 tracking-wider">Profile Strength</span>
                  <Award className="text-blue-500" size={18} />
                </div>
                <div className="text-3xl font-black text-white">{analytics.profileStrength}%</div>
                <div className="w-full bg-white/5 h-1.5 rounded-full overflow-hidden mt-3">
                  <div className="bg-blue-500 h-full transition-all" style={{ width: `${analytics.profileStrength}%` }} />
                </div>
              </div>
              <div className="bg-slate-900/50 border border-white/5 rounded-3xl p-6">
                <div className="flex justify-between items-center mb-4">
                  <span className="text-[10px] font-black uppercase text-slate-500 tracking-wider">Resume ATS score</span>
                  <Sparkles className="text-emerald-500" size={18} />
                </div>
                <div className="text-3xl font-black text-white">{analytics.resumeScore}%</div>
                <div className="w-full bg-white/5 h-1.5 rounded-full overflow-hidden mt-3">
                  <div className="bg-emerald-500 h-full transition-all" style={{ width: `${analytics.resumeScore}%` }} />
                </div>
              </div>
              <div className="bg-slate-900/50 border border-white/5 rounded-3xl p-6">
                <div className="flex justify-between items-center mb-4">
                  <span className="text-[10px] font-black uppercase text-slate-500 tracking-wider">Market Demand Score</span>
                  <LineChart className="text-purple-500" size={18} />
                </div>
                <div className="text-3xl font-black text-white">{analytics.marketDemandScore}%</div>
                <div className="w-full bg-white/5 h-1.5 rounded-full overflow-hidden mt-3">
                  <div className="bg-purple-500 h-full transition-all" style={{ width: `${analytics.marketDemandScore}%` }} />
                </div>
              </div>
              <div className="bg-slate-900/50 border border-white/5 rounded-3xl p-6">
                <div className="flex justify-between items-center mb-4">
                  <span className="text-[10px] font-black uppercase text-slate-500 tracking-wider">Application Success Rate</span>
                  <CheckCircle className="text-indigo-500" size={18} />
                </div>
                <div className="text-3xl font-black text-white">{analytics.successRate}%</div>
                <div className="w-full bg-white/5 h-1.5 rounded-full overflow-hidden mt-3">
                  <div className="bg-indigo-500 h-full transition-all" style={{ width: `${analytics.successRate}%` }} />
                </div>
              </div>
            </div>

            {/* Split layout: Hunt Params + Activity stream */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
              {/* Left column: Scanning control */}
              <div className="lg:col-span-4 space-y-8">
                <section className="bg-slate-900/50 rounded-3xl border border-white/5 p-6">
                  <h3 className="text-xs font-black text-white uppercase tracking-wider mb-6 flex items-center gap-2">
                    <Settings size={14} className="text-blue-500" /> Scanning Preferences
                  </h3>
                  <div className="space-y-5">
                    <div className="space-y-2">
                      <label className="text-[9px] font-black text-slate-500 uppercase tracking-widest">Job Keywords</label>
                      <input type="text" value={keywords} onChange={(e) => setKeywords(e.target.value)} placeholder="e.g. Frontend Engineer, Golang" className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-2.5 focus:border-blue-500 outline-none text-xs text-white" />
                    </div>
                    <div className="space-y-2">
                      <label className="text-[9px] font-black text-slate-500 uppercase tracking-widest">Target Cities</label>
                      <input type="text" value={locations} onChange={(e) => setLocations(e.target.value)} placeholder="e.g. Remote, Bangalore" className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-2.5 focus:border-blue-500 outline-none text-xs text-white" />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <label className="text-[9px] font-black text-slate-500 uppercase tracking-widest">Commitment</label>
                        <select value={jobType} onChange={(e) => setJobType(e.target.value)} className="w-full bg-black/40 border border-white/5 rounded-xl px-3 py-2.5 focus:border-blue-500 outline-none text-xs text-slate-300">
                          <option value="All">All Types</option>
                          <option value="F">Full-time</option>
                          <option value="P">Part-time</option>
                          <option value="I">Internship</option>
                        </select>
                      </div>
                      <div className="space-y-2">
                        <label className="text-[9px] font-black text-slate-500 uppercase tracking-widest">Seniority</label>
                        <select value={expLevel} onChange={(e) => setExpLevel(e.target.value)} className="w-full bg-black/40 border border-white/5 rounded-xl px-3 py-2.5 focus:border-blue-500 outline-none text-xs text-slate-300">
                          <option value="All">All Levels</option>
                          <option value="2">Fresher / Intern</option>
                          <option value="4">Experienced</option>
                        </select>
                      </div>
                    </div>
                    <button onClick={savePreferences} disabled={savingPrefs} className="w-full bg-blue-600 hover:bg-blue-500 text-white py-3 rounded-xl font-black text-[10px] uppercase tracking-widest transition-all">
                      {savingPrefs ? 'Updating scanner...' : 'Save Parameters'}
                    </button>
                  </div>
                </section>

                <section className="bg-slate-900/80 rounded-3xl border border-white/5 p-6 h-[300px] flex flex-col">
                  <h3 className="text-xs font-black text-white uppercase tracking-wider mb-4 flex items-center gap-2">
                    <Terminal size={14} className="text-green-500" /> System Stream Logs
                  </h3>
                  <div className="flex-1 bg-black/60 rounded-xl p-4 font-mono text-[10px] overflow-y-auto space-y-1.5 border border-white/5">
                    {logs.map((log, i) => (
                      <div key={i} className="text-green-500/80 leading-relaxed break-all">
                        <span className="text-slate-700 mr-1.5">[{new Date().toLocaleTimeString()}]</span>
                        {log}
                      </div>
                    ))}
                    {logs.length === 0 && <div className="text-slate-600">Waiting for discoveries...</div>}
                    <div ref={logEndRef} />
                  </div>
                </section>
              </div>

              {/* Right column: Market insights & brief statistics */}
              <div className="lg:col-span-8 space-y-8">
                <section className="bg-slate-900/50 rounded-3xl border border-white/5 p-6">
                  <h3 className="text-xs font-black text-white uppercase tracking-wider mb-6 flex items-center gap-2">
                    <TrendingUp size={14} className="text-purple-500" /> Career Market Intelligence
                  </h3>
                  {marketInsights ? (
                    <div className="space-y-6">
                      <p className="text-sm leading-relaxed text-slate-300 bg-white/[0.02] border-l-2 border-purple-500 p-4 rounded-r-xl">
                        {marketInsights.insightsSummary}
                      </p>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                          <h4 className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-3">Trending Tech Demands</h4>
                          <div className="flex flex-wrap gap-2">
                            {marketInsights.trendingSkills?.map((skill, idx) => (
                              <span key={idx} className="px-3 py-1 bg-purple-500/10 border border-purple-500/20 text-purple-400 rounded-lg text-xs font-bold">
                                {skill}
                              </span>
                            ))}
                          </div>
                        </div>
                        <div>
                          <h4 className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-3">Target Details</h4>
                          <div className="space-y-1.5 text-xs">
                            <div className="flex justify-between"><span className="text-slate-500">Average Salary Band:</span> <span className="font-bold text-white">{marketInsights.averageSalary}</span></div>
                            <div className="flex justify-between"><span className="text-slate-500">Active Hirers:</span> <span className="font-bold text-white">{marketInsights.mostHiringCompanies?.join(', ')}</span></div>
                          </div>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-slate-500 text-xs py-8 text-center">
                      Aggregating market trends. Real-time insights will populate as scanning proceeds.
                    </div>
                  )}
                </section>

                {/* Pipeline overview */}
                <section className="bg-slate-900/50 rounded-3xl border border-white/5 p-6">
                  <h3 className="text-xs font-black text-white uppercase tracking-wider mb-6">Pipeline Tracker</h3>
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                    <div className="bg-white/5 rounded-2xl p-4 text-center">
                      <div className="text-slate-500 text-[10px] font-black uppercase tracking-wider mb-1">Found</div>
                      <div className="text-2xl font-black text-white">{analytics.totalJobs}</div>
                    </div>
                    <div className="bg-blue-600/10 border border-blue-500/20 rounded-2xl p-4 text-center">
                      <div className="text-blue-400 text-[10px] font-black uppercase tracking-wider mb-1">High Match</div>
                      <div className="text-2xl font-black text-blue-400">{analytics.matchedCount}</div>
                    </div>
                    <div className="bg-yellow-600/10 border border-yellow-500/20 rounded-2xl p-4 text-center">
                      <div className="text-yellow-400 text-[10px] font-black uppercase tracking-wider mb-1">Saved</div>
                      <div className="text-2xl font-black text-yellow-400">{analytics.savedCount}</div>
                    </div>
                    <div className="bg-green-600/10 border border-green-500/20 rounded-2xl p-4 text-center">
                      <div className="text-green-400 text-[10px] font-black uppercase tracking-wider mb-1">Applied</div>
                      <div className="text-2xl font-black text-green-400">{analytics.appliedCount}</div>
                    </div>
                    <div className="bg-indigo-600/10 border border-indigo-500/20 rounded-2xl p-4 text-center col-span-2 md:col-span-1">
                      <div className="text-indigo-400 text-[10px] font-black uppercase tracking-wider mb-1">Interviews</div>
                      <div className="text-2xl font-black text-indigo-400">{analytics.interviewCount}</div>
                    </div>
                  </div>
                </section>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Job Opportunities Feed */}
        {activeTab === 'jobs' && (
          <div className="grid grid-cols-1 xl:grid-cols-12 gap-10">
            {/* Filters sidebar */}
            <div className="xl:col-span-3 space-y-6">
              <div className="bg-slate-900/50 border border-white/5 rounded-3xl p-6 sticky top-[150px]">
                <h3 className="text-xs font-black text-white uppercase tracking-wider mb-6">Filter Discoveries</h3>
                <div className="space-y-5 text-xs">
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Query</label>
                    <input 
                      type="text" 
                      value={filterKeyword} 
                      onChange={(e) => setFilterKeyword(e.target.value)} 
                      placeholder="Title, Company, Skills..."
                      className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-2.5 focus:border-blue-500 outline-none text-white" 
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Location Status</label>
                    <select value={filterRemote} onChange={(e) => setFilterRemote(e.target.value)} className="w-full bg-black/40 border border-white/5 rounded-xl px-3 py-2.5 focus:border-blue-500 outline-none text-slate-300">
                      <option value="All">All Setup</option>
                      <option value="Remote">Remote Only</option>
                      <option value="Onsite">Onsite Only</option>
                      <option value="Hybrid">Hybrid Only</option>
                    </select>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Source Platform</label>
                    <select value={filterSource} onChange={(e) => setFilterSource(e.target.value)} className="w-full bg-black/40 border border-white/5 rounded-xl px-3 py-2.5 focus:border-blue-500 outline-none text-slate-300">
                      <option value="All">All Sources</option>
                      <option value="LinkedIn">LinkedIn</option>
                      <option value="Naukri">Naukri</option>
                      <option value="Wellfound">Wellfound</option>
                      <option value="YC Jobs">YC Jobs</option>
                    </select>
                  </div>
                  <div className="space-y-1.5">
                    <div className="flex justify-between items-center mb-1">
                      <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Min Match Score</label>
                      <span className="font-bold text-blue-400">{filterMinScore}%</span>
                    </div>
                    <input 
                      type="range" 
                      min="0" 
                      max="100" 
                      value={filterMinScore} 
                      onChange={(e) => setFilterMinScore(Number(e.target.value))} 
                      className="w-full accent-blue-500" 
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Opportunity cards list */}
            <div className="xl:col-span-9 space-y-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-md font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  Matching Jobs <span className="text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">{filteredJobs.length} Hits</span>
                </h3>
              </div>

              <div className="space-y-6">
                {filteredJobs.map((job) => (
                  <div 
                    key={job.job_id} 
                    className={`bg-slate-900/40 rounded-[2rem] p-6 border transition-all duration-300 hover:border-white/10 relative overflow-hidden ${
                      job.matchScore >= 80 ? 'border-blue-500/20 bg-blue-500/[0.01]' : 'border-white/5'
                    }`}
                  >
                    <div className="flex flex-col md:flex-row gap-6 justify-between">
                      {/* Left: Job Core Info */}
                      <div className="space-y-3 flex-1">
                        <div className="flex flex-wrap gap-2 items-center">
                          <span className={`px-2.5 py-0.5 rounded-full text-[8px] font-black uppercase tracking-widest border ${
                            job.source === 'LinkedIn' ? 'bg-blue-500/10 border-blue-500/20 text-blue-400' :
                            job.source === 'Naukri' ? 'bg-purple-500/10 border-purple-500/20 text-purple-400' :
                            'bg-yellow-500/10 border-yellow-500/20 text-yellow-400'
                          }`}>
                            {job.source}
                          </span>
                          {job.remote_status && (
                            <span className="px-2.5 py-0.5 bg-white/5 border border-white/10 rounded-full text-[8px] font-bold text-slate-400">
                              {job.remote_status}
                            </span>
                          )}
                          {job.experience && (
                            <span className="px-2.5 py-0.5 bg-white/5 border border-white/10 rounded-full text-[8px] font-bold text-slate-400">
                              {job.experience}
                            </span>
                          )}
                        </div>
                        <div>
                          <h4 className="text-lg font-black text-white tracking-tight">{job.title}</h4>
                          <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">{job.company} &bull; <span className="font-normal">{job.location}</span></p>
                        </div>
                        
                        <p className="text-xs text-slate-400 leading-relaxed max-w-2xl line-clamp-2">
                          {job.summary || job.description}
                        </p>

                        {/* Matched/Missing Skills list */}
                        <div className="space-y-2 mt-4">
                          {job.matchedSkills && job.matchedSkills.length > 0 && (
                            <div className="flex flex-wrap items-center gap-1.5">
                              <span className="text-[8px] font-black text-green-500 uppercase mr-1.5">Match:</span>
                              {job.matchedSkills.map((s, idx) => (
                                <span key={idx} className="px-2 py-0.5 bg-green-500/10 border border-green-500/20 text-green-400 rounded text-[9px] font-semibold">
                                  {s}
                                </span>
                              ))}
                            </div>
                          )}
                          {job.missingSkills && job.missingSkills.length > 0 && (
                            <div className="flex flex-wrap items-center gap-1.5">
                              <span className="text-[8px] font-black text-red-400 uppercase mr-1.5">Missing:</span>
                              {job.missingSkills.map((s, idx) => (
                                <span key={idx} className="px-2 py-0.5 bg-red-500/10 border border-red-500/20 text-red-400 rounded text-[9px] font-semibold">
                                  {s}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Right: AI analysis match score & CTAs */}
                      <div className="flex flex-row md:flex-col justify-between items-center md:items-end w-full md:w-auto border-t md:border-t-0 border-white/5 pt-4 md:pt-0 gap-4">
                        <div className="flex items-center gap-4">
                          <div className="text-right">
                            <span className="text-[9px] text-slate-500 font-black uppercase tracking-wider block">Match score</span>
                            <span className={`text-2xl font-black font-mono ${
                              job.matchScore >= 80 ? 'text-blue-400' : (job.matchScore >= 60 ? 'text-yellow-400' : 'text-slate-500')
                            }`}>
                              {job.matchScore || 0}%
                            </span>
                          </div>
                          {job.applyImmediately && (
                            <span className="p-1 bg-blue-500 text-white rounded-full text-[8px] font-bold uppercase animate-pulse px-2">Apply</span>
                          )}
                        </div>

                        {/* Recommendation details popup message */}
                        {job.recommendationReason && (
                          <div className="hidden lg:block max-w-[200px] text-right text-[10px] text-slate-500 leading-snug italic">
                            "{job.recommendationReason.slice(0, 80)}..."
                          </div>
                        )}

                        {/* CTA group */}
                        <div className="flex gap-2">
                          {job.status !== 'applied' ? (
                            <button 
                              onClick={() => updateJobStatus(job.job_id, 'applied')}
                              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-black uppercase tracking-wider transition-all"
                            >
                              Applied
                            </button>
                          ) : (
                            <span className="px-3 py-2 bg-green-500/10 border border-green-500/20 text-green-400 rounded-xl text-xs font-bold flex items-center gap-1.5">
                              <Check size={14} /> Applied
                            </span>
                          )}
                          {job.status !== 'saved' && job.status !== 'applied' && (
                            <button 
                              onClick={() => updateJobStatus(job.job_id, 'saved')}
                              className="p-2 bg-white/5 border border-white/10 hover:border-yellow-500/30 text-slate-400 hover:text-white rounded-xl transition-all"
                            >
                              <Bookmark size={14} />
                            </button>
                          )}
                          <a 
                            href={job.url} 
                            target="_blank" 
                            rel="noopener noreferrer" 
                            className="px-4 py-2 bg-white/5 border border-white/10 hover:bg-white/10 hover:text-white text-slate-300 rounded-xl text-xs font-black uppercase tracking-wider text-center transition-all"
                          >
                            JD Link
                          </a>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}

                {filteredJobs.length === 0 && (
                  <div className="bg-slate-900/30 border border-white/5 rounded-3xl p-12 text-center text-slate-500">
                    No matching discoveries found matching criteria. Update keywords or sliding score filters.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Skills Pathing / Up-skill Plan */}
        {activeTab === 'upskill' && (
          <div className="space-y-8">
            <div className="max-w-4xl">
              <h3 className="text-lg font-black text-white uppercase tracking-wider mb-2 flex items-center gap-2">
                <BookOpen className="text-blue-500" size={18} /> Personalized Up-skilling Plan
              </h3>
              <p className="text-xs text-slate-500 leading-relaxed mb-8">
                Based on active search requirements across public postings, your profile shows skills gaps. 
                Improve your compatibility percentage and matching yields by adopting the following tools.
              </p>

              {upskillPlan.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  {upskillPlan.map((plan, idx) => (
                    <div key={idx} className="bg-slate-900/50 border border-white/5 rounded-3xl p-6 space-y-4">
                      <div className="flex justify-between items-start">
                        <h4 className="text-md font-black text-white tracking-tight">{plan.skill}</h4>
                        <div className="flex gap-2 text-[9px] uppercase font-bold tracking-wider">
                          <span className="px-2 py-0.5 bg-blue-500/10 border border-blue-500/20 text-blue-400 rounded flex items-center gap-1"><Clock size={10} /> {plan.learningTime}</span>
                          <span className="px-2 py-0.5 bg-green-500/10 border border-green-500/20 text-green-400 rounded">{plan.roi}</span>
                        </div>
                      </div>
                      <div className="space-y-3 text-xs leading-relaxed">
                        <div>
                          <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Recommended Course:</span>
                          <span className="text-slate-300 font-medium">{plan.course}</span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Practical Portfolio Project:</span>
                          <span className="text-slate-300 font-medium">{plan.project}</span>
                        </div>
                        {plan.certification && (
                          <div>
                            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Target Certification:</span>
                            <span className="text-slate-300 font-medium">{plan.certification}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="bg-slate-900/30 border border-white/5 rounded-3xl p-12 text-center text-slate-500 text-xs">
                  Please upload your resume to generate a personalized skills gap learning path.
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 4: Resume Critique & ATS Improvements */}
        {activeTab === 'critique' && (
          <div className="space-y-8">
            <div className="max-w-4xl">
              <h3 className="text-lg font-black text-white uppercase tracking-wider mb-2 flex items-center gap-2">
                <Sparkles className="text-emerald-500" size={18} /> AI ATS Optimization Suggests
              </h3>
              <p className="text-xs text-slate-500 leading-relaxed mb-8">
                Detailed critiques mapping your uploaded profile against recent job specifications to ensure high ATS conversion.
              </p>

              {resumeSuggestions ? (
                <div className="space-y-6 text-xs">
                  <div className="bg-slate-900/50 border border-white/5 rounded-3xl p-6">
                    <h4 className="text-[10px] font-black text-emerald-500 uppercase tracking-widest mb-3">Target Keywords to Add</h4>
                    <div className="flex flex-wrap gap-2">
                      {resumeSuggestions.missingKeywords?.map((kw, idx) => (
                        <span key={idx} className="px-2.5 py-1 bg-white/5 border border-white/10 text-slate-300 rounded font-medium">
                          + {kw}
                        </span>
                      ))}
                    </div>
                  </div>
                  
                  <div className="bg-slate-900/50 border border-white/5 rounded-3xl p-6 space-y-2">
                    <h4 className="text-[10px] font-black text-blue-400 uppercase tracking-widest">Formatting & ATS improvements</h4>
                    <p className="text-slate-300 leading-relaxed text-sm">{resumeSuggestions.atsImprovements}</p>
                  </div>
                  
                  <div className="bg-slate-900/50 border border-white/5 rounded-3xl p-6 space-y-2">
                    <h4 className="text-[10px] font-black text-purple-400 uppercase tracking-widest">Recommended Project Enhancements</h4>
                    <p className="text-slate-300 leading-relaxed text-sm">{resumeSuggestions.projectImprovements}</p>
                  </div>
                  
                  {resumeSuggestions.grammarFixes && (
                    <div className="bg-slate-900/50 border border-white/5 rounded-3xl p-6 space-y-2">
                      <h4 className="text-[10px] font-black text-yellow-500 uppercase tracking-widest">Action Verbs & Impact Metrics</h4>
                      <p className="text-slate-300 leading-relaxed text-sm">{resumeSuggestions.grammarFixes}</p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="bg-slate-900/30 border border-white/5 rounded-3xl p-12 text-center text-slate-500 text-xs">
                  Please upload your resume to generate personalized ATS suggestions.
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 5: Recruiter Profile / Parsed Resume Info */}
        {activeTab === 'profile' && (
          <div className="space-y-8">
            <div className="max-w-5xl">
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h3 className="text-lg font-black text-white uppercase tracking-wider flex items-center gap-2">
                    <User className="text-blue-500" size={18} /> Candidate Agent Profile
                  </h3>
                  <p className="text-xs text-slate-500">Parsed metadata parameters stored in database.</p>
                </div>
              </div>

              {profile ? (
                <div className="grid grid-cols-1 md:grid-cols-12 gap-8 text-xs leading-relaxed">
                  {/* Left Column: Basic Details */}
                  <div className="md:col-span-4 bg-slate-900/50 border border-white/5 rounded-3xl p-6 space-y-6">
                    <div className="text-center space-y-2">
                      <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center text-xl font-black text-white mx-auto uppercase">
                        {profile.name?.slice(0, 2)}
                      </div>
                      <h4 className="text-md font-black text-white">{profile.name}</h4>
                      <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">{profile.current_role}</span>
                    </div>

                    <hr style={{ border: 0, borderTop: "1px solid rgba(255,255,255,0.05)" }} />

                    <div className="space-y-4">
                      <div className="flex items-center gap-2.5 text-slate-400">
                        <Mail size={14} className="text-blue-500" /> <span>{profile.email || "No email parsed"}</span>
                      </div>
                      <div className="flex items-center gap-2.5 text-slate-400">
                        <Phone size={14} className="text-blue-500" /> <span>{profile.phone || "No phone parsed"}</span>
                      </div>
                      <div className="flex items-center gap-2.5 text-slate-400">
                        <MapPin size={14} className="text-blue-500" /> <span>{profile.location}</span>
                      </div>
                      <div className="flex justify-between text-slate-400">
                        <span>Experience (YOE):</span> <span className="font-bold text-white">{profile.yoe} Years</span>
                      </div>
                      <div className="flex justify-between text-slate-400">
                        <span>Work Authorization:</span> <span className="font-bold text-white text-right">{profile.work_authorization || "Not Specified"}</span>
                      </div>
                    </div>
                  </div>

                  {/* Right Column: Full details */}
                  <div className="md:col-span-8 bg-slate-900/50 border border-white/5 rounded-3xl p-6 space-y-6">
                    <div>
                      <h4 className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-3">Extracted Technology Stack</h4>
                      <div className="flex flex-wrap gap-2">
                        {profile.skills?.map((s, idx) => (
                          <span key={idx} className="px-2.5 py-1 bg-white/5 border border-white/10 text-slate-300 rounded font-medium">
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>
                    
                    {profile.projects && profile.projects.length > 0 && (
                      <div>
                        <h4 className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2">Projects</h4>
                        <ul className="list-disc pl-4 space-y-1 text-slate-400">
                          {profile.projects.map((p, idx) => (
                            <li key={idx}>{p}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    
                    {profile.previous_roles && profile.previous_roles.length > 0 && (
                      <div>
                        <h4 className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2">Previous Roles</h4>
                        <div className="flex flex-wrap gap-2">
                          {profile.previous_roles.map((r, idx) => (
                            <span key={idx} className="px-2 py-0.5 bg-slate-800/80 text-slate-400 rounded-md border border-white/5">
                              {r}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <h4 className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2">Education</h4>
                        <ul className="list-disc pl-4 space-y-1 text-slate-400">
                          {profile.education?.map((e, idx) => (
                            <li key={idx}>{e}</li>
                          ))}
                        </ul>
                      </div>
                      <div>
                        <h4 className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2">Target Preferences</h4>
                        <div className="space-y-1 text-slate-400">
                          <div>Commitment: <span className="text-white font-semibold">{profile.internship_or_fulltime}</span></div>
                          <div>Work Mode: <span className="text-white font-semibold">{profile.remote_preference}</span></div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="bg-slate-900/30 border border-white/5 rounded-3xl p-12 text-center text-slate-500 text-xs">
                  Resume details empty. Upload your PDF resume in the header toolbar to trigger AI profiling.
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
