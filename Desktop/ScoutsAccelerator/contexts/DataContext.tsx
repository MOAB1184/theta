
import React, { createContext, ReactNode } from 'react';
import { Rank } from '../types';
import { useAuth } from '../hooks/useAuth';

interface DataContextType {
  ranks: Rank[];
  loading: boolean;
  error: string | null;
}

export const DataContext = createContext<DataContextType | undefined>(undefined);

// This provider now acts as a proxy, getting its data from the central AuthContext.
// This maintains the separation of concerns for components that only need to read
// rank data, without them needing to know about the entire authentication state.
export const DataProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { ranks, loading, error } = useAuth();

  return (
    <DataContext.Provider value={{
      ranks, 
      loading, 
      error
    }}>
      {children}
    </DataContext.Provider>
  );
};
