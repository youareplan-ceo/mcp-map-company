import React from 'react';
import './TossCard.css';

interface TossCardProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
  gradient?: boolean;
}

const TossCard: React.FC<TossCardProps> = ({ 
  children, 
  className = '', 
  onClick,
  gradient = false 
}) => {
  return (
    <div 
      className={`toss-card ${gradient ? 'toss-chart-card' : ''} ${className}`}
      onClick={onClick}
    >
      {children}
    </div>
  );
};

export default TossCard;
