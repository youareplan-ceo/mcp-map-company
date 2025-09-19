import React from 'react';
import './TossButton.css';

interface TossButtonProps {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'outline';
  size?: 'small' | 'medium' | 'large';
  disabled?: boolean;
  loading?: boolean;
  onClick?: () => void;
  className?: string;
  type?: 'button' | 'submit' | 'reset';
}

const TossButton: React.FC<TossButtonProps> = ({
  children,
  variant = 'primary',
  size = 'medium',
  disabled = false,
  loading = false,
  onClick,
  className = '',
  type = 'button'
}) => {
  return (
    <button
      type={type}
      className={`toss-btn toss-btn-${variant} toss-btn-${size} ${className}`}
      disabled={disabled || loading}
      onClick={onClick}
    >
      {loading && <div className="toss-spinner" />}
      {!loading && children}
    </button>
  );
};

export default TossButton;
