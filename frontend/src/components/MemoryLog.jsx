import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { History, Share2, Clock, MapPin, Loader2, Database, ShieldCheck, Terminal, Filter, Download, Trash2, Search } from 'lucide-react';
import { motion } from 'framer-motion';

const API_BASE = 'http://127.0.0.1:8000';

const MemoryLog = () => {
  const [decisions, setDecisions] = useState([]);
  const [signals, setSignals] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [decRes, sigRes] = await Promise.all([
          axios.get(`${API_BASE}/memory/decisions`),
          axios.get(`${API_BASE}/memory/signals`)
        ]);
        setDecisions(decRes.data.decisions);
        setSignals(sigRes.data.signals);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) return (
    <div className="flex flex-col items-center justify-center h-full gap-6">
      <Loader2 className="animate-spin text-blue-500" size={32} />
      <p className="text-[11px] font-bold uppercase tracking-widest text-slate-500">Decrypting Command History</p>
    </div>
  );

  return (
    <div className="flex flex-col h-full gap-8 overflow-hidden">
      {/* Log Header Controls */}
      <div className="flex items-center justify-between pb-6 border-b border-white/5">
         <div className="flex items-center gap-6">
            <h2 className="text-sm font-bold uppercase tracking-tight">System Event Logs</h2>
            <div className="flex gap-2">
               <div className="px-3 py-1 bg-blue-500/10 border border-blue-500/20 rounded-full text-[10px] font-bold text-blue-500 uppercase tracking-widest">
                  {decisions.length} Decisions
               </div>
               <div className="px-3 py-1 bg-white/5 border border-white/10 rounded-full text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                  {signals.length} Signals
               </div>
            </div>
         </div>
         <div className="flex gap-3">
            <div className="flex items-center gap-3 px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-slate-500 hover:text-white cursor-pointer transition-all">
               <Download size={14} />
               <span className="text-[10px] font-bold uppercase tracking-widest leading-none">Export CSV</span>
            </div>
         </div>
      </div>

      <div className="flex-grow grid grid-cols-12 gap-10 overflow-hidden">
         {/* Strategic Decisions Table */}
         <div className="col-span-12 lg:col-span-7 flex flex-col gap-6 overflow-hidden">
            <div className="flex items-center gap-3 mb-2">
               <History size={16} className="text-blue-500" />
               <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Decision Registry</h3>
            </div>
            <div className="flex-grow overflow-y-auto custom-scrollbar pr-4 space-y-4">
               {decisions.map((dec, idx) => (
                 <div key={idx} className="surface-deep p-6 rounded-xl border border-white/5 hover:border-blue-500/30 transition-all flex flex-col gap-5">
                    <div className="flex justify-between items-start">
                       <div className="flex items-center gap-4">
                          <div className="p-2 bg-blue-500/10 rounded-lg">
                             <MapPin size={16} className="text-blue-500" />
                          </div>
                          <div>
                             <span className="text-sm font-bold text-white uppercase">{dec.city}</span>
                             <div className="text-[10px] text-slate-600 font-bold uppercase tracking-widest mt-0.5">{dec.agent_source} Execution</div>
                          </div>
                       </div>
                       <span className="text-[10px] font-mono text-slate-600 font-bold">{new Date(dec.timestamp).toLocaleTimeString()}</span>
                    </div>
                    <p className="text-[13px] text-slate-400 leading-relaxed font-medium bg-black/20 p-4 rounded-lg border border-white/5">
                       {dec.summary}
                    </p>
                    <div className="flex items-center justify-between text-[10px] text-slate-700 font-bold uppercase tracking-widest">
                       <div className="flex items-center gap-2">
                          <Terminal size={12} />
                          <span>Status: <span className="text-emerald-500">Committed</span></span>
                       </div>
                       <span>REF_#{idx.toString().padStart(4, '0')}</span>
                    </div>
                 </div>
               ))}
            </div>
         </div>

         {/* Telemetry Signals Strip */}
         <div className="col-span-12 lg:col-span-5 flex flex-col gap-6 overflow-hidden">
            <div className="flex items-center gap-3 mb-2">
               <Share2 size={16} className="text-purple-500" />
               <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Signal Stream</h3>
            </div>
            <div className="flex-grow overflow-y-auto custom-scrollbar pr-4 space-y-3">
               {signals.map((sig, idx) => (
                 <div key={idx} className="p-5 bg-white/[0.02] border border-white/5 rounded-xl flex items-center justify-between group hover:bg-white/[0.04] transition-all">
                    <div className="flex flex-col gap-1">
                       <span className="text-[11px] font-bold text-slate-200 uppercase tracking-tight">{sig.city || 'GLOBAL'} Telemetry</span>
                       <div className="flex gap-2">
                          {sig.weather_label && <span className="text-[9px] text-blue-500 font-bold uppercase tracking-tighter">{sig.weather_label}</span>}
                          {sig.commodity_label && <span className="text-[9px] text-emerald-500 font-bold uppercase tracking-tighter">{sig.commodity_label}</span>}
                          {sig.crisis_label && <span className="text-[9px] text-rose-500 font-bold uppercase tracking-tighter">{sig.crisis_label}</span>}
                       </div>
                    </div>
                    <span className="text-[10px] font-mono text-slate-700 font-bold">{new Date(sig.timestamp).toLocaleTimeString()}</span>
                 </div>
               ))}
            </div>
         </div>
      </div>
    </div>
  );
};

export default MemoryLog;
