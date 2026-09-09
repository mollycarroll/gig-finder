import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabaseClient'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    setLoading(false)
    if (error) {
      setError(error.message)
      return
    }
    navigate('/')
  }

  return (
    <div className="p-4 pt-10 max-w-sm mx-auto flex flex-col gap-5">
      <div className="flex bg-cream border border-line rounded-lg overflow-hidden">
        <span className="flex-1 text-center py-2.5 bg-ink text-white font-display font-semibold text-xs uppercase tracking-wide">
          Log in
        </span>
        <Link
          to="/signup"
          className="flex-1 text-center py-2.5 text-muted font-display font-semibold text-xs uppercase tracking-wide"
        >
          Sign up
        </Link>
      </div>
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <input
          type="email"
          placeholder="Email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="bg-cream border border-line rounded-lg px-3 py-2.5 text-sm placeholder:text-muted focus:outline-none focus:border-teal"
        />
        <input
          type="password"
          placeholder="Password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="bg-cream border border-line rounded-lg px-3 py-2.5 text-sm placeholder:text-muted focus:outline-none focus:border-teal"
        />
        {error && <p className="text-sm text-[#c26b5a]">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="px-4 py-2.5 rounded-lg bg-teal text-white font-display font-semibold text-sm uppercase tracking-wide disabled:opacity-50"
        >
          {loading ? 'Logging in...' : 'Log in'}
        </button>
      </form>
      <p className="text-center text-sm text-muted">
        New here?{' '}
        <Link to="/signup" className="text-teal-dark underline">
          Sign up
        </Link>
      </p>
    </div>
  )
}
