import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Factory, Zap, ShieldCheck, MapPin, Gauge, Cpu, Loader2, List, Filter, Search, MoreHorizontal } from 'lucide-react';
import { motion } from 'framer-motion';

const API_BASE = 'http://127.0.0.1:8000';

const PlantGrid = () => {
  const [plants, setPlants] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPlants = async () => {
      try {
        const res = await axios.get(`${API_BASE}/plants`);
        setPlants(res.data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchPlants();
  }, []);

  if (loading) return (
    <div className="flex flex-col items-center justify-center h-full gap-6">
      <Loader2 className="animate-spin text-blue-500" size={32} />
      <p className="text-[11px] font-bold uppercase tracking-widest text-slate-500">Retrieving Asset Directory</p>
    </div>
  );

  return (
    <div className="flex flex-col h-full gap-8 overflow-hidden">
      {/* Search and Filters */}
      <div className="flex items-center justify-between pb-6 border-b border-white/5">
         <div className="flex items-center gap-6">
            <h2 className="text-sm font-bold uppercase tracking-tight">Infrastructure Portfolio</h2>
            <div className="px-3 py-1 bg-white/5 border border-white/10 rounded-full text-[10px] font-bold text-slate-500 uppercase tracking-widest">
               {plants.length} Active Nodes
            </div>
         </div>
         <div className="flex gap-3">
            <div className="flex items-center gap-3 px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-slate-500 hover:text-white cursor-pointer transition-all">
               <Filter size={14} />
               <span className="text-[10px] font-bold uppercase tracking-widest leading-none">Filters</span>
            </div>
            <div className="flex items-center gap-3 px-4 py-2 bg-blue-600 rounded-lg text-white cursor-pointer hover:bg-blue-500 transition-all">
               <Search size={14} />
               <span className="text-[10px] font-bold uppercase tracking-widest leading-none">Search Registry</span>
            </div>
         </div>
      </div>

      {/* Asset Grid */}
      <div className="flex-grow overflow-y-auto custom-scrollbar pr-4 pb-12">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4 gap-6">
          {plants.map((plant, idx) => (
            <motion.div
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: idx * 0.02 }}
              key={idx}
              className="surface-deep rounded-xl p-6 flex flex-col gap-6 relative group cursor-pointer hover:border-blue-500/30 transition-all shadow-xl"
            >
              <div className="flex justify-between items-start">
                 <div className={`w-10 h-10 rounded-lg flex items-center justify-center bg-white/5 border border-white/5 ${
                   plant.type.toLowerCase() === 'coal' ? 'text-rose-500' :
                   plant.type.toLowerCase() === 'nuclear' ? 'text-purple-500' :
                   'text-emerald-500'
                 }`}>
                    <Zap size={20} />
                 </div>
                 <button className="text-slate-700 hover:text-white transition-colors">
                    <MoreHorizontal size={18} />
                 </button>
              </div>

              <div className="flex flex-col gap-1">
                 <h3 className="text-sm font-bold text-white uppercase tracking-tight group-hover:text-blue-500 transition-colors">{plant.name}</h3>
                 <span className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">{plant.type} Generation node</span>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-4 border-t border-white/5">
                 <div className="flex flex-col gap-1">
                    <span className="text-[9px] font-bold text-slate-700 uppercase tracking-widest">Base Output</span>
                    <span className="text-xs font-bold text-slate-200 tabular-nums">{plant.max_mw} MW</span>
                 </div>
                 <div className="flex flex-col gap-1">
                    <span className="text-[9px] font-bold text-slate-700 uppercase tracking-widest">Unit Rate</span>
                    <span className="text-xs font-bold text-slate-200 tabular-nums">₹{plant.cost}/U</span>
                 </div>
              </div>

              <div className="flex items-center justify-between text-slate-700 pt-4 mt-auto">
                 <div className="flex items-center gap-2">
                    <MapPin size={12} />
                    <span className="text-[9px] font-bold uppercase tracking-widest">{plant.state}</span>
                 </div>
                 <ShieldCheck size={14} className="text-emerald-500/40 group-hover:text-emerald-500 transition-colors" />
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default PlantGrid;
