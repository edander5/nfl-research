import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { App } from './App';
import './styles.css';
const client = new QueryClient({ defaultOptions: { queries: { staleTime: 60_000, retry: false } } });
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><QueryClientProvider client={client}><BrowserRouter><a className="skip-link" href="#main">Skip to content</a><App /></BrowserRouter></QueryClientProvider></React.StrictMode>);
