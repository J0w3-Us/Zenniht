// Must stay first: it initializes crypto.randomUUID before imported modules use it.
import './lib/polyfills';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { ErrorBoundary } from './components/ErrorBoundary';
import { ZenitPage } from './pages/ZenitPage';
import './index.css';

const requestedPath = window.location.pathname.replace(/\/+$/, '') || '/';
if (requestedPath !== '/zenit') {
  window.history.replaceState(
    null,
    '',
    `/zenit${window.location.search}${window.location.hash}`,
  );
}

document.documentElement.lang = 'es';
document.title = 'ZENIT | La Esperanza';

const root = createRoot(document.getElementById('root')!);
root.render(
  <StrictMode>
    <ErrorBoundary>
      <ZenitPage />
    </ErrorBoundary>
  </StrictMode>,
);
