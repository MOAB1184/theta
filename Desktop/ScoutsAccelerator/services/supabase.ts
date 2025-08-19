
import { createClient } from '@supabase/supabase-js';
import { Database } from './database.types';

// Use the new Supabase credentials provided by the user.
const supabaseUrl = 'https://npxjhxyhcsswusndxnvn.supabase.co';
const supabaseAnonKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5weGpoeHloY3Nzd3VzbmR4bnZuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTI2MjI2MTQsImV4cCI6MjA2ODE5ODYxNH0.aBBf65WDv3t9iSSH-AZO6x_4iJzY31LoekxZmPyDxDY';

// Initialize the Supabase client with the provided credentials and generated types.
export const supabase = createClient<Database>(supabaseUrl, supabaseAnonKey);
