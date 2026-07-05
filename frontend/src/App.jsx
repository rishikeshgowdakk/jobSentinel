import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { 
  Activity, RefreshCw, Settings, Terminal, Briefcase, 
  Upload, BookOpen, Sparkles, LineChart, CheckCircle,
  Bookmark, ChevronRight, TrendingUp, Award, Clock, 
  User, Check, Phone, Mail, MapPin, AlertCircle,
  Moon, Sun, Search, Plus, ArrowUpRight
} from 'lucide-react';

// Initialize or retrieve unique local user session
let userId = localStorage.getItem('jobsentinel_user_id');
if (!userId) {
  userId = 'user_' + Math.random().toString(36).substring(2, 11);
  localStorage.setItem('jobsentinel_user_id', userId);
}
// Attach to all outgoing axios requests automatically
axios.defaults.headers.common['X-User-ID'] = userId;

const API_BASE = 'http://localhost:8000/api';
const WS_BASE = `ws://localhost:8000/api/ws/stream?user_id=${userId}`;

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'dark');
  
  // Payment check states
  const [pendingFile, setPendingFile] = useState(null);
  const [pendingPasteText, setPendingPasteText] = useState('');
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [paymentUtr, setPaymentUtr] = useState('');
  const [paymentError, setPaymentError] = useState('');
  const [paymentVerifying, setPaymentVerifying] = useState(false);
  
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

  useEffect(() => {
    document.documentElement.className = theme;
    localStorage.setItem('theme', theme);
  }, [theme]);

  const completePaymentAndSubmit = async (utr) => {
    if (!utr.trim()) {
      setPaymentError('UTR is required.');
      return;
    }
    const cleanUtr = utr.trim();
    if (!(/^\d{12}$/.test(cleanUtr) || cleanUtr === "TEST12345678")) {
      setPaymentError('Invalid UTR format. UTR must be exactly 12 digits.');
      return;
    }

    setPaymentVerifying(true);
    setPaymentError('');
    setIsError(false);

    if (pendingFile) {
      const formData = new FormData();
      formData.append('file', pendingFile);
      formData.append('utr', cleanUtr);

      setUploading(true);
      setMessage('Uploading and verifying payment...');

      try {
        const response = await axios.post(`${API_BASE}/resume/upload`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });
        if (response.data.status === 'success') {
          setMessage(response.data.message);
          setPendingFile(null);
          setShowPaymentModal(false);
          loadAllData();
        } else {
          setPaymentError(response.data.message);
          setMessage(response.data.message);
          setIsError(true);
        }
      } catch (error) {
        console.error('Upload error details:', error);
        setPaymentError('Failed to verify payment or upload CV.');
        setMessage('Failed to upload resume.');
        setIsError(true);
      } finally {
        setUploading(false);
        setPaymentVerifying(false);
      }
    } else if (pendingPasteText) {
      setPasting(true);
      setMessage('Processing pasted CV and verifying payment...');

      try {
        const response = await axios.post(`${API_BASE}/resume/paste`, { 
          text: pendingPasteText,
          utr: cleanUtr
        });
        if (response.data.status === 'success') {
          setMessage(response.data.message);
          setPendingPasteText('');
          setPastedResumeText('');
          setShowPaymentModal(false);
          setShowPasteModal(false);
          loadAllData();
        } else {
          setPaymentError(response.data.message);
          setMessage(response.data.message);
          setIsError(true);
        }
      } catch (error) {
        setPaymentError('Failed to verify payment or process CV.');
        setMessage('Failed to connect to API server.');
        setIsError(true);
      } finally {
        setPasting(false);
        setPaymentVerifying(false);
      }
    } else {
      setPaymentVerifying(false);
      setPaymentError('No CV document loaded for evaluation.');
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setPendingFile(file);
    setPendingPasteText('');
    setPaymentUtr('');
    setPaymentError('');
    setShowPaymentModal(true);
    e.target.value = ''; // Reset input to allow selecting same file again
  };

  const handleResumePaste = async () => {
    if (!pastedResumeText.trim()) return;
    setPendingPasteText(pastedResumeText);
    setPendingFile(null);
    setPaymentUtr('');
    setPaymentError('');
    setShowPaymentModal(true);
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
      (job.title && job.title.toLowerCase().includes(filterKeyword.toLowerCase())) || 
      (job.company && job.company.toLowerCase().includes(filterKeyword.toLowerCase())) ||
      (job.skills && job.skills.toLowerCase().includes(filterKeyword.toLowerCase())) ||
      (job.description && job.description.toLowerCase().includes(filterKeyword.toLowerCase())) ||
      (job.summary && job.summary.toLowerCase().includes(filterKeyword.toLowerCase()));
      
    const matchesRemote = filterRemote === 'All' || 
      (filterRemote === 'Remote' && job.remote_status?.toLowerCase() === 'remote') ||
      (filterRemote === 'Onsite' && job.remote_status?.toLowerCase() === 'onsite') ||
      (filterRemote === 'Hybrid' && job.remote_status?.toLowerCase() === 'hybrid');
      
    const matchesSource = filterSource === 'All' || 
      (job.source && job.source.trim().toLowerCase() === filterSource.trim().toLowerCase());
      
    const matchesScore = (job.matchScore || 0) >= filterMinScore;
    
    return matchesKeyword && matchesRemote && matchesSource && matchesScore;
  });

  return (
    <div className="min-h-screen text-slate-800 dark:text-slate-100 flex flex-col lg:flex-row antialiased select-none font-sans">
      
      {/* LEFT COLUMN: Sidebar Navigation & Identity (Redesigned Monochrome Theme) */}
      <aside className="w-full lg:w-[360px] border-r border-slate-200 dark:border-slate-900/60 bg-slate-50/50 dark:bg-slate-950/45 backdrop-blur-xl p-8 flex flex-col justify-between shrink-0 relative z-10 select-none">
        <div className="space-y-8">
          


          <div className="space-y-1.5 pt-2">
            <h1 className="text-2xl font-black tracking-wider text-black dark:text-white font-sans flex items-center gap-2.5">
              <span className="w-8 h-8 rounded-xl bg-black dark:bg-white flex items-center justify-center shadow-lg shadow-black/10 dark:shadow-white/5 text-white dark:text-black font-black text-sm">JS</span>
              JobSentinel
            </h1>
            <p className="text-[10px] font-semibold tracking-[0.25em] uppercase text-slate-500 dark:text-slate-400/80 pl-0.5">
              Autonomous Search Agent
            </p>
          </div>

          <div className="thin-accent-line" />

          {/* User Welcome & Theme Toggles Card */}
          <div className="flex items-center justify-between p-4 bg-slate-200/30 dark:bg-slate-900/40 border border-slate-300/40 dark:border-slate-900/60 rounded-2xl">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-neutral-800 to-neutral-600 dark:from-neutral-300 dark:to-neutral-500 text-white dark:text-slate-950 flex items-center justify-center font-bold text-sm shadow-md shadow-black/10 dark:shadow-white/5">
                {profile?.name ? profile.name.slice(0, 2).toUpperCase() : <User size={16} />}
              </div>
              <div>
                <span className="text-[9px] font-semibold text-slate-500 uppercase tracking-wider block">
                  {new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }).toUpperCase()}
                </span>
                <h3 className="text-xs font-bold text-slate-800 dark:text-slate-100 tracking-tight">
                  Welcome back, {profile?.name ? profile.name.split(' ')[0] : 'Guest'}
                </h3>
              </div>
            </div>

          </div>

          {/* Navigation Menu */}
          <nav className="flex flex-col gap-2 pt-2">
            {[
              { id: 'dashboard', label: 'Overview', icon: Activity },
              { id: 'jobs', label: 'Discoveries', icon: Sparkles },
              { id: 'upskill', label: 'Skills Path', icon: BookOpen },
              { id: 'critique', label: 'ATS Optimize', icon: Award },
              { id: 'profile', label: 'Profile', icon: User }
            ].map(tab => {
              const IconComp = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button 
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center justify-between w-full px-4 py-3 rounded-2xl transition-all duration-300 group text-left ${
                    isActive 
                      ? 'bg-black/5 dark:bg-white/10 border-l-2 border-black dark:border-white text-slate-900 dark:text-white font-semibold shadow-[inset_0_0_12px_rgba(255,255,255,0.01)]' 
                      : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 hover:bg-slate-200/50 dark:hover:bg-slate-900/30'
                  }`}
                >
                  <div className="flex items-center gap-3.5">
                    <IconComp size={16} className={`transition-colors duration-300 ${isActive ? 'text-slate-900 dark:text-white' : 'text-slate-500 dark:text-slate-500 group-hover:text-slate-800 dark:group-hover:text-slate-300'}`} />
                    <span className="text-xs tracking-wide">{tab.label}</span>
                  </div>
                  {isActive && <div className="w-1.5 h-1.5 rounded-full bg-black dark:bg-white"></div>}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Brand/User Actions & Upgrade Card at bottom */}
        <div className="space-y-6 pt-6">
          
          {/* Quick upload tools */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <input type="file" id="resume-upload" className="hidden" accept=".pdf,.txt,.md" onChange={handleFileUpload} disabled={uploading} />
              <label htmlFor="resume-upload" className="flex-1 text-center py-2.5 bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 border border-slate-300 dark:border-slate-600 text-slate-900 dark:text-white font-semibold text-[10px] uppercase tracking-wider rounded-xl cursor-pointer hover:-translate-y-1 hover:shadow-lg active:scale-95 transition-all duration-300 select-none">
                {uploading ? 'Parsing...' : 'Upload CV'}
              </label>
              <button 
                onClick={() => setShowPasteModal(true)} 
                className="flex-1 text-center py-2.5 bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 border border-slate-300 dark:border-slate-600 text-slate-900 dark:text-white font-semibold text-[10px] uppercase tracking-wider rounded-xl cursor-pointer hover:-translate-y-1 hover:shadow-lg active:scale-95 transition-all duration-300 select-none"
              >
                Paste CV
              </button>
              <button 
                onClick={loadAllData} 
                className="p-2.5 bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-white hover:text-slate-900 rounded-xl cursor-pointer hover:-translate-y-1 hover:shadow-lg active:scale-95 transition-all duration-300 select-none"
                title="Force reload telemetry"
              >
                <RefreshCw size={11} className={loading ? 'animate-spin' : ''} />
              </button>
            </div>
            
            {/* Global Message Banner */}
            {message && (
              <div className={`p-2.5 text-[9px] uppercase font-bold tracking-wider text-center rounded-xl transition-all duration-300 ${
                isError ? 'bg-black/10 dark:bg-white/10 border border-black/30 dark:border-white/30 text-black dark:text-white' : 'bg-slate-200/40 dark:bg-slate-800/25 border border-slate-300 dark:border-slate-700/20 text-slate-800 dark:text-slate-200'
              }`}>
                {message}
              </div>
            )}
          </div>

          <div className="thin-accent-line" />

          {/* Pro Style upgrade Card */}
          <div className="bg-mesh-mono border border-slate-300 dark:border-slate-800 p-5 rounded-3xl relative overflow-hidden group shadow-[0_8px_32px_rgba(255,255,255,0.01)]">
            <div className="absolute -right-6 -bottom-6 w-24 h-24 bg-white/5 rounded-full blur-xl group-hover:bg-white/10 transition-all duration-500"></div>
            <div className="relative z-10 space-y-3.5">
              <div className="flex items-center gap-2">
                <Sparkles size={13} className="text-black dark:text-white" />
                <span className="text-[9px] font-bold tracking-[0.15em] text-black dark:text-white uppercase">
                  JobSentinel Pro
                </span>
              </div>
              <p className="text-[10px] text-slate-600 dark:text-slate-400 leading-normal font-light">
                Elevate your career search with fully autonomous search, crawl loops, and email auto-outreach.
              </p>
              <button 
                onClick={() => alert("JobSentinel Pro integration coming soon!")}
                className="w-full py-2.5 bg-black dark:bg-white hover:bg-neutral-800 dark:hover:bg-slate-200 text-white dark:text-slate-950 rounded-xl text-[9px] font-bold uppercase tracking-wider transition-all duration-300 shadow-md hover:-translate-y-1 hover:shadow-lg active:scale-95 cursor-pointer"
              >
                Elevate career with AI
              </button>
            </div>
          </div>
        </div>
      </aside>

      {/* RIGHT COLUMN: Tab Panel Contents */}
      <main className="flex-grow p-10 lg:p-14 overflow-y-auto max-h-screen relative z-10">
        
        {/* Tab 00: Overview / Dashboard */}
        {activeTab === 'dashboard' && (
          <div className="space-y-8 lg:space-y-10">
            
            {/* Top Concept Header */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center border-b border-slate-200 dark:border-slate-900/60 pb-6 gap-4">
              <div>
                <span className="text-[10px] font-bold text-slate-500 dark:text-slate-400 font-mono tracking-widest uppercase block mb-1">00 . Overview</span>
                <h2 className="text-2xl font-black uppercase tracking-wider text-slate-800 dark:text-white">System Telemetry</h2>
              </div>
              <div className="flex items-center gap-3 w-full md:w-auto justify-end">
                <div className="relative">
                  <select className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800/80 text-xs px-3.5 py-2 rounded-xl text-slate-700 dark:text-slate-300 pr-8 appearance-none cursor-pointer">
                    <option>This Month</option>
                    <option>Last 30 Days</option>
                    <option>All-Time</option>
                  </select>
                  <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-slate-500 text-[10px]">&#9662;</div>
                </div>
                <button 
                  onClick={() => {
                    document.getElementById('hunt-config-section')?.scrollIntoView({ behavior: 'smooth' });
                  }}
                  className="px-4 py-2 border border-slate-200 dark:border-slate-800 bg-slate-100 dark:bg-slate-900/60 hover:bg-slate-200 dark:hover:bg-slate-800 text-xs text-slate-700 dark:text-slate-200 font-semibold rounded-xl transition-all duration-300 cursor-pointer"
                >
                  Configure Hunt
                </button>
                <button 
                  onClick={loadAllData}
                  className="px-4 py-2 bg-black dark:bg-white hover:bg-neutral-800 dark:hover:bg-slate-200 text-white dark:text-black text-xs font-bold rounded-xl flex items-center gap-2 transition-all duration-300 shadow-md cursor-pointer"
                >
                  <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
                  <span>{loading ? 'Scanning...' : 'Scan Now'}</span>
                </button>
              </div>
            </div>

            {/* ROW 1: AI Insights, Balance Overview (Line Chart), Earnings (Radial Gauge) */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8">
              
              {/* Card A: AI Insights (Mesh Gradient Card) */}
              <div className="bg-mesh-mono p-7 rounded-[24px] text-slate-800 dark:text-white flex flex-col justify-between h-[280px] shadow-[0_12px_36px_rgba(0,0,0,0.02)] dark:shadow-[0_12px_36px_rgba(255,255,255,0.01)] relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-32 h-32 bg-white/5 rounded-full blur-xl pointer-events-none" />
                <div className="space-y-4 relative z-10">
                  <div className="flex justify-between items-center">
                    <span className="px-3 py-1 bg-black/5 dark:bg-white/10 border border-black/10 dark:border-white/10 backdrop-blur-md rounded-full text-[9px] font-bold tracking-widest text-slate-600 dark:text-slate-300 uppercase">
                      AI Insights
                    </span>
                    <Sparkles size={16} className="text-slate-500 dark:text-slate-300" />
                  </div>
                  <div className="space-y-2">
                    <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100 tracking-wide">Career Compatibility</h4>
                    <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed font-light line-clamp-4">
                      {profile?.name ? (
                        `Your match score for ${keywords || 'target roles'} has increased by ${analytics.successRate}% based on your parsed CV stacks. Your resume aligns with ${analytics.profileStrength}% of trending tech gaps.`
                      ) : (
                        "Upload your CV in the sidebar or below to unlock deep career compatibility insights, target recommendations, and automated match indicators."
                      )}
                    </p>
                  </div>
                </div>
                
                <div className="flex justify-between items-center pt-2 relative z-10">
                  {/* Page indicator dots */}
                  <div className="flex gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-black dark:bg-white"></span>
                    <span className="w-1.5 h-1.5 rounded-full bg-black/30 dark:bg-white/45"></span>
                    <span className="w-1.5 h-1.5 rounded-full bg-black/30 dark:bg-white/45"></span>
                    <span className="w-1.5 h-1.5 rounded-full bg-black/30 dark:bg-white/45"></span>
                  </div>
                  <button 
                    onClick={() => setActiveTab('critique')}
                    className="w-8 h-8 rounded-full bg-black/5 dark:bg-white/10 hover:bg-black/15 dark:hover:bg-white/20 flex items-center justify-center transition-all border border-black/10 dark:border-white/5 group-hover:scale-105 active:scale-95 cursor-pointer"
                    title="Optimize ATS Resume"
                  >
                    <ArrowUpRight size={14} className="text-black dark:text-white" />
                  </button>
                </div>
              </div>

              {/* Card B: Match Trends (SVG Line Chart) */}
              <div className="carbon-panel p-7 flex flex-col justify-between h-[280px]">
                <div className="flex justify-between items-start">
                  <div>
                    <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                      Match Telemetry
                    </span>
                    <h3 className="text-sm font-bold text-slate-800 dark:text-white tracking-wide">Match Success</h3>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-bold text-neutral-900 dark:text-white font-mono">+{analytics.successRate}%</span>
                    <span className="text-[9px] text-slate-500 block">since scan</span>
                  </div>
                </div>
                
                {/* Beautiful SVG line chart with animations */}
                <div className="flex-1 w-full flex items-end justify-center relative min-h-[120px] pt-4 text-neutral-800 dark:text-slate-200">
                  <svg className="w-full h-full min-h-[100px]" viewBox="0 0 300 100" preserveAspectRatio="none">
                    <defs>
                      <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="currentColor" stopOpacity="0.15" />
                        <stop offset="100%" stopColor="currentColor" stopOpacity="0.0" />
                      </linearGradient>
                    </defs>
                    
                    {/* Grid lines */}
                    <line x1="0" y1="20" x2="300" y2="20" stroke="rgba(128,128,128,0.05)" strokeDasharray="3,3" />
                    <line x1="0" y1="50" x2="300" y2="50" stroke="rgba(128,128,128,0.05)" strokeDasharray="3,3" />
                    <line x1="0" y1="80" x2="300" y2="80" stroke="rgba(128,128,128,0.05)" strokeDasharray="3,3" />
                    
                    {/* Area under the curve */}
                    <path 
                      d="M0,90 Q40,65 80,75 T160,35 T240,45 T300,20 L300,100 L0,100 Z" 
                      fill="url(#chartGradient)" 
                      className="animate-svg-dash"
                    />
                    
                    {/* Curve path */}
                    <path 
                      d="M0,90 Q40,65 80,75 T160,35 T240,45 T300,20" 
                      fill="none" 
                      stroke="currentColor" 
                      strokeWidth="2.5" 
                      strokeLinecap="round"
                      className="animate-svg-dash"
                    />
                    
                    {/* Interactive dots along the path */}
                    <circle cx="160" cy="35" r="4" fill="currentColor" stroke="currentColor" strokeWidth="2" className="cursor-pointer hover:r-6 transition-all text-black dark:text-white" />
                    <circle cx="300" cy="20" r="4" fill="currentColor" stroke="currentColor" strokeWidth="2" className="text-black dark:text-white" />
                  </svg>
                </div>
                
                {/* X-axis labels */}
                <div className="flex justify-between text-[9px] text-slate-500 font-mono pt-3 border-t border-slate-200 dark:border-slate-900/40">
                  <span>15</span>
                  <span>16</span>
                  <span>17</span>
                  <span>18</span>
                  <span>19</span>
                  <span className="text-neutral-900 dark:text-slate-100 font-bold">20</span>
                  <span>21</span>
                  <span>22</span>
                  <span>23</span>
                  <span>24</span>
                </div>
              </div>

              {/* Card C: ATS Compatibility Score (Monochrome Radial Progress Gauge) */}
              <div className="carbon-panel p-7 flex flex-col justify-between h-[280px]">
                <div className="flex justify-between items-start">
                  <div>
                    <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                      ATS Matching
                    </span>
                    <h3 className="text-sm font-bold text-slate-800 dark:text-white tracking-wide">ATS Compatibility</h3>
                  </div>
                  <button 
                    onClick={() => setActiveTab('critique')}
                    className="p-1.5 bg-slate-200/60 dark:bg-slate-900 border border-slate-300 dark:border-slate-800 text-slate-500 hover:text-slate-900 dark:hover:text-white rounded-xl transition-all cursor-pointer"
                    title="Critique details"
                  >
                    <ArrowUpRight size={13} />
                  </button>
                </div>
                
                <div className="flex-grow flex items-center justify-center py-2 relative">
                  <svg className="w-32 h-32 transform -rotate-90">
                    {/* Track circle */}
                    <circle 
                      cx="64" 
                      cy="64" 
                      r="48" 
                      fill="none" 
                      stroke="rgba(128, 128, 128, 0.08)" 
                      strokeWidth="8" 
                    />
                    {/* Progress circle */}
                    <circle 
                      cx="64" 
                      cy="64" 
                      r="48" 
                      fill="none" 
                      stroke="currentColor" 
                      strokeWidth="8" 
                      strokeDasharray="301.6" 
                      strokeDashoffset={301.6 - (301.6 * (analytics.resumeScore || 50)) / 100}
                      strokeLinecap="round"
                      className="text-neutral-900 dark:text-white transition-all duration-1000 ease-out animate-svg-dash"
                    />
                  </svg>
                  
                  {/* Center Label */}
                  <div className="absolute inset-0 flex flex-col items-center justify-center mt-2">
                    <span className="text-2xl font-black font-mono text-neutral-900 dark:text-white">
                      {analytics.resumeScore || 0}%
                    </span>
                    <span className="text-[8px] uppercase tracking-widest text-slate-500 font-bold">
                      Score
                    </span>
                  </div>
                </div>
                
                <div className="flex justify-between items-center text-[10px] text-slate-400 font-light border-t border-slate-200 dark:border-slate-900/60 pt-3">
                  <div className="flex items-center gap-1.5">
                    <div className="w-1.5 h-1.5 rounded-full bg-neutral-900 dark:bg-white"></div>
                    <span>Target Score</span>
                  </div>
                  <span className="font-mono font-bold text-neutral-900 dark:text-white">&gt; 80%</span>
                </div>
              </div>

            </div>

            {/* ROW 2: Recent Discoveries (Transactions layout) & Career Splits (Spending Layout) */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8">
              
              {/* Left Side: Recent Discoveries (2/3 width) */}
              <div className="lg:col-span-8 carbon-panel p-7 space-y-6 flex flex-col justify-between min-h-[380px]">
                <div className="flex justify-between items-center border-b border-slate-200 dark:border-slate-900/60 pb-4">
                  <div>
                    <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                      Scan Results
                    </span>
                    <h3 className="text-sm font-bold text-slate-800 dark:text-white tracking-wide">Recent Discoveries</h3>
                  </div>
                  <button 
                    onClick={() => setActiveTab('jobs')}
                    className="text-[10px] font-bold text-black dark:text-white hover:text-slate-700 dark:hover:text-slate-300 uppercase tracking-wider flex items-center gap-1 transition-colors cursor-pointer"
                  >
                    <span>View All</span>
                    <ChevronRight size={12} />
                  </button>
                </div>
                
                <div className="flex-grow overflow-y-auto space-y-3 pr-1 max-h-[260px] scrollbar-thin">
                  {jobs.slice(0, 5).map((job, idx) => {
                    // Pick a clean, monochrome gradient for company logo placeholder
                    const grads = [
                      'from-slate-800 to-slate-900 dark:from-slate-200 dark:to-slate-400',
                      'from-neutral-700 to-neutral-900 dark:from-neutral-300 dark:to-neutral-500',
                      'from-gray-700 to-gray-900 dark:from-gray-300 dark:to-gray-500',
                      'from-zinc-700 to-zinc-900 dark:from-zinc-300 dark:to-zinc-500',
                      'from-stone-700 to-stone-900 dark:from-stone-300 dark:to-stone-500'
                    ];
                    const grad = grads[idx % grads.length];
                    
                    return (
                      <div 
                        key={job.job_id} 
                        className="flex items-center justify-between p-3.5 bg-slate-100/50 dark:bg-slate-900/20 border border-slate-200 dark:border-slate-900/40 rounded-2xl hover:bg-slate-200/50 dark:hover:bg-slate-900/40 transition-all duration-300"
                      >
                        <div className="flex items-center gap-3.5 min-w-0">
                          {/* Logo Badge */}
                          <div className={`w-10 h-10 rounded-xl bg-gradient-to-tr ${grad} flex items-center justify-center text-white dark:text-slate-900 font-black text-xs shrink-0 shadow-md`}>
                            {job.company ? job.company.slice(0, 2).toUpperCase() : 'JB'}
                          </div>
                          <div className="min-w-0">
                            <h4 className="text-xs font-bold text-slate-800 dark:text-white truncate max-w-[180px] lg:max-w-[240px]">
                              {job.title}
                            </h4>
                            <p className="text-[10px] text-slate-500 font-medium tracking-wide">
                              {job.company} &bull; <span className="text-slate-900/70 dark:text-slate-300/70">{job.source}</span>
                            </p>
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-6 shrink-0">
                          <span className="hidden md:inline text-[10px] text-slate-500 font-mono">
                            {job.location || 'Remote'}
                          </span>
                          <span className="text-[10px] text-slate-400 font-medium">
                            {job.experience ? job.experience.split(' ')[0] : 'Experienced'}
                          </span>
                          <div className="text-right">
                            <span className={`text-xs font-bold font-mono ${job.matchScore >= 80 ? 'text-black dark:text-white' : 'text-slate-500 dark:text-slate-400'}`}>
                              +{job.matchScore || 0}%
                            </span>
                            <span className="text-[8px] text-slate-500 uppercase tracking-widest block font-bold">
                              Match
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                  {jobs.length === 0 && (
                    <div className="flex flex-col items-center justify-center py-12 text-slate-500">
                      <Briefcase size={24} className="text-slate-700 mb-2" />
                      <span className="text-xs font-light">No crawled positions logged in database yet.</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Right Side: Market Splits (1/3 width) */}
              <div className="lg:col-span-4 carbon-panel p-7 space-y-6 flex flex-col justify-between min-h-[380px]">
                <div className="border-b border-slate-200 dark:border-slate-900/60 pb-4">
                  <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                    Career Splits
                  </span>
                  <h3 className="text-sm font-bold text-slate-800 dark:text-white tracking-wide">Market Demand</h3>
                </div>
                
                {marketInsights ? (
                  <div className="flex-grow space-y-5 flex flex-col justify-center">
                    <div>
                      <div className="flex justify-between text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2">
                        <span>Junior / Fresher</span>
                        <span className="font-mono text-black dark:text-white font-bold">{marketInsights.experienceDemands?.junior || 0}%</span>
                      </div>
                      <div className="w-full h-1.5 bg-slate-200 dark:bg-slate-900 rounded-full overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-slate-800 to-black dark:from-slate-300 dark:to-white rounded-full transition-all duration-750" style={{ width: `${marketInsights.experienceDemands?.junior || 0}%` }}></div>
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2">
                        <span>Mid Level</span>
                        <span className="font-mono text-black dark:text-white font-bold">{marketInsights.experienceDemands?.mid || 0}%</span>
                      </div>
                      <div className="w-full h-1.5 bg-slate-200 dark:bg-slate-900 rounded-full overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-slate-600 to-slate-800 dark:from-slate-400 dark:to-slate-200 rounded-full transition-all duration-750" style={{ width: `${marketInsights.experienceDemands?.mid || 0}%` }}></div>
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2">
                        <span>Senior / Staff</span>
                        <span className="font-mono text-black dark:text-white font-bold">{marketInsights.experienceDemands?.senior || 0}%</span>
                      </div>
                      <div className="w-full h-1.5 bg-slate-200 dark:bg-slate-900 rounded-full overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-slate-400 to-slate-600 dark:from-slate-500 dark:to-slate-300 rounded-full transition-all duration-750" style={{ width: `${marketInsights.experienceDemands?.senior || 0}%` }}></div>
                      </div>
                    </div>
                    
                    {/* Bottom Category Badges */}
                    <div className="grid grid-cols-3 gap-2.5 pt-3 border-t border-slate-200 dark:border-slate-900/60 mt-2">
                      <div className="bg-slate-100 dark:bg-slate-900/50 p-2 border border-slate-200 dark:border-slate-900 rounded-xl text-center">
                        <span className="text-[8px] text-slate-500 uppercase block">Intern</span>
                        <span className="text-xs font-bold text-slate-800 dark:text-slate-200 font-mono mt-0.5 block">{marketInsights.jobTypeDemands?.internship || 0}%</span>
                      </div>
                      <div className="bg-slate-100 dark:bg-slate-900/50 p-2 border border-slate-200 dark:border-slate-900 rounded-xl text-center">
                        <span className="text-[8px] text-slate-500 uppercase block">Fulltime</span>
                        <span className="text-xs font-bold text-slate-800 dark:text-slate-200 font-mono mt-0.5 block">{marketInsights.jobTypeDemands?.fulltime || 0}%</span>
                      </div>
                      <div className="bg-slate-100 dark:bg-slate-900/50 p-2 border border-slate-200 dark:border-slate-900 rounded-xl text-center">
                        <span className="text-[8px] text-slate-500 uppercase block">Contract</span>
                        <span className="text-xs font-bold text-slate-800 dark:text-slate-200 font-mono mt-0.5 block">{marketInsights.jobTypeDemands?.contract || 0}%</span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="flex-grow flex items-center justify-center text-slate-600 text-[11px] text-center font-light py-8">
                    Loading demand aggregates from telemetry stream...
                  </div>
                )}
              </div>

            </div>

            {/* ROW 3: Config Panel & Real-time Logs Console */}
            <div id="hunt-config-section" className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8">
              
              {/* Config Form (1/2 width) */}
              <div className="lg:col-span-6 carbon-panel p-7 space-y-6">
                <div>
                  <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider block mb-1">01 . Config</span>
                  <h3 className="text-sm font-bold text-slate-800 dark:text-white tracking-wide">Hunt Parameters</h3>
                </div>

                <div className="space-y-4 text-xs">
                  <div className="space-y-1.5">
                    <label className="text-[9px] font-bold text-slate-400 uppercase tracking-widest pl-0.5">Job Keywords</label>
                    <input type="text" value={keywords} onChange={(e) => setKeywords(e.target.value)} placeholder="e.g. Frontend Engineer, Golang, React" className="w-full bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800/80 p-3 focus:border-neutral-500 outline-none text-slate-800 dark:text-white text-xs rounded-xl" />
                  </div>
                  
                  <div className="space-y-1.5">
                    <label className="text-[9px] font-bold text-slate-400 uppercase tracking-widest pl-0.5">Preferred Locations</label>
                    <input type="text" value={locations} onChange={(e) => setLocations(e.target.value)} placeholder="e.g. Remote, Bangalore, New York" className="w-full bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800/80 p-3 focus:border-neutral-500 outline-none text-slate-800 dark:text-white text-xs rounded-xl" />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                      <label className="text-[9px] font-bold text-slate-400 uppercase tracking-widest pl-0.5">Job Commitment</label>
                      <select value={jobType} onChange={(e) => setJobType(e.target.value)} className="w-full bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800/80 p-3 focus:border-neutral-500 outline-none text-slate-800 dark:text-slate-200 text-xs rounded-xl">
                        <option value="All">All Commitments</option>
                        <option value="F">Full-time Only</option>
                        <option value="P">Part-time Only</option>
                        <option value="I">Internships Only</option>
                      </select>
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-[9px] font-bold text-slate-400 uppercase tracking-widest pl-0.5">Experience Seniority</label>
                      <select value={expLevel} onChange={(e) => setExpLevel(e.target.value)} className="w-full bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800/80 p-3 focus:border-neutral-500 outline-none text-slate-800 dark:text-slate-200 text-xs rounded-xl">
                        <option value="All">All Seniorities</option>
                        <option value="2">Intern / Associate</option>
                        <option value="4">Experienced / Senior</option>
                      </select>
                    </div>
                  </div>

                  <button onClick={savePreferences} disabled={savingPrefs} className="w-full py-3 bg-black dark:bg-white hover:bg-neutral-800 dark:hover:bg-slate-200 text-white dark:text-slate-950 font-bold text-[10px] uppercase tracking-widest rounded-xl transition-all duration-300 hover:-translate-y-0.5 active:translate-y-0 cursor-pointer mt-2 shadow-md">
                    {savingPrefs ? 'Syncing Parameters...' : 'Save Configuration'}
                  </button>
                </div>
              </div>

              {/* Logs Console (1/2 width) */}
              <div className="lg:col-span-6 carbon-panel p-7 flex flex-col justify-between h-auto min-h-[360px]">
                <div className="mb-4">
                  <div className="flex justify-between items-center">
                    <div>
                      <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider block mb-1">02 . Console</span>
                      <h3 className="text-sm font-bold text-slate-800 dark:text-white tracking-wide">System Stream Logs</h3>
                    </div>
                    <div className="flex items-center gap-2 px-2.5 py-1 bg-black/5 dark:bg-white/10 border border-black/10 dark:border-white/20 rounded-full">
                      <span className="w-1.5 h-1.5 rounded-full bg-black dark:bg-white animate-ping"></span>
                      <span className="text-[8px] font-bold text-black dark:text-white uppercase tracking-widest">Streaming</span>
                    </div>
                  </div>
                </div>

                <div className="flex-grow bg-slate-950 dark:bg-slate-950/80 border border-slate-300 dark:border-slate-900/60 p-4 font-mono text-[9.5px] rounded-2xl overflow-y-auto space-y-2 leading-relaxed h-[220px] scrollbar-thin scanner-glow">
                  {logs.map((log, i) => (
                    <div key={i} className="text-slate-400 break-all border-b border-white/[0.01] pb-1.5">
                      <span className="text-slate-500 dark:text-slate-400 mr-2">[{new Date().toLocaleTimeString()}]</span>
                      {log}
                    </div>
                  ))}
                  {logs.length === 0 && (
                    <div className="text-slate-700 flex items-center justify-center h-full gap-2">
                      <Terminal size={14} className="animate-pulse" />
                      <span>Awaiting scanning loops and network handshakes...</span>
                    </div>
                  )}
                  <div ref={logEndRef} />
                </div>
              </div>

            </div>

            {/* Bottom Section: Pipeline Tracker */}
            <div className="carbon-panel p-7 space-y-5">
              <div>
                <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                  03 . Pipeline
                </span>
                <h3 className="text-sm font-bold text-slate-800 dark:text-white tracking-wide">Application Journey</h3>
              </div>
              
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                {[
                  { label: 'Crawled Jobs', val: analytics.totalJobs, color: 'text-slate-700 dark:text-slate-300' },
                  { label: 'Match \u2265 80%', val: analytics.matchedCount, color: 'text-neutral-900 dark:text-white' },
                  { label: 'Saved Hunt', val: analytics.savedCount, color: 'text-slate-700 dark:text-slate-300' },
                  { label: 'Applied', val: analytics.appliedCount, color: 'text-neutral-700 dark:text-neutral-300' },
                  { label: 'Interviews', val: analytics.interviewCount, color: 'text-neutral-900 dark:text-white' }
                ].map((item, index) => (
                  <div key={index} className="p-4 bg-slate-100/50 dark:bg-slate-900/25 border border-slate-200 dark:border-slate-900 rounded-2xl text-center shadow-[inset_0_0_12px_rgba(255,255,255,0.01)] hover:border-slate-300 dark:hover:border-slate-800/80 transition-all duration-300">
                    <span className="text-[8px] font-bold text-slate-500 uppercase tracking-widest block mb-1">
                      {item.label}
                    </span>
                    <span className={`text-2xl font-black font-mono ${item.color}`}>
                      {item.val}
                    </span>
                  </div>
                ))}
              </div>
            </div>

          </div>
        )}

        {/* Tab 01: Discoveries / Jobs Feed */}
        {activeTab === 'jobs' && (
          <div className="space-y-8 lg:space-y-10">
            <div className="flex justify-between items-end border-b border-slate-200 dark:border-slate-900/60 pb-6">
              <div>
                <span className="text-[10px] font-bold text-slate-500 dark:text-slate-400 font-mono tracking-widest uppercase block mb-1">01 . Discoveries</span>
                <h2 className="text-2xl font-black uppercase tracking-wider text-slate-800 dark:text-white">Active Postings</h2>
              </div>
              <div className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">
                Matches Available: {filteredJobs.length}
              </div>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">
              {/* Filters sidebar */}
              <div className="xl:col-span-3 space-y-6">
                <div className="carbon-panel p-6 space-y-6 sticky top-6">
                  <h3 className="text-xs font-bold uppercase tracking-widest text-slate-800 dark:text-white border-b border-slate-200 dark:border-slate-900/60 pb-3">Filter Results</h3>
                  
                  <div className="space-y-5 text-xs">
                    <div className="space-y-1.5">
                      <label className="text-[9px] font-bold text-slate-400 uppercase tracking-widest pl-0.5">Query</label>
                      <input 
                        type="text" 
                        value={filterKeyword} 
                        onChange={(e) => setFilterKeyword(e.target.value)} 
                        placeholder="Title, Company, Skills..."
                        className="w-full bg-white dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800/80 p-2.5 focus:border-neutral-500 outline-none text-slate-800 dark:text-white text-xs rounded-xl" 
                      />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-[9px] font-bold text-slate-400 uppercase tracking-widest pl-0.5">Location Mode</label>
                      <select value={filterRemote} onChange={(e) => setFilterRemote(e.target.value)} className="w-full bg-white dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800/80 p-2.5 focus:border-neutral-500 outline-none text-slate-800 dark:text-slate-200 text-xs rounded-xl">
                        <option value="All">All Locations</option>
                        <option value="Remote">Remote Only</option>
                        <option value="Onsite">Onsite Only</option>
                        <option value="Hybrid">Hybrid Only</option>
                      </select>
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-[9px] font-bold text-slate-400 uppercase tracking-widest pl-0.5">Source</label>
                      <select value={filterSource} onChange={(e) => setFilterSource(e.target.value)} className="w-full bg-white dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800/80 p-2.5 focus:border-neutral-500 outline-none text-slate-800 dark:text-slate-200 text-xs rounded-xl">
                        <option value="All">All Sources</option>
                        <option value="LinkedIn">LinkedIn</option>
                        <option value="Naukri">Naukri</option>
                        <option value="Wellfound">Wellfound</option>
                        <option value="YC Jobs">YC Jobs</option>
                      </select>
                    </div>
                    <div className="space-y-2">
                      <div className="flex justify-between items-center mb-1">
                        <label className="text-[9px] font-bold text-slate-400 uppercase tracking-widest pl-0.5">Min Match Score</label>
                        <span className="font-mono text-black dark:text-white font-bold">{filterMinScore}%</span>
                      </div>
                      <input 
                        type="range" 
                        min="0" 
                        max="100" 
                        value={filterMinScore} 
                        onChange={(e) => setFilterMinScore(Number(e.target.value))} 
                        className="w-full accent-black dark:accent-white bg-slate-200 dark:bg-slate-900" 
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Opportunities Feed */}
              <div className="xl:col-span-9 space-y-6">
                <div className="space-y-5">
                  {filteredJobs.map((job) => (
                    <div 
                      key={job.job_id} 
                      className={`carbon-panel p-6 border-l-4 transition-all duration-300 ${
                        job.matchScore >= 80 
                          ? 'border-l-neutral-900 dark:border-l-white shadow-[0_8px_24px_rgba(0,0,0,0.02)]' 
                          : 'border-l-slate-200 dark:border-l-slate-800'
                      }`}
                    >
                      <div className="flex flex-col md:flex-row gap-6 justify-between items-start">
                        {/* Job Details */}
                        <div className="space-y-4 flex-1 min-w-0 w-full">
                          <div className="flex flex-wrap gap-2 items-center">
                            <span className="px-2.5 py-1 bg-slate-100 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 text-[9px] font-bold font-mono rounded-lg">
                              {job.source}
                            </span>
                            {job.remote_status && (
                              <span className="px-2.5 py-1 bg-slate-100 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 text-[9px] font-bold font-mono rounded-lg">
                                {job.remote_status}
                              </span>
                            )}
                            {job.experience && (
                              <span className="px-2.5 py-1 bg-slate-100 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 text-[9px] font-bold font-mono rounded-lg">
                                {job.experience}
                              </span>
                            )}
                          </div>
                          
                          <div>
                            <h4 className="text-base font-bold text-slate-800 dark:text-white tracking-wide truncate">{job.title}</h4>
                            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mt-0.5">{job.company} &bull; <span className="font-normal text-slate-400 normal-case">{job.location}</span></p>
                          </div>
                          
                          <p className="text-xs text-slate-400 dark:text-slate-400 leading-relaxed font-light line-clamp-3">
                            {job.summary || job.description}
                          </p>

                          {/* Skill alignment tag arrays */}
                          <div className="space-y-2 pt-1">
                            {job.matchedSkills && job.matchedSkills.length > 0 && (
                              <div className="flex flex-wrap items-center gap-1.5">
                                <span className="text-[8px] font-bold text-slate-500 uppercase tracking-wider mr-1.5">Matched:</span>
                                {job.matchedSkills.map((s, idx) => (
                                  <span key={idx} className="px-2 py-0.5 bg-slate-200 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 text-[9px] font-mono rounded-md">
                                    {s}
                                  </span>
                                ))}
                              </div>
                            )}
                            {job.missingSkills && job.missingSkills.length > 0 && (
                              <div className="flex flex-wrap items-center gap-1.5">
                                <span className="text-[8px] font-bold text-slate-500 uppercase tracking-wider mr-1.5">Missing:</span>
                                {job.missingSkills.map((s, idx) => (
                                  <span key={idx} className="px-2 py-0.5 bg-slate-100 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 text-[9px] font-mono rounded-md border-dashed">
                                    {s}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Analysis Scores & Actions */}
                        <div className="flex flex-row md:flex-col justify-between items-center md:items-end w-full md:w-auto border-t md:border-t-0 border-slate-200 dark:border-slate-900/60 pt-4 md:pt-0 gap-4 shrink-0">
                          <div className="text-right">
                            <span className="text-[9px] text-slate-500 font-bold uppercase tracking-wider block mb-0.5">Match score</span>
                            <span className={`text-2xl font-black font-mono ${job.matchScore >= 80 ? 'text-black dark:text-white' : 'text-slate-500 dark:text-slate-300'}`}>
                              {job.matchScore || 0}%
                            </span>
                          </div>

                          {job.recommendationReason && (
                            <div className="hidden lg:block max-w-[200px] text-right text-[9px] text-slate-500 leading-snug font-light italic">
                              "{job.recommendationReason.slice(0, 75)}..."
                            </div>
                          )}

                          <div className="flex gap-2 w-full md:w-auto justify-end">
                            {job.status !== 'applied' ? (
                              <a 
                                href={job.url} 
                                target="_blank" 
                                rel="noopener noreferrer" 
                                onClick={() => updateJobStatus(job.job_id, 'applied')}
                                className="px-4 py-2.5 bg-black dark:bg-white hover:bg-neutral-800 dark:hover:bg-slate-200 text-white dark:text-black rounded-xl text-[10px] font-bold uppercase tracking-wider text-center transition-all duration-300 shadow-md cursor-pointer"
                              >
                                {job.company && job.company !== 'N/A' ? `Apply Now` : `Apply Now`}
                              </a>
                            ) : (
                              <div className="flex gap-2">
                                <span className="px-3 py-2.5 bg-slate-100 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 text-[10px] font-bold uppercase tracking-wider rounded-xl flex items-center gap-1.5">
                                  <Check size={11} className="text-black dark:text-white" /> Applied
                                </span>
                                <a 
                                  href={job.url} 
                                  target="_blank" 
                                  rel="noopener noreferrer" 
                                  className="px-3 py-2.5 bg-slate-100 dark:bg-slate-900/60 hover:bg-slate-200 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 text-[10px] font-bold uppercase tracking-wider text-center rounded-xl transition-all duration-300 cursor-pointer"
                                >
                                  Revisit
                                </a>
                              </div>
                            )}
                            {job.status !== 'saved' && job.status !== 'applied' && (
                              <button 
                                onClick={() => updateJobStatus(job.job_id, 'saved')}
                                className="p-2.5 bg-slate-100 dark:bg-slate-900/60 hover:bg-slate-200 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-white rounded-xl transition-all duration-300 cursor-pointer"
                                title="Bookmark Listing"
                              >
                                <Bookmark size={12} />
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}

                  {filteredJobs.length === 0 && (
                    <div className="carbon-panel p-16 text-center text-slate-500 text-xs">
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
          <div className="space-y-8 lg:space-y-10 max-w-4xl">
            <div className="flex justify-between items-end border-b border-slate-200 dark:border-slate-900/60 pb-6">
              <div>
                <span className="text-[10px] font-bold text-slate-500 dark:text-slate-400 font-mono tracking-widest uppercase block mb-1">02 . Skills Path</span>
                <h2 className="text-2xl font-black uppercase tracking-wider text-slate-800 dark:text-white">Skills Gap Analysis</h2>
              </div>
            </div>

            <p className="text-xs text-slate-500 dark:text-slate-500 leading-relaxed font-light max-w-2xl">
              Based on active search requirements across postings, your profile indicates specific technology gaps. 
              Adopt these tools to optimize your compatibility ratios.
            </p>

            {upskillPlan.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 lg:gap-8">
                {upskillPlan.map((plan, idx) => (
                  <div key={idx} className="carbon-panel p-7 space-y-6">
                    <div className="flex flex-col space-y-3">
                      <h4 className="text-base font-bold text-slate-800 dark:text-white tracking-wide">{plan.skill}</h4>
                      <div className="flex flex-wrap gap-2 text-[9px] uppercase font-bold tracking-wider font-mono">
                        <span className="px-2 py-1 bg-slate-100 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 rounded-md whitespace-nowrap">{plan.learningTime}</span>
                        <span className="px-2 py-1 bg-slate-200 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200 rounded-md leading-relaxed">{plan.roi}</span>
                      </div>
                    </div>
                    
                    <div className="space-y-4 text-xs leading-relaxed font-light">
                      <div>
                        <span className="text-[9px] text-slate-500 font-bold uppercase tracking-widest block mb-0.5">Recommended Course</span>
                        <span className="text-slate-700 dark:text-slate-300">{plan.course}</span>
                      </div>
                      <div>
                        <span className="text-[9px] text-slate-500 font-bold uppercase tracking-widest block mb-0.5">Practical Portfolio Project</span>
                        <span className="text-slate-700 dark:text-slate-300">{plan.project}</span>
                      </div>
                      {plan.certification && (
                        <div>
                          <span className="text-[9px] text-slate-500 font-bold uppercase tracking-widest block mb-0.5">Certification Goal</span>
                          <span className="text-slate-700 dark:text-slate-300">{plan.certification}</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="carbon-panel p-16 text-center text-slate-500 text-xs">
                Upload your resume to formulate a personalized learning roadmap.
              </div>
            )}
          </div>
        )}

        {/* Tab 03: Resume ATS Optimization Critique */}
        {activeTab === 'critique' && (
          <div className="space-y-8 lg:space-y-10 max-w-4xl">
            <div className="flex justify-between items-end border-b border-slate-200 dark:border-slate-900/60 pb-6">
              <div>
                <span className="text-[10px] font-bold text-slate-500 dark:text-slate-400 font-mono tracking-widest uppercase block mb-1">03 . ATS Optimize</span>
                <h2 className="text-2xl font-black uppercase tracking-wider text-slate-800 dark:text-white">Resume Critique Suggestions</h2>
              </div>
            </div>

            <p className="text-xs text-slate-500 dark:text-slate-500 leading-relaxed font-light max-w-2xl">
              AI-driven optimization critique matching your parsed profile structure against high-priority market demands.
            </p>

            {resumeSuggestions ? (
              <div className="space-y-6 text-xs font-light">
                <div className="carbon-panel p-7 space-y-4">
                  <h4 className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">High Impact Keywords to Add</h4>
                  <div className="flex flex-wrap gap-2 pt-1">
                    {resumeSuggestions.missingKeywords?.map((kw, idx) => (
                      <span key={idx} className="px-2.5 py-1 bg-black/5 dark:bg-white/10 border border-black/10 dark:border-white/20 text-black dark:text-white font-semibold font-mono rounded-lg">
                        + {kw}
                      </span>
                    ))}
                  </div>
                </div>
                
                <div className="carbon-panel p-7 space-y-3">
                  <h4 className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Formatting & Parsing Improvements</h4>
                  <p className="text-slate-700 dark:text-slate-300 leading-relaxed text-sm">{resumeSuggestions.atsImprovements}</p>
                </div>
                
                <div className="carbon-panel p-7 space-y-3">
                  <h4 className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Recommended Project Enhancements</h4>
                  <p className="text-slate-700 dark:text-slate-300 leading-relaxed text-sm">{resumeSuggestions.projectImprovements}</p>
                </div>
                
                {resumeSuggestions.grammarFixes && (
                  <div className="carbon-panel p-7 space-y-3">
                    <h4 className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Action Verbs & Impact Metrics</h4>
                    <p className="text-slate-700 dark:text-slate-300 leading-relaxed text-sm">{resumeSuggestions.grammarFixes}</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="carbon-panel p-16 text-center text-slate-500 text-xs">
                Upload your resume to analyze keyword gaps and ATS layout feedback.
              </div>
            )}
          </div>
        )}

        {/* Tab 04: Recruiter / Candidate Profile metadata details */}
        {activeTab === 'profile' && (
          <div className="space-y-8 lg:space-y-10 max-w-5xl">
            <div className="flex justify-between items-end border-b border-slate-200 dark:border-slate-900/60 pb-6">
              <div>
                <span className="text-[10px] font-bold text-slate-500 dark:text-slate-400 font-mono tracking-widest uppercase block mb-1">04 . Candidate Profile</span>
                <h2 className="text-2xl font-black uppercase tracking-wider text-slate-800 dark:text-white">Parsed Profile Parameters</h2>
              </div>
            </div>

            {profile ? (
              <div className="grid grid-cols-1 md:grid-cols-12 gap-8 text-xs leading-relaxed font-light">
                {/* Left side details */}
                <div className="md:col-span-4 carbon-panel p-7 space-y-6">
                  <div className="text-center space-y-3">
                    <div className="w-16 h-16 bg-gradient-to-tr from-neutral-800 to-neutral-600 dark:from-neutral-200 dark:to-neutral-400 text-white dark:text-slate-950 flex items-center justify-center text-xl font-black mx-auto rounded-2xl shadow-md uppercase">
                      {profile.name?.slice(0, 2)}
                    </div>
                    <div>
                      <h4 className="text-md font-bold text-slate-800 dark:text-white">{profile.name}</h4>
                      <span className="text-[9px] text-black dark:text-white font-bold uppercase tracking-widest block mt-1">{profile.current_role}</span>
                    </div>
                  </div>

                  <div className="thin-accent-line" />

                  <div className="space-y-4">
                    <div className="flex items-center gap-2.5 text-slate-500 dark:text-slate-400">
                      <Mail size={12} className="text-slate-500 dark:text-slate-300" /> <span>{profile.email || "No email parsed"}</span>
                    </div>
                    <div className="flex items-center gap-2.5 text-slate-500 dark:text-slate-400">
                      <Phone size={12} className="text-slate-500 dark:text-slate-300" /> <span>{profile.phone || "No phone parsed"}</span>
                    </div>
                    <div className="flex items-center gap-2.5 text-slate-500 dark:text-slate-400">
                      <MapPin size={12} className="text-slate-500 dark:text-slate-300" /> <span>{profile.location}</span>
                    </div>
                    
                    <div className="thin-accent-line" />
                    
                    <div className="flex justify-between text-slate-500 dark:text-slate-400">
                      <span>Experience YOE:</span> <span className="font-bold text-slate-800 dark:text-white font-mono">{profile.yoe} Years</span>
                    </div>
                    <div className="flex justify-between text-slate-500 dark:text-slate-400">
                      <span>Work Visa status:</span> <span className="font-bold text-slate-800 dark:text-white text-right">{profile.work_authorization || "Not Specified"}</span>
                    </div>

                    <button 
                      onClick={handleDeleteResume}
                      className="w-full text-center py-2.5 bg-red-950/20 hover:bg-red-900/10 border border-red-900/30 hover:border-red-800 text-red-400 font-bold text-[9px] uppercase tracking-widest rounded-xl transition-all duration-305 mt-6 cursor-pointer"
                    >
                      Remove Resume
                    </button>
                  </div>
                </div>

                {/* Right side details */}
                <div className="md:col-span-8 carbon-panel p-7 space-y-8">
                  <div className="space-y-3">
                    <h4 className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Extracted Technology Stack</h4>
                    <div className="flex flex-wrap gap-2 pt-1">
                      {profile.skills?.map((s, idx) => (
                        <span key={idx} className="px-2.5 py-1 bg-slate-200 dark:bg-slate-800 border border-slate-300 dark:border-slate-800 text-slate-700 dark:text-slate-300 font-mono text-[10px] rounded-lg">
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>
                  
                  {profile.projects && profile.projects.length > 0 && (
                    <div className="space-y-3">
                      <h4 className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Key Project Summaries</h4>
                      <ul className="list-disc pl-4 space-y-1.5 text-slate-600 dark:text-slate-400">
                        {profile.projects.map((p, idx) => (
                          <li key={idx} className="font-light">{p}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  
                  {profile.previous_roles && profile.previous_roles.length > 0 && (
                    <div className="space-y-3">
                      <h4 className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Previous Roles</h4>
                      <div className="flex flex-wrap gap-2 pt-1">
                        {profile.previous_roles.map((r, idx) => (
                          <span key={idx} className="px-2.5 py-1 bg-slate-100 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-400 text-[10px] rounded-lg">
                            {r}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2 border-t border-slate-200 dark:border-slate-900/60">
                    <div className="space-y-2">
                      <h4 className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Education Background</h4>
                      <ul className="list-disc pl-4 space-y-1 text-slate-600 dark:text-slate-400">
                        {profile.education?.map((e, idx) => (
                          <li key={idx}>{e}</li>
                        ))}
                      </ul>
                    </div>
                    <div className="space-y-2">
                      <h4 className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Candidate Target Settings</h4>
                      <div className="space-y-1.5 text-slate-600 dark:text-slate-400 pt-0.5">
                        <div>Preference commitment: <span className="text-slate-800 dark:text-white font-bold">{profile.internship_or_fulltime}</span></div>
                        <div>Target mode: <span className="text-slate-800 dark:text-white font-bold">{profile.remote_preference}</span></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="carbon-panel p-16 text-center space-y-6">
                <div className="text-slate-500 text-xs">
                  Resume details empty. Upload your resume (PDF, TXT, MD) in the sidebar toolbar, or paste it below to trigger AI profiling.
                </div>
                <div className="max-w-2xl mx-auto space-y-4">
                  <textarea 
                    placeholder="Paste your raw resume text here..." 
                    className="w-full h-48 bg-white dark:bg-slate-950/65 border border-slate-200 dark:border-slate-800 p-4 focus:border-neutral-500 outline-none text-xs text-slate-800 dark:text-white font-mono resize-none rounded-2xl"
                    value={pastedResumeText}
                    onChange={(e) => setPastedResumeText(e.target.value)}
                  />
                  <button 
                    onClick={handleResumePaste}
                    disabled={pasting || !pastedResumeText.trim()}
                    className="px-6 py-3 bg-black dark:bg-white hover:bg-neutral-800 dark:hover:bg-slate-200 text-white dark:text-slate-950 font-bold text-[10px] uppercase tracking-widest rounded-xl transition-all duration-300 disabled:opacity-50 cursor-pointer shadow-md"
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
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-md z-[100] flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800/80 backdrop-blur-xl max-w-2xl w-full p-8 space-y-6 shadow-2xl relative rounded-[24px] text-slate-800 dark:text-slate-100">
            <button 
              onClick={() => setShowPasteModal(false)}
              className="absolute top-6 right-6 text-slate-400 hover:text-slate-800 dark:hover:text-white transition-all text-xl font-bold outline-none cursor-pointer"
            >
              &times;
            </button>
            <div className="space-y-1.5">
              <h3 className="text-lg font-bold text-slate-800 dark:text-white uppercase tracking-widest flex items-center gap-2">
                Paste Resume Text
              </h3>
              <p className="text-xs text-slate-500">
                Paste your resume raw details directly below. The system will parse them and update metrics.
              </p>
            </div>
            
            <textarea 
              placeholder="Paste experiences, skills, and portfolio descriptions here..." 
              className="w-full h-64 bg-slate-50 dark:bg-slate-950/65 border border-slate-200 dark:border-slate-800 p-4 focus:border-neutral-500 outline-none text-xs text-slate-800 dark:text-white font-mono resize-none rounded-2xl"
              value={pastedResumeText}
              onChange={(e) => setPastedResumeText(e.target.value)}
            />
            
            <div className="flex gap-4 justify-end text-xs">
              <button 
                onClick={() => setShowPasteModal(false)}
                className="px-5 py-3 border border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-white uppercase tracking-widest font-bold rounded-xl transition-all duration-300 cursor-pointer"
              >
                Cancel
              </button>
              <button 
                onClick={handleResumePaste}
                disabled={pasting || !pastedResumeText.trim()}
                className="px-6 py-3 bg-black dark:bg-white text-white dark:text-black uppercase tracking-widest font-bold rounded-xl shadow-md transition-all duration-300 disabled:opacity-50 cursor-pointer"
              >
                {pasting ? 'Analyzing...' : 'Analyze Resume'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Payment Verification Modal (UPI Pay-In ₹1) */}
      {showPaymentModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-md z-[110] flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800/80 backdrop-blur-xl max-w-md w-full p-8 space-y-6 shadow-2xl relative rounded-[24px] text-slate-900 dark:text-slate-100">
            <button 
              onClick={() => {
                setShowPaymentModal(false);
                setPendingFile(null);
                setPendingPasteText('');
              }}
              className="absolute top-6 right-6 text-slate-400 hover:text-slate-800 dark:hover:text-white transition-all text-xl font-bold outline-none cursor-pointer"
            >
              &times;
            </button>
            
            <div className="space-y-1.5 text-center">
              <span className="inline-block px-2.5 py-0.5 bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 text-[9px] font-bold tracking-widest text-slate-600 dark:text-slate-400 rounded-full uppercase">
                Payment Verification
              </span>
              <h3 className="text-xl font-bold tracking-tight">
                Scan UPI to Match CV
              </h3>
              <p className="text-xs text-slate-500 max-w-xs mx-auto">
                Scan the QR code to transfer exactly ₹1.00 for autonomous matching and ATS indexing.
              </p>
            </div>

            <div className="flex flex-col items-center justify-center p-4 bg-slate-50 dark:bg-slate-950 rounded-2xl border border-slate-150 dark:border-slate-800">
              <img 
                src={`https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodeURIComponent("upi://pay?pa=8277098097@ibl&pn=JobSentinel&am=1.00&cu=INR&tn=JobSentinel%20Match")}`} 
                alt="UPI QR Code" 
                className="w-44 h-44 rounded-xl border border-slate-200 dark:border-slate-800" 
              />
              <span className="text-[11px] font-mono font-bold mt-3 text-slate-500 dark:text-slate-400">
                UPI ID: 8277098097@ibl
              </span>
            </div>

            <div className="space-y-2">
              <label className="text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider block">
                UPI Transaction UTR / Ref Number (12 digits)
              </label>
              <input 
                type="text" 
                maxLength={12}
                placeholder="e.g. 627192837482 or TEST12345678" 
                className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 rounded-xl outline-none focus:border-neutral-500 text-slate-800 dark:text-white text-xs font-mono"
                value={paymentUtr}
                onChange={(e) => setPaymentUtr(e.target.value)}
              />
              {paymentError && (
                <p className="text-red-500 text-[10px] font-semibold mt-1">
                  {paymentError}
                </p>
              )}
            </div>

            <div className="flex gap-4 justify-end text-xs pt-2">
              <button 
                onClick={() => {
                  setShowPaymentModal(false);
                  setPendingFile(null);
                  setPendingPasteText('');
                }}
                className="px-5 py-3 border border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white uppercase tracking-widest font-bold rounded-xl transition-all duration-300 cursor-pointer"
              >
                Cancel
              </button>
              <button 
                onClick={() => completePaymentAndSubmit(paymentUtr)}
                disabled={paymentVerifying || !paymentUtr.trim()}
                className="px-6 py-3 bg-black dark:bg-white text-white dark:text-black hover:bg-neutral-850 dark:hover:bg-slate-200 uppercase tracking-widest font-bold rounded-xl transition-all duration-300 disabled:opacity-50 cursor-pointer"
              >
                {paymentVerifying ? 'Verifying...' : 'Verify & Submit'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
