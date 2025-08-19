
import React, { useState } from 'react';
import { NavLink, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export const Header: React.FC = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    setIsMenuOpen(false);
    await logout();
    navigate('/');
  };

  const navLinkClass = "text-text-secondary hover:text-text-primary transition duration-300 px-3 py-2 rounded-md text-sm font-medium";
  const activeNavLinkClass = "text-text-primary font-semibold";
  
  const getNavLinkStyle = ({ isActive }: { isActive: boolean }) => isActive ? `${navLinkClass} ${activeNavLinkClass}` : navLinkClass;
  
  const handleNavClick = () => {
    setIsMenuOpen(false);
  }

  const ProfessionalLogo = () => (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="text-accent">
      <path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M16.24 7.76L14.12 14.12L7.76 16.24L9.88 9.88L16.24 7.76Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );

  return (
    <header className="bg-primary/80 backdrop-blur-md border-b border-border-color sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center">
            <Link to={user ? "/dashboard" : "/"} className="flex-shrink-0 flex items-center gap-2">
              <ProfessionalLogo />
              <span className="font-bold text-xl text-text-primary">Scout<span className="text-accent">Accelerator</span></span>
            </Link>
            <div className="hidden md:block">
                <div className="ml-10 flex items-baseline space-x-4">
                  {user ? (
                    <>
                      {user.role === 'scout' && <NavLink to="/advancement" className={getNavLinkStyle}>Advancement</NavLink>}
                      {(user.role === 'scout' || user.role === 'scoutmaster') && <NavLink to="/signoffs" className={getNavLinkStyle}>Sign-offs</NavLink>}
                      {user.role === 'scoutmaster' && <NavLink to="/scoutmaster" className={getNavLinkStyle}>Scoutmaster</NavLink>}
                      {user.role === 'admin' && <NavLink to="/admin" className={getNavLinkStyle}>Admin</NavLink>}
                    </>
                  ) : (
                    <>
                      <a href="/#features" className={navLinkClass}>Features</a>
                      <a href="/#how-it-works" className={navLinkClass}>How It Works</a>
                      <a href="/#faq" className={navLinkClass}>FAQ</a>
                    </>
                  )}
                </div>
            </div>
          </div>
          <div className="hidden md:block">
            <div className="ml-4 flex items-center md:ml-6">
                {user ? (
                    <div className="flex items-center gap-4">
                        <span className="text-text-secondary text-sm" title={user.email}>{user.email}</span>
                        <button onClick={handleLogout} className="text-sm font-medium text-text-secondary hover:text-text-primary transition-colors">Logout</button>
                    </div>
                ) : (
                    <div className="flex items-center gap-4">
                        <NavLink to="/login" className={navLinkClass}>Login</NavLink>
                        <NavLink to="/signup" className="bg-accent text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-accent-hover transition-all duration-300 shadow-[0_0_15px_theme(colors.accent/0.4)]">
                            Sign Up
                        </NavLink>
                    </div>
                )}
            </div>
          </div>
          <div className="-mr-2 flex md:hidden">
            <button onClick={() => setIsMenuOpen(!isMenuOpen)} type="button" className="bg-secondary inline-flex items-center justify-center p-2 rounded-md text-text-secondary hover:text-text-primary hover:bg-primary focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-primary focus:ring-accent" aria-controls="mobile-menu" aria-expanded="false">
              <span className="sr-only">Open main menu</span>
              {isMenuOpen ? (
                <svg className="block h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
              ) : (
                <svg className="block h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" /></svg>
              )}
            </button>
          </div>
        </div>
      </div>

      {isMenuOpen && (
        <div className="md:hidden" id="mobile-menu">
          <div className="px-2 pt-2 pb-3 space-y-1 sm:px-3">
            {user ? (
              <>
                {user.role === 'scout' && <NavLink to="/advancement" onClick={handleNavClick} className="block text-text-secondary hover:text-text-primary px-3 py-2 rounded-md text-base font-medium">Advancement</NavLink>}
                {(user.role === 'scout' || user.role === 'scoutmaster') && <NavLink to="/signoffs" onClick={handleNavClick} className="block text-text-secondary hover:text-text-primary px-3 py-2 rounded-md text-base font-medium">Sign-offs</NavLink>}
                 {user.role === 'scoutmaster' && <NavLink to="/scoutmaster" onClick={handleNavClick} className="block text-text-secondary hover:text-text-primary px-3 py-2 rounded-md text-base font-medium">Scoutmaster</NavLink>}
                 {user.role === 'admin' && <NavLink to="/admin" onClick={handleNavClick} className="block text-text-secondary hover:text-text-primary px-3 py-2 rounded-md text-base font-medium">Admin</NavLink>}
              </>
            ) : (
              <>
                <a href="/#features" onClick={handleNavClick} className="block text-text-secondary hover:text-text-primary px-3 py-2 rounded-md text-base font-medium">Features</a>
                <a href="/#how-it-works" onClick={handleNavClick} className="block text-text-secondary hover:text-text-primary px-3 py-2 rounded-md text-base font-medium">How It Works</a>
                <a href="/#faq" onClick={handleNavClick} className="block text-text-secondary hover:text-text-primary px-3 py-2 rounded-md text-base font-medium">FAQ</a>
              </>
            )}

            <div className="border-t border-border-color my-2"></div>
            {user ? (
                <>
                    <div className="px-3 py-2">
                        <p className="text-base font-medium text-text-primary truncate">{user.email}</p>
                    </div>
                    <button onClick={handleLogout} className="w-full text-left block text-text-secondary hover:text-text-primary px-3 py-2 rounded-md text-base font-medium">Logout</button>
                </>
            ) : (
                <>
                    <NavLink to="/login" onClick={handleNavClick} className="block text-text-secondary hover:text-text-primary px-3 py-2 rounded-md text-base font-medium">Login</NavLink>
                    <NavLink to="/signup" onClick={handleNavClick} className="block text-text-secondary hover:text-text-primary px-3 py-2 rounded-md text-base font-medium">Sign Up</NavLink>
                </>
            )}
          </div>
        </div>
      )}
    </header>
  );
};