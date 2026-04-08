// Example: React + TypeScript SaaS Dashboard Component

import React, { useState } from 'react';

// Design System Tokens
const designSystem = {
  colors: {
    primary: '#E8B4B8',
    secondary: '#A8D5BA',
    cta: '#D4AF37',
    bg: '#FFF5F5',
    text: '#2D3436',
    error: '#E53935',
    success: '#43A047',
  },
  typography: {
    display: '"Cormorant Garamond", serif',
    body: '"Montserrat", sans-serif',
  },
  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
    '2xl': 48,
    '3xl': 64,
  },
  shadows: {
    sm: '0 2px 4px rgba(0, 0, 0, 0.05)',
    md: '0 4px 12px rgba(0, 0, 0, 0.1)',
    lg: '0 8px 16px rgba(0, 0, 0, 0.12)',
  },
};

// Button Component
interface ButtonProps {
  variant: 'primary' | 'secondary' | 'ghost';
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
}

const Button: React.FC<ButtonProps> = ({ variant, children, onClick, disabled }) => {
  const baseStyles: React.CSSProperties = {
    padding: `${designSystem.spacing.md}px ${designSystem.spacing.lg}px`,
    borderRadius: 12,
    fontWeight: 600,
    fontSize: 14,
    fontFamily: designSystem.typography.body,
    cursor: disabled ? 'not-allowed' : 'pointer',
    transition: 'all 300ms ease-in-out',
    border: 'none',
    opacity: disabled ? 0.5 : 1,
  };

  const variants = {
    primary: {
      ...baseStyles,
      background: designSystem.colors.cta,
      color: 'white',
    },
    secondary: {
      ...baseStyles,
      background: 'transparent',
      color: designSystem.colors.cta,
      border: `1px solid ${designSystem.colors.cta}`,
    },
    ghost: {
      ...baseStyles,
      background: 'transparent',
      color: designSystem.colors.text,
    },
  };

  return (
    <button
      style={variants[variant]}
      onClick={onClick}
      disabled={disabled}
      onMouseOver={(e) => {
        if (!disabled) {
          (e.target as HTMLElement).style.boxShadow = designSystem.shadows.lg;
          (e.target as HTMLElement).style.transform = 'translateY(-2px)';
        }
      }}
      onMouseOut={(e) => {
        (e.target as HTMLElement).style.boxShadow = 'none';
        (e.target as HTMLElement).style.transform = 'none';
      }}
    >
      {children}
    </button>
  );
};

// Card Component
interface CardProps {
  title: string;
  children: React.ReactNode;
}

const Card: React.FC<CardProps> = ({ title, children }) => (
  <div
    style={{
      background: 'white',
      borderRadius: 12,
      padding: designSystem.spacing.xl,
      boxShadow: designSystem.shadows.md,
      transition: 'all 300ms ease-in-out',
      cursor: 'default',
    }}
    onMouseOver={(e) => {
      (e.currentTarget as HTMLElement).style.boxShadow = designSystem.shadows.lg;
      (e.currentTarget as HTMLElement).style.transform = 'translateY(-4px)';
    }}
    onMouseOut={(e) => {
      (e.currentTarget as HTMLElement).style.boxShadow = designSystem.shadows.md;
      (e.currentTarget as HTMLElement).style.transform = 'none';
    }}
  >
    <h3
      style={{
        fontSize: 24,
        fontWeight: 600,
        marginBottom: designSystem.spacing.md,
        color: designSystem.colors.text,
        fontFamily: designSystem.typography.display,
      }}
    >
      {title}
    </h3>
    {children}
  </div>
);

// Dashboard Layout
const Dashboard: React.FC = () => {
  const [selectedTab, setSelectedTab] = useState<'overview' | 'analytics' | 'settings'>('overview');

  return (
    <div
      style={{
        fontFamily: designSystem.typography.body,
        color: designSystem.colors.text,
        background: designSystem.colors.bg,
        minHeight: '100vh',
      }}
    >
      {/* Header */}
      <header
        style={{
          position: 'sticky',
          top: 0,
          background: designSystem.colors.bg,
          boxShadow: designSystem.shadows.md,
          zIndex: 100,
          padding: `${designSystem.spacing.md}px 0`,
        }}
      >
        <div style={{ maxWidth: 1440, margin: '0 auto', padding: `0 ${designSystem.spacing.lg}px` }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <h1
              style={{
                fontSize: 28,
                fontWeight: 700,
                fontFamily: designSystem.typography.display,
                margin: 0,
              }}
            >
              Dashboard
            </h1>
            <div style={{ display: 'flex', gap: designSystem.spacing.xl }}>
              {['overview', 'analytics', 'settings'].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setSelectedTab(tab as any)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color:
                      selectedTab === tab
                        ? designSystem.colors.cta
                        : designSystem.colors.text,
                    cursor: 'pointer',
                    fontSize: 14,
                    fontWeight: selectedTab === tab ? 600 : 400,
                    borderBottom: selectedTab === tab ? `2px solid ${designSystem.colors.cta}` : 'none',
                    paddingBottom: designSystem.spacing.sm,
                    transition: 'color 300ms ease-in-out',
                  }}
                  onMouseOver={(e) => {
                    (e.target as HTMLElement).style.color = designSystem.colors.cta;
                  }}
                  onMouseOut={(e) => {
                    (e.target as HTMLElement).style.color =
                      selectedTab === tab ? designSystem.colors.cta : designSystem.colors.text;
                  }}
                >
                  {tab.charAt(0).toUpperCase() + tab.slice(1)}
                </button>
              ))}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main
        style={{
          maxWidth: 1440,
          margin: '0 auto',
          padding: designSystem.spacing.lg,
        }}
      >
        {selectedTab === 'overview' && (
          <div>
            <h2
              style={{
                fontSize: 32,
                fontWeight: 700,
                marginBottom: designSystem.spacing.lg,
                fontFamily: designSystem.typography.display,
              }}
            >
              Welcome Back
            </h2>

            {/* Stats Grid */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
                gap: designSystem.spacing['2xl'],
                marginBottom: designSystem.spacing['2xl'],
              }}
            >
              {[
                { label: 'Total Users', value: '12,405', change: '+12%' },
                { label: 'Revenue', value: '$45.2K', change: '+8%' },
                { label: 'Conversion', value: '3.2%', change: '+1.2%' },
                { label: 'Active Sessions', value: '2,341', change: '+5%' },
              ].map((stat) => (
                <Card key={stat.label} title={stat.label}>
                  <div
                    style={{
                      fontSize: 28,
                      fontWeight: 700,
                      color: designSystem.colors.cta,
                      marginBottom: designSystem.spacing.sm,
                    }}
                  >
                    {stat.value}
                  </div>
                  <div
                    style={{
                      fontSize: 12,
                      color: designSystem.colors.success,
                      fontWeight: 600,
                    }}
                  >
                    {stat.change} vs last month
                  </div>
                </Card>
              ))}
            </div>

            {/* Action Section */}
            <Card title="Quick Actions">
              <div style={{ display: 'flex', gap: designSystem.spacing.md }}>
                <Button variant="primary">Generate Report</Button>
                <Button variant="secondary">Export Data</Button>
                <Button variant="ghost">View Details</Button>
              </div>
            </Card>
          </div>
        )}

        {selectedTab === 'analytics' && (
          <Card title="Analytics">
            <p>Chart and analytics data would go here. Use design tokens for consistency.</p>
          </Card>
        )}

        {selectedTab === 'settings' && (
          <Card title="Settings">
            <p>Settings and preferences would go here.</p>
          </Card>
        )}
      </main>
    </div>
  );
};

export default Dashboard;
