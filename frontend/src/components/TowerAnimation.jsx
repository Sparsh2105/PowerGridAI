import React from 'react';
import { motion } from 'framer-motion';

const TowerAnimation = ({ active = true }) => {
  return (
    <div className="relative w-[120px] h-[180px] flex items-center justify-center">
      {/* Glow Backdrop */}
      <div className="absolute inset-0 bg-accent-blue/10 blur-[40px] rounded-full pulse-glow"></div>
      
      <svg viewBox="0 0 100 150" className="w-full h-full relative z-10 overflow-visible">
        {/* Tower Structure */}
        <path 
          d="M20 140 L45 10 L55 10 L80 140" 
          fill="none" 
          stroke="rgba(255,255,255,0.2)" 
          strokeWidth="2.5" 
          strokeLinecap="round"
        />
        <path 
          d="M30 140 L70 140 M32 100 L68 100 M38 60 L62 60 M43 30 L57 30" 
          fill="none" 
          stroke="rgba(255,255,255,0.15)" 
          strokeWidth="1.5" 
        />
        <path 
          d="M20 140 L50 100 L80 140 M30 100 L50 60 L70 100" 
          fill="none" 
          stroke="rgba(255,255,255,0.1)" 
          strokeWidth="1" 
        />

        {/* Insulators */}
        <circle cx="20" cy="140" r="2" fill="#3b82f6" />
        <circle cx="80" cy="140" r="2" fill="#3b82f6" />
        <circle cx="32" cy="100" r="2" fill="#3b82f6" />
        <circle cx="68" cy="100" r="2" fill="#3b82f6" />

        {/* Power Lines Pulse */}
        <AnimatePresence>
          {active && (
            <motion.g
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              {/* High Voltage Lines */}
              <motion.path
                d="M45 10 L-50 50 M55 10 L150 50"
                fill="none"
                stroke="rgba(6, 182, 212, 0.4)"
                strokeWidth="1.5"
                strokeDasharray="10 15"
                className="tower-line"
              />
              <motion.path
                d="M32 100 L-50 130 M68 100 L150 130"
                fill="none"
                stroke="rgba(59, 130, 246, 0.3)"
                strokeWidth="1.5"
                strokeDasharray="8 12"
                className="tower-line"
              />

              {/* Top Beacon */}
              <motion.circle
                cx="50"
                cy="10"
                r="4"
                fill="#3b82f6"
                animate={{
                  opacity: [0.3, 1, 0.3],
                  scale: [1, 1.3, 1]
                }}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  ease: "easeInOut"
                }}
              />
            </motion.g>
          )}
        </AnimatePresence>
      </svg>
    </div>
  );
};

const AnimatePresence = ({ children }) => <>{children}</>;

export default TowerAnimation;
