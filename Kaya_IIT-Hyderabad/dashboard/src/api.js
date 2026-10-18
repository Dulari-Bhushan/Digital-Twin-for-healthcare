const j = (r) => {
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
  return r.json()
}

export const getPatients = () => fetch('/api/patients').then(j)
export const getPatient = (id) => fetch(`/api/patients/${id}`).then(j)
export const getSeries = (id, days = 3) => fetch(`/api/patients/${id}/series?days=${days}`).then(j)
export const postWhatIf = (id, body) =>
  fetch(`/api/patients/${id}/whatif`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(j)
export const getReports = (id) => fetch(`/api/patients/${id}/reports`).then(j)
export const getChanges = (id) => fetch(`/api/patients/${id}/changes`).then(j)
