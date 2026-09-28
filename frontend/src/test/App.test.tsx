import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import App from '../App'
import { AuthProvider } from '../auth'

// Mock the API module so tests don't hit the network.
vi.mock('../api', async () => {
  const actual = await vi.importActual<typeof import('../api')>('../api')
  return {
    ...actual,
    getToken: () => null,
    api: {
      listServices: vi.fn().mockResolvedValue([]),
      listStylists: vi.fn().mockResolvedValue([]),
      me: vi.fn().mockRejectedValue(new Error('no auth')),
    },
  }
})

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('App shell', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('renders the brand and booking heading', async () => {
    renderAt('/')
    expect(screen.getByText('✂️ Salon')).toBeInTheDocument()
    await waitFor(() =>
      expect(
        screen.getByRole('heading', { name: /book an appointment/i }),
      ).toBeInTheDocument(),
    )
  })

  it('redirects unauthenticated users away from /history to /login', async () => {
    renderAt('/history')
    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /login/i })).toBeInTheDocument(),
    )
  })
})
