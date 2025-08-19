
import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { UserRole } from '../types';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: UserRole[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles }) => {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return null; // or a loading spinner
  }

  if (!user) {
    // Redirect to login, saving the intended location
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (!user.role && location.pathname !== '/onboarding') {
    // If user is logged in but hasn't completed onboarding, force them to that page.
    return <Navigate to="/onboarding" replace />;
  }
  
  if (user.role && location.pathname === '/onboarding') {
    // If user has a role, don't let them go back to onboarding.
    return <Navigate to="/dashboard" replace />;
  }
  
  if (allowedRoles && user.role && !allowedRoles.includes(user.role)) {
    // User does not have the required role, redirect to their dashboard.
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
};
