import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import AuthProvider from './auth/AuthProvider'

async function enableMocking() {
  if (import.meta.env.DEV) {
    const { worker } = await import('./mocks/browser')

    return worker.start()
  }
}

enableMocking().then(() => {
  createRoot(document.getElementById('root')).render(
    <AuthProvider>
      <App />
    </AuthProvider>
  )
})
