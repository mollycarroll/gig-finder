import { Link, Route, Routes } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import LoginPage from './pages/LoginPage'
import SavedVenuesPage from './pages/SavedVenuesPage'
import SearchPage from './pages/SearchPage'
import SignupPage from './pages/SignupPage'

function Nav() {
  const { user, signOut } = useAuth()
  return (
    <nav className="flex items-center gap-4 p-4 border-b border-gray-200">
      <Link to="/">Search</Link>
      <Link to="/saved">Saved</Link>
      <div className="ml-auto flex gap-4">
        {user ? (
          <button type="button" onClick={signOut}>
            Log out
          </button>
        ) : (
          <>
            <Link to="/login">Log in</Link>
            <Link to="/signup">Sign up</Link>
          </>
        )}
      </div>
    </nav>
  )
}

export default function App() {
  return (
    <>
      <Nav />
      <Routes>
        <Route path="/" element={<SearchPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/saved" element={<SavedVenuesPage />} />
      </Routes>
    </>
  )
}
