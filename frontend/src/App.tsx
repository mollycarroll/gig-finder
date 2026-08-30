import { Route, Routes } from 'react-router-dom'
import SearchPage from './pages/SearchPage'
import LoginPage from './pages/LoginPage'
import SignupPage from './pages/SignupPage'
import SavedVenuesPage from './pages/SavedVenuesPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<SearchPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route path="/saved" element={<SavedVenuesPage />} />
    </Routes>
  )
}
