import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'

// ✅ Replace Bootstrap with Lux Bootswatch theme
import "bootswatch/dist/lux/bootstrap.min.css";

createRoot(document.getElementById('root')!).render(
    <StrictMode>
        <App />
    </StrictMode>,
)
