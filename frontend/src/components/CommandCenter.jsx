import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Send, Terminal, Loader2, Cpu, Zap, Sparkles, User, Database, ShieldAlert, Activity, ArrowRight, Target, BarChart3, ChevronRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const API_BASE = 'http://127.0.0.1:8000';

const CommandCenter = ({ onIntel, history, setHistory, details }) => {
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [history]);

  const handleSend = async () => {
    const trimmedMessage = message.trim();
    if (!trimmedMessage || loading) return;

    const userMsg = { role: 'user', content: trimmedMessage };
    setHistory(prev => [...prev, userMsg]);
    setLoading(true);
    setMessage('');

    try {
      const res = await axios.post(`${API_BASE}/chat`, { message: trimmedMessage });
      const report = res.data?.report || {};
      const botMsg = { 
        role: 'bot', 
        content: report.summary || 'Strategic assessment complete.',
        parsed: res.data?.parsed_intent || null,
        report: report
      };
      setHistory(prev => [...prev, botMsg]);
      if (onIntel) onIntel(report);
    } catch (err) {
      console.error("[Neural Relay Error]", err);
      setHistory(prev => [...prev, { 
        role: 'bot', 
        content: 'Connection to Neural Relay failed. Verify local gateway on port 8000.', 
        error: true 
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-full gap-8 overflow-hidden min-h-0">
      {/* Interaction Console */}
      <div className="flex-[3] flex flex-col glass-panel rounded-2xl overflow-hidden relative min-w-0">
        <header className="px-10 py-6 border-b border-white/5 flex items-center justify-between bg-white/[0.02] shrink-0">
           <div className="flex items-center gap-4">
              <Sparkles size={20} className="text-blue-500" />
              <h1 className="text-xs font-tech font-bold uppercase tracking-[0.2em] text-white">Neural Relay Console</h1>
           </div>
           <div className="flex items-center gap-6">
              <button 
                onClick={() => setHistory([])}
                className="text-[9px] font-tech text-slate-500 hover:text-rose-500 transition-colors uppercase tracking-[0.2em] font-black"
                title="Clear Tactical Memory"
              >
                Purge History
              </button>
              {loading && (
                 <div className="flex items-center gap-3">
                    <Loader2 size={12} className="animate-spin text-blue-500" />
                    <span className="text-[10px] font-tech text-slate-500 uppercase tracking-widest">Processing Tactical Loop</span>
                 </div>
              )}
           </div>
        </header>

        <div ref={scrollRef} className="flex-grow overflow-y-auto p-10 flex flex-col gap-10 custom-scrollbar min-h-0">
           {history.length === 0 && (
             <div className="h-full flex flex-col items-center justify-center text-center opacity-20 select-none py-20">
                <Cpu size={60} className="mb-8 text-slate-500" />
                <h3 className="text-sm font-tech font-bold uppercase mb-4 text-white tracking-[0.4em]">Strategic Uplink Enabled</h3>
                <p className="text-[11px] text-slate-500 max-w-[320px] leading-relaxed font-bold uppercase tracking-widest">Interface for direct coordination of national grid assets. Input regional status or crisis directives below.</p>
             </div>
           )}
           {history.map((msg, idx) => (
             <div key={idx} className={`flex gap-6 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                <div className={`w-12 h-12 rounded-xl shrink-0 flex items-center justify-center border ${msg.role === 'user' ? 'bg-blue-600/15 border-blue-500/20 text-blue-500' : 'bg-surface border-white/10 text-slate-500 shadow-2xl'}`}>
                   {msg.role === 'user' ? <User size={24} /> : <Cpu size={22} />}
                </div>
                <div className={`flex flex-col gap-4 max-w-[85%] ${msg.role === 'user' ? 'items-end' : ''}`}>
                    <div className={`p-8 rounded-2xl text-[15px] leading-relaxed shadow-2xl ${msg.role === 'user' ? 'bg-blue-600 text-white font-bold italic' : 'bg-bg-elevated/80 text-slate-200 border border-white/5'}`}>
                       {msg.content}
                    </div>
                    {msg.report && !msg.error && (
                       <motion.button
                         initial={{ opacity: 0, y: 10 }}
                         animate={{ opacity: 1, y: 0 }}
                         onClick={() => window.dispatchEvent(new CustomEvent('nav-tab', { detail: 'intel' }))}
                         className="flex items-center gap-3 px-6 py-3 bg-white/5 border border-white/10 rounded-xl hover:bg-white/10 transition-all group"
                       >
                          <BarChart3 size={16} className="text-blue-500" />
                          <span className="text-[10px] font-tech text-white uppercase tracking-widest">Open Strategic Intel Analysis</span>
                          <ChevronRight size={14} className="text-slate-600 group-hover:translate-x-1 transition-transform" />
                       </motion.button>
                    )}
                    {msg.parsed && (
                       <div className="flex gap-4 text-[9px] font-tech font-bold text-slate-700 uppercase tracking-[0.2em] px-2 items-center">
                          <Target size={12} className="text-blue-500/30" />
                          <span>Vector: <span className="text-slate-400 font-black">{msg.parsed.city}</span></span>
                          <span className="opacity-10">//</span>
                          <span>Context: <span className="text-slate-600 font-medium italic">"{msg.parsed.context}"</span></span>
                       </div>
                    )}
                </div>
             </div>
           ))}
        </div>

        <div className="p-10 bg-white/[0.01] border-t border-white/5 shrink-0">
           <div className="flex gap-6 p-3 bg-surface rounded-2xl border border-white/10 focus-within:border-blue-500/40 transition-all shadow-2xl group relative overflow-hidden">
              <div className="absolute top-0 left-0 w-1 h-full bg-blue-500/0 group-focus-within:bg-blue-500 transition-colors"></div>
              <input 
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                className="flex-grow bg-transparent border-none outline-none text-white px-4 text-[14px] font-medium placeholder:text-slate-800 tracking-wide"
                placeholder="Tactical directive Input_..."
              />
              <button 
                onClick={handleSend}
                disabled={loading}
                className="bg-blue-600 hover:bg-blue-500 disabled:opacity-30 text-white px-10 py-3 rounded-xl font-tech font-black text-xs uppercase tracking-widest transition-all active:scale-95 flex items-center gap-4 shadow-[0_0_20px_rgba(37,99,235,0.3)]"
              >
                Execute <Send size={16} />
              </button>
           </div>
        </div>
      </div>

      {/* Intelligence Dashboard Side */}
      <div className="flex-[2] flex flex-col gap-8 overflow-hidden min-w-0">
        <div className="flex-grow glass-panel rounded-2xl overflow-hidden flex flex-col p-10 gap-10 overflow-y-auto custom-scrollbar">
           <div className="flex items-center justify-between border-b border-white/5 pb-8 shrink-0">
              <div className="flex items-center gap-4">
                 <Activity size={18} className="text-blue-500" />
                 <h3 className="text-[10px] font-tech font-bold text-slate-500 uppercase tracking-[0.3em]">Surveillance Link</h3>
              </div>
              {details && (
                 <div className={`px-5 py-2 rounded-xl text-[9px] font-tech font-bold uppercase tracking-widest border ${details.balance_mw >= 0 ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20 shadow-[0_0_15px_rgba(16,185,129,0.1)]' : 'bg-rose-500/10 text-rose-500 border-rose-500/20 shadow-[0_0_15px_rgba(244,63,94,0.1)]'}`}>
                    {details.status || 'SYNCED'}
                 </div>
              )}
           </div>

           {details ? (
             <div className="flex flex-col gap-12 animate-in fade-in slide-in-from-right-8 duration-700 transition-all">
                {/* Aggregate Metrics */}
                <div className="grid grid-cols-2 gap-6">
                   <div className="bg-white/[0.02] p-8 rounded-2xl border border-white/5 flex flex-col gap-4 relative overflow-hidden group">
                      <div className="absolute right-[-20%] bottom-[-20%] opacity-[0.03] rotate-12 group-hover:rotate-0 transition-transform duration-1000">
                         <Zap size={100} />
                      </div>
                      <span className="text-[9px] font-tech text-slate-500 font-bold uppercase tracking-widest">Gross Load</span>
                      <div className="flex items-baseline gap-3">
                         <span className="text-4xl font-tech font-black text-white italic tabular-nums tracking-tighter">{details.demand_mw}</span>
                         <span className="text-[10px] text-slate-700 font-tech font-black">MW</span>
                      </div>
                   </div>
                   <div className="bg-white/[0.02] p-8 rounded-2xl border border-white/5 flex flex-col gap-4 relative overflow-hidden group">
                      <div className="absolute right-[-20%] bottom-[-20%] opacity-[0.03] rotate--12 group-hover:rotate-0 transition-transform duration-1000">
                         <Activity size={100} />
                      </div>
                      <span className="text-[9px] font-tech text-slate-500 font-bold uppercase tracking-widest">Active Supply</span>
                      <div className="flex items-baseline gap-3">
                         <span className="text-4xl font-tech font-black text-emerald-500 italic tabular-nums tracking-tighter">{details.supply_mw}</span>
                         <span className="text-[10px] text-slate-700 font-tech font-black">MW</span>
                      </div>
                   </div>
                </div>

                {/* Resource Matrix Summary */}
                <div className="flex flex-col gap-8">
                   <div className="flex items-center justify-between">
                      <span className="text-[10px] font-tech font-bold text-slate-200 uppercase tracking-[0.2em] italic">Resource Matrix Overview</span>
                      <span className="text-[9px] text-slate-600 font-tech font-black uppercase">V4.2_SEC</span>
                   </div>
                   <div className="flex flex-col gap-4">
                      {Object.entries(details.supply_breakdown?.by_type || {}).slice(0, 4).map(([type, stats]) => (
                        <div key={type} className="flex items-center justify-between p-5 bg-white/[0.01] border border-white/5 rounded-2xl group hover:bg-white/[0.03] transition-all cursor-pointer">
                           <div className="flex items-center gap-5">
                              <span className="text-[13px] font-tech font-black text-slate-400 uppercase tracking-tighter group-hover:text-white transition-colors italic">{type}</span>
                           </div>
                           <div className="flex items-center gap-8">
                              <span className="text-[14px] font-tech font-black text-white tabular-nums tracking-tighter italic">{stats.current_mw} <span className="text-[8px] opacity-20">MW</span></span>
                              <div className="w-20 bg-white/5 h-1 rounded-full overflow-hidden border border-white/5">
                                 <motion.div 
                                   initial={{ width: 0 }}
                                   animate={{ width: `${(stats.current_mw / stats.max_mw) * 100}%` }}
                                   className="bg-blue-600 h-full shadow-[0_0_12px_#2563eb]"
                                 />
                              </div>
                           </div>
                        </div>
                      ))}
                   </div>
                </div>

                {/* AI Executive Strategy */}
                <div className="bg-blue-600/5 border border-blue-500/10 p-8 rounded-2xl relative overflow-hidden group shadow-[0_0_40px_rgba(0,0,0,0.5)]">
                   <div className="flex items-center gap-4 text-blue-500/40 mb-8">
                      <Terminal size={16} className="group-hover:text-blue-500 transition-colors" />
                      <span className="text-[10px] font-tech font-bold uppercase tracking-[0.3em]">Executive Summary</span>
                   </div>
                   <p className="text-[15px] leading-relaxed text-slate-300 font-bold italic border-l border-blue-500/30 pl-6">
                      {details.analysis || "System stability verified. Fallback protocols enabled for regional variance."}
                   </p>
                   <div className="mt-10 pt-10 border-t border-white/5 flex justify-between items-center text-[9px] text-slate-700 font-tech font-bold uppercase tracking-[0.4em]">
                      <div className="flex items-center gap-3">
                         <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_#10b981]"></div>
                         <span>Layer: {details.agent_source || 'Core'} Analysis</span>
                      </div>
                      <span className="opacity-20 italic">TAG_REF: GRID_SEC_A1</span>
                   </div>
                </div>
             </div>
           ) : (
             <div className="h-full flex flex-col items-center justify-center opacity-10 text-center py-40 select-none">
                <Database size={50} className="mb-8 text-slate-500" />
                <p className="text-[10px] font-tech font-bold uppercase tracking-[0.6em] text-slate-600 leading-relaxed">Neural Telemetry Ready.<br/>Awaiting Tactical Uplink Broadcast...</p>
             </div>
           )}
        </div>
      </div>
    </div>
  );
};

export default CommandCenter;
