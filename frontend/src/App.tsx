import { useEffect, type ReactNode } from 'react'
import {
  NavLink,
  Navigate,
  Outlet,
  Route,
  Routes,
  useLocation,
} from 'react-router-dom'
import { ChatIcon, HomeIcon, PulseIcon, TrendIcon } from './components/icons'
import { AuthProvider, useAuth } from './auth'
import Home from './pages/Home'
import Risk from './pages/Risk'
import Weight from './pages/Weight'
import Chat from './pages/Chat'
import Login from './pages/Login'

const NAV = [
  { to: '/', label: 'Home', icon: HomeIcon, end: true },
  { to: '/risk', label: 'Risk check', icon: PulseIcon, end: false },
  { to: '/weight', label: 'Weight', icon: TrendIcon, end: false },
  { to: '/chat', label: 'Assistant', icon: ChatIcon, end: false },
]

const TITLES: Record<string, string> = {
  '/': 'Home',
  '/risk': 'Risk assessment',
  '/weight': 'Weight tracker',
  '/chat': 'Health assistant',
}

function BrandMark() {
  return <span className="brand-mark">P</span>
}

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])
  return null
}

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="app-loading">
        <span className="spinner" />
      </div>
    )
  }
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return <>{children}</>
}

function Layout() {
  const { pathname } = useLocation()
  const { user, logout } = useAuth()
  const title = TITLES[pathname] ?? 'PCOS Care'

  return (
    <div className="app">
      <ScrollToTop />
      <aside className="sidebar">
        <div className="brand">
          <BrandMark />
          <span className="brand-name">PCOS Care</span>
        </div>
        <nav className="side-nav" aria-label="Primary">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
            >
              <Icon size={20} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        {user && (
          <div className="sidebar-account">
            <span className="account-email" title={user.email}>
              {user.email}
            </span>
            <button className="btn btn-ghost logout-btn" onClick={() => void logout()}>
              Log out
            </button>
          </div>
        )}
        <p className="sidebar-foot">
          Educational support only — always confirm diagnosis with a clinician.
        </p>
      </aside>

      <div className="main">
        <header className="topbar">
          <div className="topbar-brand">
            <BrandMark />
          </div>
          <h1 className="topbar-title">{title}</h1>
          {user && (
            <button className="btn btn-ghost topbar-logout" onClick={() => void logout()}>
              Log out
            </button>
          )}
        </header>

        <main className="content">
          <Outlet />
        </main>

        <nav className="bottom-nav" aria-label="Primary">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => `bottom-nav-item${isActive ? ' active' : ''}`}
            >
              <Icon size={22} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          element={
            <RequireAuth>
              <Layout />
            </RequireAuth>
          }
        >
          <Route path="/" element={<Home />} />
          <Route path="/risk" element={<Risk />} />
          <Route path="/weight" element={<Weight />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </AuthProvider>
  )
}
