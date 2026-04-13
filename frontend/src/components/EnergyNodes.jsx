import React from 'react';
import { motion } from 'framer-motion';

const EnergyNodes = () => {
  const nodes = [
    { x: '10%', y: '20%', delay: 0 },
    { x: '85%', y: '15%', delay: 1.2 },
    { x: '15%', y: '80%', delay: 0.8 },
    { x: '90%', y: '75%', delay: 2.1 },
    { x: '50%', y: '40%', delay: 1.5 },
  ];

  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden opacity-20">
      <svg className="w-full h-full">
        {/* Dynamic Connections */}
        <motion.path
          d="M 100 150 L 900 100 L 850 600 L 150 700 Z"
          fill="none"
          stroke="rgba(59, 130, 246, 0.2)"
          strokeWidth="1"
          strokeDasharray="10 10"
          animate={{
            strokeDashoffset: [0, -100]
          }}
          transition={{
            duration: 20,
            repeat: Infinity,
            ease: "linear"
          }}
        />
        
        {nodes.map((node, i) => (
          <g key={i}>
            <motion.circle
              cx={node.x}
              cy={node.y}
              r="2"
              fill="#3b82f6"
              animate={{
                scale: [1, 2, 1],
                opacity: [0.3, 0.8, 0.3]
              }}
              transition={{
                duration: 3 + Math.random() * 2,
                delay: node.delay,
                repeat: Infinity
              }}
            />
            <motion.circle
              cx={node.x}
              cy={node.y}
              r="15"
              fill="none"
              stroke="#3b82f6"
              strokeWidth="0.5"
              animate={{
                scale: [0.5, 1.5],
                opacity: [0.5, 0]
              }}
              transition={{
                duration: 4,
                delay: node.delay,
                repeat: Infinity
              }}
            />
          </g>
        ))}
      </svg>
    </div>
  );
};

export default EnergyNodes;
