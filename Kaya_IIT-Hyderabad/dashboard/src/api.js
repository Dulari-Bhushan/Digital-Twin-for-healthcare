const j = (r) => {
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
  return r.json()
}

export const getAlertEvidence = () => fetch('/api/alerts/evidence').then(j)
export const getPatients = () => fetch('/api/patients').then(j)
export const getPatient = (id) => fetch(`/api/patients/${id}`).then(j)
export const getSeries = (id, days = 3) => fetch(`/api/patients/${id}/series?days=${days}`).then(j)
export const postWhatIf = (id, body) =>
  fetch(`/api/patients/${id}/whatif`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(j)
export const getWhatIfMedicines = (id) => fetch(`/api/patients/${id}/whatif/medicines`).then(j)
export const getMessages = (id, lang) => fetch(`/api/patients/${id}/messages${lang ? `?lang=${lang}` : ''}`).then(j)
const post = async (url, body) => {
  const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined })
  if (!r.ok) { let m = `${r.status}`; try { m = (await r.json()).detail || m } catch (e) { /* not json */ } throw new Error(typeof m === 'string' ? m : 'Please check the form') }
  return r.json()
}
export const sendMessage = (id, body) => post(`/api/patients/${id}/messages`, body)
export const sendPrescription = (id, body) => post(`/api/patients/${id}/prescriptions`, body)
export const sendPatientMessage = (id, body, check = 'none') => post(`/api/patients/${id}/patient-messages`, { body, check })
export const checkContact = (id, body) => post(`/api/patients/${id}/contact-check`, body)
export const markHandled = (id) => post(`/api/patients/${id}/messages/handled`)
export const readMessage = (id, mid) => post(`/api/patients/${id}/messages/${mid}/read`)
export const getReports = (id) => fetch(`/api/patients/${id}/reports`).then(j)
export const getChanges = (id) => fetch(`/api/patients/${id}/changes`).then(j)
export const getUploads = (id) => fetch(`/api/patients/${id}/uploads`).then(j)
export const uploadReport = async (id, file, { title, category, date, read }) => {
  const r = await fetch(`/api/patients/${id}/uploads`, {
    method: 'POST',
    headers: { 'x-filename': encodeURIComponent(file.name), 'x-title': encodeURIComponent(title || ''), 'x-category': encodeURIComponent(category || 'other'), 'x-date': encodeURIComponent(date || ''), 'x-ocr': read ? '1' : '0' },
    body: file,
  })
  if (!r.ok) { let m = `${r.status}`; try { m = (await r.json()).detail || m } catch (e) { /* not json */ } throw new Error(m) }
  return r.json()
}
export const deleteUpload = (id, uid) => fetch(`/api/patients/${id}/uploads/${uid}`, { method: 'DELETE' }).then(j)
export const getLog = (id) => fetch(`/api/patients/${id}/log`).then(j)
export const postLog = (id, body) =>
  fetch(`/api/patients/${id}/log`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(j)
export const verifyUpload = (id, uid, verified = true) =>
  fetch(`/api/patients/${id}/uploads/${uid}/verify`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ verified }) }).then(j)
export const readUpload = (id, uid) => fetch(`/api/patients/${id}/uploads/${uid}/read`, { method: 'POST' }).then(j)
