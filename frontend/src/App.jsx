import { useCallback, useEffect, useState } from 'react'

const api = async (path, options = {}) => {
  const res = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.status === 204 ? null : res.json()
}

export default function App() {
  const [tasks, setTasks] = useState([])
  const [source, setSource] = useState('')
  const [info, setInfo] = useState(null)
  const [title, setTitle] = useState('')
  const [error, setError] = useState('')

  const refresh = useCallback(async () => {
    try {
      const [list, inf] = await Promise.all([api('/tasks'), api('/info')])
      setTasks(list.tasks)
      setSource(list.source)
      setInfo(inf)
      setError('')
    } catch (e) {
      setError(e.message)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const run = (fn) => async (...args) => {
    try {
      await fn(...args)
      await refresh()
    } catch (e) {
      setError(e.message)
    }
  }

  const add = run(async (e) => {
    e.preventDefault()
    await api('/tasks', { method: 'POST', body: JSON.stringify({ title }) })
    setTitle('')
  })
  const toggle = run((id) => api(`/tasks/${id}`, { method: 'PATCH' }))
  const remove = run((id) => api(`/tasks/${id}`, { method: 'DELETE' }))

  return (
    <main>
      <h1>TaskBoard</h1>

      <form onSubmit={add}>
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Nouvelle tâche…" />
        <button disabled={!title.trim()}>Ajouter</button>
      </form>

      {error && <p className="error">API indisponible : {error}</p>}

      <ul>
        {tasks.map((t) => (
          <li key={t.id} className={t.done ? 'done' : ''}>
            <label>
              <input type="checkbox" checked={t.done} onChange={() => toggle(t.id)} />
              {t.title}
            </label>
            <button className="delete" onClick={() => remove(t.id)} aria-label="Supprimer">×</button>
          </li>
        ))}
      </ul>

      <footer>
        {info && (
          <>
            <span>Backend : <code>{info.hostname}</code></span>
            <span>Version : <code>{info.version}</code></span>
            <span>Visites : <code>{info.hits}</code></span>
            <span>Liste lue depuis : <code>{source}</code></span>
          </>
        )}
        <button onClick={refresh}>Rafraîchir</button>
      </footer>
    </main>
  )
}
