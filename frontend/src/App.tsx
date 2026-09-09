import { Link, Route, Routes } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import LoginPage from './pages/LoginPage'
import SavedVenuesPage from './pages/SavedVenuesPage'
import SearchPage from './pages/SearchPage'
import SignupPage from './pages/SignupPage'

function Nav() {
  const { user, signOut } = useAuth()
  return (
    <header
      className="bg-teal px-5 pt-4 pb-3"
      style={{
        clipPath:
          'polygon(0 0,100% 0,100% 88%,96% 100%,92% 88%,88% 100%,84% 88%,80% 100%,76% 88%,72% 100%,68% 88%,64% 100%,60% 88%,56% 100%,52% 88%,48% 100%,44% 88%,40% 100%,36% 88%,32% 100%,28% 88%,24% 100%,20% 88%,16% 100%,12% 88%,8% 100%,4% 88%,0 100%)',
      }}
    >
      <div className="max-w-2xl mx-auto">
        <div className="flex items-baseline justify-between">
          <span className="font-display font-bold text-2xl tracking-wide text-white uppercase">
            Gig Finder
          </span>
        </div>
        <nav className="flex items-center gap-5 mt-3 font-display text-sm font-semibold uppercase tracking-wide">
          <Link to="/" className="text-white border-b-2 border-white/0 [&.active]:border-white pb-1">
            Search
          </Link>
          <Link to="/saved" className="text-white/80 hover:text-white pb-1">
            Saved
          </Link>
          <div className="ml-auto flex gap-4">
            {user ? (
              <button type="button" onClick={signOut} className="text-white/80 hover:text-white">
                Log out
              </button>
            ) : (
              <>
                <Link to="/login" className="text-white/80 hover:text-white">
                  Log in
                </Link>
                <Link to="/signup" className="text-white/80 hover:text-white">
                  Sign up
                </Link>
              </>
            )}
          </div>
        </nav>
      </div>
    </header>
  )
}

export default function App() {
  return (
    <div className="min-h-screen bg-cream-deep">
      <Nav />
      <Routes>
        <Route path="/" element={<SearchPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/saved" element={<SavedVenuesPage />} />
      </Routes>
    </div>
  )
}
