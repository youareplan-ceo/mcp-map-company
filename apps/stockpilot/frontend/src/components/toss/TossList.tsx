import React from 'react';
import './TossList.css';

interface TossListItemProps {
  title: string;
  subtitle?: string;
  value?: string | number;
  badge?: {
    text: string;
    variant: 'success' | 'warning' | 'error' | 'info';
  };
  onClick?: () => void;
}

interface TossListProps {
  items: TossListItemProps[];
  className?: string;
}

const TossList: React.FC<TossListProps> = ({ items, className = '' }) => {
  return (
    <div className={`toss-list ${className}`}>
      {items.map((item, index) => (
        <div 
          key={index}
          className="toss-list-item"
          onClick={item.onClick}
        >
          <div className="toss-list-item-content">
            <div className="toss-list-item-title">{item.title}</div>
            {item.subtitle && (
              <div className="toss-list-item-subtitle">{item.subtitle}</div>
            )}
          </div>
          <div className="toss-list-item-right">
            {item.value && (
              <div className="toss-list-item-value">{item.value}</div>
            )}
            {item.badge && (
              <span className={`toss-badge toss-badge-${item.badge.variant}`}>
                {item.badge.text}
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};

export default TossList;
