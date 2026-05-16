import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Upload, Briefcase, CheckCircle, XCircle, RefreshCw, ExternalLink, FileText } from 'lucide-react';

const API_BASE = 'http://localhost:8000/api';

function App() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');

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

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 30000); // Poll every 30s
    return () => clearInterval(interval);
  }, []);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API_BASE}/resume/upload`, formData);
      setMessage(response.data.message);
      setTimeout(() => setMessage(''), 5000);
    } catch (error) {
      setMessage('Upload failed');
    }
    setUploading(false);
  };

  return (
    <div className="min-h-screen p-8 bg-slate-900 text-slate-100">
      <header className="max-w-6xl mx-auto mb-12 flex justify-between items-center">
        <div>
          <h1 className="text-4xl font-bold text-blue-400 mb-2 flex items-center gap-3">
            <Briefcase size={36} /> JobSentinel Dashboard
          </h1>
          <p className="text-slate-400 text-lg">Automated Job Hunting & Resume Tailoring</p>
        </div>
        
        <div className="flex gap-4 items-center">
          <div className="relative">
            <input
              type="file"
              id="resume-upload"
              className="hidden"
              accept=".pdf"
              onChange={handleFileUpload}
              disabled={uploading}
            />
            <label
              htmlFor="resume-upload"
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-semibold cursor-pointer transition-all ${
                uploading ? 'bg-slate-700' : 'bg-blue-600 hover:bg-blue-500'
              }`}
            >
              {uploading ? <RefreshCw className="animate-spin" /> : <Upload size={20} />}
              {uploading ? 'Uploading...' : 'Update PDF Resume'}
            </label>
          </div>
          <button 
            onClick={fetchJobs}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 transition-colors"
          >
            <RefreshCw size={24} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </header>

      {message && (
        <div className={`max-w-6xl mx-auto mb-6 p-4 rounded-lg text-center font-bold ${
          message.includes('failed') ? 'bg-red-900/50 text-red-200' : 'bg-green-900/50 text-green-200'
        }`}>
          {message}
        </div>
      )}

      <main className="max-w-6xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {jobs.map((job) => (
            <div key={job.job_id} className="bg-slate-800 rounded-xl p-6 border border-slate-700 hover:border-blue-500/50 transition-all shadow-lg">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-xl font-bold text-white line-clamp-1">{job.title}</h3>
                  <p className="text-blue-300 font-medium">{job.company}</p>
                </div>
                <div className={`px-3 py-1 rounded-full text-xs font-bold uppercase ${
                  job.status === 'tailored' ? 'bg-green-900/50 text-green-400' : 'bg-slate-700 text-slate-400'
                }`}>
                  {job.status}
                </div>
              </div>

              <div className="flex items-center gap-4 mb-6">
                <div className="flex-1 bg-slate-700 h-2 rounded-full overflow-hidden">
                  <div 
                    className={`h-full transition-all duration-1000 ${
                      job.ats_score >= 80 ? 'bg-green-500' : job.ats_score >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                    }`}
                    style={{ width: `${job.ats_score || 0}%` }}
                  />
                </div>
                <span className="font-mono font-bold text-lg">
                  {job.ats_score || 0}%
                </span>
              </div>

              <div className="flex gap-3">
                <a
                  href={job.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 flex items-center justify-center gap-2 bg-slate-700 hover:bg-slate-600 text-white py-2 rounded-lg transition-colors text-sm font-semibold"
                >
                  <ExternalLink size={16} /> View Job
                </a>
                {job.status === 'tailored' && (
                  <button className="flex-1 flex items-center justify-center gap-2 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 py-2 rounded-lg transition-colors text-sm font-semibold border border-blue-400/30">
                    <FileText size={16} /> Resume
                  </button>
                )}
              </div>
              
              <div className="mt-4 text-[10px] text-slate-500 uppercase tracking-widest font-bold">
                Found at: {new Date(job.processed_at).toLocaleString()}
              </div>
            </div>
          ))}
        </div>
        
        {jobs.length === 0 && !loading && (
          <div className="text-center py-24 text-slate-500">
            <Briefcase size={64} className="mx-auto mb-4 opacity-20" />
            <p className="text-xl italic">No jobs discovered yet. The scanner is running in the background...</p>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
